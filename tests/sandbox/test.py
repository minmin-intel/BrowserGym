

import os
import time
import json
from client import PlaywrightClient  # Import the PlaywrightClient from our client.py

ENV_VARS = ("SHOPPING", "SHOPPING_ADMIN", "REDDIT", "GITLAB", "WIKIPEDIA", "MAP", "HOMEPAGE")

def setup_env():
    append_wa = lambda x: f"WA_{x}"
    for key in ENV_VARS:
        assert append_wa(key) in os.environ, (
            f"Environment variable {append_wa(key)} missing.\n"
            + "Please set the following environment variables to use WebArena through BrowserGym:\n"
            + "\n".join([append_wa(x) for x in ENV_VARS])
        )
        os.environ[key] = os.environ[append_wa(key)]

def get_site_login(site: str):
    # setup webarena environment variables (webarena will read those on import)
    setup_env()

    # import webarena on instanciation
    from webarena.browser_env.env_config import (
        ACCOUNTS,
        # GITLAB,
        # HOMEPAGE,
        # MAP,
        # REDDIT,
        # SHOPPING,
        SHOPPING_ADMIN,
        # WIKIPEDIA,
    )

    urls = {
            # "reddit": REDDIT,
            # "gitlab": GITLAB,
            # "shopping": SHOPPING,
            "shopping_admin": SHOPPING_ADMIN,
            # "wikipedia": WIKIPEDIA,
            # "map": MAP,
        }

    username = ACCOUNTS[site]["username"]
    password = ACCOUNTS[site]["password"]
    url = urls[site]
    print(f"URL: {url}")

    return url, username, password


def get_status_from_server_response(response):
    """
    Extracts the status from the server response.
    """
    status = response.get("status", "unknown")
    return status


