"""DeepSeek AI 客户端封装（OpenAI 兼容接口，懒加载）"""
import logging
from typing import List, Tuple

from config.ai_conf import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_SYSTEM_PROMPT,
    DEEPSEEK_TIMEOUT,
)

logger = logging.getLogger(__name__)

_client = None


def get_client():
    """懒加载 AsyncOpenAI 客户端"""
    global _client
    if _client is None:
        if not DEEPSEEK_API_KEY:
            raise RuntimeError(
                "未配置 DEEPSEEK_API_KEY，请在 .env 文件中填写或设置环境变量"
            )
        _client = __import__("openai").AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            timeout=DEEPSEEK_TIMEOUT,
        )
    return _client


async def chat_with_ai(
    message: str,
    history: List[Tuple[str, str]] | None = None,
) -> str:
    """调用 DeepSeek 对话接口

    :param message: 用户当前消息
    :param history: 最近的历史对话 [(user_message, ai_reply), ...]，按时间正序
    :return: AI 回复文本
    """
    messages = [{"role": "system", "content": DEEPSEEK_SYSTEM_PROMPT}]
    if history:
        for user_msg, ai_reply in history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": ai_reply})
    messages.append({"role": "user", "content": message})

    client = get_client()
    resp = await client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        stream=False,
    )
    return (resp.choices[0].message.content or "").strip()
