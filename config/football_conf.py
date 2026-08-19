"""足球数据 API 配置：api-football（实时赛事）+ thesportsDB（球队/球员图片）

支持通过环境变量或项目根目录 .env 配置（示例见 .env.example）：
    API-FOOTBALL-API-KEY=xxx          # api-football 实时数据（v3.football.api-sports.io）
    THESPORTDB-API-KEY=xxx            # thesportsDB 球队/球员图片
    API_FOOTBALL_BASE=...             # 可选覆盖
    API_FOOTBALL_SEASON=2026          # 默认赛季年份
"""
import os

from dotenv import load_dotenv

load_dotenv()  # 加载项目根目录 .env 文件（若存在）

# ==================== api-football（实时赛事） ====================
API_FOOTBALL_KEY = os.getenv("API-FOOTBALL-API-KEY")  # 注意：.env 中变量名带连字符
API_FOOTBALL_BASE = os.getenv("API_FOOTBALL_BASE", "https://v3.football.api-sports.io")
# 默认赛季：免费套餐最多访问到 2024；升级套餐后改回当年（如 2026）。工具内还会做赛季自动回退。
API_FOOTBALL_SEASON = int(os.getenv("API_FOOTBALL_SEASON", "2024"))
API_FOOTBALL_TIMEOUT = float(os.getenv("API_FOOTBALL_TIMEOUT", "30"))  # 秒

# 联赛名 → api-football 联赛 ID（对应本站 8 个新闻分类）
LEAGUE_IDS: dict[str, int] = {
    "英超": 39,
    "西甲": 140,
    "意甲": 135,
    "德甲": 78,
    "法甲": 61,
    "中超": 175,
    "欧冠": 2,
    "世界杯": 1,
    "premier league": 39,
    "la liga": 140,
    "serie a": 135,
    "bundesliga": 78,
    "ligue 1": 61,
    "super league": 175,
    "champions league": 2,
    "world cup": 1,
}

# ==================== thesportsDB（球队/球员图片） ====================
THESPORTDB_KEY = os.getenv("THESPORTDB-API-KEY")  # 注意：.env 中变量名带连字符
THESPORTDB_BASE = os.getenv("THESPORTDB_BASE", "https://www.thesportsdb.com/api/v1/json")
THESPORTDB_TIMEOUT = float(os.getenv("THESPORTDB_TIMEOUT", "30"))  # 秒
