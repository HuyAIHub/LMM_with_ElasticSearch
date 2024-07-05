import os,re
import random
import pandas as pd
import time
import csv
import numpy as np
from openai import OpenAI
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.prompts.prompt import PromptTemplate
from ChatBot_Extract_Intent.config_app.config import get_config
# from config_app.config import get_config
from langchain.chains import LLMChain
config_app = get_config()
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import logging
import ast
os.environ['OPENAI_API_KEY'] = config_app["parameter"]["openai_api_key"]
llm = ChatOpenAI(model_name=config_app["parameter"]["gpt_model_to_use"], temperature=config_app["parameter"]["temperature"])
client = OpenAI(api_key=config_app["parameter"]["openai_api_key"])
# from langchain_groq import ChatGroq
# llm = ChatGroq(model=config_app["parameter"]["llama3_model_to_use"],api_key=config_app["parameter"]["groq_key"])

def split_sentences(text_input):
    examples = config_app['parameter']['example_input']
    example_formatter_template = """
        input text from user: {input_text}

        correct input and insert command below:
        command: {command}
        object: {object}
        value: {value}
        power: {power}
        weight: {weight}
        volume: {volume}
        intent: {intent}
    """

    example_prompt = PromptTemplate(
        input_variables=["input_text", "command", "object", "value", "power", "weight", "volume", "intent"],
        template=example_formatter_template,
    )

    few_shot_prompt = FewShotPromptTemplate(
        # These are the examples we want to insert into the prompt.
        examples=examples,
        # This is how we want to format the examples when we insert them into the prompt.
        example_prompt=example_prompt,
        # The prefix is some text that goes before the examples in the prompt.
        prefix="Please correct the following sentence for correct spelling and Extract detailed information for user needs. Returns the corresponding object and spell. Here are some examples:",
        # The suffix is some text that goes after the examples in the prompt.
        suffix="input command from user: {input_text}\nThe information extracted and correct spelling from the above command",
        # The input variables are the variables that the overall prompt expects.
        input_variables=["input_text"],
        # The example_separator is the string we will use to join the prefix, examples, and suffix together with.
        example_separator="\n\n",
    )

    chain = LLMChain(llm=llm, prompt=few_shot_prompt)

    result = chain.run(input_text=text_input)
    
    return result.lower()

def extract_info(sentences):
    try:
        print('split_sentences before:',split_sentences(sentences))
        s = split_sentences(sentences).replace('*','')
        print('split_sentences after:',s)
        logging.info(f"split_sentences after: {s}")
        variables = {}
        lines = s.strip().split('\n')
        for line in lines:
            parts = line.split(':')
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key == 'object':
                    # Xử lý phần object
                    # Loại bỏ các dấu ngoặc và khoảng trắng
                    value = value.replace('[', '').replace(']', '').strip()
                    # Tách các giá trị theo dấu phẩy
                    object_list = [item.strip().strip("'") for item in value.split(',') if item.strip()]
                    variables[key] = object_list
                else:
                    variables[key] = value
        print('variables:',variables)
        logging.info(f"after extract info: {variables}")
        return variables
        
    except Exception as e:
        print('===== few short error: {} ======='.format(e))
        s = {'object':[sentences]}
        print('extract object in few shot', s['object'])
        return s
    
def find_closest_match(input_str, list_product):
    match = process.extractOne(input_str, list_product, scorer=fuzz.partial_ratio)
    print(f"Có phải bạn tìm kiếm sản phẩm {match[0]}")
    print("Độ match:", match[1])
    if match[1] >= 55:
        return match[0]
    else:
        return None