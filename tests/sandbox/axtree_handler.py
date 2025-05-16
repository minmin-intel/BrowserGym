"""
Helper module for AX tree extraction.
"""

import logging
import re

# Set up logging
logger = logging.getLogger(__name__)

# The following extract_data_items_from_aria function is from observation.py
# We need it for AX tree extraction
__BID_EXPR = r"([a-zA-Z0-9]+)"
__DATA_REGEXP = re.compile(r"^browsergym_id_" + __BID_EXPR + r"\s?" + r"(.*)")

def extract_data_items_from_aria(string, log_level=logging.NOTSET):
    """
    Utility function to extract temporary data stored in the ARIA attributes of a node
    """
    match = __DATA_REGEXP.fullmatch(string)
    if not match:
        logger.log(
            level=log_level,
            msg=f"Failed to extract BrowserGym data from ARIA string: {repr(string)}",
        )
        return [], string

    groups = match.groups()
    data_items = groups[:-1]
    original_aria = groups[-1]
    return data_items, original_aria


async def extract_all_frame_axtrees(page):
    """
    Extracts the AXTree of all frames (main document and iframes) of a Playwright page using Chrome DevTools Protocol.

    Args:
        page: the playwright page of which to extract the frame AXTrees.

    Returns:
        A dictionary of AXTrees (as returned by Chrome DevTools Protocol) indexed by frame IDs.
    """
    cdp = await page.context.new_cdp_session(page)

    # Extract the frame tree
    frame_tree = await cdp.send(
        "Page.getFrameTree",
        {},
    )

    # Extract all frame IDs into a list
    # (breadth-first-search through the frame tree)
    frame_ids = []
    root_frame = frame_tree["frameTree"]
    frames_to_process = [root_frame]
    while frames_to_process:
        frame = frames_to_process.pop(0)  # Use pop(0) for BFS
        frames_to_process.extend(frame.get("childFrames", []))
        # Extract the frame ID
        frame_id = frame["frame"]["id"]
        frame_ids.append(frame_id)

    # Extract the AXTree of each frame
    frame_axtrees = {}
    for frame_id in frame_ids:
        try:
            axtree = await cdp.send(
                "Accessibility.getFullAXTree",
                {"frameId": frame_id},
            )
            frame_axtrees[frame_id] = axtree
        except Exception as e:
            logger.warning(f"Failed to get AXTree for frame {frame_id}: {str(e)}")

    await cdp.detach()

    # Extract browsergym data from ARIA attributes
    for ax_tree in frame_axtrees.values():
        for node in ax_tree["nodes"]:
            data_items = []
            # Look for data in the node's "roledescription" property
            if "properties" in node:
                for i, prop in enumerate(node["properties"]):
                    if prop["name"] == "roledescription":
                        data_items, new_value = extract_data_items_from_aria(prop["value"]["value"])
                        prop["value"]["value"] = new_value
                        # Remove the "description" property if empty
                        if new_value == "":
                            node["properties"].pop(i)
                        break
            # Look for data in the node's "description" (fallback plan)
            if "description" in node:
                data_items_bis, new_value = extract_data_items_from_aria(
                    node["description"]["value"]
                )
                node["description"]["value"] = new_value
                if new_value == "":
                    node.pop("description")
                if not data_items:
                    data_items = data_items_bis
            # Add the extracted "browsergym" data to the AXTree
            if data_items:
                (browsergym_id,) = data_items
                node["browsergym_id"] = browsergym_id
    
    return frame_axtrees


async def extract_merged_axtree(page):
    """
    Extracts the merged AXTree of a Playwright page (main document and iframes AXTrees merged) using Chrome DevTools Protocol.

    Args:
        page: the playwright page of which to extract the merged AXTree.

    Returns:
        A merged AXTree (same format as those returned by Chrome DevTools Protocol).
    """
    frame_axtrees = await extract_all_frame_axtrees(page)

    cdp = await page.context.new_cdp_session(page)

    # Merge all AXTrees into one
    merged_axtree = {"nodes": []}
    for ax_tree in frame_axtrees.values():
        merged_axtree["nodes"].extend(ax_tree["nodes"])
        # Connect each iframe node to the corresponding AXTree root node
        for node in ax_tree["nodes"]:
            if node.get("role", {}).get("value") == "Iframe":
                try:
                    result = await cdp.send("DOM.describeNode", {"backendNodeId": node["backendDOMNodeId"]})
                    frame_id = result.get("node", {}).get("frameId", None)
                    
                    if not frame_id:
                        logger.warning(
                            f"AXTree merging: unable to recover frameId of node with backendDOMNodeId {repr(node['backendDOMNodeId'])}, skipping"
                        )
                    # It seems Page.getFrameTree() from CDP omits certain Frames (empty frames?)
                    # If a frame is not found in the extracted AXTrees, we just ignore it
                    elif frame_id in frame_axtrees:
                        # Root node should always be the first node in the AXTree
                        frame_root_node = frame_axtrees[frame_id]["nodes"][0]
                        assert frame_root_node["frameId"] == frame_id
                        if "childIds" not in node:
                            node["childIds"] = []
                        node["childIds"].append(frame_root_node["nodeId"])
                    else:
                        logger.warning(
                            f"AXTree merging: extracted AXTree does not contain frameId '{frame_id}', skipping"
                        )
                except Exception as e:
                    logger.warning(f"Error when connecting iframe node to AXTree root: {str(e)}")

    await cdp.detach()

    return merged_axtree
