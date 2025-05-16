#!/usr/bin/env python3
"""
Example client for the Playwright browser sandbox API.
"""

import argparse
import json
import re
import requests
import sys
import time
import yaml
from typing import Dict, Optional, Any, List

# Import AX tree flattening helper
from axtree_utils import flatten_axtree_to_str

class PlaywrightClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.browser_id = None
        self.context_id = None
        self.page_id = None
    
    def launch_browser(self, headless: bool = True) -> Dict:
        """Launch a new browser instance."""
        response = requests.post(
            f"{self.base_url}/browser/launch",
            json={"headless": headless}
        )
        data = response.json()
        self.browser_id = data.get("browser_id")
        return data
    
    def create_context(self, width: int = 1280, height: int = 720) -> Dict:
        """Create a new browser context."""
        if not self.browser_id:
            raise ValueError("Browser not launched yet")
        
        response = requests.post(
            f"{self.base_url}/browser/{self.browser_id}/context",
            json={"width": width, "height": height}
        )
        data = response.json()
        self.context_id = data.get("context_id")
        return data
    
    def create_page(self) -> Dict:
        """Create a new page."""
        if not self.context_id:
            raise ValueError("Context not created yet")
        
        response = requests.post(
            f"{self.base_url}/context/{self.context_id}/page",
        )
        data = response.json()
        self.page_id = data.get("page_id")
        return data
    
    def navigate(self, url: str, wait_until: str = "networkidle") -> Dict:
        """Navigate to a URL."""
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/navigate",
            json={"url": url, "wait_until": wait_until}
        )
        return response.json()
    
    def click(self, selector: str) -> Dict:
        """Click on an element matching the selector."""
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/click",
            json={"selector": selector}
        )
        return response.json()
    
    def type_text(self, selector: str, text: str) -> Dict:
        """Type text into an element matching the selector."""
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/type",
            json={"selector": selector, "text": text}
        )
        return response.json()
    
    def get_by_label_fill(self, label: str, text: str, exact: bool = True) -> Dict:
        """Find an element by its label text and fill it with the provided text."""
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/get_by_label_fill",
            json={"label": label, "text": text, "exact": exact, "timeout": 3000}
        )
        return response.json()
    
    def get_by_role_click(self, role: str, name: Optional[str] = None, exact: bool = False) -> Dict:
        """Find an element by its ARIA role and name, and click on it."""
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        payload = {"role": role, "exact": exact, "timeout": 3000}
        if name is not None:
            payload["name"] = name
            
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/get_by_role_click",
            json=payload
        )
        return response.json()
    
    def evaluate(self, expression: str, arg: Optional[Dict] = None) -> Dict:
        """
        Evaluate JavaScript in the page context.
        
        Args:
            expression: JavaScript code to evaluate
            arg: Optional argument to pass to the expression
        """
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        payload = {"expression": expression}
        if arg is not None:
            payload["arg"] = arg
            
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/evaluate",
            json=payload
        )
        return response.json()
    
    def screenshot(self, path: Optional[str] = None, full_page: bool = False, timeout: int = 30000) -> Dict:
        """Take a screenshot of the page."""
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/screenshot",
            json={"path": path, "full_page": full_page, "timeout": timeout}
        )
        return response.json()
    
    def accessibility_snapshot(self) -> Dict:
        """Get the accessibility tree snapshot of the current page."""
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/accessibility_snapshot"
        )
        return response.json()
        
    def accessibility_snapshot_as_yaml(self) -> str:
        """Get the accessibility tree snapshot as a YAML formatted string."""
        result = self.accessibility_snapshot()
        if "snapshot" not in result:
            raise ValueError("Invalid accessibility snapshot response")
            
        return self._convert_a11y_to_yaml(result["snapshot"])
    
    def dom_snapshot(self, computed_styles=None, include_dom_rects=True, include_paint_order=True, extract_text=False) -> Dict:
        """
        Get the DOM snapshot of the current page using Chrome DevTools Protocol.
        
        Args:
            computed_styles: List of computed styles to include (e.g. ["color", "font-size"])
            include_dom_rects: Whether to include DOM rectangles
            include_paint_order: Whether to include paint orders
            extract_text: Whether to extract text content from the DOM
            
        Returns:
            A dictionary containing the DOM snapshot and optionally extracted text
        """
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        payload = {
            "computed_styles": computed_styles or [],
            "include_dom_rects": include_dom_rects,
            "include_paint_order": include_paint_order,
            "extract_text": extract_text
        }
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/dom_snapshot",
            json=payload
        )
        return response.json()
    
    def dom_snapshot_extract_text(self) -> list:
        """
        Get the DOM snapshot of the current page and extract all text content.
        
        Returns:
            A list of text content from the DOM
        """
        result = self.dom_snapshot(extract_text=True)
        if "text_content" not in result:
            raise ValueError("Invalid DOM snapshot response")
        
        return result["text_content"]
    
    def merged_axtree(self, extract_browsergym_ids: bool = True) -> Dict:
        """
        Get the merged AXTree of the current page using Chrome DevTools Protocol.
        
        Args:
            extract_browsergym_ids: Whether to extract browsergym IDs from ARIA attributes
            
        Returns:
            A dictionary containing the merged AXTree
        """
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        payload = {
            "extract_browsergym_ids": extract_browsergym_ids
        }
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/merged_axtree",
            json=payload
        )
        return response.json()
    
    def frame_axtrees(self, extract_browsergym_ids: bool = True) -> Dict:
        """
        Get all frame AXTrees of the current page using Chrome DevTools Protocol.
        
        Args:
            extract_browsergym_ids: Whether to extract browsergym IDs from ARIA attributes
            
        Returns:
            A dictionary containing the frame AXTrees
        """
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        payload = {
            "extract_browsergym_ids": extract_browsergym_ids
        }
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/frame_axtrees",
            json=payload
        )
        return response.json()
        
    def merged_axtree_as_text(self, 
                             with_visible: bool = False,
                             with_clickable: bool = False,
                             with_center_coords: bool = False,
                             with_bounding_box_coords: bool = False,
                             filter_visible_only: bool = False,
                             extra_properties: Dict = None,
                             skip_generic: bool = True) -> str:
        """
        Get the merged AXTree of the current page and format it as text.
        
        This method combines the merged_axtree call with the flatten_axtree_to_str 
        functionality from browsergym.
        
        Args:
            with_visible: Whether to include 'visible' attribute for visible elements
            with_clickable: Whether to include 'clickable' attribute for clickable elements
            with_center_coords: Whether to include center coordinates
            with_bounding_box_coords: Whether to include bounding box coordinates
            filter_visible_only: Whether to filter out non-visible elements
            extra_properties: Dictionary of extra properties for nodes (defaults to empty dict)
            skip_generic: Whether to skip generic nodes with no attributes
            
        Returns:
            A string representation of the AXTree
        """
        # Make sure extra_properties is at least an empty dict
        if extra_properties is None:
            extra_properties = {}
            
        result = self.merged_axtree()
        
        if "status" not in result or result["status"] != "success":
            raise ValueError(f"Invalid merged AXTree response: {result}")
            
        if "axtree" not in result:
            raise ValueError("No AXTree in response")
            
        axtree = result["axtree"]
        
        return flatten_axtree_to_str(
            axtree,
            extra_properties=extra_properties,
            with_visible=with_visible,
            with_clickable=with_clickable,
            with_center_coords=with_center_coords,
            with_bounding_box_coords=with_bounding_box_coords,
            filter_visible_only=filter_visible_only,
            skip_generic=skip_generic
        )
    
    def _convert_a11y_to_yaml(self, node: Dict[str, Any], indent: int = 0) -> str:
        """
        Recursively convert an accessibility node to a YAML formatted string.
        
        Args:
            node: The accessibility node to convert
            indent: Current indentation level
            
        Returns:
            A YAML formatted string representing the accessibility tree
        """
        if not node:
            return ""
            
        # Create a simplified representation of the node
        simplified = {}
        
        # Add important accessibility properties
        for key in ["role", "name", "value", "description", "checked"]:
            if key in node and node[key] is not None and node[key] != "":
                # Strip Unicode characters for 'name' field
                if key == "name" and isinstance(node[key], str):
                    # Remove all non-ASCII characters (Unicode icons)
                    text = re.sub(r'[^\x00-\x7F]+', '', node[key])
                    # Then remove any leading spaces that might have been left
                    # This ensures "\\uE60A REPORTS" becomes "REPORTS" without leading space
                    simplified[key] = text.strip()
                else:
                    simplified[key] = node[key]
        
        # Process children separately
        children = node.get("children", [])
        
        # Convert to YAML string
        yaml_str = yaml.dump(simplified, default_flow_style=False, sort_keys=False)
        
        # Process children recursively
        if children:
            yaml_str = yaml_str.rstrip() + "\nchildren:\n"
            for child in children:
                child_yaml = self._convert_a11y_to_yaml(child, indent + 2)
                # Add indentation to child YAML
                indented_child = "  " + child_yaml.replace("\n", "\n  ")
                yaml_str += "  - " + indented_child.lstrip() + "\n"
        
        return yaml_str
    
    def cleanup(self) -> None:
        """Close all resources."""
        if self.page_id:
            requests.post(f"{self.base_url}/page/{self.page_id}/close")
        
        if self.context_id:
            requests.post(f"{self.base_url}/context/{self.context_id}/close")
        
        if self.browser_id:
            requests.post(f"{self.base_url}/browser/{self.browser_id}/close")
    
    def get_clickable_elements(self, include_disabled: bool = False, include_hidden: bool = False) -> Dict:
        """
        Get all clickable elements and their URLs from the current page.
        
        Args:
            include_disabled: Whether to include disabled elements in the results
            include_hidden: Whether to include hidden elements in the results
            
        Returns:
            A dictionary containing all clickable elements with their attributes and URLs
        """
        if not self.page_id:
            raise ValueError("Page not created yet")
        
        response = requests.post(
            f"{self.base_url}/page/{self.page_id}/clickable_elements",
            json={
                "include_disabled": include_disabled,
                "include_hidden": include_hidden,
                "timeout": 3000
            }
        )
        return response.json()
    
    def click_by_element_id(self, element_id: str, elements_list: List[Dict]) -> Dict:
        """
        Click on an element using its ID from the clickable elements list.
        
        Args:
            element_id: The ID of the element to click
            elements_list: The list of clickable elements from get_clickable_elements()
            
        Returns:
            The result of the click operation
        """
        if not self.page_id:
            raise ValueError("Page not created yet")
            
        # Find the element in the list
        for element in elements_list:
            if element.get("id") == element_id:
                # Use the first selector which is usually the most reliable
                selector = element.get("selectors", [])[0] if element.get("selectors") else None
                
                if not selector:
                    raise ValueError(f"No valid selector found for element with ID {element_id}")
                    
                # Click the element
                return self.click(selector)
                
        raise ValueError(f"Element with ID {element_id} not found in the clickable elements list")
    
    def find_best_element(self, keyword: str, elements_list: List[Dict], match_type: str = "text") -> Optional[Dict]:
        """
        Find the best element for a given search term in the clickable elements list.
        
        Args:
            keyword: The text or role to search for
            elements_list: The list of clickable elements from get_clickable_elements()
            match_type: What to match against - 'text', 'role', 'url', or 'all'
            
        Returns:
            The best matching element or None if no match is found
        """
        # Prepare the keyword for case-insensitive matching
        keyword = keyword.lower()
        matches = []
        
        for element in elements_list:
            score = 0
            
            # Skip disabled or invisible elements
            if not element.get("visible", True) or element.get("disabled", False):
                continue
                
            # Match by text content
            if match_type in ["text", "all"] and element.get("text"):
                element_text = element.get("text", "").lower()
                if keyword == element_text:
                    score += 100  # Exact match
                elif keyword in element_text:
                    score += 50   # Partial match
                    
            # Match by ARIA role
            if match_type in ["role", "all"] and element.get("role"):
                element_role = element.get("role", "").lower()
                if keyword == element_role:
                    score += 75
                    
            # Match by aria label or title
            if match_type in ["text", "all"]:
                if element.get("ariaLabel") and keyword in element.get("ariaLabel", "").lower():
                    score += 60
                if element.get("title") and keyword in element.get("title", "").lower():
                    score += 40
                    
            # Match by URL
            if match_type in ["url", "all"] and element.get("href"):
                element_url = element.get("href", "").lower()
                if keyword in element_url:
                    score += 30
                    
            # If we found a match, add it to the list with its score
            if score > 0:
                matches.append((score, element))
                
        # Sort by score (highest first) and return the best match
        if matches:
            matches.sort(reverse=True, key=lambda x: x[0])
            return matches[0][1]
            
        return None


