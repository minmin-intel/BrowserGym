import gymnasium as gym
import browsergym.webarena  # register webarena tasks as gym environments

# start a webarena task
env = gym.make("browsergym/webarena.0")


