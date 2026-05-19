# 📚 StudyRAG

面向课程资料、论文和个人笔记的 **RAG（检索增强生成）知识库问答系统**。

## 项目定位

- 上传 PDF / Markdown 资料，构建个人知识库
- 基于检索到的资料片段，由大模型生成**有据可查**的中文回答
- 所有回答附带引用来源（文件名、页码、章节、原文片段）
- 资料不足时明确说明，绝不编造

## 系统架构

```
用户浏览器 (React)
      │
      ▼
FastAPI 后端 (Python)
      │
      ├──► ChromaDB (向量存储)
      │
      └──► OpenAI API 兼容 LLM + Embedding
```

### 数据流（问答流程）

```
用户提问 → 问题向量化 → Chroma 检索 Top-K → 构建 Prompt → LLM 生成 → 返回答案+来源
```

## 功能

- [ ] PDF / Markdown 文件上传与解析
- [ ] 文档自动切分与向量化
- [ ] 基于文档的 RAG 问答
- [ ] 引用来源展示（文件名、页码、章节、原文片段）
- [ ] 文档管理（列表、删除）

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.11) |
| LLM 框架 | LangChain |
| 向量数据库 | Chroma |
| 文档解析 | PyMuPDF |
| LLM / Embedding | OpenAI API 兼容接口（通过 .env 配置） |
| 前端 | React + Vite + TypeScript |
| 容器化 | Docker Compose |

## 快速启动

### 前置条件

- Docker Desktop
- OpenAI API 兼容的 API Key（或其他兼容服务）

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key 和 Base URL
```

### 2. 启动所有服务

```bash
docker compose up -d
```

### 3. 访问

| 服务 | 地址 |
|------|------|
| 后端 API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/api/health |
| 前端界面 | http://localhost:3000（后续步骤启用） |

## 示例问答

> 待步骤 7 完成后补充实际问答示例。

## 项目进度

| 步骤 | 内容 | 状态 |
|------|------|------|
| 1 | 项目搭建（工程骨架、Docker Compose、FastAPI 入口） | ✅ 已完成 |
| 2 | Document Loader（PDF/MD 加载与元数据提取） | ✅ 已完成 |
| 3 | Text Splitter（文档切分策略） | ✅ 已完成 |
| 4 | Embeddings + VectorStore（向量化与 Chroma 存储） | ✅ 已完成 |
| 5 | 文档上传 API（Loader → Splitter → Embeddings → Store 管道） | ✅ 已完成 |
| 6 | Retriever + PromptTemplate（检索与 Prompt 构建） | ✅ 已完成 |
| 7 | LCEL Chain + 问答 API | ✅ 已完成 |
| 8 | 前端基础（上传、列表、问答 UI） | ✅ 已完成 |
| 9 | 前后端联调 | ✅ 已完成 |
| 10 | 测试完善 + README 定稿 | 🔲 待开始 |

## 项目结构

```
StudyRAG/
├── docker-compose.yml
├── .env.example
├── README.md
├── docs/
│   └── langchain-notes.md        # LangChain 学习笔记
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py               # FastAPI 入口
│   │   ├── config.py             # 配置管理
│   │   ├── models/               # Pydantic 数据模型
│   │   ├── routers/              # API 路由
│   │   ├── services/             # LangChain 服务封装
│   │   └── utils/                # 工具函数
│   └── tests/                    # 单元测试
└── frontend/
    ├── Dockerfile
    └── src/
        ├── api/client.ts         # API 客户端
        ├── components/           # React 组件
        └── types/                # TypeScript 类型
```
