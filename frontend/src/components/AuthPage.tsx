/**
 * 登录/注册页面
 * 白色卡片居中布局，两个 Tab 切换
 */

import { useState, type FormEvent } from "react";
import { register, login, setToken } from "../api/client";

interface Props {
  onAuthSuccess: () => void; // 认证成功后通知父组件
}

type Tab = "login" | "register";

export default function AuthPage({ onAuthSuccess }: Props) {
  const [tab, setTab] = useState<Tab>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    // 前端校验
    if (!username.trim() || !password.trim()) {
      setError("请填写用户名和密码。");
      return;
    }
    if (tab === "register") {
      if (username.length < 2) {
        setError("用户名至少 2 个字符。");
        return;
      }
      if (password.length < 4) {
        setError("密码至少 4 个字符。");
        return;
      }
    }

    setLoading(true);
    try {
      const body = { username: username.trim(), password };
      const result = tab === "login" ? await login(body) : await register(body);
      setToken(result.access_token);
      onAuthSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败，请重试。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">📚 StudyRAG</h1>
        <p className="auth-subtitle">RAG 知识库问答系统</p>

        {/* Tab 切换 */}
        <div className="auth-tabs">
          <button
            className={`auth-tab ${tab === "login" ? "active" : ""}`}
            onClick={() => { setTab("login"); setError(null); }}
          >
            登录
          </button>
          <button
            className={`auth-tab ${tab === "register" ? "active" : ""}`}
            onClick={() => { setTab("register"); setError(null); }}
          >
            注册
          </button>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="auth-field">
            <label htmlFor="username">用户名</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="输入用户名"
              autoComplete="username"
              disabled={loading}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="password">密码</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="输入密码"
              autoComplete={tab === "login" ? "current-password" : "new-password"}
              disabled={loading}
            />
          </div>

          {error && <p className="auth-error">{error}</p>}

          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? "处理中..." : tab === "login" ? "登录" : "注册"}
          </button>
        </form>

        <p className="auth-hint">
          {tab === "login"
            ? "还没有账号？点击上方「注册」创建。"
            : "已有账号？点击上方「登录」。"
          }
        </p>
      </div>
    </div>
  );
}
