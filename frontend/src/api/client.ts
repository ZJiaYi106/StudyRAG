/**
 * StudyRAG API 客户端
 * 封装所有后端 API 调用，统一错误处理
 */

import type {
  DocumentListItem,
  DocumentUploadResponse,
  DeleteResponse,
  ChatRequest,
  ChatResponse,
  HealthStatus,
} from "../types";

// 后端 API 地址
// 开发时 Vite 代理将 /api 转发到后端，生产时通过 nginx 或直接部署
const API_BASE = "";

/**
 * 从 Response 中提取错误信息。
 * FastAPI 返回 JSON: {"detail": "错误描述"}
 * 其他情况：返回 HTTP 状态文本
 */
async function extractError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    // FastAPI 的 HTTPException 错误格式
    if (body.detail) {
      return typeof body.detail === "string"
        ? body.detail
        : JSON.stringify(body.detail);
    }
    return JSON.stringify(body);
  } catch {
    // 响应不是 JSON（如 502 网关错误），使用状态文本
    return `${response.statusText} (HTTP ${response.status})`;
  }
}

/**
 * 通用 JSON 请求
 */
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
    const msg = await extractError(response);
    throw new Error(msg);
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

  // 不设置 Content-Type，让浏览器自动处理 multipart/form-data boundary
  const response = await fetch(`${API_BASE}/api/documents`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const msg = await extractError(response);
    throw new Error(msg);
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
