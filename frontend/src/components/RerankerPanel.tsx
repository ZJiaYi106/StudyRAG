/**
 * 重排模型管理面板
 * - 查询模型状态（未加载 / 加载中 / 已加载）
 * - 选择重排模型（从后端目录）
 * - 手动触发加载（首次需下载 ~1.2GB），加载中轮询状态
 * - 卸载已加载模型
 * 未加载时问答仍可用，仅跳过精排。
 */

import { useEffect, useState, useCallback } from "react";
import { getRerankerStatus, loadReranker, unloadReranker } from "../api/client";
import type { RerankerStatus } from "../types";

export default function RerankerPanel() {
  const [status, setStatus] = useState<RerankerStatus | null>(null);
  const [selected, setSelected] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const s = await getRerankerStatus();
      setStatus(s);
      setError(s.error ?? null);
      if (!selected && s.available.length > 0) {
        const rec = s.available.find((m) => m.recommended) ?? s.available[0];
        setSelected(rec.path);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "获取状态失败");
    }
  }, [selected]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // 加载中时轮询，直到 loading=false
  useEffect(() => {
    if (!status?.loading) return;
    const id = window.setInterval(async () => {
      try {
        const s = await getRerankerStatus();
        setStatus(s);
        if (!s.loading) window.clearInterval(id);
      } catch {
        /* 忽略轮询中的瞬时错误 */
      }
    }, 1500);
    return () => window.clearInterval(id);
  }, [status?.loading]);

  const handleLoad = async () => {
    setBusy(true);
    setError(null);
    try {
      await loadReranker(selected || undefined);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载请求失败");
    } finally {
      setBusy(false);
    }
  };

  const handleUnload = async () => {
    setBusy(true);
    setError(null);
    try {
      const s = await unloadReranker();
      setStatus(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "卸载失败");
    } finally {
      setBusy(false);
    }
  };

  const loaded = status?.loaded ?? false;
  const loading = status?.loading ?? false;
  const available = status?.available ?? [];
  const badgeClass = loaded ? "ok" : loading ? "busy" : "idle";

  return (
    <div className="reranker-card">
      <div className="section-heading compact-heading">
        <div>
          <span className="eyebrow">RERANK</span>
          <h2>重排模型</h2>
        </div>
        <span className={`rerank-badge ${badgeClass}`}>
          {loaded ? "已加载" : loading ? "加载中" : "未加载"}
        </span>
      </div>

      <p className="section-description">
        精排模型首次需下载约 1.2GB，可手动加载。未加载时问答仍可用，仅跳过精排。
      </p>

      <label className="rerank-field">
        <span className="rerank-field-label">模型</span>
        <select
          className="rerank-select"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          disabled={loaded || loading || busy}
        >
          {available.length === 0 && <option value="">无可用模型</option>}
          {available.map((m) => (
            <option key={m.path} value={m.path}>
              {m.name} · {m.size}{m.recommended ? "（推荐）" : ""}
            </option>
          ))}
        </select>
      </label>

      <div className="rerank-actions">
        {loaded ? (
          <button className="btn-rerank-unload" onClick={handleUnload} disabled={busy}>
            卸载模型
          </button>
        ) : (
          <button
            className="btn-rerank-load"
            onClick={handleLoad}
            disabled={loading || busy}
          >
            {loading || busy ? "加载中…" : "加载模型"}
          </button>
        )}
      </div>

      {loaded && status?.model && (
        <p className="rerank-loaded-name">当前：{status.model}</p>
      )}

      {error && <p className="upload-error rerank-error">{error}</p>}
    </div>
  );
}
