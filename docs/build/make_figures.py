# -*- coding: utf-8 -*-
"""生成实训调查报告所需的 4 张图表"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "SimSun"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)

# 统一的配色：低饱和蓝灰系，印刷友好
C_MAIN = "#2F5D8C"
C_ACC = "#C97B4A"
C_GREY = "#8C9BA8"
C_BG = "#EDF1F5"


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", path)


# ============================================================
# 图 3-1 系统技术路线图
# ============================================================
def fig_31():
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 52)
    ax.axis("off")

    def box(x, y, w, h, text, fc=C_BG, ec=C_MAIN, fs=9):
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.6,rounding_size=2",
            linewidth=1.1, edgecolor=ec, facecolor=fc))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fs, color="#1A1A1A", linespacing=1.5)

    def arrow(x1, y1, x2, y2, style="-|>", color=C_MAIN, lw=1.3, ls="-"):
        ax.add_patch(FancyArrowPatch(
            (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=12,
            linewidth=lw, color=color, linestyle=ls,
            shrinkA=0, shrinkB=0))

    # --- 上半部分：文件上传链路 ---
    ax.text(1, 47.5, "文件入库链路", fontsize=10.5, color=C_MAIN, fontweight="bold")
    y1, h, w = 36, 8, 15
    xs = [2, 21.5, 41, 60.5, 80]
    labels = [
        "文件上传\nPDF/MD/DOCX\nPPTX/XLSX/TXT",
        "Loader\n多格式解析\n+ OCR/VLM 兜底",
        "Splitter\nrecursive/token\n/character",
        "Embeddings\ntext-embedding\n-3-small",
        "Chroma\n向量持久化\n+ owner 隔离",
    ]
    for x, lab in zip(xs, labels):
        box(x, y1, w, h, lab, fs=7.6)
    for i in range(len(xs) - 1):
        arrow(xs[i] + w, y1 + h / 2, xs[i + 1], y1 + h / 2)

    # 分隔线
    ax.plot([1, 99], [30, 30], color=C_GREY, linewidth=0.9, linestyle=(0, (4, 3)))

    # --- 下半部分：问答链路 ---
    ax.text(1, 25.5, "问答检索链路", fontsize=10.5, color=C_ACC, fontweight="bold")
    y2, h2 = 14, 8
    xs2 = [2, 21.5, 41, 60.5, 80]
    labels2 = [
        "用户提问\nQuery",
        "查询改写\nLLM + HyDE\n（线程池并行）",
        "双路召回\nDense + BM25\nrecall_k = 3×k",
        "RRF 融合\nk=60\n去重 + 排序",
        "Cross-Encoder\nbge-reranker\n-v2-m3 精排",
    ]
    for x, lab in zip(xs2, labels2):
        box(x, y2, w, h2, lab, fs=7.6, ec=C_ACC)
    for i in range(len(xs2) - 1):
        arrow(xs2[i] + w, y2 + h2 / 2, xs2[i + 1], y2 + h2 / 2, color=C_ACC)

    # 生成层
    box(60.5, 2.5, 34.5, 8, "Prompt 构建 + LLM 生成\n→ 答案 + 引用来源（文件/页码/片段）",
        fc="#FBF0E6", ec=C_ACC, fs=7.6)
    arrow(80 + w / 2, y2, 80 + w / 2, 10.5, color=C_ACC)

    # VLM 说明
    ax.text(2, 8.0, "说明：上传链路中的 OCR 为条件触发——单页文本不足\n"
                    "50 字符时以 300 DPI 渲染并识别，图表类内容交由 VLM 描述。",
            fontsize=7.2, color="#555555", linespacing=1.6, va="center")

    save(fig, "fig_3_1_arch.png")


# ============================================================
# 图 5-1 岗位需求分布图
# ============================================================
def fig_51():
    jobs = ["算法部署工程师", "AI 产品经理", "测试/数据标注", "数据分析师",
            "AI 应用开发工程师", "算法工程师"]
    vals = [6.0, 12.0, 14.0, 18.0, 22.0, 28.0]
    cnts = [3, 6, 7, 9, 11, 14]

    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    colors = [C_GREY] * 4 + [C_ACC, C_MAIN]
    bars = ax.barh(jobs, vals, color=colors, height=0.62)
    for b, v, c in zip(bars, vals, cnts):
        ax.text(v + 0.6, b.get_y() + b.get_height() / 2,
                f"{v:.1f}%（{c} 条）", va="center", fontsize=8.5, color="#333333")
    ax.set_xlabel("占有效招聘信息的比例（%）", fontsize=9)
    ax.set_xlim(0, 34)
    ax.tick_params(labelsize=9)
    ax.grid(axis="x", linestyle=":", color="#CCCCCC", linewidth=0.7)
    ax.set_axisbelow(True)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#BBBBBB")
    ax.spines["bottom"].set_color("#BBBBBB")
    save(fig, "fig_5_1_jobs.png")


# ============================================================
# 图 5-2 能力短板雷达图
# ============================================================
def fig_52():
    labels = ["编程能力", "工程部署", "机器学习", "数据处理",
              "深度学习", "团队协作", "论文阅读"]
    demand = [4.62, 4.35, 4.28, 4.21, 4.05, 3.98, 3.85]
    self_ = [3.51, 2.86, 3.74, 3.42, 3.28, 3.86, 2.94]

    n = len(labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]
    demand_c = demand + demand[:1]
    self_c = self_ + self_[:1]

    fig, ax = plt.subplots(figsize=(5.8, 5.2), subplot_kw=dict(polar=True))
    ax.plot(angles, demand_c, color=C_MAIN, linewidth=1.9, marker="o",
            markersize=4.5, label="企业需求重要性")
    ax.fill(angles, demand_c, color=C_MAIN, alpha=0.16)
    ax.plot(angles, self_c, color=C_ACC, linewidth=1.9, marker="s",
            markersize=4.5, linestyle="--", label="学生自评水平")
    ax.fill(angles, self_c, color=C_ACC, alpha=0.14)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylim(2.5, 5.0)
    ax.set_yticks([3.0, 3.5, 4.0, 4.5, 5.0])
    ax.set_yticklabels(["3.0", "3.5", "4.0", "4.5", "5.0"], fontsize=7.5, color="#777777")
    ax.tick_params(pad=6)
    ax.grid(color="#CCCCCC", linewidth=0.7)
    ax.spines["polar"].set_color("#CCCCCC")
    ax.legend(loc="upper right", bbox_to_anchor=(1.30, 1.12), fontsize=8.5, frameon=False)
    save(fig, "fig_5_2_radar.png")


# ============================================================
# 图 5-3 实训满意度柱状图
# ============================================================
def fig_53():
    items = ["教师指导", "整体收获", "内容安排", "项目难度", "设备与算力"]
    vals = [4.42, 4.18, 3.96, 3.74, 3.35]

    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    colors = [C_MAIN, C_MAIN, C_MAIN, C_MAIN, C_ACC]
    bars = ax.bar(items, vals, color=colors, width=0.52)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v:.2f}",
                ha="center", fontsize=9.5, color="#333333")
    ax.axhline(y=4.0, color=C_GREY, linewidth=1.0, linestyle="--")
    ax.text(4.45, 4.06, "4.00 参考线", fontsize=7.8, color=C_GREY, ha="right")
    ax.set_ylabel("满意度均值（5 分制）", fontsize=9)
    ax.set_ylim(0, 5.2)
    ax.set_yticks([0, 1, 2, 3, 4, 5])
    ax.tick_params(labelsize=9.5)
    ax.grid(axis="y", linestyle=":", color="#CCCCCC", linewidth=0.7)
    ax.set_axisbelow(True)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#BBBBBB")
    ax.spines["bottom"].set_color("#BBBBBB")
    save(fig, "fig_5_3_satisfaction.png")


if __name__ == "__main__":
    fig_31()
    fig_51()
    fig_52()
    fig_53()
    print("all figures done")
