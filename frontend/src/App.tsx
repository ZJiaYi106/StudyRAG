/**
 * StudyRAG 主应用组件
 * 布局：左侧文档管理（上传+列表） | 右侧问答面板
 */

import { useEffect, useState, useCallback } from "react";
import { checkHealth, listDocuments, getMe, getToken, clearToken } from "./api/client";
import type { HealthStatus } from "./types";
import AuthPage from "./components/AuthPage";
import FileUpload from "./components/FileUpload";
import DocList from "./components/DocList";
import ChatPanel from "./components/ChatPanel";
import RerankerPanel from "./components/RerankerPanel";
import ThemeToggle, { type Theme } from "./components/ThemeToggle";

const THEME_KEY = "studyarag-theme";

function getInitialTheme(): Theme {
  if (typeof window === "undefined") return "light";

  const saved = window.localStorage.getItem(THEME_KEY);
  if (saved === "light" || saved === "dark") return saved;

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function App() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [hasDocuments, setHasDocuments] = useState(false);
  const [docCount, setDocCount] = useState(0);
  const [chunkCount, setChunkCount] = useState(0);

  // --- 认证状态 ---
  const [isLoggedIn, setIsLoggedIn] = useState<boolean | null>(null); // null=检查中
  const [currentUser, setCurrentUser] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  const toggleTheme = () => setTheme((current) => current === "light" ? "dark" : "light");

  // 启动时检查 token 有效性
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setIsLoggedIn(false);
      return;
    }
    // 有 token，验证是否有效
    getMe()
      .then((user) => {
        setCurrentUser(user.username);
        setIsLoggedIn(true);
      })
      .catch(() => {
        clearToken();
        setIsLoggedIn(false);
      });
  }, []);

  // 认证成功回调
  const onAuthSuccess = useCallback(() => {
    getMe()
      .then((user) => {
        setCurrentUser(user.username);
        setIsLoggedIn(true);
      })
      .catch(() => {
        clearToken();
        setIsLoggedIn(false);
      });
  }, []);

  // 退出登录
  const handleLogout = () => {
    clearToken();
    setIsLoggedIn(false);
    setCurrentUser(null);
  };

  // 健康检查
  useEffect(() => {
    if (!isLoggedIn) return;
    checkHealth()
      .then(setHealth)
      .catch((err) => setHealthError(err.message));
  }, [isLoggedIn]);

  // 检查知识库是否为空（用于 ChatPanel 提示）
  const checkDocs = useCallback(async () => {
    if (!isLoggedIn) return;
    try {
      const docs = await listDocuments();
      setHasDocuments(docs.length > 0);
      setDocCount(docs.length);
      setChunkCount(docs.reduce((sum, d) => sum + (d.chunk_count ?? 0), 0));
    } catch {
      setHasDocuments(false);
    }
  }, [isLoggedIn]);

  useEffect(() => { checkDocs(); }, [refreshKey, checkDocs]);

  const onUploaded = () => setRefreshKey((k) => k + 1);

  // --- 渲染：未登录或检查中 ---
  if (isLoggedIn !== true) {
    return (
      <div className="app-container auth-shell">
        <div className="ambient ambient-one" />
        <div className="ambient ambient-two" />
        <div className="auth-theme-control">
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
        </div>
        <AuthPage onAuthSuccess={onAuthSuccess} />
      </div>
    );
  }

  return (
    <div className="app-container">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <header className="app-header">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">S</div>
          <div>
            <div className="brand-name">StudyRAG</div>
            <div className="brand-caption">PERSONAL KNOWLEDGE WORKSPACE</div>
          </div>
        </div>

        <div className="header-actions">
          <span className={`status-badge ${health ? "online" : "offline"}`}>
            <span className="status-dot" />
            {health
              ? `${docCount} 份资料已索引`
              : healthError
                ? "服务暂时离线"
                : "正在连接服务"}
          </span>
          <ThemeToggle theme={theme} onToggle={toggleTheme} compact />
          {currentUser && (
            <div className="user-info">
              <span className="user-avatar">{currentUser.slice(0, 1).toUpperCase()}</span>
              <span className="user-name">{currentUser}</span>
              <button className="btn-logout" onClick={handleLogout}>退出</button>
            </div>
          )}
        </div>
      </header>

      <main className="app-main">
        <aside className="sidebar">
          <div className="sidebar-inner">
            <div className="workspace-heading">
              <div>
                <span className="eyebrow">WORKSPACE</span>
                <h1>资料库</h1>
                <p>把你的课程、论文与笔记集中起来。</p>
              </div>
              <div className="workspace-count">
                <strong>{docCount}</strong>
                <span>DOCS</span>
              </div>
            </div>

            <section className="sidebar-card upload-card">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">INGEST</span>
                  <h2>添加新资料</h2>
                </div>
                <span className="section-symbol">↗</span>
              </div>
              <p className="section-description">上传后会自动解析、切分并建立可检索索引。</p>
              <FileUpload onUploaded={onUploaded} />
            </section>

            <section className="library-section">
              <div className="section-heading compact-heading">
                <div>
                  <span className="eyebrow">LIBRARY</span>
                  <h2>已收录资料</h2>
                </div>
                <span className="section-symbol">•••</span>
              </div>
              <DocList refreshKey={refreshKey} />
            </section>

            <section className="reranker-section">
              <RerankerPanel />
            </section>
          </div>
        </aside>

        <section className="chat-area">
          <div className="panel chat-panel">
            <header className="chat-header">
              <div className="chat-title-group">
                <div className="assistant-orb" aria-hidden="true">
                  <span />
                </div>
                <div>
                  <span className="eyebrow">RESEARCH DESK</span>
                  <h2>知识库问答</h2>
                  <p>从已索引资料中寻找答案，并保留每一条引用。</p>
                </div>
              </div>
              <div className="chat-header-meta">
                <span className="live-indicator"><span /> RAG 在线</span>
                <span className="header-divider" />
                <span>{docCount} 份资料 · {chunkCount} 个片段</span>
              </div>
            </header>
            <ChatPanel hasDocuments={hasDocuments} />
          </div>
        </section>
      </main>

      <footer className="app-footer">
        <span><strong>StudyRAG</strong> · v0.1.0</span>
        <span>{health ? `${health.service} ${health.version} · Chroma ${health.chroma ?? "ready"}` : "等待后端连接"}</span>
      </footer>
    </div>
  );
}

export default App;
