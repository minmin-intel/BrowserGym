from utils import (
    get_latest_snapshot,
    assemble_prompt,
    get_response_from_model,
    get_action,
    execute_action,
)

async def main():
    user_query = "What are the top-3 best-selling product in Jan 2023?"
    agent_memory = []
    n = 1
    MAX_NUM_STEPS = 10
    
    while n < MAX_NUM_STEPS:
        print(f"=======Step {n}/{MAX_NUM_STEPS}========")
        # get latest snapshot
        snapshot = await get_latest_snapshot(client)
        print(f"** Filtered axtree of current page:\n{snapshot}")

        # add the snapshot to the agent memory
        prompt = assemble_prompt(agent_memory, user_query, snapshot)

        response = get_response_from_model(prompt)
        agent_memory.append({"role": "assistant", "content": response})
        print(f"** LLM Response: {response}")

        # action
        action = get_action(response)
        print(f"** Parsed Action: {action}")
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
            print(f"** Observation: {observation}")
            agent_memory.append({"role": "user", "content": observation})
            
        n += 1