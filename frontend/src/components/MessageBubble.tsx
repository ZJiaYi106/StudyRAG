import type { ChatResponse } from "../types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import SourceCard from "./SourceCard";

interface Props { message: ChatResponse; }

export default function MessageBubble({ message }: Props) {
  return (
    <div className="message-pair">
      <div className="message user-message">
        <div className="message-bubble user-bubble">{message.question}</div>
      </div>
      <div className="message ai-message">
        <div>
          <div className="message-bubble ai-bubble markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.answer}
            </ReactMarkdown>
          </div>
          {message.sources.length > 0 && (
            <div className="sources-section">
              <h4>引用来源 · {message.sources.length} 条</h4>
              {message.sources.map((s, i) => (
                <SourceCard key={i} source={s} index={i + 1} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
