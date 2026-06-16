"""
服务接口抽象基类
定义所有可插拔组件的统一接口，实现模块化可替换架构。

每个组件都有：
- 抽象基类（定义契约）
- 一个或多个具体实现（可在工厂中切换）
- 统一的输入输出类型

这样更换向量库（Chroma → Milvus）、
更换重排模型（bge → Cohere）、
或更换 LLM（DeepSeek → GPT）时，
只需修改工厂配置，无需改动业务逻辑。
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from langchain_core.documents import Document
from app.models.search import SearchResult


# ================================================================
# Loader: 文档加载器接口
# ================================================================

class BaseLoader(ABC):
    """文档加载器抽象基类"""

    @abstractmethod
    def load(self, file_path: str, document_id: str) -> List[Document]:
        """
        加载文件并返回 LangChain Document 列表。

        Args:
            file_path: 文件绝对路径
            document_id: 关联的文档唯一 ID

        Returns:
            List[Document]: 加载后的 Document 列表（每页/每节/每幻灯片一个）
        """
        ...


# ================================================================
# Splitter: 文本切分器接口
# ================================================================

class BaseSplitter(ABC):
    """文本切分器抽象基类"""

    @abstractmethod
    def split(
        self,
        docs: List[Document],
        strategy: str = "recursive",
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[Document]:
        """
        将 Document 列表切分为 chunk 列表。

        Args:
            docs: Loader 返回的 Document 列表
            strategy: 分块策略（recursive / token / character）
            chunk_size: 每个 chunk 的最大字符/token 数
            chunk_overlap: 相邻 chunk 的重叠大小

        Returns:
            切分后的 Document 列表（chunks）
        """
        ...


# ================================================================
# Embedder: 向量化器接口
# ================================================================

class BaseEmbedder(ABC):
    """Embedding 向量化器抽象基类"""

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量向量化文本"""
        ...

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """单条查询向量化"""
        ...


# ================================================================
# Retriever: 检索器接口
# ================================================================

class BaseRetriever(ABC):
    """检索器抽象基类——所有检索策略的统一入口"""

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 4) -> List[SearchResult]:
        """
        根据查询检索最相关的文档片段。

        Args:
            query: 用户问题
            top_k: 返回结果数量

        Returns:
            排序后的 SearchResult 列表
        """
        ...


# ================================================================
# Reranker: 重排序器接口
# ================================================================

class BaseReranker(ABC):
    """重排序器抽象基类"""

    @abstractmethod
    def rerank(self, query: str, candidates: List[SearchResult]) -> List[SearchResult]:
        """
        对候选结果进行精排。

        Args:
            query: 用户问题
            candidates: 粗排返回的候选结果

        Returns:
            重排后的 SearchResult 列表（分数更新）
        """
        ...


# ================================================================
# Indexer: 索引器接口
# ================================================================

class BaseIndexer(ABC):
    """向量/关键词索引器抽象基类"""

    @abstractmethod
    def add(self, docs: List[Document]) -> List[str]:
        """将文档块添加到索引"""
        ...

    @abstractmethod
    def delete(self, document_id: str) -> int:
        """删除指定文档的所有块"""
        ...

    @abstractmethod
    def search(self, query: str, top_k: int = 4) -> List[SearchResult]:
        """
        搜索最相关的文档块。
        内部自行处理 embedding 转换。

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            排序后的 SearchResult 列表
        """
        ...


# ================================================================
# Cache: 缓存接口
# ================================================================

class BaseCache(ABC):
    """缓存抽象基类"""

    @abstractmethod
    def get(self, key: str) -> Optional[object]:
        """获取缓存值"""
        ...

    @abstractmethod
    def set(self, key: str, value: object, ttl: int = 300) -> None:
        """设置缓存值（ttl 秒后过期）"""
        ...

    @abstractmethod
    def clear(self) -> None:
        """清空缓存"""
        ...
