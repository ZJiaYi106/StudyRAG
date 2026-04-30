# StudyRAG LangChain 学习笔记

> 本文档随项目开发逐步积累，记录每个 LangChain 组件的学习心得。
> 每篇文章包含：组件作用、输入/输出、手写等价代码、最小示例。

---

## 目录

- [x] 1. Document Loader（步骤 2）
- [x] 2. Text Splitter（步骤 3）
- [x] 3. Embeddings（步骤 4）
- [x] 4. Chroma VectorStore（步骤 4）
- [x] 5. Retriever（步骤 6）
- [x] 6. PromptTemplate（步骤 6）
- [x] 7. Runnable / LCEL（步骤 7）

---

> 每完成一个步骤后，对应的章节会被补充完整。

---

## 1. Document Loader（文档加载器）

### 组件作用

将不同格式的原始文件（PDF、Markdown、Word 等）转换为 LangChain 统一的 **Document** 对象。这样下游的 Splitter、VectorStore 等组件无需关心文件格式差异，都操作同一个数据结构。

### 核心数据结构：Document

```python
from langchain_core.documents import Document

# Document 只有两个字段
doc = Document(
    page_content="这是文档的文本内容...",  # str: 文本内容
    metadata={                            # dict: 附加信息
        "source": "/path/to/file.pdf",
        "page": 3,
        "author": "张三",
    }
)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `page_content` | `str` | 文档的文本内容，切分和检索都基于这个字段 |
| `metadata` | `dict` | 任意键值对，存储文件名、页码、章节等附加信息 |

**关键设计意图**：metadata 在切分时会自动继承——每个 chunk 都知道自己来自哪个文件的哪一页。

### 本项目用到的 Loader

#### 1. PyMuPDFLoader（PDF）

```python
from langchain_community.document_loaders import PyMuPDFLoader

loader = PyMuPDFLoader("paper.pdf")
docs = loader.load()
# 返回 List[Document]，每个 Document 是一页
# docs[0].page_content → "第一页的文本..."
# docs[0].metadata → {"source": "paper.pdf", "page": 0, "file_path": "..."}
```

- **输入**：PDF 文件路径
- **输出**：`List[Document]`，每页一个，metadata 自带 `page`（0-indexed）和 `source`
- **原理**：底层调用 PyMuPDF（fitz），逐页提取文本

#### 2. 自定义 Markdown Loader

LangChain 的 `TextLoader` 会把整个 Markdown 文件作为一个 Document，不适合按章节检索。本项目手写了 `split_by_headers()` 函数，按 `#` 标题将文件拆分为章节级 Document。

### 不用 LangChain 需要手写什么？

如果不用 `PyMuPDFLoader`，需要手写以下逻辑：

```python
import fitz  # PyMuPDF

def manual_load_pdf(file_path: str) -> list[dict]:
    """手写 PDF 加载——LangChain 的 PyMuPDFLoader 替我们做了这些"""
    results = []
    doc = fitz.open(file_path)
    for i, page in enumerate(doc):
        text = page.get_text()
        results.append({
            "text": text,
            "metadata": {
                "source": file_path,
                "page": i,
            }
        })
    doc.close()
    return results
    # ← PyMuPDFLoader 就做了这些，并且返回的是 Document 对象而非裸 dict
```

**好处**：
1. 不需要关心 PyMuPDF 的 API 细节（`fitz.open`、`page.get_text()`、`doc.close()`）
2. 返回统一的 `Document` 对象，下游组件可以无缝衔接
3. 错误处理、编码问题由 Loader 内部处理

### 本项目中的元数据设计

每个 Document 在加载后都会被注入以下元数据：

```python
{
    "document_id": "uuid-xxx",    # 关联文档 ID，删除向量时用 WHERE 条件匹配
    "filename": "NLP讲义.pdf",     # 原始文件名，用于引用来源展示
    "file_type": "pdf",           # "pdf" | "markdown"，用于区分处理逻辑
    "page": 3,                    # 页码 1-indexed（PyMuPDFLoader 原为 0-indexed）
    "chapter": "2.1 注意力机制",   # 章节名，Markdown 从标题提取，PDF 为 None
}
```

