source ../tests/webarena/set_env.sh

LLM_BASE_URL="https://api.deepseek.com/v1"
API_KEY=$DEEPSEEK_API_KEY
MODEL_NAME="deepseek-chat"

python run_demo.py \
--task_name webarena.538 \
--llm_base_url $LLM_BASE_URL \
--llm_api_key $API_KEY \
--model_name $MODEL_NAME