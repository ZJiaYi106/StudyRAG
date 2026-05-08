/**
 * 引用来源卡片组件
 * 展示单个参考来源的详细信息：文件名、页码、章节、原文片段、相似度
 */

import { useState } from "react";
import type { SourceInfo } from "../types";

interface Props {
  source: SourceInfo;
  index: number;
}

export default function SourceCard({ source, index }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="source-card">
      <div className="source-header" onClick={() => setExpanded(!expanded)}>
        <span className="source-index">[{index}]</span>
        <span className="source-file">{source.filename}</span>
        {source.page && <span className="source-page">第 {source.page} 页</span>}
        {source.chapter && <span className="source-chapter">{source.chapter}</span>}
        <span className="source-toggle">{expanded ? "▲" : "▼"}</span>
      </div>
      {expanded && (
        <div className="source-body">
          <p className="source-excerpt">{source.excerpt}</p>
        </div>
      )}
    </div>
  );
}