### 最小示例

```python
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document

# 1. 加载 PDF
loader = PyMuPDFLoader("lecture.pdf")
docs = loader.load()

# 2. 查看结果
for doc in docs:
    print(f"第 {doc.metadata['page']} 页")
    print(doc.page_content[:100])  # 前 100 字
    print("---")

# 3. 注入自定义元数据
for doc in docs:
    doc.metadata["filename"] = "lecture.pdf"
    doc.metadata["document_id"] = "abc-123"
```

---

## 2. Text Splitter（文本切分器）

### 组件作用

将 Document Loader 产出的长 Document 切分为固定大小的 **chunk**（文本片段）。chunk 是向量检索的最小单元——chunk 太大检索不精确，太小语义不完整。

核心挑战：在固定字数限制内，尽可能在"自然边界"（段落、句子、标题）处切断，避免把一个完整语义切成两半。

### 核心参数

| 参数 | 说明 | 本项目默认值 |
|------|------|-------------|
| `chunk_size` | 每个 chunk 的最大字符数 | 1000 |
| `chunk_overlap` | 相邻 chunk 的重叠字符数 | 200 |
| `separators` | 分隔符优先级列表 | PDF 和 MD 各有一套 |

**chunk_overlap 为什么重要？**

```
文档: "......关键信息A。关键信息B......"
         ↑_____chunk_1_____↑
                  ↑_____chunk_2_____↑
                  ← 重叠区域 →
```

如果不重叠，关键信息 B 被切在 chunk_1 末尾、chunk_2 开头，检索时可能因语义不完整而匹配不到。`overlap=200` 让相邻 chunk 各包含一部分对方的内容，大幅降低漏检率。

### 递归切分算法

`RecursiveCharacterTextSplitter` 的工作方式：

1. 用 `separators[0]`（如 `\n\n`）尝试切分
2. 如果某个片段仍大于 `chunk_size`，用 `separators[1]`（如 `\n`）继续切
3. 递归下去，直到每个片段 ≤ `chunk_size`，或到最后用 `""` 逐字符切分

```
优先级: \n\n → \n → 。 → . → " " → ""（逐字符）
越靠前的分隔符越"自然"
```

### 本项目中的双策略设计

PDF 和 Markdown 使用不同的分隔符优先级：

```python
# PDF：段落 → 句子 → 逗号 → 字符
PDF_SEPARATORS = ["\n\n", "\n", "。", ". ", "；", "，", " ", ""]

# Markdown：标题 → 代码块 → 段落 → 句子 → 字符
MARKDOWN_SEPARATORS = [
    "\n## ", "\n### ", "\n#### ",   # 优先在二级标题前切断
    "\n```\n",                        # 代码块边界
    "\n\n", "\n", "。", ". ", " ", ""
]
```

为什么 Markdown 把 `\n## ` 放在最前面？因为如果不在标题前切断，一个 chunk 可能包含"1.2 节的后半 + 1.3 节的前半"，检索结果会显示错误的章节来源。

### 不用 LangChain 需要手写什么？

```python
def manual_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """手写滑动窗口切分 —— LangChain 的 RecursiveCharacterTextSplitter 替我们做了这些"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap  # 滑动窗口，有重叠
    return chunks
    # ← 但这样做不到"在自然边界切断"，会在任意字符中间切断
    # RecursiveCharacterTextSplitter 额外做了：递归尝试多种分隔符
```

**LangChain 替我们做的**：
1. 递归尝试多种分隔符，优先在自然边界切断
2. metadata 从父 Document 自动继承到每个 chunk
3. `chunk_overlap` 的滑动窗口逻辑
4. 长度度量和边界处理

### metadata 继承机制

这是 LangChain 最巧妙的设计之一。split_documents() 内部会调用 `copy()` 复制父 metadata：

