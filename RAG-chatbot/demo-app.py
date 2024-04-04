from basic import get_conversation
import streamlit as st
from uploader import upload_and_process_file
from rag import perform_rag_query

st.set_page_config(layout="wide")
st.title("Bedrock Q&A Chatbot")

model_options = [
    "anthropic.claude-instant-v1",
    "anthropic.claude-v2:1",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "anthropic.claude-3-sonnet-20240229-v1:0"
]
st.sidebar.title("Model Selection")
selected_model = st.sidebar.selectbox("Type of Cluade Model", model_options, index=3)

st.sidebar.title("Hybrid-RAG Search Balance")
semantic_weight = st.sidebar.slider("Semantic Search Strength", 0.0, 1.0, 0.51, 0.01, help="Adjust the strength of semantic search. The remaining weight is applied to lexical search.")

uploaded_file = st.file_uploader("파일을 업로드하세요", type=["pdf"])
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
        ensemble_weights = [1.0, 0.0]
        st.session_state.stream_handler.reset_accumulated_text()
        response, contexts = perform_rag_query(prompt, st.session_state.stream_handler.placeholder, search_type, selected_model, ensemble_weights)
        st.write("RAG에 활용된 contexts:")
        for doc in contexts:
            st.write(f"- Source: {doc.metadata['source']}")
            st.write(doc.page_content)
            st.write("---")
    elif search_type == "Hybrid-RAG":
        ensemble_weights = [semantic_weight, 1 - semantic_weight]
        st.session_state.stream_handler.reset_accumulated_text()
        response, contexts = perform_rag_query(prompt, st.session_state.stream_handler.placeholder, search_type, selected_model, ensemble_weights)
        st.write("RAG에 활용된 contexts:")
        for doc in contexts:
            st.write(f"- Source: {doc.metadata['source']}")
            st.write(doc.page_content)
            st.write("---")

if st.button("검색"):
    search_documents(search_type, prompt)

if uploaded_file is not None:
    res = upload_and_process_file(uploaded_file)
    if res:
        st.success("파일이 성공적으로 처리됐습니다.")
    else:
        st.error("파일 처리 중 오류가 발생했습니다.")
