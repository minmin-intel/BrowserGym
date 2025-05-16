#!/usr/bin/env python3
"""
Server for running a Playwright browser sandbox with API endpoints for browser actions.
"""

import asyncio
import os
from typing import Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import uvicorn

# Import DOM snapshot and AX tree handlers
from dom_snapshot_handler import extract_dom_snapshot, extract_text_content
from axtree_handler import extract_merged_axtree, extract_all_frame_axtrees

app = FastAPI(title="Playwright Browser Sandbox")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to store browser instances
browser_pool: Dict[str, Browser] = {}
context_pool: Dict[str, BrowserContext] = {}
page_pool: Dict[str, Page] = {}

# Models for request bodies
class BrowserConfig(BaseModel):
    headless: bool = os.environ.get("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
    width: int = 1280
    height: int = 720
    device_scale_factor: float = 1.0
    user_agent: Optional[str] = None

class NavigateRequest(BaseModel):
    url: str
    timeout: int = 3000
    wait_until: str = "networkidle"  # load, domcontentloaded, networkidle

class ClickRequest(BaseModel):
    selector: str
    button: str = "left"  # left, right, middle
    click_count: int = 1
    delay: int = 0
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    timeout: int = 3000

class TypeRequest(BaseModel):
    selector: str
    text: str
    delay: int = 0
    timeout: int = 3000

class GetByLabelFillRequest(BaseModel):
    label: str
    text: str
    exact: bool = True
    timeout: int = 3000

class WaitForSelectorRequest(BaseModel):
    selector: str
    state: str = "visible"  # attached, detached, visible, hidden
    timeout: int = 3000

class EvaluateRequest(BaseModel):
    expression: str
    arg: Optional[Dict] = None

class ScreenshotRequest(BaseModel):
    full_page: bool = False
    path: Optional[str] = None
    selector: Optional[str] = None
    timeout: int = 60000  # Default timeout of 60 seconds

class DOMSnapshotRequest(BaseModel):
    computed_styles: List[str] = []
    include_dom_rects: bool = True
    include_paint_order: bool = True
    extract_text: bool = False
    
class AXTreeRequest(BaseModel):
    extract_browsergym_ids: bool = True
    
class ClickableElementsRequest(BaseModel):
    include_disabled: bool = False
    include_hidden: bool = False
    timeout: int = 3000
    
@app.on_event("startup")
async def startup_event():
    """Initialize the Playwright instance."""
    global playwright
    playwright = await async_playwright().start()


@app.on_event("shutdown")
async def shutdown_event():
    """Close all browser instances and the Playwright instance."""
    for browser_id in list(browser_pool.keys()):
        await close_browser(browser_id)
    await playwright.stop()


@app.post("/browser/launch", response_model=Dict[str, str])
async def launch_browser(config: BrowserConfig):
    """Launch a new browser instance."""
    try:
        # Add additional launch options for better container compatibility
        launch_options = {
            "headless": config.headless,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        }
        browser = await playwright.chromium.launch(**launch_options)
        browser_id = str(id(browser))
        browser_pool[browser_id] = browser
        return {"browser_id": browser_id, "status": "launched"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to launch browser: {str(e)}")


@app.post("/browser/{browser_id}/context", response_model=Dict[str, str])
async def create_context(browser_id: str, config: BrowserConfig):
    """Create a new browser context."""
    if browser_id not in browser_pool:
        raise HTTPException(status_code=404, detail="Browser not found")
    
    try:
        browser = browser_pool[browser_id]
        viewport = {"width": config.width, "height": config.height, "deviceScaleFactor": config.device_scale_factor}
        context_options = {"viewport": viewport}
        
        if config.user_agent:
            context_options["userAgent"] = config.user_agent
            
        context = await browser.new_context(**context_options)
        context_id = str(id(context))
        context_pool[context_id] = context
        return {"context_id": context_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create context: {str(e)}")


@app.post("/context/{context_id}/page", response_model=Dict[str, str])
async def create_page(context_id: str):
    """Create a new page in a browser context."""
    if context_id not in context_pool:
        raise HTTPException(status_code=404, detail="Browser context not found")
    
    try:
        context = context_pool[context_id]
        page = await context.new_page()
        page_id = str(id(page))
        page_pool[page_id] = page
        return {"page_id": page_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create page: {str(e)}")


@app.post("/page/{page_id}/navigate", response_model=Dict)
async def navigate(page_id: str, request: NavigateRequest):
    """Navigate to a URL."""
    if page_id not in page_pool:
        raise HTTPException(status_code=404, detail="Page not found")
    
    try:
        page = page_pool[page_id]
        response = await page.goto(
            request.url, 
            timeout=request.timeout,
            wait_until=request.wait_until
        )
        
        result = {
            "status": "success", 
            "url": page.url
        }
        
        if response:
            result["status_code"] = response.status
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Navigation failed: {str(e)}")


@app.post("/page/{page_id}/click", response_model=Dict)
async def click(page_id: str, request: ClickRequest):
    """Click on an element matching the selector."""
    if page_id not in page_pool:
        raise HTTPException(status_code=404, detail="Page not found")
    
    try:
        page = page_pool[page_id]
        options = {
            "button": request.button,
            # "clickCount": request.click_count,
            "delay": request.delay,
            "timeout": request.timeout,
        }
        
        if request.position_x is not None and request.position_y is not None:
            options["position"] = {"x": request.position_x, "y": request.position_y}
            
        await page.click(request.selector, **options)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Click failed: {str(e)}")


@app.post("/page/{page_id}/type", response_model=Dict)
async def type_text(page_id: str, request: TypeRequest):
    """Type text into an element matching the selector."""
    if page_id not in page_pool:
        raise HTTPException(status_code=404, detail="Page not found")
    
    try:
        page = page_pool[page_id]
        await page.fill(request.selector, request.text, timeout=request.timeout)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Type operation failed: {str(e)}")


@app.post("/page/{page_id}/get_by_label_fill", response_model=Dict)
async def get_by_label_fill(page_id: str, request: GetByLabelFillRequest):
    """Find an element by its label text and fill it with the provided text."""
    if page_id not in page_pool:
        raise HTTPException(status_code=404, detail="Page not found")
    
    try:
        page = page_pool[page_id]
        locator = page.get_by_label(request.label, exact=request.exact)
        await locator.fill(request.text, timeout=request.timeout)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get by label and fill operation failed: {str(e)}")


class GetByRoleClickRequest(BaseModel):
    role: str
    name: Optional[str] = None
    exact: bool = True
    timeout: int = 3000


@app.post("/page/{page_id}/get_by_role_click", response_model=Dict)
async def get_by_role_click(page_id: str, request: GetByRoleClickRequest):
    """Find an element by its ARIA role and name, and click on it."""
    if page_id not in page_pool:
        raise HTTPException(status_code=404, detail="Page not found")
    
    try:
        page = page_pool[page_id]
        options = {}
        if request.name is not None:
            options["name"] = request.name
            options["exact"] = request.exact
            
        locator = page.get_by_role(request.role, **options)
        await locator.click(timeout=request.timeout)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get by role and click operation failed: {str(e)}")


@app.post("/page/{page_id}/wait_for_selector", response_model=Dict)
async def wait_for_selector(page_id: str, request: WaitForSelectorRequest):
    """Wait for an element matching the selector to appear in the page."""
    if page_id not in page_pool:
        raise HTTPException(status_code=404, detail="Page not found")
    
    try:
        page = page_pool[page_id]
        await page.wait_for_selector(request.selector, state=request.state, timeout=request.timeout)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Wait for selector failed: {str(e)}")


@app.post("/page/{page_id}/evaluate", response_model=Dict)
async def evaluate(page_id: str, request: EvaluateRequest):
    """Evaluate JavaScript in the page context."""
    if page_id not in page_pool:
        raise HTTPException(status_code=404, detail="Page not found")
    
    try:
        page = page_pool[page_id]
        arg = request.arg if request.arg else None
        result = await page.evaluate(request.expression, arg)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluate failed: {str(e)}")


@app.post("/page/{page_id}/screenshot", response_model=Dict)
async def screenshot(page_id: str, request: ScreenshotRequest):
    """Take a screenshot of the page."""
    if page_id not in page_pool:
        raise HTTPException(status_code=404, detail="Page not found")
    
    try:
        page = page_pool[page_id]
        # Add timeout to options and increase it for container environments
        options = {
            "full_page": request.full_page,
            "timeout": 30000  # Increase timeout to 60 seconds
        }
        
        if request.path:
            options["path"] = request.path
            
        # Make sure the page is ready for screenshot by checking document state
        await page.evaluate("() => document.readyState === 'complete'")
        
        # Add a wait for the page to be sure it's fully loaded
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            # If timeout waiting for networkidle, continue anyway
            pass
            
        if request.selector:
            element = await page.query_selector(request.selector)
            if element:
                screenshot_bytes = await element.screenshot(**options)
            else:
                raise HTTPException(status_code=404, detail="Element not found")
        else:
            screenshot_bytes = await page.screenshot(**options)
            
        # Return the base64 encoded screenshot if no path was provided
        import base64
        if not request.path:
            encoded = base64.b64encode(screenshot_bytes).decode('utf-8')
            return {"status": "success", "screenshot": encoded}
        return {"status": "success", "path": request.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screenshot failed: {str(e)}")


@app.post("/page/{page_id}/close")
async def close_page(page_id: str):
    """Close a page."""
    if page_id not in page_pool:
        raise HTTPException(status_code=404, detail="Page not found")
    
    try:
        page = page_pool[page_id]
        await page.close()
        del page_pool[page_id]
        return {"status": "closed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close page: {str(e)}")


@app.post("/context/{context_id}/close")
async def close_context(context_id: str):
    """Close a browser context."""
    if context_id not in context_pool:
        raise HTTPException(status_code=404, detail="Browser context not found")
    
    try:
        context = context_pool[context_id]
        await context.close()
        del context_pool[context_id]
        return {"status": "closed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close context: {str(e)}")


@app.post("/browser/{browser_id}/close")
async def close_browser(browser_id: str):
    """Close a browser instance."""
    if browser_id not in browser_pool:
        raise HTTPException(status_code=404, detail="Browser not found")
    
    try:
        browser = browser_pool[browser_id]
        await browser.close()
        del browser_pool[browser_id]
        return {"status": "closed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close browser: {str(e)}")


@app.post("/page/{page_id}/accessibility_snapshot", response_model=Dict)
async def accessibility_snapshot(page_id: str):
    """Get the accessibility tree snapshot of the current page."""
    if page_id not in page_pool:
        raise HTTPException(status_code=404, detail="Page not found")
    
    try:
        page = page_pool[page_id]
        # Get the accessibility snapshot using Playwright's accessibility API
        snapshot = await page.accessibility.snapshot()
        return {"status": "success", "snapshot": snapshot}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get accessibility snapshot: {str(e)}")


@app.post("/page/{page_id}/dom_snapshot", response_model=Dict)
async def get_dom_snapshot(page_id: str, request: DOMSnapshotRequest):
    """Get the DOM snapshot of the current page using Chrome DevTools Protocol."""
    if page_id not in page_pool:
        raise HTTPException(status_code=404, detail="Page not found")
    
    try:
        page = page_pool[page_id]
        # Get the DOM snapshot using Chrome DevTools Protocol
        snapshot = await page.context.new_cdp_session(page)
        dom_snapshot = await snapshot.send(
            "DOMSnapshot.captureSnapshot",
            {
                "computedStyles": request.computed_styles,
                "includeDOMRects": request.include_dom_rects,
                "includePaintOrder": request.include_paint_order,
            }
        )
        await snapshot.detach()
        
        # Extract text content if requested
        text_content = []
        if request.extract_text:
            text_content = extract_text_content(dom_snapshot)
            
        return {
            "status": "success", 
            "snapshot": dom_snapshot,
            "text_content": text_content if request.extract_text else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get DOM snapshot: {str(e)}")


@app.post("/page/{page_id}/merged_axtree", response_model=Dict)
async def get_merged_axtree(page_id: str, request: AXTreeRequest):
    """Get the merged AXTree of the current page using Chrome DevTools Protocol."""
    if page_id not in page_pool:
        raise HTTPException(status_code=404, detail="Page not found")
    
    try:
        page = page_pool[page_id]
        # Get the merged AXTree
        merged_axtree = await extract_merged_axtree(page)
        
        return {
            "status": "success", 
            "axtree": merged_axtree
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get merged AXTree: {str(e)}")


@app.post("/page/{page_id}/frame_axtrees", response_model=Dict)
async def get_frame_axtrees(page_id: str, request: AXTreeRequest):
    """Get the AXTrees of all frames in the current page using Chrome DevTools Protocol."""
    if page_id not in page_pool:
        raise HTTPException(status_code=404, detail="Page not found")
    
    try:
        page = page_pool[page_id]
        # Get the frame AXTrees
        frame_axtrees = await extract_all_frame_axtrees(page)
        
        return {
            "status": "success", 
            "frame_axtrees": frame_axtrees
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get frame AXTrees: {str(e)}")


@app.post("/page/{page_id}/clickable_elements", response_model=Dict)
async def get_clickable_elements(page_id: str, request: ClickableElementsRequest):
    """Get all clickable elements and their URLs from the current page."""
    if page_id not in page_pool:
        raise HTTPException(status_code=404, detail="Page not found")
    
    try:
        page = page_pool[page_id]
        
        # Define JavaScript expression to extract all clickable elements
        js_expression = """
        () => {
            // Helper function to check if element is visible
            function isElementVisible(element) {
                if (!element) return false;
                
                // Check if element or any ancestor has display:none or visibility:hidden
                function isVisible(el) {
                    if (!el) return true;
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && 
                           style.visibility !== 'hidden' && 
                           style.opacity !== '0' &&
                           isVisible(el.parentElement);
                }
                
                // Check if element is in viewport
                function isInViewport(el) {
                    const rect = el.getBoundingClientRect();
                    return (
                        rect.width > 0 &&
                        rect.height > 0 &&
                        rect.top >= 0 &&
                        rect.left >= 0 &&
                        rect.top <= (window.innerHeight || document.documentElement.clientHeight) &&
                        rect.left <= (window.innerWidth || document.documentElement.clientWidth)
                    );
                }
                
                return isVisible(element) && isInViewport(element);
            }
            
            // Process an element and extract its properties
            function processElement(element, index) {
                // Get element attributes
                const tagName = element.tagName.toLowerCase();
                const id = element.id;
                const classList = Array.from(element.classList);
                const href = element.href || null;
                const text = element.innerText || element.textContent || '';
                const ariaLabel = element.getAttribute('aria-label') || null;
                const title = element.getAttribute('title') || null;
                const role = element.getAttribute('role') || null;
                const disabled = element.disabled || element.getAttribute('aria-disabled') === 'true' || false;
                const visible = isElementVisible(element);
                
                // Calculate selectors for this element (multiple options)
                let selectors = [];
                
                // ID selector (most specific)
                if (id) {
                    selectors.push(`#${id}`);
                }
                
                // Class selector
                if (classList.length > 0) {
                    selectors.push(`${tagName}.${classList.join('.')}`);
                }
                
                // Attribute selectors
                if (ariaLabel) {
                    selectors.push(`[aria-label="${ariaLabel}"]`);
                }
                
                if (title) {
                    selectors.push(`[title="${title}"]`);
                }
                
                if (role) {
                    selectors.push(`[role="${role}"]`);
                }
                
                // Plain tag selector with index (least specific)
                selectors.push(`${tagName}:nth-of-type(${index})`);
                
                // Direct XPath
                const xpath = getElementXPath(element);
                
                // Get the bounding client rect for positioning
                const rect = element.getBoundingClientRect();
                const position = {
                    x: rect.left + rect.width / 2,
                    y: rect.top + rect.height / 2,
                    width: rect.width,
                    height: rect.height
                };
                
                return {
                    tag: tagName,
                    id: id || null,
                    classes: classList,
                    href: href,
                    text: text.trim().substring(0, 100), // Trim text and limit length
                    ariaLabel: ariaLabel,
                    title: title,
                    role: role,
                    disabled: disabled,
                    visible: visible,
                    selectors: selectors,
                    xpath: xpath,
                    position: position
                };
            }
            
            // Generate XPath for an element
            function getElementXPath(element) {
                if (!element) return '';
                
                // Use id if available
                if (element.id) {
                    return `//*[@id="${element.id}"]`;
                }
                
                // Get element path
                const path = [];
                while (element && element.nodeType === 1) {
                    let index = 1;
                    let sibling = element.previousSibling;
                    while (sibling) {
                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                            index++;
                        }
                        sibling = sibling.previousSibling;
                    }
                    
                    const tagName = element.tagName.toLowerCase();
                    path.unshift(`${tagName}[${index}]`);
                    element = element.parentNode;
                }
                
                return `/${path.join('/')}`;
            }
            
            // Find all potentially clickable elements
            const elements = [
                // Links
                ...document.querySelectorAll('a'),
                
                // Buttons
                ...document.querySelectorAll('button'),
                
                // Form elements
                ...document.querySelectorAll('input[type="submit"], input[type="button"], input[type="reset"]'),
                
                // Elements with click-related attributes/roles
                ...document.querySelectorAll('[onclick], [role="button"], [role="link"], [role="tab"], [role="menuitem"]'),
                
                // Elements with event listeners (may be incomplete as we can't detect all event listeners)
                ...document.querySelectorAll('[data-click], [data-toggle], .btn, .button, .clickable'),
                
                // Custom elements that may be clickable in modern web apps
                ...document.querySelectorAll('.card, .card-header, .nav-item, .menu-item, li.nav-item > a, .sidebar-item')
            ];
            
            // Process each element and filter as needed
            const include_disabled = Boolean('${request.include_disabled}' === 'true');
            const include_hidden = Boolean('${request.include_hidden}' === 'true');
            
            const clickableElements = [];
            const processedElements = new Set();
            
            for (let i = 0; i < elements.length; i++) {
                const element = elements[i];
                
                // Skip duplicate elements
                if (processedElements.has(element)) continue;
                processedElements.add(element);
                
                // Check disabled status
                if (!include_disabled && 
                    (element.disabled || element.getAttribute('aria-disabled') === 'true')) {
                    continue;
                }
                
                // Check visibility 
                if (!include_hidden && !isElementVisible(element)) {
                    continue;
                }
                
                // Process the element
                const elementInfo = processElement(element, i + 1);
                clickableElements.push(elementInfo);
            }
            
            return clickableElements;
        }
        """
        
        # Execute JavaScript to find all clickable elements
        clickable_elements = await page.evaluate(js_expression)
        
        return {
            "status": "success", 
            "clickable_elements": clickable_elements
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get clickable elements: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False,
        access_log=True
    )
