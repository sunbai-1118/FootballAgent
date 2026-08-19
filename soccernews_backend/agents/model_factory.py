"""LLM 模型工厂:多模型可配置,默认 DeepSeek(OpenAI 兼容)

新增 provider 时只需在此处扩展分支,Agent 图无感知。
"""
from typing import Any

from langchain_openai import ChatOpenAI

from agents.observability import LLMLoggingHandler
from config.ai_conf import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_TIMEOUT,
    MAX_TOKENS,
    QWEN_API_KEY,
    QWEN_BASE_URL,
    QWEN_ENABLE_THINKING,
    QWEN_MODEL,
    QWEN_TIMEOUT,
)
from config.rag_conf import LLM_PROVIDER


class LLMFactory:
    """按配置返回对话模型实例"""

    @staticmethod
    def get_chat_model(provider: str | None = None, **kwargs: Any) -> ChatOpenAI:
        """获取对话模型

        :param provider: 覆盖默认 provider(LLM_PROVIDER),为后续多 Agent 各子 Agent 用不同模型预留
        :param kwargs: 透传给底层 ChatOpenAI;可传 callbacks 覆盖默认的 LLMLoggingHandler,
                       temperature / max_tokens / timeout 可覆盖
        """
        # 可观测性：所有 provider 统一挂 LLM 回调（模型名/token 用量从 langchain 通用接口取），
        # 新增 provider 分支无需改日志代码
        if "callbacks" not in kwargs:
            kwargs["callbacks"] = [LLMLoggingHandler()]
        # temperature 允许调用方覆盖（如记忆筛选用 0 更确定），默认 0.3
        temperature = kwargs.pop("temperature", 0.3)
        # max_tokens 限制单次输出长度（防 token 过高），可覆盖
        max_tokens = kwargs.pop("max_tokens", MAX_TOKENS)
        provider = provider or LLM_PROVIDER
        if provider == "deepseek":
            return ChatOpenAI(
                model=DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=DEEPSEEK_TIMEOUT,
                **kwargs,
            )
        if provider == "qwen":  # 阿里云百炼 / DashScope（OpenAI 兼容接口）
            extra_body = dict(kwargs.pop("extra_body", {}) or {})
            if not QWEN_ENABLE_THINKING:
                extra_body["enable_thinking"] = False  # 关思考，大幅降输出 token
            return ChatOpenAI(
                model=QWEN_MODEL,
                api_key=QWEN_API_KEY,
                base_url=QWEN_BASE_URL,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=QWEN_TIMEOUT,
                extra_body=extra_body,
                **kwargs,
            )
        # 预留: elif provider == "claude": ...（同样透传 kwargs，日志/追踪自动适配）
        raise ValueError(f"不支持的模型 provider: {provider}")
