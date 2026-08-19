# ⚽ 足球头条 AI 后端

基于 **FastAPI + LangGraph ReAct Agent + 多模态 RAG + 实时足球数据** 的足球资讯问答后端，配套 Vue3 移动端前端（`xwzx-news`）。

AI Agent 能力：专业足球问答（比赛结果 / 赛程 / 排名 / 球队 / 球员实时数据）、新闻检索、用户个性化记忆、回答可信度校验、👍/👎 反馈闭环、OpenTelemetry 全链路可观测。

## 技术栈

| 分类 | 技术 |
|------|------|
| Web | FastAPI + uvicorn（异步、SSE 流式） |
| Agent | LangGraph ReAct（单 Agent，预留多 Agent 扩展） |
| LLM | DeepSeek / Qwen（`LLM_PROVIDER` 切换，OpenAI 兼容接口） |
| 向量库 / Embedding | Qdrant + bge-small-zh-v1.5（文本）+ Chinese-CLIP（图片），Docker 部署 |
| 实时足球数据 | api-football（比赛/赛程/排名/球队/球员）+ thesportsDB（队徽/球员照） |
| 存储 | MySQL + Redis（缓存不可用自动降级） |
| 可观测 | OpenTelemetry（trace/span 全链路）+ python-json-logger（JSON 日志） |

## 功能特性

- **专业足球问答**：`get_match_result` 调 api-football 返回比赛结果/赛程/排名/球队/球员，按问题类型套用回答模板（含队徽配图）
- **多模态 RAG**：Qdrant 双命名向量（text=bge / image=Chinese-CLIP），新闻图文一体检索
- **四层记忆**：工作记忆（AgentState）/ 短期（token 预算驱动，summary+key_facts+recent 三层）/ 长期（`user_memory` + `remember` + LLM 记忆筛选）/ 外部知识（RAG + 足球 API + 联网）
- **回答可信度校验**：Verifier 节点对最终回答做事实来源二次校验，识别幻觉并修正（`VERIFIER_ENABLED` 可开关）
- **反馈闭环**：`POST /api/ai/feedback` 收集 👍/👎，关联 `trace_id` 可回溯完整日志链路
- **可观测**：OTel trace/span 贯穿 HTTP→Agent→LLM→RAG→Tool；文件 JSON 日志、控制台彩色文本
- **多模型**：DeepSeek / Qwen 可切换，LLM 回调日志/追踪对多模型通用
- **健壮性**：工具调用计数上限 + 反循环规则 + `GraphRecursionError` 友好降级

## 项目结构

