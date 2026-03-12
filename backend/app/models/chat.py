"""
问答相关的 Pydantic 数据模型
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """用户提问请求"""
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    top_k: int = Field(default=4, ge=1, le=20, description="检索的参考资料片段数")


class SourceInfo(BaseModel):
    """单个引用来源的详细信息"""
    filename: str = Field(..., description="来源文件名")
    page: int | None = Field(default=None, description="页码（Markdown 文件可能没有页码）")
    chapter: str | None = Field(default=None, description="章节名称")
    excerpt: str = Field(..., description="原文片段（截取前 200 字）")
    score: float = Field(..., description="向量相似度分数")


class ChatResponse(BaseModel):
    """问答响应"""
    answer: str = Field(..., description="LLM 基于资料生成的中文回答")
    sources: list[SourceInfo] = Field(default_factory=list, description="引用的资料来源列表")
    question: str = Field(..., description="回显用户问题")
