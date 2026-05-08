/**
 * StudyRAG 主应用组件
 * 布局：左侧文档管理（上传+列表） | 右侧问答面板
 */

import { useEffect, useState, useCallback } from "react";
import { checkHealth, listDocuments } from "./api/client";
import type { HealthStatus } from "./types";
import FileUpload from "./components/FileUpload";
import DocList from "./components/DocList";
import ChatPanel from "./components/ChatPanel";

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [hasDocuments, setHasDocuments] = useState(false);

  // 健康检查
  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch((err) => setHealthError(err.message));
  }, []);

  // 检查知识库是否为空（用于 ChatPanel 提示）
  const checkDocs = useCallback(async () => {
    try {
      const docs = await listDocuments();
      setHasDocuments(docs.length > 0);
    } catch {
      setHasDocuments(false);
    }
  }, []);

  useEffect(() => { checkDocs(); }, [refreshKey, checkDocs]);

  const onUploaded = () => setRefreshKey((k) => k + 1);

  return (
    <div className="app-container">
      {/* 顶部导航 */}
      <header className="app-header">
        <h1>📚 StudyRAG</h1>
        <span className="subtitle">RAG 知识库问答系统</span>
        <span className={`status-badge ${health ? "online" : "offline"}`}>
          {health
            ? `🟢 后端已连接（${health.document_count} 篇文档）`
            : healthError
              ? "🔴 后端未连接"
              : "⏳ 连接中..."}
        </span>
      </header>

      {/* 主体区域 */}
      <main className="app-main">
        {/* 左侧：文档管理 */}
        <aside className="sidebar">
          <section className="panel">
            <h2>📁 文档管理</h2>
            <FileUpload onUploaded={onUploaded} />
            <DocList refreshKey={refreshKey} />
          </section>
        </aside>

        {/* 右侧：问答面板 */}
        <section className="chat-area">
          <div className="panel chat-panel">
            <h2>💬 问答</h2>
            <ChatPanel hasDocuments={hasDocuments} />
          </div>
        </section>
      </main>

      {/* 底部状态栏 */}
      <footer className="app-footer">
        <span>StudyRAG v0.1.0</span>
        <span>
          后端状态：{health ? `${health.service} ${health.version}` : "未连接"}
        </span>
      </footer>
    </div>
  );
}

export default App;
