import { useRef, useState, type DragEvent } from "react";
import { uploadDocument } from "../api/client";
import type { ChunkStrategy, ChunkStrategyOption } from "../types";

interface Props { onUploaded: () => void; }

const STRATEGY_OPTIONS: ChunkStrategyOption[] = [
  { value: "recursive", label: "递归分割", desc: "按段落、句号等语义边界切分" },
  { value: "token", label: "Token 分割", desc: "按 LLM Token 数精确控制上下文" },
  { value: "character", label: "固定字符", desc: "按固定字符数切分，速度最快" },
];

const ALLOWED_EXTS = [".pdf",".md",".markdown",".txt",".docx",".pptx",".xlsx",".xls"];
const ACCEPT = ".pdf,.md,.markdown,.txt,.docx,.pptx,.xlsx,.xls";

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
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      setError(`不支持「${ext}」，请上传 PDF、Markdown、Word、PPT、Excel、TXT`); return;
    }
    if (file.size > 50 * 1024 * 1024) { setError("文件不能超过 50MB"); return; }
    setError(null); setUploading(true);
    try {
      await uploadDocument(file, {
        chunkStrategy: strategy,
        chunkSize: chunkSize || undefined,
        chunkOverlap: chunkOverlap || undefined,
      });
      onUploaded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally { setUploading(false); }
  };

  const onDrop = (e: DragEvent) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f); };

  return (
    <div className="file-upload">
      <div className="chunk-options">
        <div className="chunk-option-row">
          <span className="chunk-label">分块策略</span>
          <select className="chunk-select" value={strategy}
            onChange={e => setStrategy(e.target.value as ChunkStrategy)} disabled={uploading}>
            {STRATEGY_OPTIONS.map(o => (<option key={o.value} value={o.value}>{o.label}</option>))}
          </select>
          <button className="btn-advanced-toggle" onClick={() => setShowAdvanced(!showAdvanced)} type="button">
            {showAdvanced ? "收起" : "高级"}
          </button>
        </div>
        <p className="strategy-desc">{STRATEGY_OPTIONS.find(o => o.value === strategy)?.desc}</p>
        {showAdvanced && (
          <div className="advanced-options">
            <div className="advanced-row">
              <label>大小</label>
              <input type="number" className="chunk-number" placeholder="1000" min={50} max={8000}
                value={chunkSize ?? ""} onChange={e => setChunkSize(e.target.value ? Number(e.target.value) : undefined)} disabled={uploading} />
              <span className="advanced-unit">{strategy === "token" ? "tokens" : "字符"}</span>
            </div>
            <div className="advanced-row">
              <label>重叠</label>
              <input type="number" className="chunk-number" placeholder="200" min={0} max={2000}
                value={chunkOverlap ?? ""} onChange={e => setChunkOverlap(e.target.value ? Number(e.target.value) : undefined)} disabled={uploading} />
              <span className="advanced-unit">{strategy === "token" ? "tokens" : "字符"}</span>
            </div>
          </div>
        )}
      </div>

      <div
        className={`drop-zone ${dragOver ? "drag-over" : ""} ${uploading ? "uploading" : ""}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        {uploading ? (
          <p>⏳ 正在处理文档…</p>
        ) : (
          <>
            <p className="drop-icon">📤</p>
            <p>拖拽文件上传，或<span className="link">点击选择</span></p>
            <p className="drop-hint">PDF · Markdown · Word · PPT · Excel · TXT</p>
          </>
        )}
        <input ref={fileInputRef} type="file" accept={ACCEPT}
          onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          style={{ display: "none" }} />
      </div>
      {error && <p className="upload-error">{error}</p>}
    </div>
  );
}