```
soccernews_backend/               # 后端项目根目录
├── agents/                     # Agent 核心层
│   ├── agent_service.py        # 对话服务：_prepare 组装 + chat / chat_stream(SSE) + Verifier
│   ├── graph.py                # ReAct 图：agent 节点(工具调用计数) + ToolNode
│   ├── prompts.py              # 系统提示词：日期注入 + 回答模板 + 记忆段
│   ├── memory.py               # 记忆编排：token 预算 + 短期压缩(summary/key_facts)
│   ├── memory_filter.py        # 长期记忆筛选判断层
│   ├── verifier.py             # Verifier 校验节点
│   ├── rag.py · embeddings.py  # Qdrant 多模态检索 + embedding HTTP 客户端
│   ├── model_factory.py        # LLM 工厂（DeepSeek/Qwen，max_tokens/思考开关）
│   ├── observability.py        # LLM 回调日志 + 工具日志装饰器
│   ├── state.py                # AgentState（工作记忆）
│   └── tools/                  # 工具（按 domain 分组）
│       ├── news_tools.py       # search_news / get_news_detail / get_hot_news / retrieve_news_tool
│       ├── user_tools.py       # get_my_favorites / get_my_history / remember
│       ├── image_tools.py      # get_match_pick(thesportsDB) / retrieve_images_tool
│       ├── football_tools.py   # get_match_result(api-football)
│       ├── web_tools.py        # web_search(新闻联网兜底) / pick_illustration
│       └── registry.py         # ToolRegistry
├── config/                     # 配置（均走环境变量 / .env）
│   ├── db_conf.py              # 数据库（DB_* 环境变量）
│   ├── cache_conf.py           # Redis
│   ├── ai_conf.py              # LLM（DeepSeek/Qwen/MAX_TOKENS/Verifier）
│   ├── football_conf.py        # api-football / thesportsDB
│   ├── rag_conf.py             # Qdrant / 嵌入服务 / RAG 参数
│   ├── logging_conf.py         # JSON + 彩色日志
│   └── otel_conf.py            # OpenTelemetry
├── crud/ · models/ · routers/ · schemas/ · utils/
├── sql/                        # 数据库脚本
│   ├── database.sql            # 全量建库建表 + 种子数据（新部署用）
│   ├── memory_tables.sql       # 增量：记忆表（存量库用）
│   ├── football_tables.sql     # 增量：球队/球员/比赛表（存量库用）
│   └── answer_feedback.sql     # 增量：反馈表 + ai_chat.trace_id（存量库用）
├── docker/                     # Qdrant + 嵌入服务（docker compose up -d）
├── main.py                     # 应用入口（uvicorn main:app）
├── seed_football_data.py       # 足球新闻种子生成脚本（160 条）
├── requirements.txt
└── .env.example                # 环境变量模板（复制为 .env 填密钥）
```

## 快速开始

1. **初始化数据库**：在 MySQL 执行 `sql/database.sql`（自动建库 `news_app` + 建表 + 分类种子）。已有旧库时，按需执行 `sql/` 下的增量脚本。
2. **Docker 基础设施**（Qdrant + 文本/图片嵌入服务，Agent/RAG 必需）：
   ```bash
   cd docker && docker compose up -d --build
   ```
   Qdrant `localhost:6335`；文本嵌入 `8001`；图片嵌入 `8002`。
3. **配置环境变量**：复制 `.env.example` 为 `.env`，填入密钥（至少 LLM key + 数据库）。
4. **安装依赖**：
   ```bash
   pip install -r requirements.txt   # 建议使用虚拟环境 .venv
   ```
5. **启动后端**：
   ```bash
   .venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```
   - 接口文档：http://localhost:8000/docs
   - 健康检查：http://localhost:8000/
6. **可选**：生成足球新闻种子（先建库）：`python seed_football_data.py`
7. **前端**（`xwzx-news`）：`npm install && npm run dev`

## AI Agent 能力详解

### 工具（按 domain 分组）

| 分类 | 工具 | 作用 | 数据源 |
|------|------|------|--------|
| news | `search_news` / `get_news_detail` / `get_hot_news` / `retrieve_news_tool` | 新闻搜索/详情/热门/语义检索 | MySQL / Qdrant(bge) |
| user | `get_my_favorites` / `get_my_history` / `remember` | 收藏/历史/长期记忆 | MySQL |
| image | `get_match_pick` / `retrieve_images_tool` | 球队/球员图片（thesportsDB）/ 本站图片检索 | thesportsDB / Qdrant(CLIP) |
| football | `get_match_result` | 比赛结果/赛程/排名/球队/球员（intent 路由 + 赛季自动回退） | api-football |
| web | `web_search` | 新闻/实时信息联网兜底 | Tavily |

### 四层记忆

- **工作记忆**：AgentState（messages + agent_trace），单轮 ReAct 状态
- **短期记忆**：`session_memory` 表（summary 自然语言 + key_facts 结构化 JSON）+ 最近 5~10 轮原文；**token 预算驱动**，超预算自动折叠压缩
- **长期记忆**：`user_memory` 表 + `remember` 工具 + LLM 记忆筛选（持久/个性化/重要/去重冲突）
- **外部知识**：RAG + 足球 API + 联网，按需检索；与 Memory 边界明确

