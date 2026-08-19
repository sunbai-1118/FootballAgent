# Docker 基础设施 —— AI Agent 多模态检索

为足球资讯 Agent 提供向量库与嵌入模型服务。**Embedding 模型与 Qdrant 全部部署在 Docker 中;MySQL 保持本机运行,不在此部署。**

## 服务清单

| 服务 | 容器 | 端口 | 模型 | 接口 |
|------|------|------|------|------|
| Qdrant 向量库 | `soccer-news-qdrant` | 6335 (REST) / 6336 (gRPC) | - | REST API |
| 文本嵌入 | `soccer-news-text-embedding` | 8001 | bge-small-zh-v1.5 (512维) | `POST /embed/text` |
| 图片嵌入(多模态) | `soccer-news-image-embedding` | 8002 | Chinese-CLIP (512维) | `POST /embed/text` / `POST /embed/image` |

> compose 项目名为 **`soccer-news-agent`**,唯一命名。
> Qdrant 使用**独立端口 6335/6336** 与**独立数据卷 `soccer_news_qdrant_data`**,与本机 data-agent 项目(端口 6333/6334、卷 `docker_qdrant_data`)完全隔离。
> 嵌入模型缓存卷固定为 `docker_hf_cache` / `docker_hf_cache_img`,重建项目不会重复下载模型。

## 启动

```bash
cd docker

# (可选)国内网络加速:复制 .env.example 为 .env 并设置 HF_ENDPOINT=https://hf-mirror.com
# 首次构建会下载模型,耗时取决于网络;模型缓存在 volume 中,后续重启不重复下载
docker compose up -d --build

# 查看状态
docker compose ps

# 查看日志(首次启动观察模型下载进度)
docker compose logs -f text-embedding
docker compose logs -f image-embedding
```

## 验证

```bash
# Qdrant
curl http://localhost:6333/healthz

# 文本嵌入(bge)
curl -X POST http://localhost:8001/embed/text \
  -H "Content-Type: application/json" \
  -d '{"texts": ["曼联逆转利物浦"]}'
# -> {"vectors": [[0.xxx, ... 512 个 ...]]}

# CLIP 文本编码
curl -X POST http://localhost:8002/embed/text \
  -H "Content-Type: application/json" \
  -d '{"texts": ["欧冠决赛的精彩瞬间"]}'

# CLIP 图片编码(传数据库中的真实图片 URL)
curl -X POST http://localhost:8002/embed/image \
  -H "Content-Type: application/json" \
  -d '{"images": ["https://xxx.com/a.jpg"]}'
# -> {"vectors": [[0.xxx, ...]] | [null]}(URL 加载失败返回 null)
```

## 停止 / 清理

```bash
docker compose down          # 停止并移除容器(保留数据卷)
docker compose down -v       # 同时删除数据卷(向量库与模型缓存一并清除,慎用)
docker compose build --no-cache   # 强制重建镜像(更新依赖后)
```

## 说明

- **CPU 版 torch**:两个嵌入服务均使用 `--index-url https://download.pytorch.org/whl/cpu` 安装 CPU 版 torch,镜像体积可控、可在无 GPU 机器运行。
- **国内下载加速**:模型从 HuggingFace 下载;`.env` 设 `HF_ENDPOINT=https://hf-mirror.com` 后 `docker compose` 自动注入。
- **后端连接地址**:后端 `config/rag_conf.py` 默认 `QDRANT_URL=http://localhost:6333`、`TEXT_EMBEDDING_URL=http://localhost:8001`、`IMAGE_EMBEDDING_URL=http://localhost:8002`,如需修改在 `.env` 中覆盖。
