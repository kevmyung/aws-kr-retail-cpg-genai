import boto3
from utils.ssm import parameter_store
from botocore.config import Config
from langchain_community.chat_models import BedrockChat
from langchain.callbacks.base import BaseCallbackHandler
from langchain.embeddings import BedrockEmbeddings
from opensearchpy import OpenSearch, RequestsHttpConnection
from utils.rag import qa_chain, prompt_repo, OpenSearchHybridSearchRetriever

index_name = 'sample_pdf'
region_name = 'us-east-1'
pm = parameter_store(region_name)
opensearch_user_id = pm.get_params(key="opensearch_user_id", enc=False)
opensearch_user_password = pm.get_params(key="opensearch_user_password", enc=True)
opensearch_domain_endpoint = pm.get_params(key="opensearch_domain_endpoint", enc=False)

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

def initialize_services(chat_box, model_id):
    http_auth = (opensearch_user_id, opensearch_user_password)
    os_client = OpenSearch(
        hosts=[{'host': opensearch_domain_endpoint.replace("https://", ""), 'port': 443}],
        http_auth=http_auth, 
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

    retry_config = Config(
            region_name=region_name,
            retries={
                "max_attempts": 10,
                "mode": "standard",
            },
        )
    
    boto3_bedrock = boto3.client("bedrock-runtime", region_name=region_name, config=retry_config)
    stream_handler = StreamHandler(chat_box)
    
    llmchat = BedrockChat(
        model_id=model_id,
        client=boto3_bedrock,
        streaming=True,
        callbacks=[stream_handler],
        model_kwargs={
            "max_tokens": 1024,
            "stop_sequences": ["\n\nHuman"]
        }
    )

    llmemb = BedrockEmbeddings(
        client=boto3_bedrock,
        model_id="amazon.titan-embed-g1-text-02"
    )
    dimension = 1536
    print("Bedrock Embeddings Model Loaded")

    return os_client, llmchat, llmemb

def perform_rag_query(query, chat_box, search_type, model_id, ensemble_weights=None):

    os_client, llmchat, llmemb = initialize_services(chat_box, model_id)
    
    if search_type == "Basic-RAG":
        ensemble_weights = [1.0, 0.0]
    elif search_type == "Hybrid-RAG":
        if ensemble_weights is None:
            ensemble_weights = [0.51, 0.49]
    
    opensearch_hybrid_retriever = OpenSearchHybridSearchRetriever(
        os_client=os_client,
        index_name=index_name,
        llm_text=llmchat, 
        llm_emb=llmemb,
    
        # option for lexical
        minimum_should_match=0,
        filter=[],
    
        # option for search
        fusion_algorithm="RRF", # ["RRF", "simple_weighted"], rank fusion 방식 정의
        ensemble_weights=ensemble_weights, # [for semantic, for lexical], Semantic, Lexical search 결과에 대한 최종 반영 비율 정의
        reranker=False, 
        parent_document = False, # enable parent document
        
        # option for async search
        async_mode=True,
    
        # option for output
        k=5, # 최종 Document 수 정의
        verbose=False,
    )

    system_prompt = prompt_repo.get_system_prompt()
    qa = qa_chain(
        llm_text=llmchat,
        retriever=opensearch_hybrid_retriever,
        system_prompt=system_prompt,
        return_context=True,
        verbose=False
    )

    response, contexts = qa.invoke(query=query)
    return response, contexts
