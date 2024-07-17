import os, re
import json
from pathlib import Path
import pandas as pd
import random
from config_app.config import get_config
from langchain.memory import ChatMessageHistory
from langchain.schema import messages_from_dict, messages_to_dict
from langchain_core.messages import HumanMessage, AIMessage
import requests
from ChatBot_Extract_Intent.elastic_search import search_db
from ChatBot_Extract_Intent.module.few_shot_sentence import classify_intent, find_closest_match, correct_spelling_input
from ChatBot_Extract_Intent.module.llm import initialize_chat_conversation, initialize_chat_conversation_2
import logging, time

random_number = random.randint(0, 4)

config_app = get_config()

save_outtext = {}
data_private = config_app['parameter']['data_private']
df = pd.read_excel(data_private)

def word_to_digit(word):
    word_digit_map = {
        'một': 1, 'hai': 2, 'ba': 3, 'bốn': 4, 'năm': 5,
        'sáu': 6, 'bảy': 7, 'tám': 8, 'chín': 9, 'mười': 10, 'nhất': 1
    }
    return word_digit_map.get(word.lower(), word)


def predict_rasa_llm(inputText, IdRequest, NameBot, User, type='rasa'):
    path_messages = os.path.join(config_app["parameter"]["DB_MESSAGES"], str(NameBot), str(User), str(IdRequest))
    if not os.path.exists(path_messages):
        os.makedirs(path_messages)

    query_text = correct_spelling_input(inputText)

    # Load memory
    try:
        with Path(path_messages + "/messages_conv.json").open("r") as f:
            loaded_messages_conv = json.load(f)
        with Path(path_messages + "/messages_snippets.json").open("r") as f:
            loaded_messages_snippets = json.load(f)
        conversation_messages_snippets = ChatMessageHistory(messages=messages_from_dict(loaded_messages_snippets))
        conversation_messages_conv = ChatMessageHistory(messages=messages_from_dict(loaded_messages_conv))
    except Exception as e:
        print(f"Error loading conversation: {e}")
        conversation_messages_conv, conversation_messages_snippets = [], []

    results = {'terms': [], 'out_text': '', 'inventory_status': False, 'products': [], 'object_product': '', 'similarity_status': False}
    
    if type == 'rasa':
        logging.info("=====rasa=====")
        print('======rasa======')
        conversation = initialize_chat_conversation(conversation_messages_conv, conversation_messages_snippets, "")
        response = requests.post('http://127.0.0.1:5005/webhooks/rest/webhook', json={"sender": "test", "message": query_text})
        if len(response.json()) == 0:
            results['out_text'] = config_app['parameter']['can_not_res'][random_number]
        elif response.json()[0].get("buttons"):
            results['terms'] = response.json()[0]["buttons"]
            results['out_text'] = response.json()[0]["text"]
        elif 'nhập mã' in response.json()[0]["text"]:
            results['inventory_status'] = True
            results['out_text'] = response.json()[0]["text"]
        elif "tìm sản phẩm tương tự" in response.json()[0]["text"]:
            results['similarity_status'] = True
            results['out_text'] = response.json()[0]["text"]
        else:
            results['out_text'] = response.json()[0]["text"]
        
        logging.info(f"+rasa out+:\n{results['out_text']}")
        print('+rasa out+:\n',results['out_text'])
        logging.info("====rasa done!====")
        print('====rasa done!====')
    
    if results['out_text'] == "LLM_predict":
        logging.info("=====LLM=====")
        print('======LLM======')
        # Initialize variables     
        global save_outtext
        demands = {'object': {}}
        products = []
        pattern = re.compile(r'\b(1|2|3|4|5|6|7|8|9|10|nhất|một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười)\b', re.IGNORECASE)
         
        print('check save_elsatic', save_outtext)
        list_product = df["group_name"].unique()
        check_match_product = find_closest_match(query_text, list_product)
        if check_match_product[1] < 40:
            ok = 0
            print(check_match_product)
        else:
            demands = classify_intent(query_text)
            print("= = = = result few short = = = =:", demands)
            product_dict, response_elastic, products, ok = search_db(demands)

        if ok == 0: 
            logging.info("==Conversation2==")
            print('= =  Conversation2  = =')
            response_elastic = ''
            conversation = initialize_chat_conversation_2(conversation_messages_conv, conversation_messages_snippets, response_elastic)
            result = conversation.predict(input=query_text)
        if ok != 0:
            save_outtext = product_dict
            logging.info("==Conversation==")
            print('= =  Conversation  = =')
            conversation = initialize_chat_conversation(conversation_messages_conv, conversation_messages_snippets, response_elastic)
            result = conversation.predict(input=query_text)

        result = conversation.predict(input=query_text)
        results['out_text'] = result.replace("AI: ", "").replace("Assistant: ", "").replace("Support Staff: ", "").replace("*", "")
        results['products'] = products
        if len(demands['object']) >= 1:
            results['object_product'] = demands['object'][0]
            results['terms'].append({
                "payload": "similarity_status_true",
                "title": "Bạn muốn tìm kiếm sản phẩm tương tự?"
            })
        logging.info(f"+LLM out+:\n{results['out_text']}")
        print('+LLM out+:\n',results['out_text'])
        logging.info("=====LLM done!=====")
        print('======LLM done!======')
    
    # save conv
    conversation_messages_conv = conversation.memory.memories[0].chat_memory.messages
    conversation_messages_snippets = conversation.memory.memories[1].chat_memory.messages
    if type == "rasa":
        conversation_messages_conv.append(HumanMessage(content=query_text))
        conversation_messages_conv.append(AIMessage(content=results['out_text']))
        conversation_messages_snippets.append(HumanMessage(content=query_text))
        conversation_messages_snippets.append(AIMessage(content=results['out_text']))

    messages_conv = messages_to_dict(conversation_messages_conv)
    messages_snippets = messages_to_dict(conversation_messages_snippets)

    with Path(path_messages + "/messages_conv.json").open("w", encoding="utf-8") as f:
        json.dump(messages_conv, f, indent=4, ensure_ascii=False)
    with Path(path_messages + "/messages_snippets.json").open("w", encoding="utf-8") as f:
        json.dump(messages_snippets, f, indent=4, ensure_ascii=False)
    
    results['out_text'] = re.sub(r'\([^)]*\)', '', results['out_text'])
    print("result in chat", results)
    return results

def predict_rasa_llm_for_image(objects, IdRequest, NameBot, User,type = 'image'):
    path_messages = os.path.join(config_app["parameter"]["DB_MESSAGES"], str(NameBot), str(User), str(IdRequest))

    if not os.path.exists(path_messages):
        os.makedirs(path_messages)

    query_text = 'tôi cần tìm sản phẩm '
    for ob in objects:
        query_text += ob + ','

    logging.info("---SEARCH_IMAGE---")
    logging.info(f"inputText: {query_text}")

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
    product_dict, response_elastic, products, ok = search_db(demands)
    conversation = initialize_chat_conversation(conversation_messages_conv, conversation_messages_snippets, response_elastic)
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
    
    logging.info(f"Vcc_bot:\n{results['out_text']}")
    results['out_text'] = results['out_text'].replace("AI: ", "").replace("Assistant: ", "").replace("Support Staff: ","").replace("*","")
    print("image search:",results)
    return results



