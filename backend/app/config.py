"""
StudyRAG 配置管理
使用 pydantic-settings 从 .env 文件加载配置
所有密钥类配置绝不硬编码，必须从环境变量读取
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，自动从 .env 文件和环境变量中加载"""

    # --- LLM 配置（OpenAI API 兼容接口） ---
    # SecretStr: 防止密钥在日志或 print(settings) 时泄露
    # 取值时需要用 .get_secret_value() 方法
    llm_api_key: SecretStr
    llm_api_base: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o"

    # --- Embedding 配置（OpenAI API 兼容接口） ---
    embedding_api_key: SecretStr
    embedding_api_base: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"

    # --- Chroma 向量数据库 ---
    chroma_host: str = "chroma"
    chroma_port: int = 8000
    chroma_collection: str = "studyarag_docs"

    # --- 上传文件存储路径 ---
    # 默认值指向 backend/data/uploads（本地开发），Docker 中通过环境变量覆盖
    upload_dir: str = "data/uploads"

    # --- 文本切分参数 ---
    chunk_strategy: str = Field(
        default="recursive",
        description="默认分块策略：recursive / token / character",
    )
    chunk_size: int = Field(default=1000, ge=50, le=8000)
    chunk_overlap: int = Field(default=200, ge=0, le=2000)

    # --- 检索参数 ---
    top_k: int = Field(default=4, ge=1, le=20)
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

    # --- JWT 认证 ---
    jwt_secret: str = "studyarag-secret-change-in-production"
    jwt_expire_days: int = 7

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # 声明 .env 文件路径（pydantic-settings 默认会从当前目录向上查找）
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # 忽略 .env 中未定义的额外字段
    }


# 全局单例，应用启动时加载一次
settings = Settings()
