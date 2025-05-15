from utils import (
    get_latest_snapshot,
    assemble_prompt,
    get_response_from_model,
    parse_action,
    execute_action,
)
import time

import sys
import os
# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from tests.sandbox.client import PlaywrightClient
from utils import get_site_login

def reset_browser_state(client):
    """
    Reset the browser state by closing and reopening the browser.
    """
    url, username, password = get_site_login("shopping_admin")
    
    try:
        client.cleanup()

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

        snapshot = client.accessibility_snapshot_as_yaml()
        assert "DASHBOARD" in snapshot.upper(), "Login failed, Dashboard not found"
        print(snapshot[:200])
    except Exception as e:
        print(f"Error resetting browser state: {e}")


async def new_chat(user_query):
    agent_memory = []
    n = 0
    MAX_NUM_STEPS = 5

    # make a new log directory
    timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
    log_dir = f"logs/{timestamp}"
    os.makedirs(log_dir, exist_ok=True)
    # make a new screenshots directory
    os.makedirs(f"{log_dir}/screenshots", exist_ok=True)
    os.makedirs(f"{log_dir}/accessibility", exist_ok=True)

    # initialize Playwright client
    client = PlaywrightClient()
    # reset browser state
    reset_browser_state(client)
    
    while n < MAX_NUM_STEPS:
        print(f"=======Step {n+1}/{MAX_NUM_STEPS}========")
        # get latest snapshot
        snapshot = await get_latest_snapshot(client, log_dir, n)
        # print(f"** Snapshot of current page:\n{snapshot}")

        # add the snapshot to the agent memory
        prompt = assemble_prompt(agent_memory, user_query, snapshot)

        response = get_response_from_model(prompt)
        agent_memory.append({"role": "assistant", "content": response})
        print(f"** LLM Response: {response}")

        # parse action
        action = parse_action(response)
        print(f"** Parsed Action: {action}")

        # execute the action
        print("Executing action...")
        observation = execute_action(client, action)
        print(f"** Observation: {observation}")
        
        if observation == "FINISHED":
            print("Agent finished.")
            print("** Agent answer **: ", agent_memory[-1])
            break
        else:    
            agent_memory.append({"role": "user", "content": observation})
            
        n += 1

    # close the browser and cleanup
    client.cleanup()
    print("Chat session ended.")

if __name__ == "__main__":
    import asyncio
    user_query = "What are the top-3 best-selling product in Jan 2023?"
    asyncio.run(new_chat(user_query))
    # client = PlaywrightClient()
    # reset_browser_state(client)