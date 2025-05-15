import os
import datetime
from prompt import sys_prompt
from actions import click, type_text, navigate

def assemble_prompt(agent_memory: list[dict], user_query:str, axtree: str) -> str:
    """
    agent_memory: [{"role": "user", "content": "message"}, {"role": "assistant", "content": "message"}, ...]
    """
    
    # Prepare the system prompt as the first message
    messages = [{"role": "system", "content": sys_prompt}]
    messages.append({"role": "user", "content": f"##User query:\n{user_query}"})
    
    # Add all agent memory messages to the list
    messages.extend(agent_memory)

    messages.append({"role": "user", "content": f"##Current page snapshot:\n{axtree}"})

    messages.append({"role": "user", "content": f"Remember the task to accomplish is:\n{user_query}\nNow think step by step and provide the next action to be performed."})
    
    # Return the messages list - OpenAI API expects this format
    # print(f"Prompt:\n{messages}")
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


def execute_action(client, action) -> str:
    """
    Parse the response from the agent and return the action to be performed as executable Python code.
    Based on the accessibility tree information, the appropriate client method will be used.
    """
    if action:
        # action format should be: action_name(arg1, arg2, ...)
        if action.startswith("click"):
            # Extract the arguments from the action
            obs = click(client, action)
        elif action.startswith("type"):
            obs = type_text(client, action)
        elif action.startswith("navigate"):
            obs = navigate(client, action)
        else:
            # unknown action
            obs = f"Unknown action: {action}"
    else:
        # no code to be executed, agent is done
        obs = "FINISHED"
    
    return obs



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

async def get_latest_snapshot(client, log_dir, step_num):
    """
    Get the latest snapshot from the browser client.
    """
    # Get the accessibility snapshot as YAML
    try:
        # Use the accessibility_snapshot_as_yaml method from the client
        text = client.accessibility_snapshot_as_yaml()
        # check if the directory exists
        if not os.path.exists(f"{log_dir}/accessibility"):
            os.makedirs(f"{log_dir}/accessibility")
        # save the snapshot to a file
        with open(f"{log_dir}/accessibility/snapshot_{step_num}.yaml", "w") as f:
            f.write(text)
        # get screen shot and save
        # check if the directory exists
        if not os.path.exists(f"{log_dir}/screenshots"):
            os.makedirs(f"{log_dir}/screenshots")
        filename = f"{log_dir}/screenshots/{step_num}.png"
        client.screenshot(path=filename)
        return text
    except Exception as e:
        return f"Error getting snapshot: {str(e)}"
    

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