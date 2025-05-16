"""
Browser action endpoints for the Playwright browser sandbox API.
To be imported into the main server.py file.
"""

from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field
from fastapi import HTTPException

# Models for browser actions request bodies
class NoopRequest(BaseModel):
    wait_ms: float = 1000

class BidRequest(BaseModel):
    bid: str
    
class FillRequest(BaseModel):
    bid: str
    value: str
    
class CheckRequest(BaseModel):
    bid: str
    
class SelectOptionRequest(BaseModel):
    bid: str
    options: Union[str, List[str]]
    
class BidClickRequest(BaseModel):
    bid: str
    button: Literal["left", "middle", "right"] = "left"
    modifiers: List[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]] = []
    
class BidDoubleClickRequest(BaseModel):
    bid: str
    button: Literal["left", "middle", "right"] = "left"
    modifiers: List[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]] = []
    
class HoverRequest(BaseModel):
    bid: str
    
class PressRequest(BaseModel):
    bid: str
    key_comb: str
    
class FocusRequest(BaseModel):
    bid: str
    
class ClearRequest(BaseModel):
    bid: str
    
class DragAndDropRequest(BaseModel):
    from_bid: str
    to_bid: str
    
class ScrollRequest(BaseModel):
    delta_x: float
    delta_y: float
    
class MouseMoveRequest(BaseModel):
    x: float
    y: float
    
class MouseActionRequest(BaseModel):
    x: float
    y: float
    button: Literal["left", "middle", "right"] = "left"
    
class MouseDragAndDropRequest(BaseModel):
    from_x: float
    from_y: float
    to_x: float
    to_y: float
    
class KeyboardPressRequest(BaseModel):
    key: str


