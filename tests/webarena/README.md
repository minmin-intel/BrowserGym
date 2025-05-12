
## Python env setup
1. download this repo
```bash
cd $WORKDIR
git clone https://github.com/minmin-intel/BrowserGym.git
```

2. create conda env
```bash
conda create -n browser-gym-env python=3.10
```

3. install browser-gym and other packages
```bash
cd BrowserGym
make install
pip install openai
```

## WebArena env setup
1. clone the setup repo
```bash
cd $WORKDIR
git clone https://github.com/minmin-intel/webarena-setup.git
git checkout test-webarena
```

2. Follow the instructions on this [README](https://github.com/minmin-intel/webarena-setup/blob/main/webarena/README.md)
```bash
# download the shopping-admin docker image
cd $WORKDIR
mkdir webarena_docker_images
cd webarena_docker_images
wget http://metis.lti.cs.cmu.edu/webarena-images/shopping_admin_final_0719.tar
```
Note: we will only test the shopping-admin tasks, so only need to download `shopping_admin_final_0719.tar`, no need to download other docker image tars or the map related files.

Then follow the instructions to run 01 to 06 bash scripts.

## Run demo agent test
```bash
cd $WORKDIR/BrowserGym/demo_agent
bash test_demo_agent.sh
```

## Inner working of demo agent
1. in run_demo.py
```python
# around line 106
# setting up environment config
env_args = EnvArgs(
        task_name=args.task_name, # task name is passed in here
        task_seed=None,
        max_steps=100,
        headless=True,  # run benchmark in headless mode
        # viewport={"width": 1500, "height": 1280},  # can be played with if needed
    )

# around line 122: experiment args - agent args and env args
exp_args = ExpArgs(
        env_args=env_args,
        agent_args=agent_args,
    )

# a few line later
exp_args.run() # the code to run the experiment
```

2. exp_args.run()
in loop.py, class ExpArgs is defined. Around line 379, the run() function of ExpArgs is defined.
```python
# ExpArgs.run() first make env
#around line 395: env is made. Notice action_mapping=action_set.to_python_code
env = self.env_args.make_env( # see 5. below for more details
                action_mapping=agent.action_set.to_python_code,
                exp_dir=self.exp_dir,
            )
```
Then a while loop, agent takes actions and observes the env
```python
# ExpArgs.run() then runs the agent step by step
# around line 409
while not step_info.is_done:  # set a limit
    logger.debug(f"Starting step {step_info.step}.")
    action = step_info.from_action(agent)
    logger.debug(f"Agent chose action:\n {action}")

    # around line 433
    logger.debug(f"Sending action to environment.")
    step_info.from_step(env, action, obs_preprocessor=agent.obs_preprocessor)
    logger.debug(f"Environment stepped.")
```

3. step_info.from_action, step_info.from_step
StepInfo class is also defined in loop.py
```python
# call agent.get_action
def from_action(self, agent: Agent):
    # simplified, only the most essenial code was kept
    self.action, self.agent_info = agent.get_action(self.obs.copy())
    return self.action
```
```python
def from_step(self, env: gym.Env, action: str, obs_preprocessor: callable):
    # simplified, only the most essenial code was kept
    self.obs, self.reward, self.terminated, self.truncated, env_info = env.step(action) # see 6. below for more details
    if obs_preprocessor:
        self.obs = obs_preprocessor(self.obs)
```

4. agent.get_action
in demo_agent/agent.py, assemble messages that are to be sent to LLM, action is a string returned by LLM. Depending on if using html, axtree, or screenshot, the message list can be different.
```python
# around Line 238: The descriptions of Action Space, i.e., functions available is added to the message list
{self.action_set.describe(with_long_description=False, with_examples=True)}
```

The `action_set` is defined around line 77
```python
self.action_set = HighLevelActionSet(
            subsets=["chat", "tab", "nav", "bid", "infeas"],  # define a subset of the action space
            # subsets=["chat", "bid", "coord", "infeas"] # allow the agent to also use x,y coordinates
            strict=False,  # less strict on the parsing of the actions
            multiaction=False,  # does not enable the agent to take multiple actions at once
            demo_mode=demo_mode,  # add visual effects
        )
```

`HighLevelActionSet` is defined in core highlevel.py
```python
# HighLevelActionSet.to_python_code()

# around line 491, when strict=False
# parsing string into functions
function_calls = highlevel_action_parser.search_string(
                highlevel_code
            )  # allow for multiple matches, skip anything in-between

function_calls = sum(function_calls.as_list(), [])  # unpack multiple matches
# around line 507
python_code += self.python_includes

        # function calls
        for function_name, function_args in function_calls:
            if function_name not in self.action_set:
                raise NameError(f"Invalid action type '{function_name}'.")
            python_code += (
                function_name + "(" + ", ".join([repr(arg) for arg in function_args]) + ")\n"
            )

        # return the constructed python code
        return python_code
```

The functions are implemented in core/action/functions.py. The functions use playwright.sync_api to interact with browser in the docker container.


5. env_args.make_env
in loop.py
```python
# around line 80
gym.make(
            _get_env_name(self.task_name),
            disable_env_checker=True,
            max_episode_steps=self.max_steps,
            headless=self.headless,
            wait_for_user_message=self.wait_for_user_message,
            action_mapping=action_mapping,  # action mapping is provided by the agent
            **extra_kwargs,
        )
```

6. env.step
in core env.py, class BrowserEnv
```python
# around line 412, inside step() function:
code = self.action_mapping(action) 
# recall that action_mapping is agent.action_set.to_python_code
# action_set is HighLevelActionSet
# to_python_code: see 4. above

execute_python_code( # see 7. below for more details
                code,
                self.page,
                send_message_to_user=send_message_to_user,
                report_infeasible_instructions=report_infeasible_instructions,
            )

return self.post_step(info)
```

post_step()
```python
 # wait for the network to idle before extracting the observation, reward etc.
self._wait_dom_loaded()

if validate:
    # after the action is executed, the active page might have changed
    # perform a safety check
    self._active_page_check()
    logger.debug("Active page checked")

    # if asked, wait for user message
    self._wait_for_user_message()
    logger.debug("User message done")

    logger.debug("Initiating task validation")
    # extract reward, done, user_message, info (task-specific)
    reward, done, user_message, task_info = self._task_validate()
    info["task_info"] = task_info
    logger.debug("Task validation done")
```

self._task_validate()
```python
reward, done, user_message, info = self.task.validate(self.page, self.chat.messages)
```

For WebArena task, it is defined in webarena/task.py, basically it checks if the task is completed and use webarena evaluator to score the last agent output.

7. execute_python_code
```python
def execute_python_code(
    code: str,
    page: playwright.sync_api.Page,
    send_message_to_user: callable,
    report_infeasible_instructions: callable,
):
    """
    Executes Python code in a new context, except for a playwright `page` object and a `send_message_to_user` function.

    WARNING: this is not safe!
    https://stackoverflow.com/questions/77655440/can-you-protect-a-python-variable-with-exec

    Args:
        code: the Python code to execute, as a string.
        page: the playwright page that will be made accessible to the code.
        send_message_to_user: utility function that will be made accessible to the code. It should take one text argument.
        report_infeasible_instructions: utility function that will be made accessible to the code. It should take one text argument.
    """

    globals = {
        "page": page,
        "send_message_to_user": send_message_to_user,
        "report_infeasible_instructions": report_infeasible_instructions,
        "DEMO_MODE": get_global_demo_mode(),
    }

    exec(code, globals)
```

8. Browser setup
In webarena instance.py, WebArenaInstance is defined, in its init function, things to note
```python
#1. Get the URLs env vars: we set WA_XXX_URL, but original webarena code needs XXX_URL as env var
os.environ[key] = os.environ[append_wa(key)]

#2. set up the urls lookup dict.
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

self.urls = {
    "reddit": REDDIT,
    "gitlab": GITLAB,
    "shopping": SHOPPING,
    "shopping_admin": SHOPPING_ADMIN,
    "wikipedia": WIKIPEDIA,
    "map": MAP,
}
self.home_url = HOMEPAGE
```

Then in webarena task.py, WebArenaTask is defined, in its init function, things to note:
```python
# raw task config https://github.com/web-arena-x/webarena/blob/main/config_files/test.raw.json
# the start_url is a string like __XXX__
# so replace the __XXX__ with the actual url in the webarena_instance.urls
for pattern, url_key in {
            "__GITLAB__": "gitlab",
            "__REDDIT__": "reddit",
            "__SHOPPING__": "shopping",
            "__SHOPPING_ADMIN__": "shopping_admin",
            "__WIKIPEDIA__": "wikipedia",
            "__MAP__": "map",
        }.items():
            all_configs_str = all_configs_str.replace(pattern, self.webarena_instance.urls[url_key])
```

Then in the WebArenaTask setup() function, go to the start_url page.
```python
if self.config["start_url"]:
            start_urls = self.config["start_url"].split(" |AND| ")
            for i, url in enumerate(start_urls):
                page.goto(url)
                if i < len(start_urls) - 1:
                    page = page.context.new_page()
```

Where does the `page` come from?

