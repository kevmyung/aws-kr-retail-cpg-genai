import streamlit as st #모든 Streamlit 명령은 "st" 별칭을 통해 사용할 수 있습니다.
import image_search_lib_kr as glib #로컬 라이브러리 스크립트에 대한 참조


st.set_page_config(page_title="Image Search", layout="wide") #HTML 제목
st.title("Image Search") #페이지 제목


if 'vector_index' not in st.session_state: #벡터 인덱스가 아직 생성되지 않았는지 확인합니다.
    with st.spinner("Indexing images..."): #이 블록의 코드가 실행되는 동안 스피너를 표시합니다.
        st.session_state.vector_index = glib.get_index() #지원 라이브러리를 통해 인덱스를 검색하고 앱의 세션 캐시에 저장합니다.


search_images_tab, find_similar_images_tab = st.tabs(["Image search", "Find similar images"])


with search_images_tab:

    search_col_1, search_col_2 = st.columns(2)

    with search_col_1:
        input_text = st.text_input("Search for:") #레이블이 없는 여러 줄 텍스트 상자 표시하기
        search_button = st.button("Search", type="primary") #기본 버튼 표시

    with search_col_2:
        if search_button: #버튼이 클릭될 때 이 if 블록의 코드가 실행됩니다.
            st.subheader("Results")
            with st.spinner("Searching..."): #이 블록의 코드가 실행되는 동안 스피너를 표시합니다.
                response_content = glib.get_similarity_search_results(index=st.session_state.vector_index, search_term=input_text)
                
                for res in response_content:
                    st.image(res, width=250)


with find_similar_images_tab:
    
    find_col_1, find_col_2 = st.columns(2)

    with find_col_1:
    
        uploaded_file = st.file_uploader("Select an image", type=['png', 'jpg'])
        
        if uploaded_file:
            uploaded_image_preview = uploaded_file.getvalue()
            st.image(uploaded_image_preview)
    
        find_button = st.button("Find", type="primary") #기본 버튼 표시

    with find_col_2:
        if find_button: #버튼이 클릭될 때 이 if 블록의 코드가 실행됩니다.
            st.subheader("Results")
            with st.spinner("Finding..."): #이 블록의 코드가 실행되는 동안 스피너를 표시합니다.
                response_content = glib.get_similarity_search_results(index=st.session_state.vector_index, search_image=uploaded_file.getvalue())
                
                #st.write(response_content) #표를 사용하여 텍스트가 줄 바꿈되도록 합니다.
                
                for res in response_content:
                    st.image(res, width=250)
    
            
        