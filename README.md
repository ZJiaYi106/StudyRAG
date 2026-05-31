# 📚 StudyRAG

面向课程资料、论文和个人笔记的 **RAG（检索增强生成）知识库问答系统**。

## 项目定位

- 上传 PDF / Markdown 资料，构建个人知识库
- 基于检索到的资料片段，由大模型生成**有据可查**的中文回答
- 所有回答附带引用来源（文件名、页码、章节、原文片段）
- 资料不足时明确说明，绝不编造

## 系统架构

```
┌─────────────────────────────────────────────────┐
│              用户浏览器 (React + Vite)            │
│   上传文件 │ 提问 │ 查看答案+来源 │ 管理文档       │
└──────────────────┬──────────────────────────────┘
                   │ HTTP REST API
┌──────────────────▼──────────────────────────────┐
│              FastAPI 后端 (Python 3.11)          │
│                                                   │
│  POST /upload  ──► Loader ──► Splitter            │
│                      │          │                  │
│                      ▼          ▼                  │
│                   Embeddings  VectorStore (Chroma) │
│                                                   │
│  POST /chat    ──► Retriever ──► PromptTemplate    │
│                      │               │             │
│                      ▼               ▼             │
│                   Chroma          ChatOpenAI (LLM) │
└──────────────────┬──────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
┌────────┐  ┌──────────┐  ┌──────────────┐
│ Chroma │  │ Embedding│  │   OpenAI API  │
│ (向量库)│  │  API     │  │  兼容 LLM     │
└────────┘  └──────────┘  └──────────────┘
```

### RAG 数据流

```
文件上传：
  PDF/MD → Document Loader → List[Document] → Text Splitter
  → List[Document] (chunks) → Embeddings → Chroma 持久化

问答：
  用户提问 → Embedding 向量化 → Chroma 检索 Top-K → 构建 Prompt
  → ChatOpenAI 生成 → StrOutputParser → 返回答案 + 引用来源
```

## 功能

- [x] PDF / Markdown 文件上传与解析
- [x] 文档自动切分与向量化
- [x] 基于文档的 RAG 问答
- [x] 引用来源展示（文件名、页码、章节、原文片段）
- [x] 文档管理（列表、删除）

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.11) |
| LLM 框架 | LangChain（7 个核心组件） |
| 向量数据库 | Chroma（持久化内嵌模式） |
| 文档解析 | PyMuPDF |
| LLM / Embedding | OpenAI API 兼容接口（通过 `.env` 配置） |
| 前端 | React + Vite + TypeScript |
| 容器化 | Docker Compose |

## API 清单

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查（含 Chroma 状态、文档数） |
| `POST` | `/api/documents` | 上传文档（PDF / MD） |
| `GET` | `/api/documents` | 列出所有已上传文档 |
| `DELETE` | `/api/documents/{id}` | 删除指定文档及其向量 |
| `POST` | `/api/chat` | RAG 问答 |

## 快速启动

### 前置条件

- Python 3.11+ / Docker Desktop
- OpenAI API 兼容的 API Key

### 方式一：本地开发（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 2. 安装后端依赖
cd backend
pip install -r requirements.txt

# 3. 启动后端
python -m uvicorn app.main:app --reload --port 8000
# 访问 API 文档: http://localhost:8000/docs

