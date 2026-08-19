"""AI 聊天模块数据验证模型"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AiChatRequest(BaseModel):
    """AI 对话请求"""
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    sessionId: Optional[str] = Field(None, description="会话ID，不传则后端新建")


class AiChatResponse(BaseModel):
    """AI 对话返回"""
    chatId: int
    sessionId: str
    reply: str
    agentTrace: Optional[list] = Field(None, description="Agent工具调用轨迹")
    createTime: Optional[datetime] = None


class AnswerFeedbackRequest(BaseModel):
    """回答反馈请求（👍/👎）"""
    chatId: Optional[int] = Field(None, description="回答记录ID(ai_chat.id)，可选")
    traceId: Optional[str] = Field(None, max_length=32, description="OTel trace_id，可选")
    score: str = Field(..., description="up(👍)/down(👎)")
    reason: Optional[str] = Field(None, max_length=500, description="反馈原因，可选")

    @field_validator("score")
    @classmethod
    def _check_score(cls, v: str) -> str:
        if v not in ("up", "down"):
            raise ValueError("score 只能是 up(👍) 或 down(👎)")
        return v
