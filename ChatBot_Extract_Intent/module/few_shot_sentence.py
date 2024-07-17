from langchain_community.chat_models import ChatOpenAI
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.prompts.prompt import PromptTemplate
from config_app.config import get_config
from langchain.chains import LLMChain
config_app = get_config()
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import logging, os
os.environ['OPENAI_API_KEY'] = config_app["parameter"]["openai_api_key"]
llm = ChatOpenAI(model_name=config_app["parameter"]["gpt_model_to_use"], temperature=config_app["parameter"]["temperature"])

def split_sentences(text_input, examples):
    example_formatter_template = """
        Input command from user: {input_text}
        The information extracted from above command:\n
        ----
        object: {object}
        value: {value}
        power: {power}
        weight: {weight}
        volume: {volume}
        intent: {intent}
    """

    example_prompt = PromptTemplate(
        input_variables=["input_text", "object", "value", "power", "weight", "volume", "intent"],
        template=example_formatter_template,
    )

    few_shot_prompt = FewShotPromptTemplate(
        # These are the examples we want to insert into the prompt.
        examples=examples,
        # This is how we want to format the examples when we insert them into the prompt.
        example_prompt=example_prompt,
        # The prefix is some text that goes before the examples in the prompt.
        prefix="Extract detailed information for an input command asking. Return the corresponding object. Below are some examples:",
        # The suffix is some text that goes after the examples in the prompt.
        # Usually, this is where the user input will go
        suffix="Input command from user: {input_text}\nThe information extracted from above command:",
        # The input variables are the variables that the overall prompt expects.
        input_variables=["input_text"],
        # The example_separator is the string we will use to join the prefix, examples, and suffix together with.
        example_separator="\n\n",
    )

    # Print the formatted prompt for debugging purposes (optional)
    # print(few_shot_prompt.format(input_text="Mua den nang luong mat troi giá 15 triệu"))

    chain = LLMChain(llm=llm, prompt=few_shot_prompt)

    result = chain.run(input_text=text_input)
    
    return result.lower()

def correct_sentences(text_input, examples):
    example_formatter_template = """
        input text: {input_text}
        ----
        {command}
    """
    example_prompt = PromptTemplate(
        input_variables=["input_text", "command"],
        template=example_formatter_template,
    )
    few_shot_prompt = FewShotPromptTemplate(
        # These are the examples we want to insert into the prompt.
        examples=examples,
        # This is how we want to format the examples when we insert them into the prompt.
        example_prompt=example_prompt,
        # The prefix is some text that goes before the examples in the prompt.
        prefix="Please correct the following sentence for correct spelling in Vietnamese",
        # The suffix is some text that goes after the examples in the prompt.
        suffix="input command from user: {input_text}\n",
        # The input variables are the variables that the overall prompt expects.
        input_variables=["input_text"],
        # The example_separator is the string we will use to join the prefix, examples, and suffix together with.
        example_separator="\n\n",
    )
    # Print the formatted prompt for debugging purposes (optional)
    chain = LLMChain(llm=llm, prompt=few_shot_prompt)

    result = chain.run(input_text=text_input)
    
    return result.lower()

def extract_info(sentences, examples):
    try:
        s = split_sentences(sentences,examples)
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
        return variables
    except Exception as e:
        s = {'object': sentences, 'power':'', 'values':[''], 'weight': '','volume':'','intent':''}
        print('extract object in few shot', s['object'])
        return s
    
def classify_intent(question):
    # Các intent cần phân loại
    intents = ["giá", "công suất", "dung tích", "khối lượng", "so sánh", "số lượng","thông tin chung"]

    # Tạo prompt để phân loại câu hỏi
    prompt_template = """
    Phân loại câu hỏi sau đây chỉ một trong các loại sau: {intents}.

    Câu hỏi: {question}

    Loại:
    """

    prompt = PromptTemplate(
        input_variables=["intents", "question"],
            template=prompt_template,
    )

    # Sử dụng OpenAI làm LLM
    llm = ChatOpenAI(model_name=config_app["parameter"]["gpt_model_to_use"], temperature=config_app["parameter"]["temperature"],api_key=config_app["parameter"]["openai_api_key"])

    # Tạo LLMChain để phân loại câu hỏi
    chain = LLMChain(
        llm=llm,
        prompt=prompt
    )

    # Hàm phân loại câu hỏi
    result = chain.run({
        "intents": ", ".join(intents),
        "question": question
    })
    print(result)
    json_value = {}
    examples = []
    if result.lower() == "giá":
        examples = config_app['parameter']['example_price']
        json_value =  extract_info(question, examples)
    elif result.lower() == "công suất":
        examples = config_app['parameter']['example_power']
        json_value =  extract_info(question, examples)
    elif result.lower() == "khối lượng":
        examples = config_app['parameter']['example_weight']
        json_value =  extract_info(question, examples)
    elif result.lower() == "dung tích":
        examples = config_app['parameter']['example_volume']
        json_value =  extract_info(question, examples)
    elif result.lower() == "so sánh":
        examples = config_app['parameter']['example_compare']
        json_value =  extract_info(question, examples)
    elif result.lower() == "số lượng":
        examples = config_app['parameter']['example_quantity']
        json_value =  extract_info(question, examples)
    else:
        examples = config_app['parameter']['example_descriptions']
        json_value =  extract_info(question, examples)
    print(examples)
    return json_value

    # Ví dụ sử dụng
# question = "Tôi quan tâm tới sản phẩm đèn năng lượng mặt trời và Thiết bị Wifi có giá tiết kiệm"
# print(classify_intent(question))   

def correct_spelling_input(sentences):
    print('sentences', sentences)
    examples = config_app['parameter']['example_correct_spelling']
    try:
        res_correct = correct_sentences(sentences, examples)
        results = res_correct.split(':')
        print('check command fewshot', results)
        if len(results) == 1:
            command = results[0]
        else:
            command = results[1]
        return command
    except Exception as e:
        return sentences

def find_closest_match(input_str, list_product):
    match = process.extractOne(input_str, list_product, scorer=fuzz.partial_ratio)
    print(f"Có phải bạn tìm kiếm sản phẩm {match[0]}")
    print("Độ match:", match[1])
    # if match[1] >= 60:
    #     return match[0]
    # else:
    #     return 0
    return match
    
