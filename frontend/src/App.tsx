/**
 * StudyRAG 主应用组件
 * 布局：左侧文档管理 | 右侧问答面板
 */

import { checkHealth } from "./api/client";
import type { HealthStatus } from "./types";
import { useEffect, useState } from "react";

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="app-container">
      {/* 顶部导航 */}
      <header className="app-header">
        <h1>📚 StudyRAG</h1>
        <span className="subtitle">RAG 知识库问答系统</span>
        <span className={`status-badge ${health ? "online" : "offline"}`}>
          {health ? "🟢 后端已连接" : error ? "🔴 后端未连接" : "⏳ 连接中..."}
        </span>
      </header>

      {/* 主体区域 */}
      <main className="app-main">
        {/* 左侧：文档管理 */}
        <aside className="sidebar">
          <section className="panel">
            <h2>📁 文档管理</h2>
            <p className="placeholder-text">文档上传和列表将在后续步骤中实现</p>
          </section>
        </aside>

        {/* 右侧：问答面板 */}
        <section className="chat-area">
          <div className="panel chat-panel">
            <h2>💬 问答</h2>
            <p className="placeholder-text">问答功能将在后续步骤中实现</p>
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
