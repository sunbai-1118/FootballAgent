"""统一日志配置：控制台实时输出 + 文件按天命名 JSON 落盘

用法：应用启动时调用 setup_logging()（见 main.py）。
级别默认 INFO，可通过环境变量 LOG_LEVEL 覆盖（如 DEBUG/WARNING）。
控制台日志按级别着色（INFO 绿 / WARNING 黄 / ERROR 红），可用 LOG_COLOR=false 关闭；
文件日志为 JSON 结构化（每行一条，含 OTel trace_id/span_id 与业务 context），
可用 LOG_FILE_FORMAT=text 回退为纯文本。

文件命名：日志文件按天命名 app-YYYY-MM-DD.log（日期直接体现在文件名），
跨天第一条日志写入时自动切换到新文件，并清理保留期之外（默认 14 天，
可用 LOG_BACKUP_DAYS 覆盖）的旧文件。
"""
import copy
import json
import logging.config
import os
import re
import time
from datetime import datetime

from pythonjsonlogger.json import JsonFormatter

from utils.log_context import ContextFilter

# 日志目录（相对项目根目录）
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
# 文件名模板：实际文件名为其日期派生名（app-YYYY-MM-DD.log）
LOG_FILE = os.path.join(LOG_DIR, "app.log")
# 文件日志保留天数（按文件名中的日期计算）
LOG_BACKUP_DAYS = int(os.getenv("LOG_BACKUP_DAYS", "14"))
# 文件日志格式：json（默认，结构化）| text（纯文本，排查用）
LOG_FILE_FORMAT = os.getenv("LOG_FILE_FORMAT", "json").lower()

# 日志级别：默认 INFO，可用环境变量 LOG_LEVEL 覆盖
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# 控制台是否按级别着色：默认开，可用 LOG_COLOR=false 关闭（例如在只支持纯文本的老终端）
LOG_COLOR = os.getenv("LOG_COLOR", "true").lower() in ("1", "true", "yes", "on")