def main():
    parser = argparse.ArgumentParser(description="Example client for Playwright browser sandbox API")
    parser.add_argument("--url", type=str, default="https://www.google.com", help="URL to navigate to")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--server", type=str, default="http://localhost:8000", help="API server URL")
    parser.add_argument("--a11y-output", type=str, default="accessibility_tree.yaml", 
                        help="Output file path for accessibility tree YAML (default: accessibility_tree.yaml)")
    parser.add_argument("--dom-output", type=str, default="dom_snapshot.json", 
                        help="Output file path for DOM snapshot JSON (default: dom_snapshot.json)")
    parser.add_argument("--axtree-output", type=str, default="merged_axtree.txt", 
                        help="Output file path for merged AXTree text (default: merged_axtree.txt)")
    parser.add_argument("--clickable-output", type=str, default="clickable_elements.json", 
                        help="Output file path for clickable elements JSON (default: clickable_elements.json)")
    
    args = parser.parse_args()
    
    client = PlaywrightClient(base_url=args.server)
    
    try:
        print("Launching browser...")
        client.launch_browser(headless=args.headless)
        
        print("Creating context...")
        client.create_context()
        
        print("Creating page...")
        client.create_page()
        
        print(f"Navigating to {args.url}...")
        client.navigate(args.url)
        
        # Add a short wait to ensure page is fully loaded before screenshot
        print("Waiting for page to load completely...")
        time.sleep(2)
        
        print("Taking screenshot...")
        screenshot_result = client.screenshot(path="screenshot.png")
        print(f"Screenshot saved: {screenshot_result}")
        
        # Example of evaluating JavaScript
        print("Getting page title...")
        title_result = client.evaluate("document.title")
        print(f"Page title: {title_result.get('result', '')}")
        
        # Get DOM snapshot
        print("Getting DOM snapshot...")
        try:
            dom_result = client.dom_snapshot(computed_styles=["color", "font-size"], extract_text=True)
            
            # Save full DOM snapshot to file
            dom_file = args.dom_output
            with open(dom_file, "w") as f:
                import json
                json.dump(dom_result["snapshot"], f, indent=2)
            print(f"DOM snapshot saved to {dom_file}")
            
            # Print extracted text content sample
            if dom_result.get("text_content"):
                print("\nSample of extracted text content:")
                text_sample = dom_result["text_content"][:5]  # Show first 5 text items
                for text in text_sample:
                    print(f"- {text}")
                if len(dom_result["text_content"]) > 5:
                    print(f"... and {len(dom_result['text_content']) - 5} more text elements")
                    
        except Exception as e:
            print(f"Failed to get DOM snapshot: {e}")
        
        # Get accessibility snapshot
        print("Getting accessibility tree snapshot...")
        try:
            a11y_result = client.accessibility_snapshot()
            root_role = a11y_result.get('snapshot', {}).get('role', 'unknown')
            print(f"Accessibility tree: {json.dumps(a11y_result, indent=2)}")
            
            # Convert to YAML format
            print("\nConverting accessibility tree to YAML format...")
            yaml_output = client.accessibility_snapshot_as_yaml()
            
            # Save YAML to file
            yaml_file = args.a11y_output
            with open(yaml_file, "w") as f:
                f.write(yaml_output)
            print(f"YAML accessibility tree saved to {yaml_file}")
            
            # Print a sample of the YAML (first 10 lines)
            print("\nSample of YAML output:")
            yaml_lines = yaml_output.split('\n')
            sample_lines = min(10, len(yaml_lines))
            for i in range(sample_lines):
                print(yaml_lines[i])
            if len(yaml_lines) > sample_lines:
                print("... (truncated)")
            
        except Exception as e:
            print(f"Failed to get accessibility snapshot: {e}")
            
        # Get merged AXTree and format as text
        print("Getting merged AXTree as text...")
        try:
            # Get the AXTree as text with formatting options
            axtree_text = client.merged_axtree_as_text(
                with_visible=True,
                with_clickable=True,
                skip_generic=True
            )
            
            # Save the text to a file
            axtree_file = args.axtree_output
            with open(axtree_file, "w") as f:
                f.write(axtree_text)
            print(f"Merged AXTree text saved to {axtree_file}")
            
            # Print a sample of the text (first 10 lines)
            print("\nSample of AXTree text output:")
            axtree_lines = axtree_text.split('\n')
            sample_lines = min(10, len(axtree_lines))
            for i in range(sample_lines):
                print(axtree_lines[i])
            if len(axtree_lines) > sample_lines:
                print("... (truncated)")
                
        except Exception as e:
            print(f"Failed to get merged AXTree: {e}")
        
        # Get clickable elements
        print("Getting clickable elements...")
        try:
            # Get all clickable elements that are visible
            clickable_elements_result = client.get_clickable_elements(include_disabled=False, include_hidden=False)
            
            if clickable_elements_result.get("status") == "success" and "clickable_elements" in clickable_elements_result:
                elements = clickable_elements_result["clickable_elements"]
                print(f"\nFound {len(elements)} clickable elements on the page:")
                
                # Save the clickable elements to a file
                clickable_file = args.clickable_output
                with open(clickable_file, "w") as f:
                    json.dump(elements, f, indent=2)
                print(f"Clickable elements saved to {clickable_file}")
                
                # Print a sample of the elements (first 5)
                sample_size = min(5, len(elements))
                for i in range(sample_size):
                    element = elements[i]
                    print(f"\nElement {i+1}:")
                    print(f"  Type: {element.get('tag')}")
                    print(f"  Text: {element.get('text', '')[:50]}...")
                    print(f"  URL: {element.get('href', 'N/A')}")
                    print(f"  Selectors: {', '.join(element.get('selectors', [])[:2])}")  # Show first 2 selectors
                
                if len(elements) > sample_size:
                    print(f"... and {len(elements) - sample_size} more elements")
                    
                print("\nYou can now click on any of these elements using the client.click() method with one of the provided selectors.")
                
                # Example of how to find and click an element by text content
                if elements:
                    print("\nExample of finding an element:")
                    # Let's try to find a "login" or "search" button as an example
                    search_terms = ["login", "search", "submit", "sign in", "menu"]
                    
                    for term in search_terms:
                        best_element = client.find_best_element(term, elements, match_type="all")
                        if best_element:
                            print(f"Found a matching element for '{term}':")
                            print(f"  Type: {best_element.get('tag')}")
                            print(f"  Text: {best_element.get('text', '')[:50]}")
                            print(f"  Selector: {best_element.get('selectors', [])[0] if best_element.get('selectors') else 'N/A'}")
                            
                            # Uncomment the following line to actually click the element
                            # click_result = client.click(best_element.get('selectors', [])[0])
                            # print(f"Click result: {click_result}")
                            
                            break
                    else:
                        print("No matching elements found for the search terms.")
                
        except Exception as e:
            print(f"Failed to get clickable elements: {e}")
        
        # Wait a bit to see the browser if running in non-headless mode
        if not args.headless:
            print("Waiting for 3 seconds...")
            time.sleep(3)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        print("Cleaning up resources...")
        client.cleanup()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
