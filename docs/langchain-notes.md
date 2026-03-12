# StudyRAG LangChain 学习笔记

> 本文档随项目开发逐步积累，记录每个 LangChain 组件的学习心得。
> 每篇文章包含：组件作用、输入/输出、手写等价代码、最小示例。

---

## 目录

- [x] 1. Document Loader（步骤 2）
- [ ] 2. Text Splitter（步骤 3）
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
