from fastmcp import Client
import asyncio
import subprocess
import os
from playwright.sync_api import sync_playwright


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
        GITLAB,
        HOMEPAGE,
        MAP,
        REDDIT,
        SHOPPING,
        SHOPPING_ADMIN,
        WIKIPEDIA,
    )

    urls = {
            "reddit": REDDIT,
            "gitlab": GITLAB,
            "shopping": SHOPPING,
            "shopping_admin": SHOPPING_ADMIN,
            "wikipedia": WIKIPEDIA,
            "map": MAP,
        }

    username = ACCOUNTS[site]["username"]
    password = ACCOUNTS[site]["password"]
    url = urls[site]
    print(f"URL: {url}")

    return url, username, password

def test_login_with_playwright():
    url, username, password = get_site_login("shopping_admin")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url)
        # wait for the page to load
        page.wait_for_load_state("networkidle")
        # # get accessibility tree of the page
        # axtree = page.accessibility.snapshot()
        # print(axtree)

        # log in
        page.get_by_label("Username").fill(username)
        page.get_by_label("Password").fill(password)
        page.get_by_role("button", name="Sign in").click()
        page.wait_for_load_state("networkidle")
        # get the url of the page
        new_url = page.url
        print(f"New URL: {new_url}")
        # get accessibility tree of the page
        axtree = page.accessibility.snapshot()
        print(axtree)
    return new_url

async def login():
    url, username, password = get_site_login("shopping_admin")
    async with Client("http://localhost:8931/mcp") as client:
        # # list tools
        # tools = await client.list_tools()
        # print(tools)
        # # navigate to a URL
        result = await client.call_tool("browser_navigate", {"url":url}) #"http://10.7.4.57:9083/admin"
        print(result)
        print("Navigated to URL: ", url)
        print("==========================")

        
        try:
            # # use playwright mcp tool to log in
            print("Logging in...")
            # Fill username field
            await client.call_tool("browser_type", {
                "element": "Username",
                "ref": "e16",
                "text": username,
            })
            
            # Fill password field
            await client.call_tool("browser_type", {
                "element": "Password",
                "ref": "e21",
                "text": password,
            })

            snapshot = await client.call_tool("browser_snapshot", {})
            print(snapshot)
            print("===========================")

            await asyncio.sleep(5)

            # Click the sign in button
            await client.call_tool("browser_click", {
                "element": "Sign in",
                "ref": "e25",
            })

        except Exception as e:
            print(f"Error: {e}")
            # If the click fails, take a snapshot
            snapshot = await client.call_tool("browser_snapshot", {})
            print(snapshot)


async def get_latest_snapshot():
    url, _, _ = get_site_login("shopping_admin")
    async with Client("http://localhost:8931/mcp") as client:
        # capture snapshot of the page
        asyncio.sleep(5)
        await client.call_tool("browser_navigate", {"url":url})
        snapshot = await client.call_tool("browser_snapshot", {})
    return snapshot


def get_response_from_model(messages):
    from openai import OpenAI
    model = OpenAI(
        base_url= "https://api.deepseek.com/v1",
        api_key=os.environ["DEEPSEEK_API_KEY"],   
    )

    response = model.chat.completions.create(
        model = "deepseek-chat",
        messages=messages,
        temperature=0.3,
        max_tokens=4096,
    )
    raw_output = response.choices[0].message.content
    useage = response.usage
    print(f"Tokens stats: {useage}")
    return raw_output


sys_prompt = """
    You are a web browser agent. Your task is to navigate to a website and perform actions on it to help users achieve their goal.
    You can use the following actions:
    1. click: Click on an element. 
        args: 
        - element (string): the name of the element to click on 
        - ref (string): Exact target element reference from the page snapshot
    2. type: Type text into an element
        args:
        - element (string): the name of the element to type into
        - ref (string): Exact target element reference from the page snapshot
        - text (string): the text to type
    3. navigate: Navigate to a URL
        args:
        - url (string): the URL to navigate to
    
    Write your action in the following format:
    ```<action_name>(<args>)```
    For example, to click on a button with the name "Submit", you would write:
    ```click("Submit", "e25")```
    If you want to type "Hello" into a text field with the name "Input", you would write:
    ```type("Input", "e21", "Hello")```
    If you want to navigate to a URL, you would write:
    ```navigate("http://example.com")```

    Think step by step and provide the next action to be performed. Only output one action at a time.
    When you are done, output your final answer in plain text string.
    """

