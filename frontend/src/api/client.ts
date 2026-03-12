/**
 * StudyRAG API 客户端
 * 封装所有后端 API 调用
 */

import type {
  DocumentListItem,
  DocumentUploadResponse,
  DeleteResponse,
  ChatRequest,
  ChatResponse,
  HealthStatus,
} from "../types";

// 后端 API 地址（开发时指向本地 8000 端口）
const API_BASE = "http://localhost:8000";

async function request<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(errorBody || `HTTP ${response.status}`);
  }

  return response.json();
}

/** 健康检查 */
export async function checkHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/api/health");
}

/** 上传文档 */
export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/api/documents`, {
    method: "POST",
    body: formData,
    // 不设置 Content-Type，让浏览器自动处理 multipart/form-data
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(errorBody || `上传失败 (HTTP ${response.status})`);
  }

  return response.json();
}

/** 获取文档列表 */
export async function listDocuments(): Promise<DocumentListItem[]> {
  return request<DocumentListItem[]>("/api/documents");
}

/** 删除文档 */
export async function deleteDocument(id: string): Promise<DeleteResponse> {
  return request<DeleteResponse>(`/api/documents/${id}`, {
    method: "DELETE",
  });
}

/** 提问 */
export async function askQuestion(body: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
