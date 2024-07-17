
from typing import Any, Dict, List
from langchain.prompts.prompt import PromptTemplate
from langchain import PromptTemplate
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferWindowMemory, CombinedMemory
from langchain_core.messages.human import HumanMessage

from config_app.config import get_config
from utils.llm_manager import get_llm

config_app = get_config()


class SnippetsBufferWindowMemory(ConversationBufferWindowMemory):
    """
    MemoryBuffer được sử dụng để giữ các đoạn tài liệu. Kế thừa từ ConversationBufferWindowMemory và ghi đè lên
    phương thức Load_memory_variables
    """
    memory_key = 'snippets'
    snippets: list = []
    response_rules = ''

    def __init__(self, *args, **kwargs):
        ConversationBufferWindowMemory.__init__(self, *args, **kwargs)

    def load_memory_variables(self, inputs) -> Dict:
        """Return history buffer."""
        buffer: Any = self.buffer[-self.k * 2 :] if self.k > 0 else []
        string_messages = []
        for m in buffer:
            if isinstance(m, HumanMessage):
                message = f"{m.content}"
                string_messages.append(message)
        string_messages.append(self.response_rules)

        to_return = "\n".join(string_messages)
        return {'snippets': to_return}

def construct_conversation(prompt: str, llm, memory) -> ConversationChain:
    """
    Construct a ConversationChain object
    """
    prompt = PromptTemplate.from_template(template=prompt)
    conversation = ConversationChain(
        llm=llm,
        memory=memory,
        verbose=False,
        prompt=prompt
    )
    return conversation

def initialize_chat_conversation(conv_memory, snippets_memory, response_rules) -> ConversationChain:
    prompt_header = """You are a product information lookup support, your task is to answer customer questions based on the technical paragraphs provided. Note that you need to answer in Vietnamese.
    The following passages may help you answer the questions:
    {snippets}
    If a question is repeated within the conversation, provide a detailed response similar to the initial question.
    Answers display listing, using line break
    Answers concise, and easy to understand to support the customer effectively
    Ensure all your answers are in Vietnamese.
    History chat: {history} 
    Customer: {input}
    """
    if conv_memory == [] and snippets_memory == []:
        conv_memory = ConversationBufferWindowMemory(k=config_app["parameter"]["search_number_messages"], input_key="input")
        snippets_memory = SnippetsBufferWindowMemory(k=config_app["parameter"]["prompt_number_snippets"], response_rules=response_rules, 
                                                     memory_key='snippets', input_key="snippets")
    else:
        conv_memory = ConversationBufferWindowMemory(k=config_app["parameter"]["search_number_messages"], input_key="input", chat_memory=conv_memory)
        snippets_memory = SnippetsBufferWindowMemory(k=config_app["parameter"]["prompt_number_snippets"], response_rules=response_rules, 
                                                     memory_key='snippets', input_key="snippets", chat_memory=snippets_memory)

    memory = CombinedMemory(memories=[conv_memory, snippets_memory])
    llm = get_llm()
    conversation = construct_conversation(prompt_header, llm, memory)
    return conversation

def initialize_chat_conversation_2(conv_memory, snippets_memory, response_rules) -> ConversationChain:
    prompt_header = """
    You are a support staff specializing electronic with products and household appliance as Air conditioner, solar lights. 
    Your task is to answer customer questions based on the knowledge provided 
    Perform your role as effectively as a seasoned salesperson.
    The following knowledge will help you respond to customer queries about products available in the Vietnamese market:
    {snippets}
    Warning: When listing products, use line breaks and number them in order, answers concise, and easy to understand to support the customer effectively.
    If a question is repeated within the conversation, provide a detailed response similar to the initial question.
    Ensure all your answers are in Vietnamese, 
    History chat: {history} 
    Customer: {input}
    """
    if conv_memory == [] and snippets_memory == []:
        conv_memory = ConversationBufferWindowMemory(k=config_app["parameter"]["search_number_messages"], input_key="input")
        snippets_memory = SnippetsBufferWindowMemory(k=config_app["parameter"]["prompt_number_snippets"], response_rules=response_rules, 
                                                     memory_key='snippets', input_key="snippets")
    else:
        conv_memory = ConversationBufferWindowMemory(k=config_app["parameter"]["search_number_messages"], input_key="input", chat_memory=conv_memory)
        snippets_memory = SnippetsBufferWindowMemory(k=config_app["parameter"]["prompt_number_snippets"], response_rules=response_rules, 
                                                     memory_key='snippets', input_key="snippets", chat_memory=snippets_memory)

    memory = CombinedMemory(memories=[conv_memory, snippets_memory])
    llm = get_llm()
    conversation = construct_conversation(prompt_header, llm, memory)
    return conversation
