"""AI 模型配置（多 provider，通过 LLM_PROVIDER 切换）

支持通过环境变量或项目根目录下的 .env 文件配置（示例见 .env.example）。

DeepSeek：
    DEEPSEEK_API_KEY=sk-xxx
    DEEPSEEK_BASE_URL=https://api.deepseek.com
    DEEPSEEK_MODEL=deepseek-chat

Qwen（阿里云百炼 / DashScope，OpenAI 兼容接口）：
    QWEN_API_KEY=sk-xxx
    QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
    QWEN_MODEL=qwen3.7-flash
"""
import os

from dotenv import load_dotenv

load_dotenv()  # 加载项目根目录 .env 文件（若存在）

# ==================== DeepSeek API 配置 ====================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "120"))  # 秒

# ==================== Qwen（阿里云百炼 / DashScope）配置 ====================
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen3.7-flash")
QWEN_TIMEOUT = int(os.getenv("QWEN_TIMEOUT", "120"))  # 秒
# 是否开启 qwen 思考（reasoning）：false 时传 enable_thinking=false，大幅降输出 token（牺牲推理质量）
QWEN_ENABLE_THINKING = os.getenv("QWEN_ENABLE_THINKING", "false").lower() in ("1", "true", "yes", "on")

# 全局 LLM 输出 token 上限（qwen3.7-flash 为推理模型，推理 token 计入输出，
# 默认 4096 给"推理+正文"留足空间，避免正文被截断成空；如换非推理模型可下调）
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
# Verifier 校验节点开关（Agent→Answer→Verifier→检查事实来源→返回）
VERIFIER_ENABLED = os.getenv("VERIFIER_ENABLED", "true").lower() in ("1", "true", "yes", "on")

# AI 系统提示词（可自定义角色设定）
DEEPSEEK_SYSTEM_PROMPT = os.getenv(
    "DEEPSEEK_SYSTEM_PROMPT",
    "你是一个专业的足球资讯助手，精通英超、西甲、意甲、德甲、法甲、中超、欧冠、世界杯等赛事。"
    "请用简洁、专业、热情的中文回答用户关于足球新闻、比赛结果、球队与球员动态、转会传闻、战术分析、积分赛程等问题。"
    "涉及实时比分或最新转会时请提示用户以官方渠道为准。",
)
