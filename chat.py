import os
import json
from pathlib import Path
from ChatBot_Extract_Intent.module.llm2 import initialize_chat_conversation, initialize_chat_conversation_2
from ChatBot_Extract_Intent.config_app.config import get_config
from langchain.memory import (
    ChatMessageHistory
)
from langchain.schema import messages_from_dict, messages_to_dict
from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import requests
from ChatBot_Extract_Intent.elastic_search import search_db
from ChatBot_Extract_Intent.module.few_shot_sentence import extract_info
from ChatBot_Extract_Intent.module.few_shot_sentence import find_closest_match
import pandas as pd
import random
import logging
import datetime
import time, re
logging.basicConfig(filename=f"logs/{datetime.date.today()}_chatbot.log", level=logging.INFO, format='%(asctime)s - %(message)s')

random_number = random.randint(0, 4)

config_app = get_config()
response_elsatic={}

# os.environ['OPENAI_API_KEY'] = config_app["parameter"]["openai_api_key"]
# llm = ChatOpenAI(model_name=config_app["parameter"]["gpt_model_to_use"], temperature=config_app["parameter"]["temperature"])
from langchain_groq import ChatGroq
llm = ChatGroq(model=config_app["parameter"]["gpt_model_to_use"],api_key=config_app["parameter"]["groq_key"])
data_private = config_app['parameter']['data_private']
df = pd.read_excel(data_private)

def word_to_digit(word):
    word_digit_map = {
        'một': 1, 'hai': 2, 'ba': 3, 'bốn': 4, 'năm': 5,
        'sáu': 6, 'bảy': 7, 'tám': 8, 'chín': 9, 'mười': 10, 'nhất': 1
    }
    return word_digit_map.get(word.lower(), word)

def predict_rasa_llm(InputText, IdRequest, NameBot, User,type='rasa'):
    User = str(User)
    logging.info("----------------NEW_SESSION--------------")
    logging.info(f"User: {User}")
    logging.info(f"InputText: {InputText}")
    print("----------------NEW_SESSION--------------")
    print("GuildID  = ", IdRequest)
    print("InputText  = ", InputText)

    query_text = InputText

    path_messages = config_app["parameter"]["DB_MESSAGES"] + str(NameBot) + "/" +  str(User) + "/" + str(IdRequest)
    if not os.path.exists(path_messages):
        os.makedirs(path_messages)

    # Load memory
    try:
        with Path(path_messages + "/messages_conv.json").open("r") as f:
            loaded_messages_conv = json.load(f)
        with Path(path_messages + "/messages_snippets.json").open("r") as f:
            loaded_messages_snippets = json.load(f)
        conversation_messages_snippets = ChatMessageHistory(messages=messages_from_dict(loaded_messages_snippets))
        conversation_messages_conv = ChatMessageHistory(messages=messages_from_dict(loaded_messages_conv))
    except:
        conversation_messages_conv, conversation_messages_snippets = [], []

    results = {'terms':[],'out_text':'', 'inventory_status' : False, 'products': [], 'object_product' :'', 'similarity_status': False}
    
    if type == 'rasa':
        print('========rasa=========')
        # Predict Text
        conversation = initialize_chat_conversation(conversation_messages_conv, conversation_messages_snippets, "")
        # message_data = '''InputText:{},IdRequest:{},NameBot:{},User:{}'''.format(InputText,IdRequest,NameBot,User)
        response = requests.post('http://127.0.0.1:5005/webhooks/rest/webhook', json={"sender": "test", "message": query_text})
        if len(response.json()) == 0:
            results['out_text'] = config_app['parameter']['can_not_res'][random_number]
            # results['out_text'] = "Lỗi Rasa rồi!"
        elif response.json()[0].get("buttons"):
            results['terms'] = response.json()[0]["buttons"]
            results['out_text'] = response.json()[0]["text"]
        elif 'M&EDM000005' in response.json()[0]["text"]:
            results['inventory_status'] = True
            results['out_text'] = response.json()[0]["text"]
        else:
            results['out_text'] = response.json()[0]["text"]
        print('========rasa done!=========')
    if results['out_text'] == "LLM_predict":
        logging.info("------------llm------------")
        logging.info(f"User: {query_text}")  
        # Initialize variables     
        global response_elsatic
        demands = {'object': {}}
        flag = 0
        products = []
        product_name = []
        # Assume df and find_closest_match, extract_info, search_db, initialize_chat_conversation
        list_product = df['GROUP_PRODUCT_NAME'].unique()
        product = find_closest_match(query_text, list_product)
        pattern = re.compile(r'\b(1|2|3|4|5|6|7|8|9|10|nhất|một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười)\b', re.IGNORECASE)
        print('check save_elsatic',response_elsatic)
        if product: 
            print("check product", product)
            demands = extract_info(query_text)
            product_name = demands['object']
            print("= = = = result few short = = = =:", demands)
            product_dict, response_rules, products = search_db(demands)
            response_elsatic = product_dict
            flag = 1
        elif pattern.search(query_text):
            match = pattern.search(query_text)
            matched_string = match.group()
            # Convert to integer if it is a word, else convert directly
            if matched_string.isdigit():
                number = matched_string
            else:
                number = word_to_digit(matched_string)
            string_new = query_text + ' '+ response_elsatic.get(number)
            print('check input query new', string_new)
            demands = extract_info(string_new)
            product_name = demands['object']
            # print("check demands in chat", demands)
            product_dict,response_rules, products = search_db(demands)
            flag = 1
        else:
            input_text = f"chúng tôi không kinh doanh và tìm thấy {query_text} mà bạn muốn tìm. KHÔNG BÁN SẢN PHẨM KHÁC.Tôi có một số đề xuất mới cho bạn"
            flag = 0
        if flag == 0:
            response_rules = ''
            print("check tivi", input_text)
            conversation = initialize_chat_conversation_2(conversation_messages_conv, conversation_messages_snippets, response_rules)
            result = conversation.predict(input = input_text)
        else:
            print('= = = = response_rules = = = = :',response_rules)
            conversation = initialize_chat_conversation(conversation_messages_conv, conversation_messages_snippets, response_rules)
            result = conversation.predict(input = query_text)
        
        print('======conversation_predict======')
        t1 = time.time()
        result = conversation.predict(input = query_text)
        print("time predict conver: ", time.time() - t1)
        results['out_text'] = result
        results['products'] = products
        if len(demands['object']) >= 1:
            results['object_product'] = demands['object'][0]
            results['terms'].append({
                "payload": "similarity_status_true",
                "title": "Bạn muốn tìm kiếm sản phẩm tương tự?"
                })
        # except:
        #     results['out_text'] = config_app['parameter']['can_not_res'][random_number]
    # Save DB
    conversation_messages_conv = conversation.memory.memories[0].chat_memory.messages
    conversation_messages_snippets = conversation.memory.memories[1].chat_memory.messages
    if type == "rasa":
        conversation_messages_conv.append(HumanMessage(content=query_text))
        conversation_messages_conv.append(AIMessage(content=results['out_text']))
        conversation_messages_snippets.append(HumanMessage(content=query_text))
        conversation_messages_snippets.append(AIMessage(content=results['out_text']))

    messages_conv = messages_to_dict(conversation_messages_conv)
    messages_snippets  = messages_to_dict(conversation_messages_snippets)

    with Path(path_messages + "/messages_conv.json").open("w",encoding="utf-8") as f:
        json.dump(messages_conv, f, indent=4,ensure_ascii=False)
    with Path(path_messages + "/messages_snippets.json").open("w",encoding="utf-8") as f:
        json.dump(messages_snippets, f, indent=4, ensure_ascii=False)
    logging.info(f"Vcc_bot: {results['out_text']}")
    results['out_text'] = results['out_text'].replace("AI: ", "").replace("Assistant: ", "").replace("Support Staff: ","").replace("*","")
    return results