def assemble_prompt(agent_memory: list[dict], user_query:str) -> str:
    """
    agent_memory: [{"role": "user", "content": "message"}, {"role": "assistant", "content": "message"}, ...]
    """
    
    # Prepare the system prompt as the first message
    messages = [{"role": "system", "content": sys_prompt}]
    messages.append({"role": "user", "content": f"##User query:\n{user_query}"})
    
    # Add all agent memory messages to the list
    messages.extend(agent_memory)

    messages.append({"role": "user", "content": f"Remember the task to accomplish is:\n{user_query}\nNow think step by step and provide the next action to be performed."})
    
    # Return the messages list - OpenAI API expects this format
    return messages

def parse_action(raw_output: str) -> str:
    """
    raw output: Thinking process....```click()```
    we need to get the string between ```` and ````
    """
    # Split the raw output by triple backticks
    parts = raw_output.split("```")
    
    # Check if there are at least two parts (before and after the code block)
    if len(parts) >= 3:
        # Return the action part (the second part)
        return parts[1].strip()
    
    # If no action found, return an empty string or handle as needed
    return ""


BOILERPLATE = """
from fastmcp import Client
import asyncio

async with Client("http://localhost:8931/mcp") as client:
    try:
        await client.call_tool({tool_name}, {args})
        await asyncio.sleep(5)

    except Exception as e:
        print(f"Error: {{e}}")  
"""

def get_action(raw_output) -> dict:
    """
    Parse the response from the agent and return the action to be performed.
    """

    action = parse_action(raw_output)

    if action:
        # assemble python code to be executed
        if "click" in action:
            # click action
            tool_name = "browser_click"
            args = {"element": action.split("(")[1].split(")")[0], "ref": action.split(",")[1]}
            code = BOILERPLATE.format(tool_name=tool_name, args=args)
        elif "type" in action:
            # type action
            tool_name = "browser_type"
            args = {
                "element": action.split("(")[1].split(",")[0],
                "ref": action.split(",")[1],
                "text": action.split(",")[2].split(")")[0]
            }
            code = BOILERPLATE.format(tool_name=tool_name, args=args)
        elif "navigate" in action:
            # navigate action
            tool_name = "browser_navigate"
            args = {"url": action.split("(")[1].split(")")[0]}
            code = BOILERPLATE.format(tool_name=tool_name, args=args)
        else:
            # unknown action
            code = f"Unknown action: {action}"
    else:
        # no code to be executed, agent is done
        code = "FINISHED"
    return code


def execute_action(action: str):
    with open("temp_action.py", "w") as f:
        f.write(action)
    
    # Execute the code and capture the output
    try:
        result = subprocess.run(
            ["python", "temp_action.py"], 
            capture_output=True, 
            text=True,
            timeout=30
        )
        observation = f"Action executed. Output:\n{result.stdout}\n"
        if result.stderr:
            observation += f"Errors:\n{result.stderr}"
    except Exception as e:
        observation = f"Failed to execute action: {str(e)}"
    
    # Clean up the temporary file
    if os.path.exists("temp_action.py"):
        os.remove("temp_action.py")
    return observation


async def agent_loop():
    user_query = "What are the top-3 best-selling product in Jan 2023?"
    agent_memory = []
    n = 1
    MAX_NUM_STEPS = 10
    while n < MAX_NUM_STEPS:
        print(f"=======Step {n}/{MAX_NUM_STEPS}========")
        # get latest snapshot
        snapshot = await get_latest_snapshot()
        # add the snapshot to the agent memory
        agent_memory.append({"role": "user", "content": f"##Current page:\n{snapshot}"})
        prompt = assemble_prompt(agent_memory, user_query)

        response = get_response_from_model(prompt)
        agent_memory.append({"role": "assistant", "content": response})
        print(f"Response: {response}")

        # action
        action = get_action(response)
        print(f"Action: {action}")
        if action == "FINISHED":
            print("Agent finished.")
            break
        elif action.startswith("Unknown action:"):
            agent_memory.append({"role": "user", "content": action})
        else:
            # execute the action
            print("Executing action...")
            # execute the code and save the output as the observation
            # Create a temporary Python file with the action code
            observation = execute_action(action)
            print(f"Observation: {observation}")
            agent_memory.append({"role": "user", "content": observation})
            
        n += 1
        

async def main():
    snapshot = await get_latest_snapshot()
    print(snapshot)


if __name__ == "__main__":
    asyncio.run(agent_loop())
