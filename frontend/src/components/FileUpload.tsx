/**
 * 文件上传组件
 * 支持点击选择文件和拖拽上传，可配置分块策略
 */

import { useRef, useState, type DragEvent, type ChangeEvent } from "react";
import { uploadDocument } from "../api/client";
import type { ChunkStrategy, ChunkStrategyOption } from "../types";

interface Props {
  onUploaded: () => void; // 上传成功后通知父组件刷新列表
}

/** 分块策略选项定义 */
const STRATEGY_OPTIONS: ChunkStrategyOption[] = [
  {
    value: "recursive",
    label: "递归分割",
    desc: "按段落、句号等语义边界递归切分，兼顾语义和效率",
  },
  {
    value: "token",
    label: "Token 分割",
    desc: "按 LLM Token 数切分，精确控制上下文窗口大小",
  },
  {
    value: "character",
    label: "固定字符",
    desc: "按固定字符数切分，不保留语义边界，速度最快",
  },
];

/** 支持的文件格式 */
const ALLOWED_EXTS = [
  ".pdf", ".md", ".markdown",   // 原始格式
  ".txt",                        // 纯文本
  ".docx",                       // Word
  ".pptx",                       // PowerPoint
  ".xlsx", ".xls",              // Excel
];

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

/** 根据扩展名获取文件类型图标 */
function getFileIcon(ext: string): string {
  const iconMap: Record<string, string> = {
    ".pdf": "📄", ".md": "📝", ".markdown": "📝",
    ".txt": "📃", ".docx": "📘", ".pptx": "📊",
    ".xlsx": "📈", ".xls": "📈",
  };
  return iconMap[ext] || "📎";
}

export default function FileUpload({ onUploaded }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [strategy, setStrategy] = useState<ChunkStrategy>("recursive");
  const [chunkSize, setChunkSize] = useState<number | undefined>(undefined);
  const [chunkOverlap, setChunkOverlap] = useState<number | undefined>(undefined);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    // 前端预校验
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      setError(
        `不支持的文件类型「${ext}」。请上传 ${ALLOWED_EXTS.filter(e => e.length <= 5).join("、")} 等格式。`
      );
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError("文件大小不能超过 50MB。");
      return;
    }

    setError(null);
    setUploading(true);
    try {
      await uploadDocument(file, {
        chunkStrategy: strategy,
        chunkSize: chunkSize || undefined,
        chunkOverlap: chunkOverlap || undefined,
      });
      onUploaded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败，请重试。");
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="file-upload">
      {/* 分块策略选择器 */}
      <div className="chunk-options">
        <div className="chunk-option-row">
          <label className="chunk-label">分块策略</label>
          <select
            className="chunk-select"
            value={strategy}
            onChange={(e) => setStrategy(e.target.value as ChunkStrategy)}
            disabled={uploading}
          >
            {STRATEGY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <button
            className="btn-advanced-toggle"
            onClick={() => setShowAdvanced(!showAdvanced)}
            type="button"
          >
            {showAdvanced ? "收起 ▲" : "高级 ▼"}
          </button>
        </div>
        {/* 策略描述 */}
        <p className="strategy-desc">
          {STRATEGY_OPTIONS.find((o) => o.value === strategy)?.desc}
        </p>
        {/* 高级选项（可折叠） */}
        {showAdvanced && (
          <div className="advanced-options">
            <div className="advanced-row">
              <label>Chunk 大小</label>
              <input
                type="number"
                className="chunk-number"
                placeholder="默认 1000"
                min={50}
                max={8000}
                value={chunkSize ?? ""}
                onChange={(e) =>
                  setChunkSize(e.target.value ? Number(e.target.value) : undefined)
                }
                disabled={uploading}
              />
              <span className="advanced-unit">
                {strategy === "token" ? "tokens" : "字符"}
              </span>
            </div>
            <div className="advanced-row">
              <label>重叠大小</label>
              <input
                type="number"
                className="chunk-number"
                placeholder="默认 200"
                min={0}
                max={2000}
                value={chunkOverlap ?? ""}
                onChange={(e) =>
                  setChunkOverlap(e.target.value ? Number(e.target.value) : undefined)
                }
                disabled={uploading}
              />
              <span className="advanced-unit">
                {strategy === "token" ? "tokens" : "字符"}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 拖拽上传区域 */}
      <div
        className={`drop-zone ${dragOver ? "drag-over" : ""} ${uploading ? "uploading" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        {uploading ? (
          <p>⏳ 正在上传并处理文档...</p>
        ) : (
          <>
            <p className="drop-icon">📤</p>
            <p>拖拽文件到此处，或<span className="link">点击选择文件</span></p>
            <p className="drop-hint">
              支持 PDF、Markdown、TXT、Word、PPT、Excel（最大 50MB）
            </p>
          </>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.md,.markdown,.txt,.docx,.pptx,.xlsx,.xls"
          onChange={onChange}
          style={{ display: "none" }}
        />
      </div>
      {error && <p className="upload-error">{error}</p>}
    </div>
  );
}