```python
# LangChain 内部大致逻辑（简化版）
for parent_doc in docs:
    for chunk_text in split_text(parent_doc.page_content):
        new_doc = Document(
            page_content=chunk_text,
            metadata=parent_doc.metadata.copy()  # ← 自动继承！
        )
        yield new_doc
```

所以 Loader 阶段注入的 `document_id`、`filename`、`page`、`chapter`，到了 Splitter 阶段每个 chunk 都会自动带着——这就是引用溯源的保证。

### 最小示例

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# 1. 创建 Splitter
splitter = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", "。", " ", ""],
    chunk_size=1000,
    chunk_overlap=200,
)

# 2. 切分文档
docs = [Document(page_content="很长的文本..." * 500, metadata={"source": "test.pdf"})]
chunks = splitter.split_documents(docs)

# 3. 检查结果
print(f"切分为 {len(chunks)} 个 chunk")
print(f"第一个 chunk 长度: {len(chunks[0].page_content)}")
print(f"metadata 已继承: {chunks[0].metadata}")  # 包含 source
```

---

## 3. Embeddings（文本向量化）

### 组件作用

将自然语言文本转换为**固定维度的数值向量**。这是 RAG 的"桥梁"——人类语言和数学计算之间的翻译器。

```
"深度学习是什么？" → Embedding 模型 → [0.012, -0.034, 0.056, ...]（1536 维）
```

**核心原理**：语义相近的文本，其向量在空间中距离近（余弦相似度高）。因此向量化让我们可以用"计算距离"代替"理解语义"来做检索。

### 本项目用的 Embedding 服务

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",     # 1536 维
    openai_api_key="sk-xxx",
    openai_api_base="https://api.openai.com/v1",  # 换成兼容服务的地址
)
```

- **输入**：`embed_documents(["文本1", "文本2", ...])` 或 `embed_query("单个查询")`
- **输出**：`List[List[float]]`（每个文本一个 1536 维向量）
- **openai_api_base**：支持任何 OpenAI API 兼容的 Embedding 服务（本地 vLLM、Ollama 等）

### embed_documents vs embed_query

LangChain 将两者分开，允许使用不同的预处理策略：

| 方法 | 用途 | 输入 | 典型预处理 |
|------|------|------|-----------|
| `embed_documents` | 文档入库 | `List[str]` | 不做任务前缀 |
| `embed_query` | 查询向量化 | `str` | 可能加 "search_query:" 前缀 |

对于 OpenAI 模型这两者行为相同，但某些模型（如 BGE）会区分。

### 不用 LangChain 需要手写什么？

```python
import requests

def manual_embed(texts: list[str]) -> list[list[float]]:
    """手写调用 /v1/embeddings API"""
    resp = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "text-embedding-3-small", "input": texts},
    )
    return [item["embedding"] for item in resp.json()["data"]]
    # ← OpenAIEmbeddings 替我们做了：鉴权、重试、batch 优化、错误处理
```

### 最小示例

```python
from langchain_openai import OpenAIEmbeddings

# 1. 初始化
emb = OpenAIEmbeddings(
    model="text-embedding-3-small",
    openai_api_key="sk-xxx",
)

# 2. 批量向量化（入库用）
docs = ["Transformer 是一种深度学习架构", "RNN 存在梯度消失问题"]
vectors = emb.embed_documents(docs)
print(f"向量数: {len(vectors)}, 维度: {len(vectors[0])}")  # 2, 1536

# 3. 单条向量化（查询用）
query_vec = emb.embed_query("什么是 Transformer？")
# query_vec 和 vectors[0] 的内积 > vectors[1] 的内积（语义更近）
```

---

## 4. Chroma VectorStore（向量存储）

### 组件作用

存储文档的**向量 + 原文 + 元数据**，并提供**相似度检索**。它是 RAG 的"资料库"——用户提问时，在这里找最相关的资料片段。

### Chroma 简介

Chroma 是一个轻量级开源向量数据库，专门为 LLM 应用设计：

- **零配置**：内嵌模式一行代码启动，无需独立服务
- **自动向量化**：配合 LangChain 的 `add_documents()`，自动调用 Embeddings 向量化
- **元数据过滤**：支持 `WHERE` 条件查询（如按 document_id 删除）
- **持久化**：数据存本地磁盘，重启不丢失

