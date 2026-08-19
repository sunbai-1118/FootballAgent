"""数据模型包：注册所有 ORM 模型"""
from models.users import User, UserToken
from models.news import NewsCategory, News, RelatedNews
from models.favorite import Favorite
from models.history import History
from models.ai_chat import AiChat
from models.user_memory import UserMemory
from models.session_memory import SessionMemory
from models.team import Team
from models.player import Player
from models.match import Match
from models.answer_feedback import AnswerFeedback

__all__ = [
    "User",
    "UserToken",
    "NewsCategory",
    "News",
    "RelatedNews",
    "Favorite",
    "History",
    "AiChat",
    "UserMemory",
    "SessionMemory",
    "Team",
    "Player",
    "Match",
    "AnswerFeedback",
]