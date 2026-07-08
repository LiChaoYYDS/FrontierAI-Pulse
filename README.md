# FrontierAI Pulse · 前沿 AI 脉搏

把互联网上每天涌出的技术资讯，变成真正属于你的个人知识库。

---

## 🚀 项目背景与痛点

技术人每天面对的信息焦虑是真实存在的：

- Hacker News、arXiv、掘金、GitHub Trending 每天产出数百篇内容，你根本没时间筛选；
- 收藏夹堆积如山，却从未真正消化；
- AI 工具越来越多，但没有一个能将「抓取 → 理解 → 与你关联」这条链路打通。

FrontierAI Pulse 是一个面向个人开发者的 AI 驱动技术资讯中枢。它自动从12个主流来源抓取内容，用大语言模型完成摘要、标签、评分、个人洞察四步处理，再通过 RAG 知识库问答、个性化周报等方式，让你真正消化所读内容，而非只是"又收藏了一篇"。

---

## ✨ 核心功能特性

- 🔄 全自动多源抓取 — 内置12个优质来源（掘金、InfoQ、Hacker News、arXiv AI、HuggingFace Blog、GitHub Trending 等），每2小时自动抓取，也支持手动触发单源拉取。
- 🤖 四步 AI 处理流水线 — 每篇文章依次经过：摘要生成（60-120字）→ 技术标签提取（从预定义标签集中选取）→ 兴趣匹配评分（0-100分，基于向量语义相似度）→ 个人关联洞察（LLM 解释这篇文章与你技术方向的关联价值）。
- 🧠 RAG 混合检索问答 — 基于 pgvector 向量检索 + jieba 关键词检索的 RRF 融合策略，支持多轮对话。检索自动按问题意图路由到「个人收藏」「精选高分」「全量库」三个层级，兼顾精度与覆盖率。
- 📊 结构化个性化周报 — 每周自动生成包含：概览统计、热点趋势 Top 5（带同比变化箭头）、AI 精选文章（标题 + 摘要 + 标签 + 阅读时长）、洞见摘录、3条可执行行动建议、下周关注方向、阅读趋势图表（ECharts）。仅需1次 LLM 调用，Token 消耗极低。
- 🔍 全文搜索 + 智能筛选 — 支持关键词（标题/摘要/正文 ILIKE）、标签、来源、日期范围多维组合过滤，搜索框实时返回标签补全建议。
- 🎯 兴趣驱动的个性化 — 用户设置技术兴趣标签后，所有文章评分、RAG 检索层路由、周报内容全部围绕兴趣个性化，并支持一键全库重评分（pgvector 侧运算，秒级完成）。

---

## 🧱 技术架构

    ┌─────────────────────────────────────────────────────────────────┐
    │                        浏览器 (Vue 3 + Vite)                     │
    │  Pinia Store ←→ API Layer (axios) ←→ Vite Proxy /api → :8000   │
    └────────────────────────────┬────────────────────────────────────┘
                                 │ HTTP/JSON
    ┌────────────────────────────▼────────────────────────────────────┐
    │                    FastAPI (Python 3.11+)                        │
    │                                                                  │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
    │  │  /articles   │  │   /rag       │  │  /dashboard          │  │
    │  │  /sources    │  │   /search    │  │  /knowledge          │  │
    │  │  /user       │  │   /brief     │  │  /tools              │  │
    │  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
    │         │                 │                      │               │
    │  ┌──────▼─────────────────▼──────────────────────▼───────────┐  │
    │  │                    Services Layer                          │  │
    │  │  ┌────────────┐ ┌──────────────┐ ┌──────────────────────┐ │  │
    │  │  │ LLM Service│ │  RAG Service │ │  Scraper / Scheduler │ │  │
    │  │  │ (summarize │ │ (embedder    │ │  (APScheduler,       │ │  │
    │  │  │  tag/score │ │  retriever   │ │   每2小时自动抓取)    │ │  │
    │  │  │  insight)  │ │  qa_chain)   │ │                      │ │  │
    │  │  └──────┬─────┘ └──────┬───────┘ └──────────────────────┘ │  │
    │  └─────────┼──────────────┼────────────────────────────────────┘  │
    │            │              │                                        │
    │  ┌─────────▼──────────────▼────────────────────┐                  │
    │  │          PostgreSQL + pgvector               │                  │
    │  │  articles / sources / users                  │                  │
    │  │  knowledge_nodes / knowledge_edges           │                  │
    │  │  article.embedding  Vector(512)              │                  │
    │  └──────────────────────────────────────────────┘                  │
    │                                                                     │
    │  LLM Provider（优先级）:                                            │
    │    DeepSeek API → OpenAI API → Ollama（本地）→ Mock（降级）         │
    └─────────────────────────────────────────────────────────────────────┘
