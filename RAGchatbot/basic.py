import streamlit as st
from langchain_community.chat_models import BedrockChat
from langchain.callbacks.base import BaseCallbackHandler
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory


###### 스트리밍 응답 처리 ######
class StreamHandler(BaseCallbackHandler):
    def __init__(self, placeholder):
        super().__init__()
        self.placeholder = placeholder
        self.accumulated_text = ""

    def reset_accumulated_text(self):
        self.accumulated_text = ""
        self.placeholder.text(self.accumulated_text)

    def on_llm_new_token(self, token: str, **kwargs):
        self.accumulated_text += token
        self.placeholder.text(self.accumulated_text)

def get_conversation(chat_box, model_id):
    stream_handler = StreamHandler(chat_box)
    
    llmchat = BedrockChat(
        model_id=model_id,
        streaming=True,
        region_name="us-west-2",
        callbacks=[stream_handler], 
        model_kwargs={
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "temperature": 0,
            "top_k": 350,
            "top_p": 0.999
        }
    )

    prompt_template = """
    Human: You're an advanced AI assistant. Please provide a short answer about my query.
    <context>
    {history}
    </context>
    query - {input}
    
    Assistant:
    """

    PROMPT = PromptTemplate(
        template=prompt_template,
        input_variables=['history', 'input']
    )

    conversation = ConversationChain(
        llm=llmchat, 
        verbose=False, 
        memory=ConversationBufferMemory(human_prefix="Human", ai_prefix="Assistant"),
        prompt=PROMPT
    )

    return conversation, stream_handler
