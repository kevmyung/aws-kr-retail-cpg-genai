import os
import boto3
import json
import base64
from langchain.vectorstores import FAISS
from io import BytesIO


#Bedrock을 호출하여 이미지, 텍스트 또는 둘 다에서 벡터를 가져옵니다.
def get_multimodal_vector(input_image_base64=None, input_text=None):
    
    session = boto3.Session(
        profile_name=os.environ.get("BWB_PROFILE_NAME")
    ) #AWS 자격 증명에 사용할 프로필 이름 설정
    
    bedrock = session.client(
        service_name='bedrock-runtime', #Bedrock client 생성
        region_name=os.environ.get("BWB_REGION_NAME"),
        endpoint_url=os.environ.get("BWB_ENDPOINT_URL")
    )
    
    request_body = {}
    
    if input_text:
        request_body["inputText"] = input_text
        
    if input_image_base64:
        request_body["inputImage"] = input_image_base64
    
    body = json.dumps(request_body)
    
    response = bedrock.invoke_model(
    	body=body, 
    	modelId="amazon.titan-embed-image-v1", 
    	accept="application/json", 
    	contentType="application/json"
    )
    
    response_body = json.loads(response.get('body').read())
    
    embedding = response_body.get("embedding")
    
    return embedding


#파일에서 벡터를 생성합니다
def get_vector_from_file(file_path):
    with open(file_path, "rb") as image_file:
        input_image_base64 = base64.b64encode(image_file.read()).decode('utf8')
    
    vector = get_multimodal_vector(input_image_base64 = input_image_base64)
    
    return vector


#디렉터리에서 (경로, 벡터) 튜플 목록을 생성합니다
def get_image_vectors_from_directory(path):
    items = []
    
    for file in os.listdir("images"):
        file_path = os.path.join(path,file)
        
        vector = get_vector_from_file(file_path)
        
        items.append((file_path, vector))
        
    return items


#애플리케이션에서 사용할 인메모리 벡터 저장소를 생성하고 반환합니다
def get_index(): 

    image_vectors = get_image_vectors_from_directory("images")
    
    text_embeddings = [("", item[1]) for item in image_vectors]
    metadatas = [{"image_path": item[0]} for item in image_vectors]
    
    index = FAISS.from_embeddings(
        text_embeddings=text_embeddings,
        embedding = None,
        metadatas = metadatas
    )
    
    return index


#파일 바이트에서 base64로 인코딩된 문자열 가져오기
def get_base64_from_bytes(image_bytes):
    
    image_io = BytesIO(image_bytes)
    
    image_base64 = base64.b64encode(image_io.getvalue()).decode("utf-8")
    
    return image_base64


#제공된 검색어 및/또는 검색 이미지를 기반으로 이미지 목록을 가져옵니다
def get_similarity_search_results(index, search_term=None, search_image=None):
    
    search_image_base64 = (get_base64_from_bytes(search_image) if search_image else None)

    search_vector = get_multimodal_vector(input_text=search_term, input_image_base64=search_image_base64)
    
    results = index.similarity_search_by_vector(embedding=search_vector)
    
    results_images = []
    
    for res in results: #리스트에 이미지 로드
        
        with open(res.metadata['image_path'], "rb") as f:
            img = BytesIO(f.read())
        
        results_images.append(img)
    
    
    return results_images