# 统一日志格式：时间 | 级别 | 模块 | [trace前缀] 消息（trace_prefix 由 ContextFilter 计算）
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(trace_prefix)s%(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class ColoredFormatter(logging.Formatter):
    """控制台彩色格式化器：按级别给级别前缀着色，文件日志不用它（保持纯文本便于 grep）"""

    COLORS = {
        "DEBUG": "\033[36m",        # 青
        "INFO": "\033[32m",         # 绿
        "WARNING": "\033[33m",      # 黄
        "ERROR": "\033[31m",        # 红
        "CRITICAL": "\033[1;31m",   # 亮红
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # 深拷贝，避免改动原始 record 影响文件 handler（文件里不应出现 ANSI 颜色码）
        colored = copy.copy(record)
        color = self.COLORS.get(colored.levelname, "")
        colored.levelname = f"{color}{colored.levelname}{self.RESET}"
        return super().format(colored)


class OTelJsonFormatter(JsonFormatter):
    """文件日志 JSON formatter：ts/level/logger/msg + OTel trace_id/span_id + 业务 context + 结构化 extra + exception

    覆盖 add_fields 精确控制输出字段（避免把 LogRecord 内部属性全量打进 JSON）；
    覆盖 serialize_log_record 保证 ensure_ascii=False（中文不转义）与 default=str 兜底非序列化值。
    """

    # 各模块通过 extra={"section": {...}} 传入的结构化段落
    _STRUCTURED_SECTIONS = ("request", "tool", "rag", "llm", "graph", "chat")

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        log_record.clear()
        log_record["ts"] = datetime.fromtimestamp(record.created).astimezone().isoformat(timespec="milliseconds")
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["msg"] = message_dict.get("message") or record.getMessage()
        log_record["trace_id"] = getattr(record, "trace_id", "") or ""
        log_record["span_id"] = getattr(record, "span_id", "") or ""
        log_record["context"] = getattr(record, "context", None)
        for section in self._STRUCTURED_SECTIONS:
            value = getattr(record, section, None)
            if value is not None:
                log_record[section] = value
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

    def serialize_log_record(self, log_record: dict) -> str:
        return json.dumps(log_record, ensure_ascii=False, default=str)


class DailyDateFileHandler(logging.FileHandler):
    """按天命名日志文件：文件名直接带日期（app-YYYY-MM-DD.log）。

    与 TimedRotatingFileHandler 不同，不保留固定 app.log 主名 + 滚动后缀，
    而是每个日志日一个独立文件；跨天第一条日志写入时自动切换，
    并清理超过 backup_count 天的旧文件（按文件名里的日期解析）。
    """

    def __init__(self, filename: str, backup_count: int = 14, encoding: str = "utf-8", mode: str = "a"):
        # filename 只是模板（.../logs/app.log），实际文件名为其日期派生名
        self.filename_template = os.path.abspath(filename)
        self.backup_count = backup_count
        self._current_day = self._today()
        # delay=True：首次 emit 才真正打开文件，跨天切换更干净
        super().__init__(self._date_filename(), mode=mode, encoding=encoding, delay=True)

    @staticmethod
    def _today() -> str:
        return time.strftime("%Y-%m-%d")

    def _date_filename(self) -> str:
        base, ext = os.path.splitext(self.filename_template)
        return f"{base}-{self._today()}{ext}"

    def emit(self, record: logging.LogRecord) -> None:
        # 跨天：关闭旧文件流，切换到新日期文件
        if self._today() != self._current_day:
            self._current_day = self._today()
            if self.stream:
                self.flush()
                self.close()
            self.baseFilename = os.path.abspath(self._date_filename())
            self.stream = self._open()
            self._closed = False
            self._cleanup_old_files()
        super().emit(record)

    def _cleanup_old_files(self) -> None:
        """删除 backup_count 天之前的 app-YYYY-MM-DD.log 旧文件"""
        if self.backup_count <= 0:
            return
        base, ext = os.path.splitext(self.filename_template)
        prefix = os.path.basename(base) + "-"
        pattern = re.compile(rf"^{re.escape(prefix)}(\d{{4}}-\d{{2}}-\d{{2}}){re.escape(ext)}$")
        directory = os.path.dirname(self.filename_template)
        dated = []
        for name in os.listdir(directory):
            m = pattern.match(name)
            if m:
                dated.append((m.group(1), name))
        dated.sort(key=lambda x: x[0], reverse=True)  # 新日期在前
        for _, name in dated[self.backup_count:]:
            try:
                os.remove(os.path.join(directory, name))
            except OSError:
                pass


def setup_logging() -> None:
    """初始化统一日志配置（幂等：重复调用仅覆盖配置）"""
    # 确保日志目录存在
    os.makedirs(LOG_DIR, exist_ok=True)

    config = {
        "version": 1,
        "disable_existing_loggers": False,  # 不关闭已有 logger，避免影响第三方库
        "formatters": {
            "default": {
                "format": LOG_FORMAT,
                "datefmt": DATE_FORMAT,
            },
            "colored": {
                "()": ColoredFormatter,
                "format": LOG_FORMAT,
                "datefmt": DATE_FORMAT,
            },
            "json": {
                "()": OTelJsonFormatter,
            },
        },
        "filters": {
            "context": {
                "()": ContextFilter,     # 注入 OTel trace_id/span_id + 业务上下文
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "colored" if LOG_COLOR else "default",
                "filters": ["context"],
                "level": LOG_LEVEL,
            },
            "file": {
                "class": "config.logging_conf.DailyDateFileHandler",
                "formatter": "json" if LOG_FILE_FORMAT == "json" else "default",
                "filters": ["context"],
                "level": LOG_LEVEL,
                "filename": LOG_FILE,     # 模板，实际文件名 app-YYYY-MM-DD.log
                "backup_count": LOG_BACKUP_DAYS,
                "encoding": "utf-8",
            },
        },
        "root": {
            "level": LOG_LEVEL,
            "handlers": ["console", "file"],
        },
        # 单独降噪：db_conf.py 的 echo=True 会让每条 SQL 都刷 INFO，压到 WARNING
        "loggers": {
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
    }
    logging.config.dictConfig(config)
