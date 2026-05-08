/**
 * 问答面板组件
 * 输入框 + 发送按钮 + 消息列表 + 空状态提示
 */

import { useState, useRef, useEffect, type FormEvent } from "react";
import { askQuestion } from "../api/client";
import type { ChatResponse } from "../types";
import MessageBubble from "./MessageBubble";

interface Props {
  hasDocuments: boolean; // 知识库是否有文档
}

export default function ChatPanel({ hasDocuments }: Props) {
  const [messages, setMessages] = useState<ChatResponse[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e?: FormEvent) => {
    e?.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setError(null);
    setLoading(true);

    try {
      const response = await askQuestion({ question });
      setMessages((prev) => [...prev, response]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "问答请求失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-panel-inner">
      {/* 消息列表 */}
      <div className="messages-container">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p className="chat-empty-icon">💬</p>
            <p>
              {hasDocuments
                ? "在下方输入问题，基于已上传的资料获取回答。"
                : "请先上传文档到左侧知识库，再开始提问。"}
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {loading && (
          <div className="message ai-message">
            <div className="message-bubble ai-bubble thinking">
              正在检索资料并生成回答...
            </div>
          </div>
        )}

        {error && <p className="upload-error">{error}</p>}
        <div ref={bottomRef} />
      </div>

      {/* 输入区域 */}
      <form className="chat-input-area" onSubmit={handleSend}>
        <input
          type="text"
          className="chat-input"
          placeholder={hasDocuments ? "输入您的问题..." : "请先上传文档..."}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="btn-send"
          disabled={!input.trim() || loading}
        >
          {loading ? "思考中..." : "发送"}
        </button>
      </form>
    </div>
  );
}
