/**
 * 文档列表组件
 * 展示已上传文档，支持删除
 */

import { useEffect, useState } from "react";
import { listDocuments, deleteDocument } from "../api/client";
import type { DocumentListItem } from "../types";

interface Props {
  refreshKey: number; // 外部变化时重新加载列表
}

export default function DocList({ refreshKey }: Props) {
  const [docs, setDocs] = useState<DocumentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listDocuments()
      .then(setDocs)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  const handleDelete = async (id: string, filename: string) => {
    if (!confirm(`确定要删除「${filename}」吗？\n删除后将无法恢复。`)) return;
    try {
      await deleteDocument(id);
      setDocs((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : "删除失败");
    }
  };

  if (loading) return <p className="muted">加载中...</p>;
  if (error) return <p className="upload-error">{error}</p>;

  return (
    <div className="doc-list">
      {docs.length === 0 ? (
        <p className="muted">暂无文档，请上传 PDF 或 Markdown 文件。</p>
      ) : (
        <ul>
          {docs.map((doc) => (
            <li key={doc.id} className="doc-item">
              <div className="doc-info">
                <span className="doc-icon">{doc.file_type === "pdf" ? "📄" : "📝"}</span>
                <div className="doc-meta">
                  <span className="doc-name" title={doc.filename}>{doc.filename}</span>
                  <span className="doc-detail">
                    {doc.chunk_count} 个片段 · {new Date(doc.created_at).toLocaleDateString("zh-CN")}
                  </span>
                </div>
              </div>
              <button
                className="btn-delete"
                onClick={() => handleDelete(doc.id, doc.filename)}
                title="删除文档"
              >
                🗑️
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
