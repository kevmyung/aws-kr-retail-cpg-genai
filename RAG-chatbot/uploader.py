import os
import boto3
import re
import json
import pdfplumber
from utils.ssm import parameter_store
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from botocore.config import Config
from langchain_core.documents import Document
from langchain_community.embeddings import BedrockEmbeddings
from langchain_community.vectorstores import OpenSearchVectorSearch

index_name = 'sample_pdf'
region_name = 'us-east-1'
pm = parameter_store(region_name)
opensearch_user_id = pm.get_params(key="opensearch_user_id", enc=False)
opensearch_user_password = pm.get_params(key="opensearch_user_password", enc=True)
opensearch_domain_endpoint = pm.get_params(key="opensearch_domain_endpoint", enc=False)

def setup_opensearch_client():
    http_auth = (opensearch_user_id, opensearch_user_password)
    os_client = OpenSearch(
                hosts=[{'host': opensearch_domain_endpoint.replace("https://", ""), 'port': 443}],
                http_auth=http_auth, 
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection
            )
    return os_client
    
os_client = setup_opensearch_client()

retry_config = Config(
    region_name=region_name,
    retries={
        "max_attempts": 10,
        "mode": "standard",
    },
)
boto3_bedrock = boto3.client("bedrock-runtime", region_name=region_name, config=retry_config)

llmemb = BedrockEmbeddings(
    client=boto3_bedrock,
    model_id="amazon.titan-embed-g1-text-02"
)

http_auth = (opensearch_user_id, opensearch_user_password)
vector_db = OpenSearchVectorSearch(
    index_name=index_name,
    opensearch_url=opensearch_domain_endpoint,
    embedding_function=llmemb,
    http_auth=http_auth,
)

# PDF에서 cid를 추출해서 ASCII 문자로 변환하는 함수
def text_pruner(text, current_pdf_file):
    def replace_cid(match):
        ascii_num = int(match.group(1))
        try:
            return chr(ascii_num)
        except:
            return ''  # 변환 실패 시 빈 문자열로 처리
    cid_pattern = re.compile(r'\(cid:(\d+)\)')
    return re.sub(cid_pattern, replace_cid, text)

# PDF 파일 처리 함수
def process_pdf(pdf_file):
    docs = []
    source_name = pdf_file.name
    type_name = source_name.split(' ')[-1].replace('.pdf', '')

    with pdfplumber.open(pdf_file) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                pruned_text = text_pruner(page_text, pdf_file)
            else:
                pruned_text = ""
            if len(pruned_text) >= 20:  
                doc = Document(
                    page_content=pruned_text.replace('\n', ' '),
                    metadata={
                        "source": source_name,
                        "type": type_name,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                docs.append(doc)
    if docs:
        load_document(docs)

def load_document(docs):
    vector_db.add_documents(docs)
    print("Done")


# 인덱스 생성 및 관리
def manage_index(os_client):
    with open('index_template.json', 'r') as f:
        index_body = json.load(f)
        
    exists = os_client.indices.exists(index_name)
    if exists:
        os_client.indices.delete(index=index_name)
    else:
        os_client.indices.create(index_name, body=index_body)

def upload_and_process_file(uploaded_file):
    try:
        print("File uploaded:", uploaded_file.name)
        manage_index(os_client)
        process_pdf(uploaded_file)
        return True
    except Exception as e:
        print(f"Error processing file: {{e}}")
        return False
