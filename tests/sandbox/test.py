

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
            print("Username field filled successfully")
        except Exception as e:
            print(f"Warning: Could not fill username field: {e}")
            
        # Fill the password field using get_by_label
        print("Filling password...")
        try:
            password_result = client.get_by_label_fill("Password", password)
            print("Password field filled successfully")
        except Exception as e:
            print(f"Warning: Could not fill password field: {e}")
            
        # Click the sign-in button using get_by_role
        print("Clicking sign-in button...")
        try:
            # Using get_by_role with "button" role and "Sign in" name
            sign_in_result = client.get_by_role_click("button", name="Sign in")
            print("Sign-in button clicked successfully")
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
        print("Getting accessibility tree after login...")
        a11y_after = client.accessibility_snapshot()
        
        # Convert to YAML and save
        print("Saving accessibility tree as YAML...")
        yaml_output = client.accessibility_snapshot_as_yaml()
        with open("login_accessibility_tree.yaml", "w") as f:
            f.write(yaml_output)
        print("YAML accessibility tree saved to login_accessibility_tree.yaml")
        
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