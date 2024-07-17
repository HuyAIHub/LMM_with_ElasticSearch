from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from config_app.config import get_config
config_app = get_config()

# Các intent cần phân loại
intents = ["giá, công suất, dung tích, khối lượng", "so sánh", "số lượng", "thông tin chung"]

# Tạo prompt để phân loại câu hỏi
prompt_template = """
Phân loại câu hỏi sau đây vào một trong các loại sau: {intents}.

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
def classify_question(question):
    result = chain.run({
        "intents": ", ".join(intents),
        "question": question
    })
    return result.strip()

# Ví dụ sử dụng
question = "các sản phẩm dưới 10 triệu"
classified_intent = classify_question(question)
print(f"Intent: {classified_intent}")
