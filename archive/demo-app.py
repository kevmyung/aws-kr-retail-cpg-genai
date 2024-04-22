from RAGchatbot.basic import get_conversation
import streamlit as st

st.set_page_config(layout="wide")
st.title("Bedrock Q&A Chatbot")

model_options = [
    "anthropic.claude-instant-v1",
    "anthropic.claude-v2:1",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "anthropic.claude-3-sonnet-20240229-v1:0"
]
st.sidebar.title("Model Selection (Claude)")
selected_model = st.sidebar.selectbox("모델 선택", model_options, index=3)

uploaded_file = st.file_uploader("파일을 업로드하세요", type=["pdf"], accept_multiple_files=False)
prompt = st.text_input("프롬프트를 입력하세요.")
search_type = st.radio("Search Type", ["Basic", "Basic-RAG", "Hybrid-RAG"])

chat_box = st.empty()

if 'conversation' not in st.session_state or 'stream_handler' not in st.session_state:  
    st.session_state.conversation, st.session_state.stream_handler = get_conversation(chat_box, selected_model)

def search_documents(search_type: str, prompt: str):
    if search_type == "Basic":
        st.session_state.stream_handler.reset_accumulated_text()
        st.session_state.conversation.predict(input=prompt)
    elif search_type == "Basic-RAG":
        st.write(f"문서 기본 검색: {prompt}")
    elif search_type == "Hybrid-RAG":
        st.write(f"하이브리드 검색: {prompt}")

if st.button("검색"):
    search_documents(search_type, prompt)
