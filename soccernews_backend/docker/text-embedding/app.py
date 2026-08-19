"""bge 文本嵌入服务(供后端 agents/embeddings.py 调用)

接口:
  POST /embed/text  {"texts": ["...", ...]} -> {"vectors": [[512 维, ...], ...]}
  GET  /health

模型:默认 BAAI/bge-small-zh-v1.5,输出 512 维,L2 归一化。
"""
import os

from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

MODEL = os.getenv("MODEL", "BAAI/bge-small-zh-v1.5")
model = SentenceTransformer(MODEL)
model.eval()

app = FastAPI(title="text-embedding (bge)")


class TextRequest(BaseModel):
    texts: list[str]


@app.post("/embed/text")
def embed_text(req: TextRequest):
    vectors = model.encode(req.texts, normalize_embeddings=True).tolist()
    return {"vectors": vectors}


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL}
