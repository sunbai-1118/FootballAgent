"""RAG / 多模态检索与 Agent 配置

Embedding 模型(bge / Chinese-CLIP)与 Qdrant 向量库部署在 Docker 中(见项目根目录 docker/),
后端只通过 HTTP(httpx)调用,不在本地加载模型。

支持通过环境变量或项目根目录 .env 配置(示例见 .env.example):
    LLM_PROVIDER=deepseek
    QDRANT_URL=http://localhost:6333
    TEXT_EMBEDDING_URL=http://localhost:8001
    IMAGE_EMBEDDING_URL=http://localhost:8002
"""
import os

from dotenv import load_dotenv

load_dotenv()  # 加载项目根目录 .env 文件(若存在)

# ==================== 主 LLM ====================
# 默认 DeepSeek;其他 provider 需在 agents/model_factory.py 中扩展分支
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")

# ==================== Qdrant ====================
# 本项目独立部署的 Qdrant(端口 6335/6336),与 data-agent 项目的 6333 完全隔离
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "news_rag")
# bge-small-zh-v1.5 与 chinese-clip-vit-base-patch16 输出维度均为 512
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "512"))

# ==================== 嵌入服务(Docker) ====================
TEXT_EMBEDDING_URL = os.getenv("TEXT_EMBEDDING_URL", "http://localhost:8001")   # bge 文本
IMAGE_EMBEDDING_URL = os.getenv("IMAGE_EMBEDDING_URL", "http://localhost:8002")  # Chinese-CLIP(文本+图片)
EMBED_TIMEOUT = float(os.getenv("EMBED_TIMEOUT", "30"))        # 文本编码超时(秒)
EMBED_TIMEOUT_IMAGE = float(os.getenv("EMBED_TIMEOUT_IMAGE", "120"))  # 图片加载/编码更慢(服务端并发拉图)

# ==================== RAG 检索 ====================
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
# bge 官方建议的检索查询前缀,检索时拼在问题前可提升命中质量
BGE_QUERY_PREFIX = os.getenv(
    "BGE_QUERY_PREFIX", "为这个句子生成表示以用于检索相关文章:"
)

# ==================== Chunk 切片 ====================
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# ==================== 联网搜索 ====================
# 文本搜索:Tavily;图片搜索:SerpAPI google_images(分别走各自 API 额度)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SERPAPI_IMAGE_ENGINE = os.getenv("SERPAPI_IMAGE_ENGINE", "google_images")
WEB_SEARCH_TOP_K = int(os.getenv("WEB_SEARCH_TOP_K", "5"))
IMAGE_SEARCH_TOP_K = int(os.getenv("IMAGE_SEARCH_TOP_K", "4"))
# 图片向量相似度阈值(cosine,0~1):低于该值视为"无匹配",避免返回不相关图片。
# 注意:当前种子数据是 picsum 占位图,CLIP 对占位图分数集中在 ~0.35、无区分度,
# 故默认 0.40(高于占位图峰值)可让 DB 优先拒绝占位图、落到联网取真图;
# 接入真实新闻图后,按实际分布下调(真实相关图文常见 0.25~0.35)。
IMAGE_SIM_THRESHOLD = float(os.getenv("IMAGE_SIM_THRESHOLD", "0.40"))
