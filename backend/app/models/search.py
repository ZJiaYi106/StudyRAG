"""
检索结果数据模型
统一的多路召回和重排结果格式
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchResult:
    """统一的检索结果，可用于 Dense、Sparse、Rerank 各阶段"""
    content: str                                    # chunk 文本内容
    score: float                                    # 相似度分数（0-1）
    filename: str = ""                              # 来源文件名
    page: Optional[int] = None                      # 页码
    chapter: Optional[str] = None                   # 章节
    document_id: str = ""                           # 文档 ID
    chunk_index: int = 0                            # chunk 序号
    source: str = "unknown"                         # 来源标记: dense / sparse / rerank
    metadata: dict = field(default_factory=dict)    # 额外元数据

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "excerpt": self.content[:200],
            "score": round(self.score, 4),
            "filename": self.filename,
            "page": self.page,
            "chapter": self.chapter,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "source": self.source,
        }
