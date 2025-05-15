import os
import subprocess
from prompt import sys_prompt, BOILERPLATE

def assemble_prompt(agent_memory: list[dict], user_query:str, axtree: str) -> str:
    """
    agent_memory: [{"role": "user", "content": "message"}, {"role": "assistant", "content": "message"}, ...]
    """
    
    # Prepare the system prompt as the first message
    messages = [{"role": "system", "content": sys_prompt}]
    messages.append({"role": "user", "content": f"##User query:\n{user_query}"})
    
    # Add all agent memory messages to the list
    messages.extend(agent_memory)

    messages.append({"role": "user", "content": f"##Current page:\n{axtree}"})

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


def get_action(raw_output) -> str:
    """
    Parse the response from the agent and return the action to be performed as executable Python code.
    Based on the accessibility tree information, the appropriate client method will be used.
    """
    action = parse_action(raw_output)

    if action:
        # action format should be: action_name(arg1, arg2, ...)
        if action.startswith("click"):
            # Extract the arguments from the action
            # Expected format: click("role", "name")
            try:
                # Extract all arguments inside the parentheses
                args_str = action[action.find("(")+1:action.rfind(")")]
                # Split by comma and strip spaces and quotes, but respect commas inside quotes
                args = []
                in_quotes = False
                current_arg = ""
                quote_char = None
                
                for char in args_str:
                    if char in ['"', "'"] and (not quote_char or char == quote_char):
                        in_quotes = not in_quotes
                        if not in_quotes:
                            quote_char = None
                        else:
                            quote_char = char
                    
                    if char == ',' and not in_quotes:
                        args.append(current_arg.strip())
                        current_arg = ""
                    else:
                        current_arg += char
                
                if current_arg:
                    args.append(current_arg.strip())
                
                # Remove quotes from args
                args = [arg.strip().strip('"\'') for arg in args]
                
                # Handle both formats:
                # click("name") and click("role", "name")
                if len(args) >= 2:
                    # Format: click("role", "name")
                    role = args[0]
                    element_name = args[1]
                    
                    # Verify role is valid
                    valid_roles = ["button", "link", "checkbox", "textbox", "combobox", "radio", "tab", "menuitem"]
                    if role.lower() not in valid_roles:
                        # If role is not valid, swap - maybe user specified name first
                        element_name, role = role, element_name
                        # Default to "link" if still invalid
                        if role.lower() not in valid_roles:
                            role = "link"
                elif len(args) == 1:
                    # Format: click("name")
                    element_name = args[0]
                    
                    # Determine role based on element name
                    role = "link"  # Default role
                    
                    # Check if it contains "button" in the name to determine role
                    if "button" in element_name.lower():
                        role = "button"
                    elif "textbox" in element_name.lower() or "input" in element_name.lower():
                        role = "textbox"
                else:
                    raise ValueError("Not enough arguments for click action")
                
                # Use get_by_role_click for accessible elements
                tool_name = "get_by_role_click"
                args = f'role="{role}", name="{element_name}"'
                code = BOILERPLATE.format(tool_name=tool_name, args=args)
            except Exception as e:
                code = f"Error parsing click action: {str(e)}"
                
        elif action.startswith("type"):
            # Extract the arguments from the action
            # Expected format: type("element_name", "text_to_type") or type("element_name", "ref_id", "text_to_type")
            try:
                # Extract all arguments inside the parentheses
                args_str = action[action.find("(")+1:action.rfind(")")]
                # Split by comma and strip spaces, but respect commas inside quotes
                args = []
                in_quotes = False
                current_arg = ""
                quote_char = None
                
                for char in args_str:
                    if char in ['"', "'"] and (not quote_char or char == quote_char):
                        in_quotes = not in_quotes
                        if not in_quotes:
                            quote_char = None
                        else:
                            quote_char = char
                    
                    if char == ',' and not in_quotes:
                        args.append(current_arg.strip())
                        current_arg = ""
                    else:
                        current_arg += char
                
                if current_arg:
                    args.append(current_arg.strip())
                
                # Remove quotes from args
                args = [arg.strip().strip('"\'') for arg in args]
                
                # Handle different formats
                if len(args) >= 3:  # type("element_name", "ref_id", "text_to_type")
                    element_name = args[0]
                    text = args[2]
                elif len(args) == 2:  # type("element_name", "text_to_type")
                    element_name = args[0]
                    text = args[1]
                else:
                    raise ValueError("Not enough arguments for type action")
                    
                # Use get_by_label_fill for text input by label
                # This helps when working with input fields in accessibility tree
                tool_name = "get_by_label_fill"
                args = f'label="{element_name}", text="{text}"'
                code = BOILERPLATE.format(tool_name=tool_name, args=args)
            except Exception as e:
                code = f"Error parsing type action: {str(e)}"
                
        elif action.startswith("navigate"):
            # Extract the arguments from the action
            # Expected format: navigate("https://example.com")
            try:
                # Extract all arguments inside the parentheses
                args_str = action[action.find("(")+1:action.rfind(")")]
                # Strip spaces and quotes
                url = args_str.strip().strip('"\'')
                
                tool_name = "navigate"
                args = f'url="{url}"'
                code = BOILERPLATE.format(tool_name=tool_name, args=args)
            except Exception as e:
                code = f"Error parsing navigate action: {str(e)}"
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

async def get_latest_snapshot(client):
    """
    Get the latest snapshot from the browser client.
    """
    # Get the accessibility snapshot as YAML
    try:
        # Use the accessibility_snapshot_as_yaml method from the client
        text = client.accessibility_snapshot_as_yaml()
        return text
    except Exception as e:
        return f"Error getting snapshot: {str(e)}"