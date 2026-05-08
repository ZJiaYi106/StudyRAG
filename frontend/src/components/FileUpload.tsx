/**
 * 文件上传组件
 * 支持点击选择文件和拖拽上传
 */

import { useRef, useState, type DragEvent, type ChangeEvent } from "react";
import { uploadDocument } from "../api/client";

interface Props {
  onUploaded: () => void; // 上传成功后通知父组件刷新列表
}

export default function FileUpload({ onUploaded }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const allowedExts = [".pdf", ".md", ".markdown"];

  const handleFile = async (file: File) => {
    // 前端预校验
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!allowedExts.includes(ext)) {
      setError(`不支持的文件类型「${ext}」。请上传 PDF 或 Markdown 文件。`);
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setError("文件大小不能超过 50MB。");
      return;
    }

    setError(null);
    setUploading(true);
    try {
      await uploadDocument(file);
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
            <p className="drop-hint">支持 PDF、Markdown（最大 50MB）</p>
          </>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.md,.markdown"
          onChange={onChange}
          style={{ display: "none" }}
        />
      </div>
      {error && <p className="upload-error">{error}</p>}
    </div>
  );
}
