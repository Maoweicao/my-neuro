import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"  # 禁用网络连接
os.environ["HF_DATASETS_OFFLINE"] = "1"  # 禁用数据集网络连接
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder
import chromadb
import uvicorn

# 加载模型
print("正在加载用于RAG的模型和向量数据库...")
try:
    # Embedding模型, 用于将文本转为向量
    embedding_model = SentenceTransformer("shibing624/text2vec-base-chinese", cache_folder=r"models_for_rag")
    # CrossEncoder模型, 用于重排以得到更精确的文本
    cross_encoder = CrossEncoder('cross-encoder/mmarco-mMiniLMv2-L12-H384-v1', cache_folder=r"models_for_rag")
    # 向量数据库
    chromadb_client = chromadb.PersistentClient('memory.db')
    chromadb_collection = chromadb_client.get_or_create_collection(name='default')
    print("加载完成!")
except Exception as e:
    print(f"加载失败: {str(e)}")
    raise

# 数据模型
class RagRequest(BaseModel):
    query: str

class UpdateDatabase(BaseModel):
    chunks: List[str]
    counts: int


def embed_chunk(chunk: str) -> List[float]:
    """索引 - 对切分后的文本进行向量化"""
    embedding = embedding_model.encode(chunk)
    return embedding.tolist()
    
def retrieve(query: str, top_k: int) -> List[str]:
    """召回 - 从向量库中取出与query最匹配的top_k条文本"""
    query_embedding = embed_chunk(query)
    results = chromadb_collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    documents = results['documents']
    return documents[0] if documents is not None else [] 

def rerank(query: str, retrieved_chunks: List[str], top_k: int) -> List[str]:
    """重排 - 从召回的文本中进一步获取与query最匹配的top_k条文本"""
    pairs = [(query, chunk) for chunk in retrieved_chunks]
    scores = cross_encoder.predict(pairs)

    chunk_with_score_list = list(zip(retrieved_chunks, scores))
    chunk_with_score_list.sort(key=lambda pair: pair[1], reverse=True)
    return [chunk for chunk, score in chunk_with_score_list[:top_k] if score >= -5]

def save_embeddings(chunks: List[str], embeddings: List[List[float]], counts: int) -> None:
    """保存到向量数据库中"""
    ids = [str(i+counts) for i in range(len(chunks))]
    chromadb_collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=ids
    )
    print('数据更新成功')


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/')
def root() -> Dict[str, str]:
    return {'hello':'rag'}

@app.post('/rag/output')
async def output(request: RagRequest) -> List[str]:
    retrieved_chunks = retrieve(request.query, 10)
    reranked_chunks = rerank(request.query, retrieved_chunks, 3)
    return reranked_chunks

@app.post('/rag/update')
async def update(request: UpdateDatabase) -> int:
    """进行分片和索引操作, 将文档数据放进向量库"""
    chunks = request.chunks[request.counts:]
    embeddings = [embed_chunk(chunk) for chunk in chunks]
    save_embeddings(chunks, embeddings, request.counts)
    return len(chunks)

# 健康检查
@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}

if __name__ == "__main__":
    print("启动服务器...")
    uvicorn.run(app, host="0.0.0.0", port=6600, log_level="info")