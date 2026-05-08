/**
 * StudyRAG 前端类型定义
 * 与后端 Pydantic 模型一一对应
 */

/** 文档列表项 */
export interface DocumentListItem {
  id: string;
  filename: string;
  file_type: string;
  chunk_count: number;
  created_at: string;
}

/** 上传响应 */
export interface DocumentUploadResponse {
  id: string;
  filename: string;
  file_type: string;
  page_count: number;
  chunk_count: number;
  created_at: string;
}

/** 删除响应 */
export interface DeleteResponse {
  message: string;
}

/** 引用来源 */
export interface SourceInfo {
  filename: string;
  page: number | null;
  chapter: string | null;
  excerpt: string;
  score: number;
}

/** 问答请求 */
export interface ChatRequest {
  question: string;
  top_k?: number;
}

/** 问答响应 */
export interface ChatResponse {
  answer: string;
  sources: SourceInfo[];
  question: string;
}

/** 健康检查 */
export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  chroma?: string;
  document_count?: number;
}
