# StudyRAG 项目长期备忘

## 部署目标
用户计划后续部署到腾讯云轻量应用服务器（Lighthouse），从本地 WebUI 演进到公网。

## 关键约束 / 待办
- **服务器内存门槛**：bge-reranker-v2-m3 约 2.27GB，加载进内存需 ~2.3-3GB RAM。2核2G 的轻量机必 OOM，**至少 4G、建议 8G**。CPU 推理在高并发下是吞吐瓶颈。
- **模型下载**：在服务器上 SSH 跑一次 `huggingface-cli download BAAI/bge-reranker-v2-m3` 预下载到 HF 缓存（`~/.cache/huggingface/hub`），用户侧零下载。
- **启动自动加载（已实现）**：config 加 `rerank_autoload` 开关（默认 false 本地开发）；`main.py` lifespan 里 `rerank_autoload=true` 时调 `get_reranker_service().start_load()`（非阻塞后台线程）。本地 .env 留 false 手动加载，生产 .env 设 true 自动加载。需先预下载模型到 HF 缓存。
- **uvicorn --reload 会杀掉后台下载线程**：预下载或加载期间去掉 --reload。