### 本项目两种部署模式

| 模式 | 适用场景 | 本项目用法 |
|------|---------|-----------|
| 持久化内嵌 | 单机开发 / MVP | 默认模式，数据存 `backend/data/chroma/` |
| HTTP 客户端 | 生产 / 多副本 | `docker compose` 中的独立 Chroma 容器 |

```python
from langchain_chroma import Chroma

# 持久化内嵌模式
store = Chroma(
    embedding_function=embeddings,      # 向量化函数
    persist_directory="./data/chroma",  # 数据存放路径
    collection_name="studyarag_docs",   # 集合名
)
```

### 核心操作

```
┌─────────────────────────────────────────────────────┐
│  add_documents([Document, ...])                      │
│  文档入库：向量化 + 存储文本 + 存储元数据              │
│                                                      │
│  similarity_search_with_score("什么是RAG？", k=4)    │
│  检索：问题向量化 → 计算距离 → 返回 Top-K + 分数     │
│                                                      │
│  delete(where={"document_id": "xxx"})                │
│  删除：按元数据条件批量删除                           │
└─────────────────────────────────────────────────────┘
```

### Chroma 内部存储结构

每个 Collection 内部是一张表：

| id (UUID) | embedding (Vector) | document (Text) | metadata (JSON) |
|-----------|--------------------|-----------------|-----------------|
| `abc...` | `[0.01, -0.03, ...]` | "Transformer 是..." | `{filename, page, document_id}` |
| `def...` | `[0.05, 0.02, ...]` | "自注意力允许..." | `{filename, page, document_id}` |

检索时，Chroma 计算 query 的向量与所有 embedding 列的距离，返回最近 K 行。

### 不用 LangChain 需要手写什么？

```python
# 手写向量存储 = 管理向量数组 + 手写余弦相似度
import numpy as np
class ManualVectorDB:
    def __init__(self):
        self.vectors = []    # 向量数组
        self.texts = []      # 对应文本
        self.metas = []      # 对应元数据

    def add(self, text, meta, vec):
        self.vectors.append(vec)
        self.texts.append(text)
        self.metas.append(meta)

    def search(self, query_vec, k=4):
        # 手写余弦相似度计算
        scores = [np.dot(query_vec, v) for v in self.vectors]
        top_k = sorted(enumerate(scores), key=lambda x: -x[1])[:k]
        return [(self.texts[i], self.metas[i], scores[i]) for i, s in top_k]
# ← Chroma 替我们做了：持久化、索引优化、元数据过滤、并发安全
```

### 最小示例

```python
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# 1. 初始化
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
store = Chroma(
    embedding_function=embeddings,
    persist_directory="./chroma_data",
    collection_name="my_docs",
)

# 2. 入库（自动向量化）
docs = [
    Document(page_content="Transformer 使用自注意力机制", metadata={"source": "paper.pdf", "page": 1}),
    Document(page_content="BERT 基于双向 Transformer", metadata={"source": "paper.pdf", "page": 2}),
]
store.add_documents(docs)

# 3. 检索（返回 Document + 相似度分数）
results = store.similarity_search_with_score("注意力机制", k=2)
for doc, score in results:
    print(f"[{score:.4f}] {doc.page_content[:50]}... (来源: {doc.metadata['source']} p{doc.metadata['page']})")

# 4. 按条件删除
store.delete(where={"source": "paper.pdf"})
```

---

## 5. Retriever（检索器）

### 组件作用

Retriever 是 VectorStore 的"查询接口"——它只负责**检索**，不负责存储。任何实现了 `invoke(query) → List[Document]` 的对象都可以作为 Retriever。

### Retriever vs VectorStore

```
VectorStore   = 存储 + 检索（数据库）
Retriever     = 仅检索（查询接口）
```

同一个 VectorStore 可以产出多种 Retriever：不同的 `k` 值、不同的过滤条件、不同的排序策略。这种分离让你可以为不同场景创建不同的检索器，而不影响底层数据。

