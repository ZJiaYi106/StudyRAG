# StudyRAG LangChain 学习笔记

> 本文档随项目开发逐步积累，记录每个 LangChain 组件的学习心得。
> 每篇文章包含：组件作用、输入/输出、手写等价代码、最小示例。

---

## 目录

- [x] 1. Document Loader（步骤 2）
- [x] 2. Text Splitter（步骤 3）
- [ ] 3. Embeddings（步骤 4）
- [ ] 4. Chroma VectorStore（步骤 4）
- [ ] 5. Retriever（步骤 6）
- [ ] 6. PromptTemplate（步骤 6）
- [ ] 7. Runnable / LCEL（步骤 7）

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