# 4. 启动前端（新终端）
cd frontend
npm install
npm run dev
# 访问前端: http://localhost:5173
```

### 方式二：Docker Compose

```bash
cp .env.example .env    # 编辑填入 API Key
docker compose up -d    # 启动后端 + Chroma + 前端
```

| 服务 | 地址 |
|------|------|
| 后端 API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/api/health |
| 前端界面 | http://localhost:5173 |

## 示例问答

以 NLP 课程讲义为例，上传 `NLP讲义.pdf` 后提问：

**用户**：什么是 Transformer？

**回答**：
> Transformer 是一种基于自注意力机制的深度学习架构，由 Vaswani 等人于 2017 年在论文《Attention Is All You Need》中提出 [1]。
>
> 1. Transformer 完全基于注意力机制，摒弃了传统的循环和卷积结构 [1]
> 2. 核心组件包括多头自注意力和位置编码 [2]
> 3. 在机器翻译、文本生成等任务中取得了突破性成果 [1]
>
> ---
> **参考来源：**
> [1] NLP讲义.pdf 第3页
> [2] NLP讲义.pdf 第5页 - "2.1 自注意力机制"

**用户**：爱因斯坦的相对论是什么？

**回答**：
> 资料中未找到足够依据来回答这个问题。当前知识库仅包含 NLP 课程相关内容，建议上传物理学相关资料后再提问。

## LangChain 学习

本项目系统使用了 7 个 LangChain 核心组件，每个组件都有详细的中文注释和学习笔记：

| 组件 | 文件 | 笔记 |
|------|------|------|
| Document Loader | `services/loader.py` | [链接](docs/langchain-notes.md#1-document-loader文档加载器) |
| Text Splitter | `services/splitter.py` | [链接](docs/langchain-notes.md#2-text-splitter文本切分器) |
| Embeddings | `services/embeddings.py` | [链接](docs/langchain-notes.md#3-embeddings文本向量化) |
| Chroma VectorStore | `services/vectorstore.py` | [链接](docs/langchain-notes.md#4-chroma-vectorstore向量存储) |
| Retriever | `services/retriever.py` | [链接](docs/langchain-notes.md#5-retriever检索器) |
| PromptTemplate | `services/prompt.py` | [链接](docs/langchain-notes.md#6-prompttemplateprompt-模板) |
| Runnable / LCEL | `services/chain.py` | [链接](docs/langchain-notes.md#7-runnable--lcellangchain-expression-language) |

每篇笔记包括：组件作用、输入/输出、不用 LangChain 的手写等价代码、最小示例。

## 项目进度

| 步骤 | 内容 | 状态 |
|------|------|------|
| 1 | 项目搭建（工程骨架、Docker Compose、FastAPI 入口） | ✅ |
| 2 | Document Loader（PDF/MD 加载与元数据提取） | ✅ |
| 3 | Text Splitter（文档切分策略） | ✅ |
| 4 | Embeddings + VectorStore（向量化与 Chroma 存储） | ✅ |
| 5 | 文档上传 API（Loader → Splitter → Embeddings → Store） | ✅ |
| 6 | Retriever + PromptTemplate（检索与 Prompt 构建） | ✅ |
| 7 | LCEL Chain + 问答 API | ✅ |
| 8 | 前端基础（上传、列表、问答 UI） | ✅ |
| 9 | 前后端联调 | ✅ |
| 10 | 测试完善 + README 定稿 | ✅ |

## 测试

```bash
cd backend
python -m pytest -v        # 108 个测试
```

## 项目结构

```
StudyRAG/
├── docker-compose.yml              # Docker 编排（后端 + Chroma + 前端）
├── .env.example                    # 环境变量模板
├── .gitignore
├── README.md
├── docs/
│   └── langchain-notes.md          # LangChain 学习笔记（7 篇）
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                 # FastAPI 应用入口 + 生命周期
│   │   ├── config.py               # Pydantic Settings 配置管理
│   │   ├── models/
│   │   │   ├── document.py         # 文档相关数据模型
│   │   │   └── chat.py             # 问答相关数据模型
│   │   ├── routers/
│   │   │   ├── documents.py        # 上传/列表/删除 API
│   │   │   └── chat.py             # 问答 API
│   │   ├── services/
│   │   │   ├── loader.py           # [LangChain] Document Loader
│   │   │   ├── splitter.py         # [LangChain] Text Splitter
│   │   │   ├── embeddings.py       # [LangChain] Embeddings
│   │   │   ├── vectorstore.py      # [LangChain] Chroma VectorStore
│   │   │   ├── retriever.py        # [LangChain] Retriever
│   │   │   ├── prompt.py           # [LangChain] PromptTemplate
│   │   │   └── chain.py            # [LangChain] LCEL Chain
│   │   └── utils/
│   │       ├── file_utils.py       # 文件校验/保存/删除
│   │       └── registry.py         # JSON 文档注册表
│   └── tests/
│       ├── test_health.py          # 健康检查测试
│       ├── test_loader.py          # Loader 测试（21 个）
│       ├── test_splitter.py        # Splitter 测试（18 个）
│       ├── test_embeddings.py      # Embeddings 测试（7 个）
│       ├── test_vectorstore.py     # VectorStore 测试（13 个）
│       ├── test_retriever.py       # Retriever 测试（7 个）
│       ├── test_prompt.py          # Prompt 测试（12 个）
│       ├── test_chain.py           # Chain 测试（7 个）
│       ├── test_documents_api.py   # 文档 API 集成测试（12 个）
│       ├── test_chat_api.py        # 问答 API 集成测试（8 个）
│       └── fixtures/               # 测试用 PDF/MD 文件
└── frontend/
    ├── Dockerfile
    ├── vite.config.ts              # Vite 配置（含 API 代理）
    └── src/
        ├── main.tsx
        ├── App.tsx                 # 主应用（布局 + 路由）
        ├── api/
        │   └── client.ts           # API 客户端（错误解析）
        ├── components/
        │   ├── FileUpload.tsx       # 文件上传（拖拽/点击）
        │   ├── DocList.tsx          # 文档列表（含删除）
        │   ├── ChatPanel.tsx        # 问答面板
        │   ├── MessageBubble.tsx    # 消息气泡
        │   └── SourceCard.tsx       # 引用来源卡片
        ├── types/
        │   └── index.ts            # TypeScript 类型定义
        └── styles/
            └── index.css           # 全局样式
```