# Define the endpoint functions to be added to the FastAPI app
async def setup_action_endpoints(app, page_pool):
    """Set up all browser action endpoints on the FastAPI app."""
    
    @app.post("/page/{page_id}/accessibility_snapshot_with_bids", response_model=Dict)
    async def accessibility_snapshot_with_bids(page_id: str):
        """
        Get the accessibility tree snapshot of the current page with browser IDs (bids).
        
        This endpoint enhances the regular accessibility snapshot by attaching unique browser IDs
        to each element in the tree, which can be used for targeting elements in other browser actions.
        """
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            
            # Get the accessibility snapshot using Playwright's accessibility API
            snapshot = await page.accessibility.snapshot()
            
            # Add BIDs to the DOM elements if they don't already have them
            await page.evaluate("""() => {
                // Generate unique BIDs for all relevant elements
                const elements = document.querySelectorAll('button, a, input, select, textarea, [role]');
                elements.forEach((elem, index) => {
                    if (!elem.hasAttribute('data-bid')) {
                        elem.setAttribute('data-bid', `bid_${Date.now()}_${index}`);
                    }
                });
            }""")
            
            # Get the mapping between accessibility nodes and DOM elements with BIDs
            bid_map = await page.evaluate("""() => {
                const result = {};
                
                // Get all elements with data-bid attributes
                const elementsWithBids = document.querySelectorAll('[data-bid]');
                
                elementsWithBids.forEach(elem => {
                    const bid = elem.getAttribute('data-bid');
                    const role = elem.getAttribute('role') || elem.tagName.toLowerCase();
                    const name = elem.innerText || elem.getAttribute('aria-label') || 
                                elem.getAttribute('placeholder') || elem.getAttribute('name') || '';
                    
                    if (bid) {
                        // Create a key that we can use to match with the a11y tree
                        result[`${role}_${name}`] = bid;
                    }
                });
                
                return result;
            }""")
            
            # Function to recursively attach BIDs to the accessibility tree
            def attach_bids(node):
                if node:
                    # Create a key that matches our bid_map keys
                    role = node.get('role', '')
                    name = node.get('name', '')
                    node_key = f"{role}_{name}"
                    
                    # Add the BID to this node if we have a match
                    if node_key in bid_map:
                        node['bid'] = bid_map[node_key]
                    
                    # Process all children recursively
                    children = node.get('children', [])
                    for child in children:
                        attach_bids(child)
            
            # Attach BIDs to the snapshot tree
            attach_bids(snapshot)
            
            return {"status": "success", "snapshot": snapshot}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get accessibility snapshot with BIDs: {str(e)}")
    
    @app.post("/page/{page_id}/noop", response_model=Dict)
    async def noop(page_id: str, request: NoopRequest):
        """Do nothing, and optionally wait for the given time."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            await page.wait_for_timeout(request.wait_ms)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Noop failed: {str(e)}")
    
    @app.post("/page/{page_id}/bid_fill", response_model=Dict)
    async def bid_fill(page_id: str, request: FillRequest):
        """Fill out a form field using a bid identifier."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            # Get the element using the bid
            element = await page.evaluate(f"""(bid) => {{
                return document.querySelector(`[data-bid="${{bid}}"]`);
            }}""", request.bid)
            
            if not element:
                raise HTTPException(status_code=404, detail=f"Element with bid {request.bid} not found")
            
            # Fill the element
            await page.evaluate(f"""(args) => {{
                const elem = document.querySelector(`[data-bid="${{args.bid}}"]`);
                if (elem) {{
                    elem.value = args.value;
                    // Trigger input and change events
                    const event = new Event('input', {{ bubbles: true }});
                    elem.dispatchEvent(event);
                    const changeEvent = new Event('change', {{ bubbles: true }});
                    elem.dispatchEvent(changeEvent);
                }}
            }}""", {"bid": request.bid, "value": request.value})
            
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fill failed: {str(e)}")

    @app.post("/page/{page_id}/bid_check", response_model=Dict)
    async def bid_check(page_id: str, request: CheckRequest):
        """Check a checkbox or radio element using a bid identifier."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            # Check the element using the bid
            await page.evaluate(f"""(bid) => {{
                const elem = document.querySelector(`[data-bid="${{bid}}"]`);
                if (elem && (elem.tagName === 'INPUT' && (elem.type === 'checkbox' || elem.type === 'radio'))) {{
                    elem.checked = true;
                    // Trigger change event
                    const event = new Event('change', {{ bubbles: true }});
                    elem.dispatchEvent(event);
                }}
            }}""", request.bid)
            
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Check failed: {str(e)}")

    @app.post("/page/{page_id}/bid_uncheck", response_model=Dict)
    async def bid_uncheck(page_id: str, request: CheckRequest):
        """Uncheck a checkbox element using a bid identifier."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            # Uncheck the element using the bid
            await page.evaluate(f"""(bid) => {{
                const elem = document.querySelector(`[data-bid="${{bid}}"]`);
                if (elem && elem.tagName === 'INPUT' && elem.type === 'checkbox') {{
                    elem.checked = false;
                    // Trigger change event
                    const event = new Event('change', {{ bubbles: true }});
                    elem.dispatchEvent(event);
                }}
            }}""", request.bid)
            
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Uncheck failed: {str(e)}")

    @app.post("/page/{page_id}/bid_select_option", response_model=Dict)
    async def bid_select_option(page_id: str, request: SelectOptionRequest):
        """Select one or multiple options in a select element using a bid identifier."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            # Convert options to list if it's a string
            options = request.options
            if isinstance(options, str):
                options = [options]
                
            # Select options using the bid
            await page.evaluate(f"""(args) => {{
                const select = document.querySelector(`[data-bid="${{args.bid}}"]`);
                if (select && select.tagName === 'SELECT') {{
                    // Deselect all options first if it's a multi-select
                    if (select.multiple) {{
                        for (const option of select.options) {{
                            option.selected = false;
                        }}
                    }}
                    
                    // Select the specified options
                    for (const optionValue of args.options) {{
                        for (const option of select.options) {{
                            if (option.value === optionValue || option.text === optionValue) {{
                                option.selected = true;
                            }}
                        }}
                    }}
                    
                    // Trigger change event
                    const event = new Event('change', {{ bubbles: true }});
                    select.dispatchEvent(event);
                }}
            }}""", {"bid": request.bid, "options": options})
            
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Select option failed: {str(e)}")

    @app.post("/page/{page_id}/bid_click", response_model=Dict)
    async def bid_click(page_id: str, request: BidClickRequest):
        """Click an element using a bid identifier."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            
            # Get the element's bounding box
            box = await page.evaluate(f"""(bid) => {{
                const elem = document.querySelector(`[data-bid="${{bid}}"]`);
                if (elem) {{
                    const rect = elem.getBoundingClientRect();
                    return {{ 
                        x: rect.left + rect.width / 2, 
                        y: rect.top + rect.height / 2,
                        width: rect.width,
                        height: rect.height
                    }};
                }}
                return null;
            }}""", request.bid)
            
            if not box:
                raise HTTPException(status_code=404, detail=f"Element with bid {request.bid} not found")
            
            # Apply modifiers if specified
            keyboard = page.keyboard
            for modifier in request.modifiers:
                await keyboard.down(modifier)
                
            try:
                # Click in the middle of the element
                await page.mouse.move(box["x"], box["y"])
                await page.mouse.down(button=request.button)
                await page.mouse.up(button=request.button)
            finally:
                # Release modifiers
                for modifier in request.modifiers:
                    await keyboard.up(modifier)
            
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Click failed: {str(e)}")

    @app.post("/page/{page_id}/bid_dblclick", response_model=Dict)
    async def bid_dblclick(page_id: str, request: BidDoubleClickRequest):
        """Double click an element using a bid identifier."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            
            # Get the element's bounding box
            box = await page.evaluate(f"""(bid) => {{
                const elem = document.querySelector(`[data-bid="${{bid}}"]`);
                if (elem) {{
                    const rect = elem.getBoundingClientRect();
                    return {{ 
                        x: rect.left + rect.width / 2, 
                        y: rect.top + rect.height / 2,
                        width: rect.width,
                        height: rect.height
                    }};
                }}
                return null;
            }}""", request.bid)
            
            if not box:
                raise HTTPException(status_code=404, detail=f"Element with bid {request.bid} not found")
            
            # Apply modifiers if specified
            keyboard = page.keyboard
            for modifier in request.modifiers:
                await keyboard.down(modifier)
                
            try:
                # Double click in the middle of the element
                await page.mouse.move(box["x"], box["y"])
                await page.mouse.dblclick(button=request.button)
            finally:
                # Release modifiers
                for modifier in request.modifiers:
                    await keyboard.up(modifier)
            
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Double click failed: {str(e)}")

    @app.post("/page/{page_id}/bid_hover", response_model=Dict)
    async def bid_hover(page_id: str, request: HoverRequest):
        """Hover over an element using a bid identifier."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            
            # Get the element's bounding box
            box = await page.evaluate(f"""(bid) => {{
                const elem = document.querySelector(`[data-bid="${{bid}}"]`);
                if (elem) {{
                    const rect = elem.getBoundingClientRect();
                    return {{ 
                        x: rect.left + rect.width / 2, 
                        y: rect.top + rect.height / 2
                    }};
                }}
                return null;
            }}""", request.bid)
            
            if not box:
                raise HTTPException(status_code=404, detail=f"Element with bid {request.bid} not found")
            
            # Move mouse to hover over the element
            await page.mouse.move(box["x"], box["y"])
            
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hover failed: {str(e)}")

    @app.post("/page/{page_id}/bid_press", response_model=Dict)
    async def bid_press(page_id: str, request: PressRequest):
        """Focus an element and press a key combination."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            
            # Focus the element first
            success = await page.evaluate(f"""(bid) => {{
                const elem = document.querySelector(`[data-bid="${{bid}}"]`);
                if (elem) {{
                    elem.focus();
                    return true;
                }}
                return false;
            }}""", request.bid)
            
            if not success:
                raise HTTPException(status_code=404, detail=f"Element with bid {request.bid} not found")
            
            # Press the key combination
            await page.keyboard.press(request.key_comb)
            
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Press failed: {str(e)}")

    @app.post("/page/{page_id}/bid_focus", response_model=Dict)
    async def bid_focus(page_id: str, request: FocusRequest):
        """Focus an element."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            
            # Focus the element
            success = await page.evaluate(f"""(bid) => {{
                const elem = document.querySelector(`[data-bid="${{bid}}"]`);
                if (elem) {{
                    elem.focus();
                    return true;
                }}
                return false;
            }}""", request.bid)
            
            if not success:
                raise HTTPException(status_code=404, detail=f"Element with bid {request.bid} not found")
            
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Focus failed: {str(e)}")

    @app.post("/page/{page_id}/bid_clear", response_model=Dict)
    async def bid_clear(page_id: str, request: ClearRequest):
        """Clear an input field."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            
            # Clear the input
            success = await page.evaluate(f"""(bid) => {{
                const elem = document.querySelector(`[data-bid="${{bid}}"]`);
                if (elem && (elem.tagName === 'INPUT' || elem.tagName === 'TEXTAREA')) {{
                    elem.value = '';
                    // Trigger input and change events
                    const event = new Event('input', {{ bubbles: true }});
                    elem.dispatchEvent(event);
                    const changeEvent = new Event('change', {{ bubbles: true }});
                    elem.dispatchEvent(changeEvent);
                    return true;
                }}
                return false;
            }}""", request.bid)
            
            if not success:
                raise HTTPException(status_code=404, detail=f"Element with bid {request.bid} not found or is not an input element")
            
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Clear failed: {str(e)}")

    @app.post("/page/{page_id}/bid_drag_and_drop", response_model=Dict)
    async def bid_drag_and_drop(page_id: str, request: DragAndDropRequest):
        """Drag and drop from one element to another."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            
            # Get the source and target elements' positions
            positions = await page.evaluate(f"""(args) => {{
                const fromElem = document.querySelector(`[data-bid="${{args.from_bid}}"]`);
                const toElem = document.querySelector(`[data-bid="${{args.to_bid}}"]`);
                
                if (!fromElem || !toElem) return null;
                
                const fromRect = fromElem.getBoundingClientRect();
                const toRect = toElem.getBoundingClientRect();
                
                return {{
                    from_x: fromRect.left + fromRect.width / 2,
                    from_y: fromRect.top + fromRect.height / 2,
                    to_x: toRect.left + toRect.width / 2,
                    to_y: toRect.top + toRect.height / 2
                }};
            }}""", {"from_bid": request.from_bid, "to_bid": request.to_bid})
            
            if not positions:
                raise HTTPException(status_code=404, detail="One or both elements not found")
            
            # Perform the drag and drop
            await page.mouse.move(positions["from_x"], positions["from_y"])
            await page.mouse.down()
            await page.mouse.move(positions["to_x"], positions["to_y"])
            await page.mouse.up()
            
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Drag and drop failed: {str(e)}")

    @app.post("/page/{page_id}/scroll", response_model=Dict)
    async def scroll(page_id: str, request: ScrollRequest):
        """Scroll horizontally and vertically."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            await page.mouse.wheel(delta_x=request.delta_x, delta_y=request.delta_y)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Scroll failed: {str(e)}")

    @app.post("/page/{page_id}/mouse_move", response_model=Dict)
    async def mouse_move(page_id: str, request: MouseMoveRequest):
        """Move the mouse to a location."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            await page.mouse.move(request.x, request.y)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Mouse move failed: {str(e)}")

    @app.post("/page/{page_id}/mouse_up", response_model=Dict)
    async def mouse_up(page_id: str, request: MouseActionRequest):
        """Move the mouse to a location and release a button."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            await page.mouse.move(request.x, request.y)
            await page.mouse.up(button=request.button)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Mouse up failed: {str(e)}")

    @app.post("/page/{page_id}/mouse_down", response_model=Dict)
    async def mouse_down(page_id: str, request: MouseActionRequest):
        """Move the mouse to a location and press a button."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            await page.mouse.move(request.x, request.y)
            await page.mouse.down(button=request.button)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Mouse down failed: {str(e)}")

    @app.post("/page/{page_id}/mouse_click", response_model=Dict)
    async def mouse_click(page_id: str, request: MouseActionRequest):
        """Move the mouse to a location and click."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            await page.mouse.click(request.x, request.y, button=request.button)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Mouse click failed: {str(e)}")

    @app.post("/page/{page_id}/mouse_dblclick", response_model=Dict)
    async def mouse_dblclick(page_id: str, request: MouseActionRequest):
        """Move the mouse to a location and double-click."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            await page.mouse.dblclick(request.x, request.y, button=request.button)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Mouse double-click failed: {str(e)}")

    @app.post("/page/{page_id}/mouse_drag_and_drop", response_model=Dict)
    async def mouse_drag_and_drop(page_id: str, request: MouseDragAndDropRequest):
        """Drag and drop from one location to another."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            await page.mouse.move(request.from_x, request.from_y)
            await page.mouse.down()
            await page.mouse.move(request.to_x, request.to_y)
            await page.mouse.up()
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Mouse drag and drop failed: {str(e)}")

    @app.post("/page/{page_id}/keyboard_press", response_model=Dict)
    async def keyboard_press(page_id: str, request: KeyboardPressRequest):
        """Press a key or key combination."""
        if page_id not in page_pool:
            raise HTTPException(status_code=404, detail="Page not found")
        
        try:
            page = page_pool[page_id]
            await page.keyboard.press(request.key)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Keyboard press failed: {str(e)}")

    return "Browser action endpoints have been set up successfully"