### 本项目的 Retriever 封装

LangChain 提供了 `vectorstore.as_retriever()` 一键转换：

```python
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
docs = retriever.invoke("什么是 RAG？")
# 返回 List[Document]
```

但本项目手写了自己的 `retrieve()` 函数，原因是可以加入自定义逻辑：

1. **结果格式化**：Document → dict（提取 excerpt、格式化字段名）
2. **相似度阈值**：可配置的最低分数门槛（虽然 Chroma 用 L2 距离，阈值需根据模型调优）
3. **日志可观测**：记录每次检索的耗时和结果数

### 不用 LangChain 需要手写什么？

```python
def manual_retrieve(query: str, k: int = 4) -> list[dict]:
    """手写检索 = query 向量化 + 遍历所有向量计算距离 + 排序取 Top-K"""
    query_vec = embed_query(query)
    scores = []
    for i, doc_vec in enumerate(all_vectors):
        # 余弦相似度（需自己实现）
        sim = np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec))
        scores.append((i, sim))
    top_k = sorted(scores, key=lambda x: -x[1])[:k]
    return [{"content": all_texts[i], "score": s} for i, s in top_k]
# ← Chroma + LangChain 替我们做了：
#   - 高效的向量索引（HNSW 算法），不需要遍历所有向量
#   - 持久化和并发安全
#   - 元数据过滤
```

### 最小示例

```python
from langchain_chroma import Chroma

store = Chroma(persist_directory="./data", ...)

# 方式 1：LangChain Retriever 接口（用于 LCEL Chain）
retriever = store.as_retriever(search_kwargs={"k": 4})
docs = retriever.invoke("什么是 RAG？")

# 方式 2：直接调用（本项目方式）
results = store.similarity_search_with_score("什么是 RAG？", k=4)
for doc, score in results:
    print(f"[{score:.4f}] {doc.metadata['filename']} — {doc.page_content[:80]}")
```

---

## 6. PromptTemplate（Prompt 模板）

### 组件作用

将**动态变量**填入**预设的 Prompt 结构**。RAG 系统中最重要的 Prompt 设计是：如何把检索到的参考资料注入 LLM 的上下文。

### ChatPromptTemplate 结构

```python
from langchain_core.prompts import ChatPromptTemplate

template = ChatPromptTemplate.from_messages([
    ("system", "你是 {role}。"),              # SystemMessage: 角色设定
    ("human", "参考资料：{context}\n问题：{question}"),  # HumanMessage: 注入变量
])

# 填充变量 → ChatPromptValue → 发送给 LLM
prompt_value = template.invoke({
    "role": "课程助手",
    "context": "[1] Transformer 是...",
    "question": "什么是 Transformer？",
})
```

- **输入**：变量 dict `{"context": ..., "question": ...}`
- **输出**：`ChatPromptValue`（包含 SystemMessage + HumanMessage）

### 本项目的 Prompt 设计

```
┌──────────────────────────────────────────┐
│ SystemMessage                            │
│                                          │
│ 你是一个严谨的课程资料问答助手。           │
│ 只能依据参考资料回答。                    │
│ 每个观点标注来源编号 [1]、[2]。           │
│ 资料不足时明确说明。                      │
│ 使用简体中文。                           │
├──────────────────────────────────────────┤
│ HumanMessage                             │
│                                          │
│ ## 参考资料                              │
│ [1] (来源: NLP讲义.pdf, 第3页)           │
│ Transformer 是一种基于自注意力机制的...    │
│                                          │
│ [2] (来源: 笔记.md, 2.1 注意力机制)       │
│ 自注意力机制允许模型...                   │
│                                          │
│ ## 用户问题                              │
│ 什么是 Transformer？                     │
└──────────────────────────────────────────┘
```

### 不用 LangChain 需要手写什么？

