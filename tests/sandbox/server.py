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
    timeout: int = 30000
    wait_until: str = "networkidle"  # load, domcontentloaded, networkidle

class ClickRequest(BaseModel):
    selector: str
    button: str = "left"  # left, right, middle
    click_count: int = 1
    delay: int = 0
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    timeout: int = 30000

class TypeRequest(BaseModel):
    selector: str
    text: str
    delay: int = 0
    timeout: int = 30000

class WaitForSelectorRequest(BaseModel):
    selector: str
    state: str = "visible"  # attached, detached, visible, hidden
    timeout: int = 30000

class EvaluateRequest(BaseModel):
    expression: str
    arg: Optional[Dict] = None

class ScreenshotRequest(BaseModel):
    full_page: bool = False
    path: Optional[str] = None
    selector: Optional[str] = None

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
        browser = await playwright.chromium.launch(headless=config.headless)
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
            "clickCount": request.click_count,
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
        options = {"full_page": request.full_page}
        
        if request.path:
            options["path"] = request.path
            
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
