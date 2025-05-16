import sys
import os
import time

def get_status_from_server_response(response):
    """
    Extracts the status from the server response.
    """
    status = response.get("status", "unknown")
    return status


def click(client, action):
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
        print(f"Parsed arguments: {args}")
        
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
            
            result = client.get_by_role_click(role=role, name=element_name)
            time.sleep(3)  # Wait for the action to complete
            print("Click action: ", result)
            observation = f"click({role}, {element_name}): {get_status_from_server_response(result)}"
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
            result = client.get_by_role_click(role=role, name=element_name)
            time.sleep(3)  # Wait for the action to complete
            print(result)
            observation = f"click({role}, {element_name}): {get_status_from_server_response(result)}"
        else:
            observation = "Not enough arguments for click action"
        
    except Exception as e:
        observation = f"Error parsing click action: {str(e)}"
    return observation

def type_text(client, action):
    # Extract the arguments from the action
    # Expected format: type("element_name", "text_to_type")
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
        print(f"Parsed arguments: {args}")
        
        
        if len(args) >= 2:  # type("element_name", "text_to_type")
            element_name = args[0]
            text = args[1]
            result = client.get_by_label_fill(label=element_name, text=text)
            print("Type action: ", result)
            time.sleep(3)  # Wait for the action to complete
            observation = f"type({element_name}, {text}): {get_status_from_server_response(result)}"
        else:
            observation = "Not enough arguments for type action"
    except Exception as e:
        observation = f"Error parsing type action: {str(e)}"
    return observation

def navigate(client, action):
    # Extract the arguments from the action
    # Expected format: navigate("https://example.com")
    try:
        # Extract all arguments inside the parentheses
        args_str = action[action.find("(")+1:action.rfind(")")]
        # Strip spaces and quotes
        url = args_str.strip().strip('"\'')
        print(f"Parsed URL: {url}")
        
        result = client.navigate(url)
        print("Navigate action: ", result)
        time.sleep(3)  # Wait for the action to complete
        observation = f"navigate({url}): {get_status_from_server_response(result)}"
    except Exception as e:
        observation = f"Error parsing navigate action: {str(e)}"
    return observation

if __name__ == "__main__":
    # Example usage
    client = None  # Replace with actual client initialization
    action = 'click("button", "Sign in")'
    result = click(client, action)
    print(result)
    
    action = 'type("Password", "my_password")'
    result = type_text(client, action)
    print(result)
    
    action = 'navigate("https://example.com")'
    result = navigate(client, action)
    print(result)