```python
def manual_prompt(context: str, question: str) -> list[dict]:
    """手写 Prompt 构建 —— 就是字符串拼接 + 字典构造"""
    system = "你是一个严谨的助手。只能依据参考资料回答。"
    human = f"## 参考资料\n{context}\n\n## 用户问题\n{question}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": human},
    ]
# ← ChatPromptTemplate 替我们做的：
#   - 变量验证（缺失变量会报错）
#   - 消息类型管理（SystemMessage、HumanMessage、AIMessage）
#   - 与 LangChain LLM 接口无缝衔接
```

### 关键设计决策

1. **System Message 设定边界**：明确 LLM 不能用自己的知识，只能基于参考资料
2. **引用编号 [N]**：要求 LLM 在回答中标注来源编号，方便用户追溯
3. **兜底规则**：资料不足时拒绝回答，这是反幻觉的核心机制
4. **中文约束**：确保 LLM 不会切换到英文

### 最小示例

```python
from langchain_core.prompts import ChatPromptTemplate

# 1. 定义模板
template = ChatPromptTemplate.from_messages([
    ("system", "你是一个{subject}专家，只基于给定资料回答。"),
    ("human", "资料：{context}\n\n问题：{question}"),
])

# 2. 填充变量
prompt_value = template.invoke({
    "subject": "深度学习",
    "context": "Transformer 使用自注意力机制来处理序列数据。",
    "question": "Transformer 的核心机制是什么？",
})

# 3. 查看生成的 messages
for msg in prompt_value.to_messages():
    print(f"[{msg.type}] {msg.content[:100]}...")
```

---

## 7. Runnable / LCEL（LangChain Expression Language）

### 组件作用

LCEL 是 LangChain 的**组合语言**。用管道符 `|` 将多个 Runnable 组件串联，数据从左到右自动流经每个步骤。它是 LangChain 最核心的设计理念：**一切皆 Runnable，统一接口，任意组合**。

### Runnable 接口

任何 Runnable 都实现了两个方法：

```python
class Runnable:
    def invoke(self, input, config=None) -> output:  # 同步执行
        ...

    async def ainvoke(self, input, config=None) -> output:  # 异步执行
        ...
```

- Document Loader 是 Runnable
- Text Splitter 不是（但可以被包装成 RunnableLambda）
- ChatOpenAI 是 Runnable
- StrOutputParser 是 Runnable
- 你自己用 `|` 串起来的 Chain 也是 Runnable

### 管道操作符 `|`

这是 LCEL 的灵魂。`A | B` 的意思是：把 A 的输出作为 B 的输入。

```python
chain = step1 | step2 | step3
result = chain.invoke(input)
# 等价于：
# tmp1 = step1.invoke(input)
# tmp2 = step2.invoke(tmp1)
# result = step3.invoke(tmp2)
```

### 本项目的完整 RAG Chain

```python
rag_chain = (
    {                                                       # Step 1: 并行准备变量
        "context": RunnableLambda(_retrieve_and_format),     #   检索+格式化
        "question": RunnablePassthrough(),                  #   问题原样传递
    }
    | prompt_template                                       # Step 2: 填入 Prompt
    | llm                                                   # Step 3: LLM 生成
    | StrOutputParser()                                     # Step 4: 提取纯文本
)
```

逐步骤拆解：

```
输入: "什么是 Transformer？"
    │
    ▼ Step 1: 并行字典
    │ {
    │   "context": _retrieve_and_format("什么是 Transformer？")
    │            → "[1] (来源: NLP讲义.pdf) Transformer 是..."
    │   "question": RunnablePassthrough() → "什么是 Transformer？"
    │ }
    │ → {"context": "[1] ...", "question": "什么是 Transformer？"}
    │
    ▼ Step 2: PromptTemplate
    │ System: "你是一个严谨的课程资料问答助手..."
    │ Human:  "## 参考资料\n[1] ...\n\n## 用户问题\n什么是 Transformer？"
    │ → ChatPromptValue
    │
    ▼ Step 3: ChatOpenAI
    │ → AIMessage(content="Transformer 是一种基于自注意力机制的...")
    │
    ▼ Step 4: StrOutputParser
    │ → "Transformer 是一种基于自注意力机制的..."
    │
    输出: 纯文本字符串
```

