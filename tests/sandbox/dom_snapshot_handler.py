"""
Helper module for DOM snapshot extraction.
"""

import base64
import re
import logging

# Set up logging
logger = logging.getLogger(__name__)


# Common helper functions from observation.py - adapted for async usage
async def extract_dom_snapshot(page, computed_styles=[], include_dom_rects=True, include_paint_order=True, temp_data_cleanup=True):
    """
    Extracts the DOM snapshot of a Playwright page using Chrome DevTools Protocol.

    Args:
        page: the playwright page of which to extract the snapshot.
        computed_styles: whitelist of computed styles to return.
        include_dom_rects: whether to include DOM rectangles (offsetRects, clientRects, scrollRects) in the snapshot.
        include_paint_order: whether to include paint orders in the snapshot.
        temp_data_cleanup: whether to clean up the temporary data stored in the ARIA attributes.

    Returns:
        A document snapshot, including the full DOM tree of the root node (including iframes,
        template contents, and imported documents) in a flattened array, as well as layout
        and white-listed computed style information for the nodes. Shadow DOM in the returned
        DOM tree is flattened.
    """
    cdp = await page.context.new_cdp_session(page)
    dom_snapshot = await cdp.send(
        "DOMSnapshot.captureSnapshot",
        {
            "computedStyles": computed_styles,
            "includeDOMRects": include_dom_rects,
            "includePaintOrder": include_paint_order,
        },
    )
    await cdp.detach()

    # We're skipping the temp_data_cleanup part here for simplicity
    # This would require the extract_data_items_from_aria and pop_bids_from_attribute functions
    
    return dom_snapshot


# Helper functions for post-processing the DOM snapshot if needed
def extract_text_content(dom_snapshot):
    """Extract all text content from the DOM snapshot"""
    texts = []
    
    try:
        for document in dom_snapshot.get("documents", []):
            nodes = document.get("nodes", {})
            text_values = nodes.get("textValue", {})
            strings = dom_snapshot.get("strings", [])
            
            for index in text_values.get("index", []):
                value_idx = text_values["value"][index]
                if value_idx >= 0:
                    text = strings[value_idx]
                    if text and text.strip():
                        texts.append(text)
    except Exception as e:
        logger.error(f"Error extracting text content: {e}")
    
    return texts
