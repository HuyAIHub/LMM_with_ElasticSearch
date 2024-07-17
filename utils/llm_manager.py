import logging, time
from langchain_community.chat_models import ChatOpenAI
from config_app.config import get_config
from langchain_groq import ChatGroq
import requests
# Cấu hình logging
import logging

config_app = get_config()

# Danh sách các API key
api_keys = config_app['parameter']['llm_api_keys']

# Chỉ số hiện tại của API key
current_key_index = 0

    
def get_llm():
    global current_key_index
    try:
        key = api_keys[current_key_index]
        if "gsk" in key:
            print('---- grog ----')
            return ChatGroq(model=config_app['parameter']['grog_model_to_use'], api_key=key)
        else:
            print('---- openai ----')
            return ChatOpenAI(model_name=config_app["parameter"]["gpt_model_to_use"], temperature=config_app["parameter"]["temperature"], openai_api_key=key)
    except Exception as e:
        # Ghi log lỗi và chuyển sang API key tiếp theo nếu có lỗi
        logging.error(f"Error with API key {api_keys[current_key_index]}: {str(e)}")
        current_key_index = (current_key_index + 1) % len(api_keys)
        time.sleep(1)  # Thêm thời gian chờ để tránh giới hạn yêu cầu
        return get_llm()