### 关键 Runnable 组件详解

| 组件 | 作用 | 输入 → 输出 |
|------|------|------------|
| `RunnablePassthrough()` | 原样传递数据 | `x` → `x` |
| `RunnableLambda(fn)` | 包装普通函数为 Runnable | 函数入参 → 函数返回值 |
| `StrOutputParser()` | 从 AIMessage 提取纯文本 | `AIMessage` → `str` |
| `ChatPromptTemplate` | 格式化为 Chat 消息 | `{变量} dict` → `ChatPromptValue` |
| `ChatOpenAI` | 调用大语言模型 | `ChatPromptValue` → `AIMessage` |

### 为什么本项目的 ask() 不直接用 Chain 传 sources？

面试中你可能会被问到："你的 Chain 返回的是纯文本，那 sources 是怎么拿到前端的？"

设计决策：**检索和生成分两步执行，不在 Chain 内部回传 sources。**

```python
def ask(question: str) -> dict:
    # Step 1: 执行检索（拿到带 metadata 的原始结果）
    retrieved = retrieve(question)

    # Step 2: Chain 只负责生成答案（纯文本）
    answer = chain.invoke(question)

    # Step 3: 在函数层面组合两者
    return {"answer": answer, "sources": retrieved}
```

**为什么不把 sources 嵌入 Chain 内部？**
- Chain 的内部数据流是单向的：输入 → 步骤1 → 步骤2 → ... → 输出
- 中间步骤的检索结果在 Chain 结束时已经"丢失"（被 PromptTemplate 转换成了字符串）
- 要让 sources 从 Chain 中透传出来，需要写复杂的自定义 Runnable
- 在函数层面分开调用，逻辑更清晰，面试时更容易解释

### 不用 LangChain 需要手写什么？

```python
def manual_rag(question: str) -> dict:
    """手写 RAG = 手动编排检索 → Prompt → LLM → 解析"""
    # 1. 检索
    retrieved = my_retrieve(question)
    context = format_context(retrieved)

    # 2. 构建 Prompt
    system = "你是助手，只基于资料回答。"
    human = f"资料：{context}\n\n问题：{question}"

    # 3. 调用 LLM
    import openai
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": human},
        ],
    )
    answer = response.choices[0].message.content

    # 4. 返回
    return {"answer": answer, "sources": retrieved}
# ← LCEL Chain 替我们做的：
#   - 统一的 invoke/ainvoke 接口
#   - 每个步骤可独立测试和替换
#   - 自动处理异步、流式、回调
#   - 可视化链路追踪（LangSmith 集成）
```

### 最小示例

```python
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# 自定义检索+格式化函数
def get_context(query: str) -> str:
    return "[1] Transformer 使用自注意力机制..."

# 构建 Chain
chain = (
    {
        "context": RunnableLambda(get_context),
        "question": RunnablePassthrough(),
    }
    | ChatPromptTemplate.from_messages([
        ("system", "你是一个助手。参考资料：{context}"),
        ("human", "{question}"),
    ])
    | ChatOpenAI(model="gpt-4o")
    | StrOutputParser()
)

# 执行
answer = chain.invoke("什么是 Transformer？")
print(answer)
```

### 七个组件总结

至此，我们学完了 StudyRAG 用到的全部 7 个 LangChain 核心组件：

```
Document Loader  →  Text Splitter  →  Embeddings  →  VectorStore
      ↓                                              ↓
  原始文件 → Document → chunks → 向量 → Chroma 存储 → 检索
                                                         ↓
                                          Retriever ←───┘
                                              ↓
                                        检索结果 (List[dict])
                                              ↓
                                       PromptTemplate
                                              ↓
                                         Prompt (含来源)
                                              ↓
                                          ChatOpenAI
                                              ↓
                                        AIMessage
                                              ↓
                                      StrOutputParser
                                              ↓
                                          纯文本回答
```

**数据流一句话总结**：文件加载 → 切分 → 向量化 → 存储 → 检索 → Prompt → LLM → 解析 → 回答+来源。
