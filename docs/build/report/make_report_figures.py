# -*- coding: utf-8 -*-
"""生成《人工智能应用开发实训》课程设计报告所需的设计图。

输出目录：docs/build/report/figures/
  fig_2_1_modules.png   图2-1  系统功能模块图
  fig_3_1_ingest.png    图3-1  文档解析入库流程图
  fig_3_2_retrieval.png 图3-2  多路召回与 RRF 融合流程图
  fig_3_3_generate.png  图3-3  问答生成流程图
  fig_4_1_calls.png     图4-1  函数调用关系图
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "SimSun"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)

# 低饱和蓝灰配色，印刷友好（与实训调查报告保持一致）
C_MAIN = "#2F5D8C"
C_ACC = "#C97B4A"
C_GREY = "#8C9BA8"
C_BG = "#EDF1F5"
C_GREEN = "#3F7D63"
C_RED = "#B4553F"


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", path)


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fc=C_BG, ec=C_MAIN, fs=8, bold=False, tc="#1A1A1A"):
    """以左下角 (x, y) 为基准画圆角矩形。"""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.5,rounding_size=1.6",
        linewidth=1.0, edgecolor=ec, facecolor=fc, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, linespacing=1.55, zorder=3,
            fontweight="bold" if bold else "normal")


def diamond(ax, cx, cy, w, h, text, fc="#FBF0E6", ec=C_ACC, fs=7.4):
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=fc, edgecolor=ec,
                         linewidth=1.0, zorder=2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            color="#1A1A1A", linespacing=1.4, zorder=3)


def arrow(ax, p1, p2, color=C_MAIN, lw=1.15, style="-|>", ls="-", rad=0.0):
    ax.add_patch(FancyArrowPatch(
        p1, p2, arrowstyle=style, mutation_scale=11, linewidth=lw,
        color=color, linestyle=ls, shrinkA=0, shrinkB=0, zorder=1,
        connectionstyle=f"arc3,rad={rad}"))


def elbow(ax, p1, p2, color=C_MAIN, lw=1.15, ls="-"):
    """直角折线箭头：先垂直后水平（用于旁支）。"""
    (x1, y1), (x2, y2) = p1, p2
    ax.plot([x1, x1], [y1, y2], color=color, linewidth=lw, linestyle=ls, zorder=1)
    arrow(ax, (x1, y2), (x2, y2), color=color, lw=lw, ls=ls)


def label(ax, x, y, text, fs=7, color="#555555", ha="left", va="center"):
    ax.text(x, y, text, fontsize=fs, color=color, ha=ha, va=va, linespacing=1.5)


# ============================================================
# 图 2-1  系统功能模块图
# ============================================================
def fig_2_1():
    fig, ax = canvas(9.4, 5.2)

    box(ax, 30, 88, 40, 9, "StudyRAG 知识库问答系统", fc=C_MAIN, ec=C_MAIN,
        fs=10.5, bold=True, tc="white")

    groups = [
        (1.5, "用户认证模块", ["用户注册", "用户登录", "JWT 令牌校验", "bcrypt 口令散列"]),
        (26.0, "资料管理模块", ["六格式文件上传", "分块策略与参数", "文档列表查询", "文档删除与隔离"]),
        (50.5, "检索问答模块", ["查询类型路由", "查询改写与 HyDE", "稠密/稀疏混合召回",
                             "RRF 融合与精排", "流式生成与引用"]),
        (75.0, "系统支撑模块", ["健康检查接口", "RAGAS 效果评测", "内存结果缓存",
                             "Docker 编排部署"]),
    ]
    GW, GH = 23.0, 42.0
    GY = 40.0

    for gx, gname, items in groups:
        # 分组容器
        ax.add_patch(FancyBboxPatch(
            (gx, GY), GW, GH, boxstyle="round,pad=0.5,rounding_size=1.6",
            linewidth=1.0, edgecolor=C_GREY, facecolor="#F7F9FB", zorder=1))
        # 分组标题
        box(ax, gx + 1.5, GY + GH - 7.5, GW - 3.0, 6.4, gname,
            fc=C_ACC, ec=C_ACC, fs=8.4, bold=True, tc="white")
        arrow(ax, (gx + GW / 2, GY + GH), (gx + GW / 2, 88), color=C_GREY)
        # 功能项
        iy = GY + GH - 12.5
        for it in items:
            box(ax, gx + 1.5, iy - 5.4, GW - 3.0, 5.4, it, fs=7.2)
            iy -= 7.2

    save(fig, "fig_2_1_modules.png")


# ============================================================
# 图 3-1  文档解析入库流程图
# ============================================================
def fig_3_1():
    fig, ax = canvas(8.4, 11.8)

    # 12 行主干：行心自上而下等距分布，判定菱形独占整行，避免任何重叠
    CX, BW, BH = 27.0, 40.0, 5.6
    left = CX - BW / 2
    tops = [96.0 - i * 8.4 for i in range(12)]   # 每行中心 y
    DIAM_W, DIAM_H = 32.0, 8.4

    def proc(row, text, fs=7.4):
        box(ax, left, tops[row] - BH / 2, BW, BH, text, fc="#E4EDF5",
            ec=C_MAIN, fs=fs)

    def term(row, text):
        box(ax, left, tops[row] - BH / 2, BW, BH, text, fc="#DCE9E1",
            ec=C_GREEN, fs=7.8)

    def down(a, b):
        """row a 底部 -> row b 顶部"""
        arrow(ax, (CX, tops[a] - BH / 2), (CX, tops[b] + BH / 2))

    term(0, "开始")
    proc(1, "用户上传文件\n（PDF / MD / TXT / DOCX / PPTX / XLSX）")
    proc(2, "格式与大小校验\nvalidate_file() / ALLOWED_EXTS")
    diamond(ax, CX, tops[3], DIAM_W, DIAM_H, "格式合法？")
    proc(4, "保存至 data/uploads/\nuuid4().hex + 原扩展名")
    diamond(ax, CX, tops[5], DIAM_W, DIAM_H, "内容已存在？")
    proc(6, "按扩展名分派解析器\nload_document()")
    proc(7, "文本分块（三策略可选）\nrecursive / token / character")
    proc(8, "向量化并写入 Chroma\nadd_documents(owner)")
    proc(9, "重建 BM25 倒排索引\nbm25.add_chunks()")
    proc(10, "登记元数据与哈希\nadd_record() / mark_indexed()")
    term(11, "结束（201 Created）")

    # ---- 主干箭头 ----
    for a, b in [(0, 1), (1, 2)]:
        down(a, b)
    arrow(ax, (CX, tops[2] - BH / 2), (CX, tops[3] + DIAM_H / 2))
    arrow(ax, (CX, tops[3] - DIAM_H / 2), (CX, tops[4] + BH / 2))
    down(4, 5)
    arrow(ax, (CX, tops[5] - DIAM_H / 2), (CX, tops[6] + BH / 2))
    for a, b in [(6, 7), (7, 8), (8, 9), (9, 10), (10, 11)]:
        down(a, b)

    # ---- 异常出口统一走右侧，避免与主干重叠 ----
    RX, RW = 56.0, 43.0
    arrow(ax, (CX + DIAM_W / 2, tops[3]), (RX, tops[3]), color=C_RED)
    box(ax, RX, tops[3] - 4.2, RW, 8.4,
        "返回 400 不支持的文件类型\n（ValueError → HTTPException）",
        fc="#FBECE8", ec=C_RED, fs=7.2)
    label(ax, (CX + DIAM_W / 2 + RX) / 2, tops[3] + 2.2, "否", fs=7.6,
          color=C_RED, ha="center")

    arrow(ax, (CX + DIAM_W / 2, tops[5]), (RX, tops[5]), color=C_RED)
    box(ax, RX, tops[5] - 4.2, RW, 8.4,
        "返回 409 该文件已上传过\n（sha256 : owner 命中）",
        fc="#FBECE8", ec=C_RED, fs=7.2)
    label(ax, (CX + DIAM_W / 2 + RX) / 2, tops[5] + 2.2, "是", fs=7.6,
          color=C_RED, ha="center")

    # ---- 解析阶段的条件兜底说明（虚线关联，非流程节点） ----
    ax.plot([CX + BW / 2, RX], [32.0, 32.0], color=C_ACC,
            linewidth=0.9, linestyle=(0, (4, 3)), zorder=1)
    box(ax, RX, 20.0, RW, 24.0,
        "PDF 解析的条件兜底\n"
        "────────────────\n"
        "① 页面文本不足 50 字符：\n"
        "   以 300 DPI 渲染并 OCR\n"
        "   （Tesseract，chi_sim+eng）\n\n"
        "② 页面含插图：调用视觉大模型\n"
        "   生成描述并追加为\n"
        "   「[图片i描述] …」",
        fc="#FBF0E6", ec=C_ACC, fs=6.9)

    save(fig, "fig_3_1_ingest.png")


# ============================================================
# 图 3-2  多路召回与 RRF 融合流程图
# ============================================================
def fig_3_2():
    fig, ax = canvas(9.6, 6.6)

    box(ax, 33, 92, 34, 7, "用户提问 Question", fc=C_MAIN, ec=C_MAIN,
        fs=9, bold=True, tc="white")

    # 并行分支
    ax.plot([18, 82], [82.5, 82.5], color=C_GREY, linewidth=1.0, zorder=1)
    arrow(ax, (50, 92), (50, 86.5))
    arrow(ax, (18, 82.5), (18, 78.5))
    arrow(ax, (82, 82.5), (82, 78.5))

    box(ax, 4, 71.5, 28, 7, "查询类型路由 QueryRouter\nfact / concept / compare / summary",
        fc="#E4EDF5", fs=7.0)
    box(ax, 68, 71.5, 28, 7, "查询改写 QueryRewriter\n同义改写 + HyDE 假设答案",
        fc="#E4EDF5", fs=7.0)
    arrow(ax, (18, 78.5), (18, 78.5))

    box(ax, 26, 61.5, 48, 7,
        "RouteConfig → top_k / enable_sparse / enable_rerank\n"
        "查询集合 ≤ 3 条（原问题 + 改写 + HyDE），recall_k = top_k × 3",
        fc="#F2F4F7", ec=C_GREY, fs=7.0)
    arrow(ax, (18, 71.5), (30, 68.5), color=C_GREY)
    arrow(ax, (82, 71.5), (70, 68.5), color=C_GREY)

    # 双路召回
    box(ax, 6, 46, 38, 9,
        "稠密召回 DenseRetriever\nChroma cosine 相似度\n相似度 = 1 - 距离，带 owner 过滤",
        fc="#E4EDF5", fs=7.2)
    box(ax, 56, 46, 38, 9,
        "稀疏召回 BM25Retriever\njieba 分词 + BM25Okapi\nmin-max 归一化到 [0,1]",
        fc="#E4EDF5", fs=7.2)
    arrow(ax, (36, 61.5), (25, 55), color=C_MAIN)
    arrow(ax, (64, 61.5), (75, 55), color=C_ACC)

    # RRF
    box(ax, 22, 33.5, 56, 8,
        "RRF 融合  reciprocal_rank_fusion\n"
        "score(d) = Σ 1 / (k + rank_i(d))，k = 60；去重键 content[:80] + filename",
        fc="#FBF0E6", ec=C_ACC, fs=7.2, bold=False)
    arrow(ax, (25, 46), (40, 41.5), color=C_MAIN)
    arrow(ax, (75, 46), (60, 41.5), color=C_ACC)

    box(ax, 22, 21.5, 56, 8,
        "Cross-Encoder 精排 bge-reranker-v2-m3\n取融合前 6 条候选送入精排模型 → 输出 Top-K",
        fc="#FBF0E6", ec=C_ACC, fs=7.2)
    arrow(ax, (50, 33.5), (50, 29.5), color=C_ACC)

    box(ax, 28, 10, 44, 7,
        "检索结果集 List[SearchResult]\n含 content / filename / page / chapter / score",
        fc="#DCE9E1", ec=C_GREEN, fs=7.4)
    arrow(ax, (50, 21.5), (50, 17), color=C_GREEN)

    label(ax, 1.0, 88.0, "并行执行：\nThreadPoolExecutor\n(max_workers = 4)", fs=6.8)
    save(fig, "fig_3_2_retrieval.png")


# ============================================================
# 图 3-3  问答生成流程图
# ============================================================
def fig_3_3():
    fig, ax = canvas(9.0, 4.4)

    xs = [1.0, 20.5, 40.0, 59.5, 79.0]
    W, H, Y = 18.5, 12.0, 46.0
    titles = [
        "检索结果集\nList[SearchResult]",
        "上下文构建\nformat_context()\n编号 [1][2] + 来源标注",
        "提示词组装\nSYSTEM_TEMPLATE\n+ HUMAN_TEMPLATE",
        "大模型生成\nChatOpenAI\n temperature = 0.1",
        "答案与引用\nanswer + sources[]\n（文件 / 页码 / 章节 / 片段）",
    ]
    colors = ["#DCE9E1", "#E4EDF5", "#E4EDF5", "#FBF0E6", "#DCE9E1"]
    edges = [C_GREEN, C_MAIN, C_MAIN, C_ACC, C_GREEN]
    for x, t, fc, ec in zip(xs, titles, colors, edges):
        box(ax, x, Y, W, H, t, fc=fc, ec=ec, fs=7.2)
    for i in range(len(xs) - 1):
        arrow(ax, (xs[i] + W, Y + H / 2), (xs[i + 1], Y + H / 2))

    box(ax, 8.0, 20.0, 84.0, 13.0,
        "约束规则（SYSTEM_TEMPLATE）\n"
        "① 只能依据参考资料作答，不得使用资料以外的知识；② 引用处标注编号 [1][2]；\n"
        "③ 资料不足时回答「资料中未找到足够依据来回答这个问题。」；④ 统一使用简体中文输出。",
        fc="#F2F4F7", ec=C_GREY, fs=7.0)
    save(fig, "fig_3_3_generate.png")


# ============================================================
# 图 4-1  函数调用关系图
# ============================================================
def fig_4_1():
    fig, ax = canvas(9.6, 8.2)

    # 层 1：路由层
    box(ax, 2, 88, 29, 7.5, "routers/documents.py\nupload_document()", fc=C_MAIN,
        ec=C_MAIN, fs=7.2, bold=False, tc="white")
    box(ax, 35, 88, 30, 7.5, "routers/chat.py\nask_question() / ask_stream()",
        fc=C_MAIN, ec=C_MAIN, fs=7.2, tc="white")
    box(ax, 69, 88, 29, 7.5, "routers/auth.py\nget_current_user()", fc=C_MAIN,
        ec=C_MAIN, fs=7.2, tc="white")

    # 层 2：服务编排层
    box(ax, 2, 74, 29, 8.5, "loader.load_document()\nsplitter.split_documents()",
        fc="#E4EDF5", fs=7.0)
    box(ax, 35, 74, 30, 8.5, "chain.ask()\nchain._full_search_sync()", fc="#E4EDF5", fs=7.0)
    box(ax, 69, 74, 29, 8.5, "utils/auth.py\nverify_password()\ncreate_access_token()",
        fc="#E4EDF5", fs=7.0)

    arrow(ax, (16.5, 88), (16.5, 82.5))
    arrow(ax, (50, 88), (50, 82.5))
    arrow(ax, (83.5, 88), (83.5, 82.5))

    # 层 3：检索与索引层
    box(ax, 1.5, 58, 22.5, 9.5, "vectorstore\nadd_documents()\nsimilarity_search()",
        fc="#FBF0E6", ec=C_ACC, fs=7.0)
    box(ax, 26.5, 58, 22.0, 9.5, "retrievers/\ndense_retriever\ndense_retriever.retrieve()",
        fc="#FBF0E6", ec=C_ACC, fs=7.0)
    box(ax, 51.0, 58, 22.0, 9.5, "retrievers/\nbm25_retriever\nBM25Retriever.retrieve()",
        fc="#FBF0E6", ec=C_ACC, fs=7.0)
    box(ax, 75.5, 58, 23.0, 9.5, "query_rewriter / router\nrewrite() / get_config()",
        fc="#FBF0E6", ec=C_ACC, fs=7.0)

    arrow(ax, (12, 74), (12, 67.5))
    arrow(ax, (45, 74), (37, 67.5))
    arrow(ax, (55, 74), (62, 67.5))
    arrow(ax, (52, 74), (86, 67.5), rad=-0.15)

    # 层 4：融合与生成
    box(ax, 12, 43, 30, 8.0, "fusion.reciprocal_rank_fusion()\nRRF，k = 60", fc="#F3E7F0",
        ec="#8A5B8C", fs=7.2)
    box(ax, 46, 43, 26, 8.0, "reranker.CrossEncoderReranker\n.rerank()", fc="#F3E7F0",
        ec="#8A5B8C", fs=7.2)
    box(ax, 76, 43, 22, 8.0, "prompt.format_context()\nbuild_prompt_messages()",
        fc="#F3E7F0", ec="#8A5B8C", fs=7.2)

    arrow(ax, (23, 58), (23, 51))
    arrow(ax, (37, 58), (50, 51))
    arrow(ax, (85, 58), (88, 51))

    # 层 5：外部依赖
    box(ax, 2, 24, 30, 10.0,
        "Chroma 向量库\ncollection = studyarag_docs\nhnsw:space = cosine",
        fc="#E8EAEE", ec=C_GREY, fs=7.0)
    box(ax, 36, 24, 28, 10.0,
        "sentence-transformers\nCrossEncoder\nbge-reranker-v2-m3",
        fc="#E8EAEE", ec=C_GREY, fs=7.0)
    box(ax, 68, 24, 30, 10.0,
        "ChatOpenAI\nLLM 生成 / VLM 图注\nEmbeddings 向量化",
        fc="#E8EAEE", ec=C_GREY, fs=7.0)

    arrow(ax, (17, 43), (17, 34))
    arrow(ax, (59, 43), (50, 34))
    arrow(ax, (87, 43), (83, 34))

    label(ax, 50, 17.5, "箭头 A → B 表示 A 直接调用 B", fs=7.2, color="#777777", ha="center")
    save(fig, "fig_4_1_calls.png")


if __name__ == "__main__":
    fig_2_1()
    fig_3_1()
    fig_3_2()
    fig_3_3()
    fig_4_1()
    print("all report figures done")
