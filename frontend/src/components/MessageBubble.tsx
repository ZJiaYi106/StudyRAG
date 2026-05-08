/**
 * 消息气泡组件
 * 用户问题靠右（蓝色），AI 回答靠左（灰色），含引用来源卡片
 */

import type { ChatResponse } from "../types";
import SourceCard from "./SourceCard";

interface Props {
  message: ChatResponse;
}

export default function MessageBubble({ message }: Props) {
  return (
    <div className="message-pair">
      {/* 用户问题 */}
      <div className="message user-message">
        <div className="message-bubble user-bubble">
          {message.question}
        </div>
      </div>

      {/* AI 回答 */}
      <div className="message ai-message">
        <div className="message-bubble ai-bubble">
          <div className="answer-text">
            {message.answer.split("\n").map((line, i) => (
              <p key={i}>{line || " "}</p>
            ))}
          </div>
        </div>

        {/* 引用来源 */}
        {message.sources.length > 0 && (
          <div className="sources-section">
            <h4>📎 参考来源（{message.sources.length} 条）</h4>
            {message.sources.map((s, i) => (
              <SourceCard key={i} source={s} index={i + 1} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
