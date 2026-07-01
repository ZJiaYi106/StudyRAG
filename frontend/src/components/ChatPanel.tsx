import { useState, useRef, useEffect, type FormEvent } from "react";
import { askQuestionStream, type ProgressEvent } from "../api/client";
import type { ChatResponse } from "../types";
import MessageBubble from "./MessageBubble";

interface Props { hasDocuments: boolean; }

const STEPS = ["route","rewrite","search","rerank","done","generate"];
const STEP_LABELS: Record<string, string> = {
  route: "分析", rewrite: "改写", search: "召回",
  rerank: "精排", done: "完成", generate: "生成",
};

export default function ChatPanel({ hasDocuments }: Props) {
  const [messages, setMessages] = useState<ChatResponse[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [streamText, setStreamText] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    // 仅当用户本来就在底部附近时才自动滚动，避免打断回看历史消息
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 140;
    if (nearBottom) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, progress, streamText]);

  const handleSend = async (e?: FormEvent) => {
    e?.preventDefault();
    const question = input.trim();
    if (!question || loading) return;
    setInput(""); setError(null); setLoading(true);
    setProgress({ step: "start", message: "正在处理…" });
    setStreamText("");

    await askQuestionStream(
      { question },
      (evt) => setProgress(evt),
      (delta) => setStreamText((prev) => prev + delta),
      (answer, sources) => {
        setMessages(prev => [...prev, { question, answer, sources }]);
        setLoading(false); setProgress(null); setStreamText("");
      },
      (err) => { setError(err); setLoading(false); setProgress(null); setStreamText(""); },
    );
  };

  return (
    <div className="chat-panel-inner">
      <div className="messages-container" ref={containerRef}>
        {messages.length > 0 && (
          <div className="chat-toolbar">
            <span>{messages.length} 轮对话</span>
            <button className="btn-clear" onClick={() => { if (confirm("清空对话？")) setMessages([]); }}>
              清空
            </button>
          </div>
        )}
        {messages.length === 0 && !loading && (
          <div className="chat-empty">
            <p className="chat-empty-icon">📚</p>
            <p>{hasDocuments ? "基于你的知识库，开始提问吧" : "先上传文档到左侧知识库"}</p>
          </div>
        )}
        {messages.map((msg, i) => (<MessageBubble key={i} message={msg} />))}

        {loading && (streamText ? (
          <div className="message ai-message">
            <div className="message-bubble ai-bubble streaming-bubble" style={{ minWidth: 280 }}>
              <p className="streaming-text">{streamText}<span className="streaming-caret">▋</span></p>
            </div>
          </div>
        ) : progress && (
          <div className="message ai-message">
            <div className="message-bubble ai-bubble" style={{ minWidth: 280 }}>
              <div className="progress-bar-container">
                <div className="progress-steps">
                  {STEPS.map((step) => {
                    const idx = STEPS.indexOf(step);
                    const curIdx = STEPS.indexOf(progress.step);
                    let cls = "progress-step";
                    if (idx < curIdx) cls += " done";
                    else if (idx === curIdx) cls += " active";
                    return (
                      <div key={step} className={cls}>
                        <div className="progress-dot" />
                      </div>
                    );
                  })}
                </div>
                <div className="progress-labels">
                  {STEPS.map(step => {
                    const curIdx = STEPS.indexOf(progress.step);
                    const idx = STEPS.indexOf(step);
                    let labelCls = "progress-label";
                    if (idx <= curIdx) labelCls += " active";
                    return <span key={step} className={labelCls}>{STEP_LABELS[step]}</span>;
                  })}
                </div>
                <p className="progress-msg">{progress.message}</p>
              </div>
            </div>
          </div>
        ))}
        {error && <p className="upload-error" style={{ margin: "0 24px" }}>{error}</p>}
      </div>

      <form className="chat-input-area" onSubmit={handleSend}>
        <input type="text" className="chat-input"
          placeholder={hasDocuments ? "输入你的问题…" : "请先上传文档"}
          value={input} onChange={e => setInput(e.target.value)} disabled={loading} />
        <button type="submit" className="btn-send" disabled={!input.trim() || loading}>
          {loading ? "思考中" : "发送"}
        </button>
      </form>
    </div>
  );
}