### Verifier 校验节点

`Agent → Answer → Verifier → 检查事实来源 → 返回`。Verifier 用「问题 + 答案 + 工具证据 + 用户记忆」做 LLM 二次校验，识别幻觉并给修正回复（流式 `done` 帧带 `verified` 信息）。

### 反馈闭环

`POST /api/ai/feedback`（body：`chatId`/`traceId` + `score('up'/'down')` + `reason`），落库 `answer_feedback`，关联 `ai_chat` 的 `trace_id` 可回溯日志链路，用于优化 Prompt/RAG/Tool。

## API 一览

| 接口 | 方法 | 说明 | 需登录 |
|------|------|------|:------:|
| `/api/user/register` / `/login` / `/info` / `/update` / `/password` | POST/POST/GET/PUT/PUT | 用户模块 | 部分 |
| `/api/news/categories` / `/list` / `/detail` | GET | 新闻模块 | |
| `/api/favorite/check` `/add` `/remove` `/list` `/clear` | 组合 | 收藏模块 | ✅ |
| `/api/history/add` `/list` `/delete/{id}` `/clear` | 组合 | 浏览历史 | ✅ |
| `/api/ai/chat` | POST | AI Agent 对话（一次性） | ✅ |
| `/api/ai/chat/stream` | POST | AI Agent 对话（SSE 流式 + 工具过程） | ✅ |
| `/api/ai/history` | GET | 会话历史（前端刷新恢复） | ✅ |
| `/api/ai/rag/reindex` | POST | 重建 RAG 索引 | ✅ |
| `/api/ai/feedback` | POST | 回答反馈（👍/👎） | ✅ |

## 配置项（.env）

| 变量 | 默认 | 说明 |
|------|------|------|
| `LLM_PROVIDER` | `qwen` | 主 LLM：`qwen` / `deepseek` |
| `QWEN_API_KEY` / `DEEPSEEK_API_KEY` | — | 各 provider 密钥 |
| `QWEN_ENABLE_THINKING` | `false` | 是否开启 qwen 思考（false 大幅降 token） |
| `MAX_TOKENS` | `4096` | LLM 输出 token 上限 |
| `VERIFIER_ENABLED` | `true` | Verifier 校验节点开关 |
| `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` / `DB_NAME` | 默认本地 | 数据库连接 |
| `API-FOOTBALL-API-KEY` | — | 实时赛事（免费套餐 2022-2024 赛季） |
| `THESPORTDB-API-KEY` | — | 球队/球员图片 |
| `TAVILY_API_KEY` / `SERPAPI_KEY` | — | 联网搜索 |
| `LOG_LEVEL` / `LOG_COLOR` / `LOG_FILE_FORMAT` | INFO/true/json | 日志 |
| `OTEL_TRACES_EXPORTER` | `none` | `console` 本地看 span；设 OTLP endpoint 生产导出 |

## 常见问题

| 现象 | 原因与解决 |
|------|-----------|
| 启动报 `[WinError 10013]` | 8000 端口已被占用（旧的 uvicorn 实例没关），`netstat -ano \| findstr :8000` 查 PID 杀掉再启 |
| AI 对话返回错误 | 检查 `.env` 的 LLM key、Docker（Qdrant/嵌入）是否就绪、`VERIFIER_ENABLED` 是否影响 |
| 比赛数据只到 2024 | api-football 免费套餐仅覆盖 2022-2024 赛季，升级套餐后在 `.env` 改 `API_FOOTBALL_SEASON` |
| 数据库连接失败 | 检查 `.env` 的 `DB_*`、MySQL 是否启动、是否已执行 `sql/database.sql` |
| 中文乱码 | 确认连接串含 `?charset=utf8mb4`（已默认配置） |

> 前端项目：`F:\PyCharm\soccernews\xwzx-news`（Vue3 + Vant + Pinia），AI 问答页支持流式 + 工具过程卡片 + 👍/👎 反馈。
