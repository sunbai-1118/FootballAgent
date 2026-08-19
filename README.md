# ⚽ 足球头条 AI（Football News AI）

基于 **Vue3 + FastAPI + LangGraph Agent + 多模态 RAG + 实时足球数据**
构建的智能足球资讯平台。

项目集成移动端新闻浏览、足球资讯检索、AI
智能问答、用户系统、个性化记忆以及实时赛事数据能力，为用户提供专业化、智能化的足球信息服务。

------------------------------------------------------------------------

## ✨ 项目特点

-   📰 **足球资讯平台**
    -   新闻首页展示
    -   分类浏览
    -   新闻详情阅读
    -   Markdown 富文本渲染
    -   收藏与历史记录
-   🤖 **AI 足球智能助手**
    -   基于 LangGraph ReAct Agent
    -   支持足球赛事、球队、球员、排名等专业问答
    -   支持新闻检索与实时信息查询
    -   SSE 流式输出
-   🧠 **多模态 RAG 检索系统**
    -   文本知识库检索
    -   图片语义检索
    -   新闻图文联合检索
-   🏟️ **实时足球数据**
    -   比赛结果
    -   赛事赛程
    -   联赛排名
    -   球队信息
    -   球员数据
-   💾 **用户记忆系统**
    -   工作记忆
    -   短期上下文记忆
    -   长期用户偏好记忆
-   ✅ **回答可信度校验**
    -   Agent 输出后进行事实验证
    -   降低 AI 幻觉问题

------------------------------------------------------------------------

# 🏗️ 系统架构

                      用户
                       |
                  Vue3 移动端
                       |
                 FastAPI 后端
                       |
            -----------------------
            |          |          |
        AI Agent      RAG      数据服务
            |          |          |
       LangGraph    Qdrant   Football API
            |
       LLM模型
    (DeepSeek/Qwen)

------------------------------------------------------------------------

# 🛠️ 技术栈

## 前端

  分类       技术
  ---------- --------------------
  框架       Vue3
  构建工具   Vite
  路由       Vue Router 4
  状态管理   Pinia
  UI组件     Vant 4
  网络请求   Axios
  国际化     vue-i18n
  富文本     marked + DOMPurify

## 后端

  分类         技术
  ------------ ----------------------------------
  Web框架      FastAPI
  AI Agent     LangGraph ReAct
  大语言模型   DeepSeek / Qwen
  向量数据库   Qdrant
  Embedding    bge-small-zh-v1.5 / Chinese-CLIP
  数据库       MySQL
  缓存         Redis
  实时数据     api-football / thesportsDB
  日志系统     JSON Logger
  链路追踪     OpenTelemetry

------------------------------------------------------------------------

# 🚀 功能模块

## 新闻资讯

-   新闻首页展示
-   体育分类浏览
-   新闻详情查看
-   收藏管理
-   浏览历史记录

## AI 智能问答

支持：

-   比赛结果查询
-   赛事赛程查询
-   联赛排名查询
-   球队信息查询
-   球员数据查询
-   新闻智能检索

## RAG 知识增强

    用户问题
       |
    Embedding
       |
    Qdrant向量检索
       |
    相关足球知识
       |
    LLM生成回答

------------------------------------------------------------------------

# 📁 项目结构

    football-ai/

    ├── frontend/              # Vue3前端
    ├── backend/               # FastAPI后端
    ├── docker/                # Docker基础服务
    ├── README.md
    └── .env.example

------------------------------------------------------------------------

# ⚙️ 环境要求

## 前端

    Node.js >= 18
    npm

启动：

``` bash
npm install
npm run dev
```

生产构建：

``` bash
npm run build
```

## 后端

环境：

    Python >= 3.10
    MySQL
    Redis
    Docker

安装依赖：

``` bash
pip install -r requirements.txt
```

启动：

``` bash
uvicorn main:app --reload
```

接口文档：

    http://localhost:8000/docs

------------------------------------------------------------------------

# 🐳 Docker服务

项目依赖：

-   Qdrant
-   Embedding服务

启动：

``` bash
cd docker
docker compose up -d
```

------------------------------------------------------------------------

# 🔧 配置说明

复制：

    .env.example

配置：

    LLM_API_KEY
    DATABASE_CONFIG
    REDIS_CONFIG
    QDRANT_CONFIG
    FOOTBALL_API_KEY

------------------------------------------------------------------------

# 📌 项目亮点

-   基于 LangGraph 构建可扩展 Agent 架构
-   支持 Tool Calling 工具调用
-   多模态 RAG 检索
-   用户长期记忆管理
-   实时足球数据融合
-   OpenTelemetry 全链路监控
-   前后端分离架构

------------------------------------------------------------------------

# 📄 License

暂无开源许可证。