def predict_rasa_llm_for_image(objects, IdRequest, NameBot, User,type = 'image'):
    User = str(User)
    logging.info("----------------NEW_SESSION--------------")
    logging.info(f"User: {User}")
    logging.info(f"InputText: {objects}")
    print("----------------predict_rasa_llm_for_image--------------")
    print("GuildID  = ", IdRequest)
    print("InputText  = ", objects)
    query_text = 'tôi cần tìm sản phẩm '
    for ob in objects:
        query_text += ob + ','
        
    print('query_text_image:',query_text)
    path_messages = config_app["parameter"]["DB_MESSAGES"] + str(NameBot) + "/" +  str(User) + "/" + str(IdRequest)
    if not os.path.exists(path_messages):
        os.makedirs(path_messages)

    # Load memory
    try:
        with Path(path_messages + "/messages_conv.json").open("r") as f:
            loaded_messages_conv = json.load(f)
        with Path(path_messages + "/messages_snippets.json").open("r") as f:
            loaded_messages_snippets = json.load(f)
        conversation_messages_snippets = ChatMessageHistory(messages=messages_from_dict(loaded_messages_snippets))
        conversation_messages_conv = ChatMessageHistory(messages=messages_from_dict(loaded_messages_conv))
    except:
        conversation_messages_conv, conversation_messages_snippets = [], []

    results = {'terms':[],'out_text':'', 'inventory_status' : False, 'products': [], 'object_product' :'', 'similarity_status': False}
    
    demands = {'object':objects}
    product_dict, response_rules, products = search_db(demands)
    conversation = initialize_chat_conversation(conversation_messages_conv, conversation_messages_snippets, response_rules)
    result = conversation.predict(input = query_text)
    print('======conversation_predict======')
    t1 = time.time()
    result = conversation.predict(input = query_text)
    print("time predict conver: ", time.time() - t1)
    results['out_text'] = result
    results['products'] = products
    if len(objects) >= 1:
        results['object_product'] =objects[0]
        results['terms'].append({
            "payload": "similarity_status_true",
            "title": "Bạn muốn tìm kiếm sản phẩm tương tự với nhu cầu"
            })
        # except:
        #     results['out_text'] = config_app['parameter']['can_not_res'][random_number]
    # Save DB
    conversation_messages_conv = conversation.memory.memories[0].chat_memory.messages
    conversation_messages_snippets = conversation.memory.memories[1].chat_memory.messages
    if type == "image":
        conversation_messages_conv.append(HumanMessage(content=query_text))
        conversation_messages_conv.append(AIMessage(content=results['out_text']))
        conversation_messages_snippets.append(HumanMessage(content=query_text))
        conversation_messages_snippets.append(AIMessage(content=results['out_text']))

    messages_conv = messages_to_dict(conversation_messages_conv)
    messages_snippets  = messages_to_dict(conversation_messages_snippets)

    with Path(path_messages + "/messages_conv.json").open("w",encoding="utf-8") as f:
        json.dump(messages_conv, f, indent=4,ensure_ascii=False)
    with Path(path_messages + "/messages_snippets.json").open("w",encoding="utf-8") as f:
        json.dump(messages_snippets, f, indent=4, ensure_ascii=False)
    logging.info(f"Vcc_bot: {results['out_text']}")
    results['out_text'] = results['out_text'].replace("AI: ", "").replace("Assistant: ", "").replace("Support Staff: ","").replace("*","")
    return results