def test_login_with_playwright_client():
    """
    Test login functionality using the PlaywrightClient from client.py
    """
    # Get login credentials and URL
    url, username, password = get_site_login("shopping_admin")
    
    # Initialize the client
    client = PlaywrightClient(base_url="http://localhost:8000")
    
    try:
        print("Launching browser...")
        client.launch_browser(headless=True)
        
        print("Creating browser context...")
        client.create_context(width=1280, height=720)
        
        print("Creating page...")
        client.create_page()
        
        print(f"Navigating to {url}...")
        nav_result = client.navigate(url, wait_until="networkidle")
        print(f"Navigation status: {nav_result.get('status', 'unknown')}")
        
        # Wait for page to load completely
        print("Waiting for page to settle...")
        time.sleep(2)
        
        # Get accessibility snapshot before login (optional)
        print("Getting accessibility tree before login...")
        a11y_before = client.accessibility_snapshot()
        
        # Perform login using our new Playwright API methods
        
        # Fill the username field using get_by_label
        print("Filling username...")
        try:
            username_result = client.get_by_label_fill("Username", username)
            print("User name type: ",get_status_from_server_response(username_result))
        except Exception as e:
            print(f"Warning: Could not fill username field: {e}")
            
        # Fill the password field using get_by_label
        print("Filling password...")
        try:
            password_result = client.get_by_label_fill("Password", password)
            print("Password field: ",get_status_from_server_response(password_result))
        except Exception as e:
            print(f"Warning: Could not fill password field: {e}")
            
        # Click the sign-in button using get_by_role
        print("Clicking sign-in button...")
        try:
            # Using get_by_role with "button" role and "Sign in" name
            sign_in_result = client.get_by_role_click("button", name="Sign in")
            print("Sign-in button: ",get_status_from_server_response(sign_in_result))
        except Exception as e:
            print(f"Warning: Could not click sign-in button: {e}")
            # Fallback to JavaScript if needed
            print("Attempting fallback with JavaScript...")
            sign_in_script = """
            () => {
                const signInButton = Array.from(document.querySelectorAll('button')).find(
                    button => button.textContent.includes('Sign in')
                );
                if (signInButton) {
                    signInButton.click();
                    return true;
                }
                return false;
            }
            """
            sign_in_result = client.evaluate(sign_in_script)
            if not sign_in_result.get("result"):
                print("Warning: Could not find sign-in button")
        
        # Wait for navigation after login
        print("Waiting for page to load after login...")
        time.sleep(3)
        
        # Get the current URL
        url_script = "() => window.location.href"
        url_result = client.evaluate(url_script)
        new_url = url_result.get("result", "")
        print(f"New URL after login: {new_url}")
        
        # Get accessibility tree after login
        # print("Getting accessibility tree after login...")
        # a11y_after = client.accessibility_snapshot()
        # with open("login_accessibility_tree.json", "w") as f:
        #     json.dump(a11y_after, f, indent=4)
        
        # # Convert to YAML and save
        # print("Saving accessibility tree as YAML...")
        # yaml_output = client.accessibility_snapshot_as_yaml()
        # with open("login_accessibility_tree.yaml", "w") as f:
        #     f.write(yaml_output)
        # print("YAML accessibility tree saved to login_accessibility_tree.yaml")
        client.screenshot(path="test_logs/screenshot_login.png")

        
        client.screenshot(path="test_logs/screenshot_report.png")
        print("Getting clickable elements...")
        try:
            # Get all clickable elements that are visible
            clickable_elements_result = client.get_clickable_elements(include_disabled=False, include_hidden=False)
            
            if clickable_elements_result.get("status") == "success" and "clickable_elements" in clickable_elements_result:
                elements = clickable_elements_result["clickable_elements"]
                print(f"\nFound {len(elements)} clickable elements on the page:")
                
                # Save the clickable elements to a file
                clickable_file = "test_logs/clickable_elements_after_login.json"
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

                term = "reports"
                best_element = client.find_best_element(term, elements, match_type="all")
                if best_element:
                    print(f"Found a matching element for '{term}':")
                    print(f"  Type: {best_element.get('tag')}")
                    print(f"  Text: {best_element.get('text', '')[:50]}")
                    print(f"  Selector: {best_element.get('selectors', [])[0] if best_element.get('selectors') else 'N/A'}")

                click_result = client.click(best_element.get('selectors', [])[0])
                print(f"Click result: {click_result}")
        except Exception as e:
            print(f"Failed to get clickable elements: {e}")

        # print("Clicking on REPORTS link...")
        
        # result = client.get_by_role_click("link", name="REPORTS", exact=False)
        # print(result)
        # print("Clicking on REPORTS link: ",get_status_from_server_response(result))
        # time.sleep(3)
        # # a11y_after = client.accessibility_snapshot()
        # # with open("report_accessibility_tree.json", "w") as f:
        # #     json.dump(a11y_after, f, indent=4)
        # # yaml_output = client.accessibility_snapshot_as_yaml()
        # # with open("report_accessibility_tree.yaml", "w") as f:
        # #     f.write(yaml_output)
        # # # get screenshot and save

        # print("Clicking on Bestsellers link...")
        # # Bestsellers requires exact=True to avoid matching the tab element with a longer name
        # result = client.get_by_role_click("link", name="Bestsellers", exact=True)
        # print(result)
        # print("Clicking on Bestsellers link: ",get_status_from_server_response(result))
        # time.sleep(3)
        # client.screenshot(path="test_logs/screenshot_bestsellers.png")

        # print("getting snapshot of the page...")
        # yaml_output = client.accessibility_snapshot_as_yaml()
        # with open("test_logs/report_accessibility_tree.yaml", "w") as f:
        #     f.write(yaml_output)
        # print("YAML accessibility tree saved.")

        # print("Getting merged AXTree as text...")
        # try:
        #     # Get the AXTree as text with formatting options
        #     axtree_text = client.merged_axtree_as_text(
        #         with_visible=True,
        #         with_clickable=True,
        #         skip_generic=True
        #     )
            
        #     # Save the text to a file
        #     axtree_file = "test_logs/merged_axtree.txt"
        #     with open(axtree_file, "w") as f:
        #         f.write(axtree_text)
        #     print(f"Merged AXTree text saved to {axtree_file}")
            
        #     # Print a sample of the text (first 10 lines)
        #     print("\nSample of AXTree text output:")
        #     axtree_lines = axtree_text.split('\n')
        #     sample_lines = min(10, len(axtree_lines))
        #     for i in range(sample_lines):
        #         print(axtree_lines[i])
        #     if len(axtree_lines) > sample_lines:
        #         print("... (truncated)")
                
        # except Exception as e:
        #     print(f"Failed to get merged AXTree: {e}")

        return new_url
    
    except Exception as e:
        print(f"Error during test: {e}")
        return None
    finally:
        print("Cleaning up resources...")
        client.cleanup()

# Example of how to run the test
if __name__ == "__main__":
    result_url = test_login_with_playwright_client()
    print(f"Login test completed. Final URL: {result_url}")