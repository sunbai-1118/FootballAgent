"""Chinese-CLIP 多模态嵌入服务(供后端 agents/embeddings.py 调用)

接口:
  POST /embed/text   {"texts": ["...", ...]} -> {"vectors": [[512 维, ...], ...]}  # CLIP 文本编码,与图片同空间
  POST /embed/image  {"images": ["http://.../a.jpg", ...]} -> {"vectors": [[512 维] | null, ...]}
                     # CLIP 图片编码;某个 URL 加载失败时对应位置返回 null
  GET  /health

模型:默认 OFA-Sys/chinese-clip-vit-base-patch16,输出 512 维,L2 归一化。
图片加载失败返回 null,由后端填零向量 + has_image=false 降级,不影响文本检索。
"""
import concurrent.futures
import io
import os
import urllib.request

import torch
from fastapi import FastAPI
from PIL import Image
from pydantic import BaseModel
from transformers import ChineseCLIPModel, ChineseCLIPProcessor

MODEL = os.getenv("MODEL", "OFA-Sys/chinese-clip-vit-base-patch16")
model = ChineseCLIPModel.from_pretrained(MODEL)
processor = ChineseCLIPProcessor.from_pretrained(MODEL)
model.eval()

app = FastAPI(title="image-embedding (Chinese-CLIP)")


class TextRequest(BaseModel):
    texts: list[str]


class ImageRequest(BaseModel):
    images: list[str]  # 图片 URL


def _load_image(url: str) -> Image.Image | None:
    """按 URL 加载图片为 RGB;失败返回 None"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return Image.open(io.BytesIO(resp.read())).convert("RGB")
    except Exception:
        return None


def _normalize(features: torch.Tensor) -> torch.Tensor:
    return features / features.norm(dim=-1, keepdim=True)


@app.post("/embed/text")
def embed_text(req: TextRequest):
    inputs = processor(text=req.texts, return_tensors="pt", padding=True)
    with torch.no_grad():
        # 新版 transformers 返回 BaseModelOutputWithPooling,取 pooler_output 得到投影后的向量
        features = _normalize(model.get_text_features(**inputs).pooler_output)
    return {"vectors": features.tolist()}


@app.post("/embed/image")
def embed_image(req: ImageRequest):
    # 并发拉取整批图片,避免逐个串行导致请求超时
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        images = list(pool.map(_load_image, req.images))
    vectors = []
    for img in images:
        if img is None:
            vectors.append(None)  # 加载失败:置 null,由调用方降级
            continue
        inputs = processor(images=img, return_tensors="pt")
        with torch.no_grad():
            features = _normalize(model.get_image_features(**inputs).pooler_output)
        vectors.append(features.squeeze(0).tolist())
    return {"vectors": vectors}


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL}