**分层说明**
| 层         | 目录                         | 职责                                                             |
| :--------- | :--------------------------- | :--------------------------------------------------------------- |
| 接口层     | `backend/app/api/endpoints/` | 路由、请求/响应校验，不含业务逻辑                                 |
| Schema 层  | `backend/app/schemas/`       | Pydantic 数据契约                                                |
| 服务层     | `backend/app/services/`      | 业务逻辑、LLM 调用、爬虫、RAG                                    |
| 模型层     | `backend/app/models/`        | SQLAlchemy ORM 定义                                              |
| 常量层     | `backend/app/core/`          | 配置（`config.py`）、常量（`constants.py`）                      |
| 前端类型   | `frontend/src/types/`        | TypeScript 接口定义（与后端 Schema 对应）                        |
| 前端 Store | `frontend/src/stores/`       | Pinia 状态管理，含 `sessionStorage` 持久化                       |
| 前端视图   | `frontend/src/views/`        | Vue 组件，不含业务逻辑                                           |
---

## ⚡ 快速开始

###环境要求

| 依赖       | 版本要求 | 说明                   |
| :--------- | :------- | :--------------------- |
| Python     | 3.11+    | 后端运行时             |
| Node.js    | 18+      | 前端构建               |
| PostgreSQL | 14+      | 需安装 pgvector 扩展   |
| pgvector   | 0.5+     | 向量检索扩展           |
| Git        | 任意版本 | 克隆仓库               |      

> pgvector 安装：参考 pgvector 官方文档。应用启动时会自动执行 CREATE EXTENSION IF NOT EXISTS vector，无需手动建表。

---
1. 克隆仓库
```bash
git clone https://github.com/your-username/technology_program.git
cd technology_program
```
---
2. 后端安装
```bash
# 创建并激活虚拟环境
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# 安装依赖
pip install -r backend/requirements.txt
```
---
3. 配置环境变量
在项目根目录创建 .env 文件（参考下方示例，.env 已加入 .gitignore）：
```ini
# ── LLM 配置（三选一，优先级：DeepSeek > OpenAI > Ollama）──────────────────
# 推荐使用 DeepSeek，性价比最高
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# 可用模型：deepseek-chat（V3）/ deepseek-reasoner（R1）
DEEPSEEK_MODEL=deepseek-chat

# OpenAI（可选，DeepSeek 未配置时生效）
# OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# OPENAI_MODEL=gpt-4o-mini

# ── 数据库配置 ──────────────────────────────────────────────────────────────
# 格式：postgresql+asyncpg://用户名:密码@host:port/数据库名
# 密码中含特殊字符时需 URL 编码（如 @ → %40）
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/tech_news

# ── Embedding 配置 ──────────────────────────────────────────────────────────
# local：使用本地 sentence-transformers（首次运行自动下载 ~130MB 模型，无需 API Key）
# api：使用 OpenAI 兼容接口
EMBEDDING_BACKEND=local

# ── Git 工具（可选）─────────────────────────────────────────────────────────
# 留空则自动从 PATH 查找 git；Windows 下若 git 不在 PATH，填写完整路径
# GIT_CMD_PATH=C:\Program Files\Git\cmd\git.exe
```
---

4. 创建数据库
```bash
# 连接 PostgreSQL 并创建数据库
psql -U postgres -c "CREATE DATABASE tech_news;"
```
应用启动时会自动完成建表和 pgvector 扩展初始化，无需手动执行 migration。

---
5. 启动后端
```bash
# 在项目根目录执行
uvicorn main:app --port 8000 --reload
```
启动成功后访问 http://localhost:8000/docs 查看交互式 API 文档。

---

6. 启动前端
```bash
cd frontend
# 安装依赖（仅首次）
npm install
# 启动开发服务器
npm run dev
```
浏览器访问 http://localhost:5173 即可使用。

---

7. 初始化资讯来源

前端启动后，依次完成：

1. 导航至 🎯 兴趣 页，勾选你关注的技术方向；
2. 导航至 📡 来源 页，启用你想订阅的资讯来源；
3. 点击来源卡片上的「立即抓取」，获取第一批文章；
4. 回到 📰 资讯 页，点击文章卡片上的「AI 处理」，触发四步 AI 流水线。

