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
  UploadOptions,
  RegisterRequest,
  LoginRequest,
  TokenResponse,
  UserInfo,
} from "../types";

// 后端 API 地址
// 开发时 Vite 代理将 /api 转发到后端，生产时通过 nginx 或直接部署
const API_BASE = "";

// ================================================================
// Token 管理
// ================================================================

const TOKEN_KEY = "studyarag_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * 构建带认证头的请求选项
 */
function authOptions(options?: RequestInit): RequestInit {
  const token = getToken();
  const headers: Record<string, string> = {
    ...((options?.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // 只有 JSON 请求设置 Content-Type（FormData 上传由浏览器自动设置）
  if (!(options?.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  return { ...options, headers };
}

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
 * 通用 JSON 请求（自动附带认证 token）
 */
async function request<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, authOptions(options));

  if (!response.ok) {
    const msg = await extractError(response);
    throw new Error(msg);
  }

  return response.json();
}

/** 健康检查（无需认证） */
export async function checkHealth(): Promise<HealthStatus> {
  // 健康检查不需要认证，直接用 fetch
  const response = await fetch(`${API_BASE}/api/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return response.json();
}

// ================================================================
// 认证 API
// ================================================================

/** 注册 */
export async function register(body: RegisterRequest): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const msg = await extractError(response);
    throw new Error(msg);
  }
  return response.json();
}

/** 登录 */
export async function login(body: LoginRequest): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const msg = await extractError(response);
    throw new Error(msg);
  }
  return response.json();
}

/** 获取当前用户信息 */
export async function getMe(): Promise<UserInfo> {
  return request<UserInfo>("/api/auth/me");
}

/** 上传文档 */
export async function uploadDocument(
  file: File,
  options?: UploadOptions
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  // 构建 query string 传递分块参数
  const params = new URLSearchParams();
  if (options?.chunkStrategy) {
    params.set("chunk_strategy", options.chunkStrategy);
  }
  if (options?.chunkSize !== undefined) {
    params.set("chunk_size", String(options.chunkSize));
  }
  if (options?.chunkOverlap !== undefined) {
    params.set("chunk_overlap", String(options.chunkOverlap));
  }

  const queryString = params.toString();
  const url = `${API_BASE}/api/documents${queryString ? "?" + queryString : ""}`;

  // 不设置 Content-Type，让浏览器自动处理 multipart/form-data boundary
  const response = await fetch(url, authOptions({
    method: "POST",
    body: formData,
  }));

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

/** SSE 进度事件 */
export interface ProgressEvent {
  step: string;
  message: string;
  answer?: string;
  sources?: ChatResponse["sources"];
}

/** 流式提问（SSE），支持进度回调 */
export async function askQuestionStream(
  body: ChatRequest,
  onProgress: (evt: ProgressEvent) => void,
  onDone: (answer: string, sources: ChatResponse["sources"]) => void,
  onError: (err: string) => void,
): Promise<void> {
  const token = getToken();
  try {
    const response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const msg = await extractError(response);
      onError(msg);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) { onError("无法读取响应流"); return; }

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = JSON.parse(line.slice(6)) as ProgressEvent;
          if (data.step === "result") {
            onDone(data.answer || "", data.sources || []);
          } else {
            onProgress(data);
          }
        }
      }
    }
  } catch (err) {
    onError(err instanceof Error ? err.message : "请求失败");
  }
}