---


## 📖 使用指南

### 核心页面一览

| 页面     | 路由         | 功能                                                           |
| :------- | :----------- | :------------------------------------------------------------- |
| 资讯列表 | `/articles`  | 浏览所有文章，支持标签/来源/已读/收藏/时间/评分多维筛选        |
| 全文搜索 | `/search`    | 关键词 + 标签 + 来源 + 日期范围组合搜索                        |
| 知识库问答 | `/knowledge` | RAG 多轮对话，自动引用来源文章；知识图谱浏览                   |
| AI 周报  | `/brief`     | 结构化个性化周报，含 ECharts 图表；首次加载后缓存，手动刷新    |
| 仪表盘   | `/dashboard` | 阅读统计概览                                                   |
| 来源管理 | `/sources`   | 启用/禁用资讯来源，手动触发抓取                                |
| 兴趣标签 | `/interests` | 设置技术兴趣，影响文章评分和周报个性化                         |       

---    
### API 核心端点示例

触发单篇文章 AI 处理：

    curl -X POST http://localhost:8000/api/articles/{article_id}/process

RAG 知识库问答：

    curl -X POST http://localhost:8000/api/rag/ask \
      -H "Content-Type: application/json" \
      -d '{
        "question": "最近 RAG 有什么新进展？",
        "history": []
      }'

批量处理所有待处理文章：

    curl -X POST http://localhost:8000/api/articles/batch-process

触发全库重评分（基于兴趣质心向量，pgvector 侧运算）：

    curl -X POST http://localhost:8000/api/rag/rescore-all \
      -H "Content-Type: application/json" \
      -d '{"interests": ["大语言模型", "AI Agent", "RAG"]}'

---

## 截图预览
<img width="1920" height="958" alt="image" src="https://github.com/user-attachments/assets/95a269ef-4940-4dac-a8bb-1c528d25679c" />
<img width="1920" height="958" alt="image" src="https://github.com/user-attachments/assets/8e919f93-463d-4e27-807a-960331fb17ca" />
<img width="1920" height="958" alt="image" src="https://github.com/user-attachments/assets/d4368084-f25b-4c2d-be38-27882e66b197" />
<img width="1920" height="958" alt="image" src="https://github.com/user-attachments/assets/1d50bdca-92d9-43df-adea-0ca808dba682" />
<img width="1920" height="958" alt="image" src="https://github.com/user-attachments/assets/b3c43fc2-1e8f-4f63-b5b2-013d2a210426" />
<img width="1920" height="958" alt="image" src="https://github.com/user-attachments/assets/65b81c3d-80fa-491e-98c5-1565c3aa76d1" />
<img width="1920" height="958" alt="image" src="https://github.com/user-attachments/assets/e0aa70f7-9568-4bc1-9fe1-9e991281ca29" />










---

## 🤝 贡献指南
本项目目前还在完善优化，在努力改进中
欢迎提交 Issue 和 Pull Request。

提交 Issue

- Bug 报告：描述复现步骤、期望行为、实际行为，附上相关日志（uvicorn.err）。
- 功能建议：说明使用场景和预期效果。

提交 Pull Request
```bash
# 1. Fork 本仓库并克隆到本地
git clone https://github.com/your-username/technology_program.git

# 2. 基于 main 创建功能分支
git checkout -b feat/your-feature-name

# 3. 完成开发，确保后端 Python 导入无误
cd technology_program
.venv/Scripts/python -c "import app.api.endpoints.articles"

# 4. 确保前端 TypeScript 编译通过
cd frontend && npx tsc --noEmit

# 5. 提交并推送
git add .
git commit -m "feat: 描述你的改动"
git push origin feat/your-feature-name

# 6. 在 GitHub 上开启 Pull Request
```
代码规范要求

- 后端严格遵循分层规范：Schema 定义在 schemas/，业务逻辑在 services/，接口层只做路由和校验；
- 前端类型定义必须放在 src/types/ 对应目录，不得在 Store 或 View 中内联定义接口；
- LLM 调用统一走 provider_factory.get_provider()，不直接实例化 Provider；
- 新增 API Key 或敏感配置必须通过 .env，不得硬编码。

---

📄 开源协议

本项目基于 MIT License 开源。

MIT License

Copyright (c) 2026 FrontierAI Pulse Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
