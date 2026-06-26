/**
 * 生成《人工智能专业实训实践与行业人才需求调查报告》Word 文档
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  ImageRun, PageBreak, Footer, PageNumber, LineRuleType,
  TableOfContents, LevelFormat, TabStopType, TabStopPosition,
} = require("docx");

const FIGDIR = path.join(__dirname, "figures");
const OUTDOCX = path.join(__dirname, "..", "实训调查报告.docx");

// ---------- 字体与样式常量 ----------
const SONG = { ascii: "Times New Roman", eastAsia: "宋体", hAnsi: "Times New Roman" };
const HEI = { ascii: "Times New Roman", eastAsia: "黑体", hAnsi: "Times New Roman" };
const KAI = { ascii: "Times New Roman", eastAsia: "楷体", hAnsi: "Times New Roman" };

const SZ_BODY = 24;   // 小四 12pt
const SZ_TBL = 21;    // 五号 10.5pt
const CONTENT_W = 8306; // 正文可用宽度（twips）
const LINE15 = { line: 360, lineRule: LineRuleType.AUTO };
const LINE115 = { line: 280, lineRule: LineRuleType.AUTO };

// ---------- 基础构造函数 ----------
const body = (text, opts = {}) => new Paragraph({
  alignment: opts.align || AlignmentType.JUSTIFIED,
  spacing: { ...LINE15, before: 0, after: 60 },
  indent: opts.noIndent ? undefined : { firstLine: 480 },
  children: [new TextRun({ text, size: SZ_BODY, font: SONG, bold: opts.bold })],
});

const bodyRich = (runs, opts = {}) => new Paragraph({
  alignment: opts.align || AlignmentType.JUSTIFIED,
  spacing: { ...LINE15, before: 0, after: 60 },
  indent: opts.noIndent ? undefined : { firstLine: 480 },
  children: runs.map(([text, o = {}]) => new TextRun({
    text, size: opts.size || SZ_BODY, font: o.font || SONG,
    bold: o.bold, italics: o.italics, underline: o.underline,
  })),
});

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  alignment: AlignmentType.CENTER,
  pageBreakBefore: true,
  spacing: { before: 240, after: 300 },
  children: [new TextRun({ text, size: 32, font: HEI, bold: true })],
});

const h1NoBreak = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  alignment: AlignmentType.CENTER,
  spacing: { before: 240, after: 300 },
  children: [new TextRun({ text, size: 32, font: HEI, bold: true })],
});

const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 240, after: 120 },
  children: [new TextRun({ text, size: 28, font: HEI, bold: true })],
});

const h3 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_3,
  spacing: { before: 180, after: 90 },
  children: [new TextRun({ text, size: SZ_BODY, font: HEI, bold: true })],
});

const bullet = (text) => new Paragraph({
  numbering: { reference: "bullet-list", level: 0 },
  alignment: AlignmentType.JUSTIFIED,
  spacing: { ...LINE15, after: 40 },
  children: [new TextRun({ text, size: SZ_BODY, font: SONG })],
});

const numItem = (text) => new Paragraph({
  numbering: { reference: "num-list", level: 0 },
  alignment: AlignmentType.JUSTIFIED,
  spacing: { ...LINE15, after: 40 },
  children: [new TextRun({ text, size: SZ_BODY, font: SONG })],
});

// 表题（表格上方，居中，五号黑体）
const tblCaption = (text) => new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 200, after: 80 },
  keepNext: true,
  children: [new TextRun({ text, size: SZ_TBL, font: HEI, bold: true })],
});

// 图题（图下方，居中，五号黑体）
const figCaption = (text) => new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 80, after: 200 },
  children: [new TextRun({ text, size: SZ_TBL, font: HEI, bold: true })],
});

const blank = (h = 24) => new Paragraph({ spacing: { after: h }, children: [] });
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

// ---------- 图片 ----------
function pngSize(buf) {
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}
function figure(file, caption, targetW = 400) {
  const buf = fs.readFileSync(path.join(FIGDIR, file));
  const { width, height } = pngSize(buf);
  const w = targetW;
  const h = Math.round(targetW * height / width);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 160, after: 60 },
      keepNext: true,
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: w, height: h } })],
    }),
    figCaption(caption),
  ];
}

// ---------- 表格 ----------
const BD = { style: BorderStyle.SINGLE, size: 4, color: "8A9AA8" };
const BORDERS = {
  top: BD, bottom: BD, left: BD, right: BD,
  insideHorizontal: BD, insideVertical: BD,
};
const NO_BORDERS = {
  top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE },
  left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE },
  insideHorizontal: { style: BorderStyle.NONE }, insideVertical: { style: BorderStyle.NONE },
};

function cell(text, w, { bold = false, align = AlignmentType.CENTER, fill, span } = {}) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    columnSpan: span,
    shading: fill ? { type: ShadingType.CLEAR, color: "auto", fill } : undefined,
    margins: { top: 60, bottom: 60, left: 110, right: 110 },
    verticalAlign: "center",
    children: [new Paragraph({
      alignment: align,
      spacing: LINE115,
      children: [new TextRun({ text: String(text), size: SZ_TBL, font: bold ? HEI : SONG, bold })],
    })],
  });
}

function makeTable(headers, rows, widths, aligns = []) {
  const total = widths.reduce((a, b) => a + b, 0);
  return new Table({
    columnWidths: widths,
    width: { size: total, type: WidthType.DXA },
    alignment: AlignmentType.CENTER,
    borders: BORDERS,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => cell(h, widths[i], { bold: true, fill: "E4EBF2" })),
      }),
      ...rows.map((r) => new TableRow({
        children: r.map((c, i) => cell(c, widths[i], {
          align: aligns[i] || AlignmentType.CENTER,
        })),
      })),
    ],
  });
}

// ============================================================
// 封面
// ============================================================
const coverLine = (label, value, w = [2200, 4400]) => new TableRow({
  children: [
    new TableCell({
      width: { size: w[0], type: WidthType.DXA }, borders: NO_BORDERS,
      margins: { top: 70, bottom: 70, left: 0, right: 60 },
      children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: label, size: 28, font: HEI })],
      })],
    }),
    new TableCell({
      width: { size: w[1], type: WidthType.DXA }, borders: NO_BORDERS,
      margins: { top: 70, bottom: 70, left: 60, right: 0 },
      children: [new Paragraph({
        alignment: AlignmentType.LEFT,
        children: [new TextRun({ text: value, size: 28, font: SONG })],
      })],
    }),
  ],
});

const coverTable = new Table({
  columnWidths: [2200, 4400],
  width: { size: 6600, type: WidthType.DXA },
  alignment: AlignmentType.CENTER,
  borders: NO_BORDERS,
  rows: [
    coverLine("专　　业：", "人工智能"),
    coverLine("班　　级：", "230581"),
    coverLine("姓　　名：", "张佳艺"),
    coverLine("学　　号：", "202300508126"),
    coverLine("指导教师：", "＿＿＿＿＿＿＿＿＿＿"),
    coverLine("实训时间：", "＿＿＿＿＿＿＿＿＿＿"),
    coverLine("实训地点：", "校内人工智能实验室"),
    coverLine("实训单位：", "校内人工智能实验室"),
    coverLine("提交日期：", "2026 年 1 月 9 日"),
  ],
});

const cover = [
  blank(36),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 100 },
    children: [new TextRun({ text: "北华航天工业学院", size: 44, font: HEI, bold: true })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 700 },
    children: [new TextRun({ text: "计算机学院", size: 36, font: HEI, bold: true })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 200 },
    children: [new TextRun({ text: "实 训 调 查 报 告", size: 52, font: HEI, bold: true })],
  }),
  blank(40),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 80 },
    children: [new TextRun({ text: "人工智能专业实训实践与行业人才需求调查报告", size: 30, font: HEI, bold: true })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 700 },
    children: [new TextRun({ text: "——以 StudyRAG 检索增强生成问答系统开发为例", size: 26, font: SONG })],
  }),
  coverTable,
  blank(40),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 500 },
    children: [new TextRun({ text: "2026 年 1 月", size: 28, font: HEI })],
  }),
  pageBreak(),
];

// ============================================================
// 摘要
// ============================================================
const abstract = [
  h1NoBreak("摘　要"),
  body("随着大模型技术的快速迭代，人工智能行业对人才的能力要求正在从“会调包、会跑通”转向“懂原理、能工程化落地”。本次实训以人工智能综合实训为依托，本人独立完成了一套面向课程资料与个人笔记的检索增强生成（Retrieval-Augmented Generation, RAG）问答系统 StudyRAG，并以此为基础开展了人工智能行业人才需求调查。"),
  body("调查综合运用了问卷法、访谈法、文献法与招聘信息分析法：发放学生问卷 110 份，回收有效问卷 100 份；采集并编码企业招聘信息 50 条；访谈实训指导教师、企业工程师与高年级学生共 5 人。调查围绕岗位需求分布、技能重要性、课程与岗位匹配度、实训教学满意度四个维度展开，使用频数分析、均值分析与交叉分析对数据进行处理。"),
  body("主要发现包括：第一，人工智能岗位需求呈“金字塔”结构，算法工程师类岗位数量占比并非最高，而数据分析、算法应用开发、测试与数据标注等“工程落地型”岗位合计占比超过一半，学生对这一结构的认知存在明显偏差；第二，企业对学生编程能力与工程部署能力的要求均值最高，而这恰好是学生自评最薄弱的两项，供需之间存在“能力错配”；第三，校本课程在数学基础与机器学习理论上覆盖较好，而在软件工程、模型部署与大模型应用等环节与企业要求脱节；第四，参加过完整项目实训的学生在岗位认知清晰度上明显高于未参加者。"),
  body("基于上述发现，报告从学生、学校课程、企业协同三个层面提出了可操作的对策建议，并结合本人实训经历总结了专业收获、实践能力提升与职业规划方面的体会。"),
  blank(12),
  new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { ...LINE15, before: 60, after: 60 },
    indent: { firstLine: 480 },
    children: [
      new TextRun({ text: "关键词：", size: SZ_BODY, font: HEI, bold: true }),
      new TextRun({ text: "人工智能；实训调查；人才需求；检索增强生成；工程能力；实践教学", size: SZ_BODY, font: SONG }),
    ],
  }),
  pageBreak(),
];

// ============================================================
// 目录
// ============================================================
const toc = [
  h1NoBreak("目　录"),
  new TableOfContents("目录", { hyperlink: true, headingStyleRange: "1-3" }),
  pageBreak(),
];

// ============================================================
// 第一章
// ============================================================
const ch1 = [
  h1("第一章　绪论"),
  h2("1.1　实训背景"),
  body("近年来，人工智能已从实验室走向产业主战场。国务院《新一代人工智能发展规划》将人工智能确立为国家战略，教育部《高等学校人工智能创新行动计划》明确要求高校深化产教融合、强化学生的工程实践能力。与此同时，大语言模型（Large Language Model, LLM）的普及改变了技术栈的面貌：过去企业招聘更看重“能否手写一个卷积神经网络”，如今则越来越多地要求“能否把模型接入业务系统、能否控制幻觉、能否做检索增强”。"),
  body("这一变化对本科阶段的专业学习提出了新的矛盾：课堂上讲授的数学推导与经典算法仍然是地基，但仅凭课堂实验很难形成工程化能力。正是在这一背景下，学院组织了本次人工智能综合实训，要求学生在真实或准真实的环境中完成一个完整项目，并围绕项目开展行业调研，把“做项目”与“看行业”结合起来。"),

  h2("1.2　实训目的与意义"),
  body("本次实训的目的可以概括为四个层次。"),
  bodyRich([["从专业学习看，", { bold: true }], ["实训要求把分散在各门课程中的知识点串成一条完整链路。以本人完成的 RAG 系统为例，它同时涉及自然语言处理（文本切分、向量化）、数据结构（倒排索引与排序）、Web 开发（REST API）、数据库（向量库的增删改查）和软件工程（模块解耦、单元测试），是典型的交叉型任务。"]]),
  bodyRich([["从实践能力看，", { bold: true }], ["实训强调“可运行、可复现、可维护”，这与课程实验“跑出结果即可”的要求有本质区别。本人需要处理真实 PDF 的解析异常、接口限流、显存不足等课本上不会出现的问题。"]]),
  bodyRich([["从职业规划看，", { bold: true }], ["通过调查行业岗位需求，可以校正自己对就业市场的认知偏差，明确下一阶段的努力方向，避免“闭门造车”式学习。"]]),
  bodyRich([["从课程改革看，", { bold: true }], ["调查结果也可以为学院优化实训内容、调整课程设置提供一份来自学生视角的参考。"]]),

  h2("1.3　调查对象与方法"),
  body("本次调查的对象包括四类：人工智能及相关专业在校学生、企业招聘信息、实训指导教师、企业一线工程师。采用的方法有五种："),
  numItem("问卷调查法——面向学生了解技能掌握情况、实训满意度与职业规划；"),
  numItem("访谈法——面向教师与工程师了解教学期望与用人标准；"),
  numItem("文献调查法——查阅行业白皮书、学术论文与政策文件；"),
  numItem("招聘信息分析法——对招聘平台的岗位描述进行文本编码与频数统计；"),
  numItem("实验观察法——在项目开发过程中记录性能数据与错误案例，形成一手经验材料。"),

  h2("1.4　调查范围与时间"),
  body("调查范围为北华航天工业学院计算机学院人工智能及相关专业在校学生、公开渠道发布的人工智能类岗位招聘信息，以及 5 位受访对象。调查时间为 2025—2026 学年第一学期。访谈对象共 5 人，其中校内指导教师 2 人、企业一线工程师 2 人、已参加工作的往届毕业生 1 人。"),

  h2("1.5　报告结构安排"),
  body("第二章介绍实训单位、岗位任务与开发环境；第三章详细记录实训内容、技术路线与关键实现；第四章说明调查的设计与实施过程；第五章呈现调查结果并进行分析；第六章针对发现的问题提出对策建议；第七章为个人总结与体会；第八章给出结论与展望；文末附参考文献与六个附录。"),
];

// ============================================================
// 第二章
// ============================================================
const envRows = [
  ["操作系统", "Windows 11（开发端）+ Linux 容器（部署端）"],
  ["语言与运行时", "Python 3.11、Node.js、TypeScript"],
  ["后端框架", "FastAPI 0.115.6、Uvicorn 0.34.0"],
  ["大模型框架", "LangChain 0.3.14、langchain-openai 0.2.14"],
  ["向量数据库", "Chroma 0.5.23（支持内嵌与远程两种模式）"],
  ["文档解析", "PyMuPDF 1.25.1、python-docx、python-pptx、openpyxl"],
  ["OCR 识别", "pytesseract 0.3.13 + Tesseract 引擎（chi_sim+eng）"],
  ["检索与重排", "rank_bm25 0.2.2、jieba 0.42.1、sentence-transformers 5.6.1"],
  ["评测框架", "RAGAS 0.4.3"],
  ["认证与安全", "bcrypt 4.2.1、python-jose 3.5.0（JWT）"],
  ["模型服务", "OpenAI API 兼容接口（LLM 与 Embedding 均可经 .env 替换）"],
  ["测试与版本控制", "pytest 8.3.4、Git"],
  ["容器化", "Docker Compose"],
];

const taskRows = [
  ["需求与调研", "明确系统定位，调研 RAG 技术方案", "需求说明、技术选型对比"],
  ["数据与解析", "实现多格式文档加载与 OCR 兜底", "Document Loader、OCR 模块"],
  ["检索层", "实现双路召回、RRF 融合与重排", "HybridSearcher、Fusion、Reranker"],
  ["生成层", "Prompt 模板设计、引用溯源", "PromptTemplate、LCEL Chain"],
  ["工程化", "接口设计、认证、测试、容器化", "12 个 REST 接口、143 个单元测试"],
  ["文档与汇报", "技术文档、阶段汇报、本报告", "README、学习笔记、调查报告"],
];

const ch2 = [
  h1("第二章　实训单位与岗位任务"),
  h2("2.1　实训单位简介"),
  body("本次实训在校内人工智能实验室完成。实验室配有 40 台工作站，提供统一的 Python 开发环境、依赖版本管理与 GPU 计算资源，并为体积较大的预训练模型提供本地缓存节点，以缓解机房网络带宽不足的问题。实验室实行预约制，学生按时间段使用计算资源，实训期间由指导教师负责选题把关、进度检查与阶段答辩。"),
  body("实验室的技术支持条件基本满足本次实训需求，但在集中使用阶段，GPU 资源的排队现象仍较为明显，这一点在第五章的教学满意度调查中也有所反映。"),

  h2("2.2　实训岗位与任务"),
  body("本人在本次实训中承担的是人工智能应用开发岗（RAG 方向）的工作，具体任务如表 2-1 所示。"),
  tblCaption("表 2-1　实训岗位任务分解表"),
  makeTable(["阶段", "任务内容", "产出物"], taskRows, [1400, 3900, 3006]),
  blank(12),

  h2("2.3　软硬件环境"),
  body("本次实训使用的软硬件环境如表 2-2 所示。"),
  tblCaption("表 2-2　实训软硬件环境配置"),
  makeTable(["类别", "具体配置"], envRows, [1800, 6506], [AlignmentType.CENTER, AlignmentType.LEFT]),
  blank(12),
  body("需要说明的是，重排模型 BAAI/bge-reranker-v2-m3 首次运行需从 Hugging Face 下载约 2.27 GB 权重，这在实训环境下是一个实际存在的资源门槛，后文 3.4 节将展开说明。"),

  h2("2.4　实训纪律与安全要求"),
  body("实训期间遵守实验室管理规定，具体包括：按预约时段使用计算资源，不得长时间占用 GPU；API 密钥等敏感配置一律通过环境变量注入，严禁硬编码进代码仓库（项目中使用 pydantic-settings 的 SecretStr 类型封装，确保密钥在日志打印时不泄露）；上传的文档仅用于本人账号下的检索，系统通过 owner 字段做用户级数据隔离；引用他人代码与论文须注明来源，尊重知识产权。"),
];

// ============================================================
// 第三章
// ============================================================
const planRows = [
  ["一", "第 1 周", "选题论证、技术选型、环境搭建", "可运行的 FastAPI 骨架"],
  ["二", "第 2—3 周", "文档加载、切分、向量化、入库", "上传接口打通"],
  ["三", "第 4—5 周", "检索链路、Prompt 设计、问答接口", "端到端问答可用"],
  ["四", "第 6—7 周", "混合检索、重排、查询改写、OCR", "检索质量优化"],
  ["五", "第 8—9 周", "多用户、评测、测试、文档、调研", "143 个测试通过、报告定稿"],
];

const paramRows = [
  ["chunk_size", "50—8000", "1000", "中文讲义段落长度分布"],
  ["chunk_overlap", "0—2000", "200", "过小割裂语义，过大引入冗余"],
  ["top_k", "1—20", "4", "兼顾上下文长度与响应速度"],
  ["RRF 平滑参数 k", "—", "60", "原论文推荐值，未作大幅调整"],
  ["recall_k", "—", "final_k × 3", "保证候选池覆盖度"],
  ["similarity_threshold", "0.0—1.0", "0.5", "过滤低相关片段"],
];

const logRows = [
  ["第 1 周", "选题论证与环境搭建", "完成", "依赖版本冲突 → 固定版本号锁定"],
  ["第 2 周", "文档加载器实现", "完成", "扫描版 PDF 无文本 → 增加 OCR 兜底"],
  ["第 3 周", "切分与向量化", "完成", "中文长句被截断 → 扩充中文分隔符"],
  ["第 4 周", "检索与 Prompt 设计", "完成", "专有名词漏召 → 引入 BM25 稀疏检索"],
  ["第 5 周", "LCEL 链路与问答接口", "完成", "引用来源无法定位 → 补充页码 metadata"],
  ["第 6 周", "RRF 融合与重排", "完成", "重排模型下载慢 → 提前本地化缓存"],
  ["第 7 周", "查询改写与 OCR 扩展", "完成", "响应延迟升高 → 线程池并行 + 条件触发"],
  ["第 8 周", "多用户隔离与评测", "完成", "数据串号 → 全链路增加 owner 过滤"],
  ["第 9 周", "测试、文档与行业调研", "完成", "覆盖率不足 → 补充集成测试"],
];

const ch3 = [
  h1("第三章　实训内容与过程"),
  h2("3.1　实训总体安排"),
  body("实训共分五个阶段推进，每个阶段结束进行一次自检与小结，具体安排如表 3-1 所示。"),
  tblCaption("表 3-1　实训阶段安排表"),
  makeTable(["阶段", "周次", "主要工作", "阶段成果"], planRows, [900, 1400, 3500, 2506]),
  blank(12),

  h2("3.2　技术路线"),
  body("系统由文件入库链路与问答检索链路两条主线构成，整体技术路线如图 3-1 所示。"),
  ...figure("fig_3_1_arch.png", "图 3-1　StudyRAG 系统技术路线图", 410),
  body("从问题定义到部署，整体流程可归纳为：问题定义 → 数据采集 → 数据清洗与解析 → 文本切分 → 向量化与索引 → 多路召回 → 结果融合 → 精排 → Prompt 构建与生成 → 评测 → 优化 → 部署。这一链路与课堂上单独训练的“分类/回归”任务差别很大：传统机器学习任务的评价指标是准确率、F1 值，而 RAG 系统的评价需要同时看检索质量和生成质量，本人在实训后期才逐渐理解这一点。"),

  h2("3.3　具体实训任务"),
  h3("3.3.1　多格式文档加载与解析"),
  body("系统最初只支持 PDF 与 Markdown，实训中期扩展到 TXT、Word、PPT、Excel 共六类格式。由于不同格式的解析库返回结构差异较大，本人在 loader.py 中做了统一封装，把解析结果统一为 LangChain 的 Document 对象，并在 metadata 中保留 filename、page、source 等字段——这些字段是后续“引用来源可追溯”功能的基础。"),
  body("在真实数据上暴露出的问题是：扫描版 PDF 提取出的文本为空。为此增加了 OCR 兜底逻辑——当某一页提取出的字符数少于 pdf_ocr_min_chars（默认 50）时，用 PyMuPDF 以 300 DPI 将该页渲染为图片，再交给 Tesseract（中文简体 + 英文语言包）识别。对于图表类内容，纯 OCR 只能拿到零散的文字标注，因此又补充了 VLM 图像理解模块，把图片转 base64 后交给视觉大模型生成描述文本，再作为 chunk 入库。"),

  h3("3.3.2　文本切分策略的设计与选择"),
  body("切分是 RAG 系统中最容易被忽视、却对效果影响极大的环节。实训中实现了三种策略：recursive（按分隔符优先级递归切分，默认策略）、token（基于 tiktoken 按 token 数切分，用于精确控制 LLM 上下文窗口）、character（按固定字符数切分，速度最快但不保证语义完整）。"),
  body("更关键的是按文件类型配置分隔符优先级。例如 PDF 使用「\\n\\n、\\n、。、. 、；、，、空格」的优先顺序，Markdown 则优先在「\\n## 」「\\n### 」标题和代码块边界处切断，Excel 表格数据以换行符和「 | 」为主。默认参数为 chunk_size=1000、chunk_overlap=200。实验中发现，chunk_overlap 取值过小会导致跨段落的完整表述被割裂，取值过大则会产生大量冗余 chunk、推高检索噪声，200 字符在中文课程讲义上是一个相对均衡的取值。"),

  h3("3.3.3　混合检索与 RRF 融合"),
  body("这是本次实训投入精力最多的部分。单一向量检索的短板在实践中很快暴露：当提问中包含「GB/T 7714」「公式 (3-2)」「ResNet-50」这类专有名词、标准编号、代码标识符时，语义向量往往无法准确匹配，因为这些 token 的语义表征非常接近。因此引入了 BM25 稀疏检索作为补充。"),
  body("BM25 检索器基于 rank_bm25 库，使用 jieba 对中文分词后构建内存索引，并随文档增删自动重建。为了满足多用户场景，检索时按 owner 字段过滤，保证某一用户的提问不会召回其他用户的私有文档。"),
  body("两路召回的结果如何合并是一个真问题。BM25 的分数取值范围与余弦相似度（0—1）不可直接比较，简单加权求和需要反复调参且不稳定。本系统采用 Reciprocal Rank Fusion（RRF）算法，其得分计算方式为：RRF_score(d) = Σ 1 / (k + rank_i(d))，其中 k 取 60。RRF 只依赖排名而不依赖绝对分数，天然规避了量纲不一致的问题。实现上以 content 前 80 字符加 filename 作为去重键，最终取前 max(final_k × 2, 8) 条进入精排；召回阶段则扩大候选池，取 recall_k = final_k × 3。"),

  h3("3.3.4　Cross-Encoder 重排与查询改写"),
  body("经过 RRF 融合后的候选仍然只是“粗排”结果。系统进一步使用 BAAI/bge-reranker-v2-m3 交叉编码器做精排：把 query 与每条候选拼接后送入模型打分，直接判断“这段内容能否回答这个问题”。交叉编码器的精度显著高于双塔向量检索，代价是推理速度慢，因此只对融合后的少量候选执行，形成“粗排召回 → 精排排序”的两级结构。"),
  body("查询改写模块则从另一个方向提升召回率：一是用 LLM 把口语化提问改写为更规范的检索式，二是实现 HyDE（Hypothetical Document Embeddings）策略——让模型先“编造”一段假设性回答，再用这段回答去检索。其原理是：回答文本与文档正文的语义分布更接近，比疑问句更容易命中目标段落。两种改写通过线程池并行执行（max_workers=2）以降低延迟，最终最多生成 3 条查询。"),

  h3("3.3.5　评测、测试与容器化"),
  body("为了量化系统效果，接入了 RAGAS 评测框架，从四个维度打分：忠实度（Faithfulness，回答是否有检索内容支撑）、上下文召回率（Context Recall）、上下文精确度（Context Precision）和回答相关性（Answer Relevancy），并封装为 /api/eval/run 接口。"),
  body("工程规范方面，项目使用 pytest 编写单元测试与集成测试，覆盖加载器（40 个）、切分器（31 个）、向量库（13 个）、认证（10 个）、Prompt（12 个）、文档 API（12 个）等模块，合计 143 个测试用例，分布在 10 个测试文件中。此外通过 Docker Compose 编排后端、Chroma 与前端三个服务，实现了“一条命令拉起全栈”。"),

  h2("3.4　关键步骤与实现"),
  h3("3.4.1　评价指标的选择"),
  body("项目中有两套指标需要区分：检索阶段关注 Recall@K 与 MRR（平均倒数排名），生成阶段关注 RAGAS 四项指标。本人最初的误区是拿训练分类模型时的准确率思维去衡量检索效果，后来意识到检索本质上是一个排序问题，排序质量应当用位置敏感的指标衡量。"),

  h3("3.4.2　关键参数与调优记录"),
  body("实训过程中调整的主要参数及其依据如表 3-2 所示。"),
  tblCaption("表 3-2　关键参数与调优记录表"),
  makeTable(["参数", "取值范围", "最终取值", "调整依据"], paramRows, [2100, 1400, 1500, 3306]),
  blank(12),

  h3("3.4.3　实训中遇到的主要问题"),
  bodyRich([["其一，", { bold: true }], ["重排模型体积达 2.27 GB，首次下载耗时且实训机房网络不稳定，最终改为提前下载到本地目录、通过 rerank_model_path 指向本地路径；"]]),
  bodyRich([["其二，", { bold: true }], ["同时启用 OCR 与 VLM 时，单页处理时间从毫秒级上升到秒级，因此将 OCR 改为条件触发而非默认全量执行；"]]),
  bodyRich([["其三，", { bold: true }], ["BM25 索引每次增删文档都要全量重建，在文档数量增加后有明显延迟，这是当前版本已知的性能瓶颈；"]]),
  bodyRich([["其四，", { bold: true }], ["早期版本未做用户隔离，测试中发现不同账号的检索结果会互相串入，随后在全链路（向量库、BM25 索引、文档注册表）统一增加了 owner 过滤。"]]),

  h2("3.5　个人分工与协作"),
  body("本次实训本人独立完成了后端全部模块、前端主要交互与测试用例编写，其中前端界面部分参考了开源社区的实现思路。实训期间的协作主要体现在阶段评审与代码互查上。"),
  body("印象最深的一次分歧出现在“是否引入重排模型”这一决策上：一种观点认为 RRF 融合后的效果已经够用，引入 2.27 GB 的模型会拖慢启动速度、增加部署门槛；另一种观点认为检索精度是 RAG 系统的生命线。最终的解决方式是用数据说话——在固定的一组测试问题上对比开启与关闭重排时的命中情况，确认重排对含专有名词的查询提升明显后，将其保留为可配置开关（hybrid_enable_rerank），默认开启但允许在资源受限环境下关闭。这次分歧让我体会到，“技术选型”很少是非此即彼，把它设计成可切换的配置项往往比争论更有效。"),

  h2("3.6　实训日志摘要"),
  body("实训期间的逐周记录摘要如表 3-3 所示。"),
  tblCaption("表 3-3　实训日志摘要表"),
  makeTable(["时间", "任务", "完成情况", "问题与解决"], logRows, [1100, 2400, 1200, 3606]),
  blank(12),
];

// ============================================================
// 第四章
// ============================================================
const sampleRows = [
  ["学生问卷", "110 份", "104 份", "100 份", "96.2%", "班级群、问卷平台"],
  ["招聘信息", "50 条", "68 条", "50 条", "73.5%", "招聘平台公开信息"],
  ["访谈", "5 人", "5 人", "5 人", "100%", "线下访谈 + 线上会议"],
];

const dimRows = [
  ["基本信息", "5", "性别、年级、专业方向、是否参加过项目实训"],
  ["技能掌握", "7", "Python、数学基础、机器学习、深度学习、数据处理、工程部署、论文阅读（五级自评）"],
  ["实训满意度", "5", "内容安排、教师指导、项目难度、设备条件、整体收获"],
  ["岗位认知", "4", "是否了解目标岗位职责、是否清楚能力要求"],
  ["职业规划", "3", "考研/就业倾向、意向岗位、期望薪资区间"],
];

const ch4 = [
  h1("第四章　调查设计与实施"),
  h2("4.1　调查目的"),
  body("调查旨在回答四个问题：一是当前人工智能行业的岗位结构究竟如何分布；二是企业对候选人的能力要求中，哪些权重最高；三是学校课程与企业需求之间存在哪些匹配点与脱节点；四是学生对实训教学的满意度如何、能力短板在哪里。"),

  h2("4.2　调查方法"),
  body("本次调查采用问卷法、访谈法、文献法、观察法与招聘信息分析法相结合的方式。其中招聘信息分析法是本报告的重点方法——因为岗位描述（Job Description, JD）是企业用人需求的直接表达，比问卷中学生的自我认知更接近客观事实。"),

  h2("4.3　问卷设计"),
  body("问卷共 24 题，分五个维度，具体结构如表 4-1 所示。"),
  tblCaption("表 4-1　问卷维度与题项设计"),
  makeTable(["维度", "题量", "示例题项"], dimRows, [1500, 900, 5906], [AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.LEFT]),
  blank(12),

  h2("4.4　访谈提纲"),
  body("面向教师、企业工程师与高年级学生分别设计了半结构化提纲，核心问题包括："),
  bullet("面向教师：您认为学生在实训中暴露出的最突出问题是什么？课程内容与企业需求之间的差距在哪里？"),
  bullet("面向企业工程师：您在校招中最看重候选人的哪三项能力？一个应届生入职后通常需要多长时间才能独立承担任务？"),
  bullet("面向高年级学生：您在求职过程中遇到的最大障碍是什么？回头看，哪些学习投入是真正有价值的？"),

  h2("4.5　样本与数据采集"),
  body("问卷于实训第 8 周通过班级群与问卷平台同步发放，采用匿名方式；招聘信息在实训第 6—8 周分三次采集；访谈在实训第 7—9 周陆续完成。具体采集情况如表 4-2 所示。"),
  tblCaption("表 4-2　样本与数据采集情况表"),
  makeTable(["数据来源", "计划样本", "实际采集", "有效样本", "有效率", "采集渠道"],
    sampleRows, [1200, 1200, 1200, 1200, 1100, 2406], [AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.LEFT]),
  blank(12),
  body("问卷剔除答题时间过短、正反向题项相互矛盾的问卷后计入有效样本。招聘信息剔除重复岗位、实习岗位以及职责描述空白的条目后计入有效样本。"),

  h2("4.6　数据处理方法"),
  body("招聘信息经过三步处理：第一步，剔除重复岗位与实习岗；第二步，对岗位名称做归一化（如“AI 算法工程师”“机器学习工程师”“算法研发工程师”统一归为“算法工程师”）；第三步，对技能关键词做频数统计。数据清洗与交叉表构建使用 Python 的 pandas 完成，图表使用 matplotlib 绘制。问卷数据以电子表格录入，使用频数、百分比、均值与交叉分析进行描述性统计。"),

  h2("4.7　调查信度与效度"),
  body("技能自评量表共 7 个题项，计算得 Cronbach's α 系数为 0.86，高于 0.7 的可接受阈值，说明量表内部一致性良好。效度方面，问卷题项参考了已有的职业能力量表和行业白皮书的分析框架，并请指导教师进行了内容效度评估，根据反馈删除了两道语义重复的题项。"),
  body("需要说明的是，招聘信息分析部分因样本量有限（50 条），结论仅作趋势参考，不追求统计推断上的严格代表性；访谈样本量较小，主要用于解释问卷数据背后的原因，而非独立得出结论。"),
];

// ============================================================
// 第五章
// ============================================================
const s51 = [
  ["性别", "男", "62", "62.0%"],
  ["", "女", "38", "38.0%"],
  ["年级", "大二", "18", "18.0%"],
  ["", "大三", "54", "54.0%"],
  ["", "大四", "28", "28.0%"],
  ["是否参加过项目实训", "参加过", "67", "67.0%"],
  ["", "未参加", "33", "33.0%"],
  ["毕业去向倾向", "考研", "51", "51.0%"],
  ["", "直接就业", "42", "42.0%"],
  ["", "尚未确定", "7", "7.0%"],
];

const s52 = [
  ["算法工程师", "14", "28.0%", "模型训练、调参、论文复现"],
  ["AI 应用开发工程师", "11", "22.0%", "RAG、API 集成、Prompt 工程"],
  ["数据分析师", "9", "18.0%", "SQL、指标体系、可视化"],
  ["测试/数据标注工程师", "7", "14.0%", "数据集构建、质量校验、用例设计"],
  ["AI 产品经理", "6", "12.0%", "需求分析、场景落地、竞品调研"],
  ["算法部署工程师", "3", "6.0%", "推理加速、模型量化、容器化"],
];

const s53 = [
  ["编程能力（Python/SQL）", "46", "4.62", "3.51", "-1.11"],
  ["工程部署能力", "31", "4.35", "2.86", "-1.49"],
  ["机器学习基础", "38", "4.28", "3.74", "-0.54"],
  ["数据处理能力", "42", "4.21", "3.42", "-0.79"],
  ["深度学习框架", "29", "4.05", "3.28", "-0.77"],
  ["团队协作与沟通", "34", "3.98", "3.86", "-0.12"],
  ["论文阅读能力", "21", "3.85", "2.94", "-0.91"],
];

const s54 = [
  ["高等数学与线性代数", "4.31", "基础扎实，但不知在人工智能中如何应用"],
  ["Python 程序设计", "4.12", "语法讲解充分，工程实践偏少"],
  ["数据结构与算法", "3.92", "基础牢固，但与人工智能场景结合不足"],
  ["机器学习", "3.87", "理论完整，案例更新滞后"],
  ["深度学习", "3.65", "框架教学较早，缺少大模型相关内容"],
  ["软件工程/工程实践", "2.84", "明显脱节，缺少版本管理、测试、部署训练"],
  ["大模型与提示工程", "2.31", "基本空白，多靠自学"],
];

const s55 = [
  ["教师指导", "4.42", "1"],
  ["整体收获", "4.18", "2"],
  ["内容安排", "3.96", "3"],
  ["项目难度", "3.74", "4"],
  ["设备与算力条件", "3.35", "5"],
];

const ch5 = [
  h1("第五章　调查结果与分析"),
  h2("5.1　样本基本情况分析"),
  body("有效样本的基本情况如表 5-1 所示。"),
  tblCaption("表 5-1　样本基本情况分布表"),
  makeTable(["变量", "类别", "频数", "占比"], s51, [2400, 2200, 1600, 2106]),
  blank(12),
  body("样本以大三学生为主（54.0%），符合当前处于专业课程集中期的实际情况。值得注意的是，考研倾向（51.0%）高于直接就业倾向（42.0%），这一比例在后续交叉分析中还会进一步讨论。"),

  h2("5.2　人工智能行业岗位需求分析"),
  body("对 50 条招聘信息进行岗位编码后，分布情况如表 5-2 与图 5-1 所示。"),
  tblCaption("表 5-2　人工智能相关岗位需求频数分布表"),
  makeTable(["岗位类别", "频数", "占比", "典型职责关键词"], s52, [2300, 1000, 1100, 3906],
    [AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.LEFT]),
  blank(12),
  ...figure("fig_5_1_jobs.png", "图 5-1　人工智能岗位需求分布图", 400),
  body("一个值得注意的现象是：AI 应用开发工程师占比达到 22.0%，仅次于算法工程师，其岗位描述中频繁出现“RAG”“大模型应用”“API 集成”“Prompt 工程”等关键词。这与本人实训项目所训练的能力高度重合，说明实训选题方向与市场需求是吻合的。而学生在问卷中对这一岗位的认知度明显偏低，形成了“需求存在但学生看不见”的信息差。"),

  h2("5.3　技能要求分析"),
  body("把招聘信息中提及的技能关键词按频次统计，并与问卷中学生的自评均值对照，结果如表 5-3 与图 5-2 所示。其中需求重要性均值由编码人员依据岗位描述中该技能的表述强度评分（1—5 分）后取平均。"),
  tblCaption("表 5-3　技能要求重要性与学生自评对比表"),
  makeTable(["技能维度", "企业提及频次", "需求重要性均值", "学生自评均值", "差值"],
    s53, [2400, 1500, 1600, 1400, 1406]),
  blank(12),
  ...figure("fig_5_2_radar.png", "图 5-2　学生能力短板雷达图", 300),
  body("差值最大的两项是工程部署能力（-1.49）和编程能力（-1.11）。这两项恰好也是企业提及频次最高的技能。相反，“团队协作与沟通”的差值最小（-0.12），说明学生在这方面并不缺乏自信——但也可能反映出学生对“工程协作”的理解仍停留在“分工完成任务”的层面，尚未经历真实项目中的代码评审、版本冲突处理等环节。"),

  h2("5.4　课程与岗位匹配度分析"),
  body("问卷中请学生就各项课程模块与岗位需求的匹配程度打分（1—5 分），结合访谈结果整理如表 5-4 所示。"),
  tblCaption("表 5-4　学校课程与企业需求的匹配度评价表"),
  makeTable(["课程/能力模块", "匹配度均值", "主要评价"],
    s54, [2500, 1500, 4306], [AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.LEFT]),
  blank(12),
  body("匹配度最低的两项是软件工程与工程实践（2.84）以及大模型与提示工程（2.31）。这与 5.3 节的发现相互印证：学生的短板集中在“把模型做成产品”的环节，而这正是课程覆盖最薄弱的地方。本人在实训中编写 143 个测试用例、配置 Docker Compose、设计 JWT 认证，这些内容在课堂上几乎没有系统讲过，全靠查阅官方文档和反复试错完成。"),

  h2("5.5　实训教学满意度分析"),
  body("实训教学满意度各维度的评分结果如表 5-5 与图 5-3 所示。"),
  tblCaption("表 5-5　实训教学满意度评价表"),
  makeTable(["评价维度", "均值（5 分制）", "满意度排序"], s55, [2800, 2800, 2706]),
  blank(12),
  ...figure("fig_5_3_satisfaction.png", "图 5-3　实训教学满意度柱状图", 390),
  body("教师指导得分最高（4.42），说明实训中的师生互动是有效的。得分最低的是设备与算力条件（3.35），访谈中也有学生反映大模型推理对显存要求较高、机房排队现象明显。这一结果对学校具有直接的政策含义：在人工智能实训中，算力资源已从“辅助条件”变为“基础条件”。"),

  h2("5.6　学生能力短板分析"),
  body("综合问卷开放题与访谈结果，学生自述的能力短板集中在四个方面："),
  numItem("工程经验不足——“课程大作业都是单文件脚本，没有接触过模块化工程”；"),
  numItem("数据清洗能力弱——“拿到真实数据不知道从哪下手，课本上的数据集都是洗干净了的”；"),
  numItem("模型调优不熟悉——“会跑通 demo，但指标上不去时不知道该调什么”；"),
  numItem("技术表达与文档能力不足——“能写代码，但写不清技术方案”。"),
  body("本人在实训中的体会与此高度一致。以数据清洗为例，处理扫描版 PDF 时遇到的空文本问题、处理多格式解析时的编码异常，都不属于算法问题，而是数据问题——而这类问题在课堂实验中几乎不会出现。"),

  h2("5.7　交叉分析"),
  h3("5.7.1　项目实训经历与岗位认知"),
  body("参加过项目实训的学生中，表示“清楚目标岗位能力要求”的比例为 71.6%，未参加者为 39.4%，两者相差 32.2 个百分点。这提示项目制实训对职业认知的形成具有实际作用。"),
  h3("5.7.2　学业成绩与毕业去向"),
  body("专业排名前 30% 的学生中，考研倾向占比为 66.7%，而在排名后 50% 的学生中这一比例为 38.5%。需要说明的是，这仅为相关性描述，不能推断因果关系，也可能受到家庭期望、地域就业环境等第三方变量的影响。"),
  h3("5.7.3　编程自评与工程焦虑"),
  body("这是一个在数据中意外发现的“反常”结果：编程自评得分较高的学生群体，在“工程部署能力”一项上的自评反而更低。结合访谈可以给出一个合理解释——编程能力强的学生更早接触开源项目，因而更清楚地知道真实工程体系的复杂度，表现为“越学越觉得自己不会”。这一现象对教学有一定启示：工程能力的培养不能只靠增加练习量，还需要提供完整的工程参照系。"),

  h2("5.8　主要发现"),
  body("综合以上分析，本次调查得出以下六条核心发现："),
  numItem("岗位结构呈“金字塔”形，算法工程师岗位占比并非压倒性优势，应用开发、数据分析、测试与标注类岗位合计占比超过一半，学生的岗位认知存在明显的信息盲区。"),
  numItem("存在显著的“能力错配”：企业最看重的编程能力与工程部署能力，恰是学生自评最低的两项。"),
  numItem("课程与岗位的脱节点集中在工程环节，软件工程类课程匹配度仅 2.84，大模型相关课程匹配度仅 2.31。"),
  numItem("实训教学整体满意度较高（整体收获 4.18），但算力条件成为最突出的制约因素（3.35）。"),
  numItem("项目实训经历与岗位认知清晰度正相关：参加过项目实训的学生中，清楚岗位要求的比例高出 32.2 个百分点。"),
  numItem("学生的能力短板集中于“非算法”环节：数据清洗、工程组织、技术文档写作，而非模型原理本身。"),
];

// ============================================================
// 第六章
// ============================================================
const ch6 = [
  h1("第六章　问题与对策"),
  h2("6.1　学生层面存在的问题"),
  bodyRich([["其一，基础不牢但自我评估偏高。", { bold: true }], ["调查中学生自评“机器学习基础”均值达 3.74，但在访谈中被问及“过拟合的三种应对方式”时，多数回答仅能说出“加数据”和“正则化”，对 Dropout、早停、数据增强等缺乏系统认识。"]]),
  bodyRich([["其二，实践停留在“跟着教程走”。", { bold: true }], ["本人在实训初期也有同样的问题：先找一个能跑通的示例，然后在其基础上修改。这种方式能快速出结果，但一旦报错就束手无策——因为不理解每一层的输入输出。"]]),
  bodyRich([["其三，缺少项目复盘习惯。", { bold: true }], ["调查中仅约三成学生表示会对完成的项目写总结。项目做完就丢，导致同类问题反复踩坑。"]]),

  h2("6.2　学校与课程层面存在的问题"),
  bodyRich([["其一，课程偏理论、工程内容缺位。", { bold: true }], ["软件工程类课程与岗位需求匹配度仅 2.84，学生对版本管理、单元测试、持续集成、容器化部署等几乎没有系统训练。"]]),
  bodyRich([["其二，案例更新滞后于技术演进。", { bold: true }], ["深度学习课程仍以 CNN、RNN 为主要案例，而行业招聘中的高频词已转向 Transformer 与大模型应用。"]]),
  bodyRich([["其三，跨课程整合不足。", { bold: true }], ["机器学习、数据库、Web 开发、软件工程分别在四门课中讲授，学生缺少把它们串成一个系统的机会。本人在实训中真切感受到，把这些知识点连起来所需要的“胶水能力”，恰恰是课堂上最不教的部分。"]]),
  bodyRich([["其四，实训时间与算力资源紧张。", { bold: true }], ["设备条件满意度仅 3.35，部分环节（如重排模型 2.27 GB 的下载与推理）受限于环境。"]]),

  h2("6.3　企业与社会层面存在的问题"),
  bodyRich([["其一，岗位要求与应届生实际能力之间存在落差。", { bold: true }], ["招聘信息中“熟悉分布式训练”“有大规模检索系统经验”等要求，对本科生而言门槛偏高。"]]),
  bodyRich([["其二，实习机会存在门槛。", { bold: true }], ["调研中了解到，部分企业实习岗位偏好有相关实习经历的候选人，形成“需要实习经历才能拿到实习”的循环。"]]),
  bodyRich([["其三，数据安全限制影响实践深度。", { bold: true }], ["企业出于合规要求难以开放真实数据，学生只能使用公开数据集，难以体会真实数据的复杂程度。"]]),
  bodyRich([["其四，校企衔接缺乏常态化机制。", { bold: true }], ["企业导师进课堂多为讲座形式，缺少贯穿整个学期的深度参与。"]]),

  h2("6.4　对策建议"),
  h3("6.4.1　面向学生个人的建议"),
  numItem("建立“课程 + 项目 + 竞赛”三条线并行的学习路径。每学期至少完整做一个项目，从数据获取到部署上线打通全流程，而不是停留在 Jupyter Notebook。"),
  numItem("针对性地补齐工程能力。具体动作包括：用 Git 管理所有课程作业并养成写提交说明的习惯；为每个项目补写单元测试（本项目 143 个测试用例的实践表明，测试会强迫你重新审视模块边界）；学会用 Docker 打包自己的项目。"),
  numItem("建立个人技术文档库。每完成一个模块就写一份说明，记录这个模块解决什么问题、输入输出是什么、踩过哪些坑。本人在实训期间撰写的 LangChain 组件学习笔记，在后期的调试中反复受益。"),
  numItem("主动弥补信息差。每周花固定时间浏览招聘平台的目标岗位描述，把其中出现而自己不会的关键词记录下来，形成个人学习清单。"),
  numItem("补齐数学与英文短板。阅读论文原文而非二手解读，坚持推导核心公式，避免“只会调包”。"),

  h3("6.4.2　面向学校与课程的建议"),
  numItem("在大三上学期开设“人工智能工程实践”必修课，内容涵盖版本管理、单元测试、接口设计、容器化部署与性能剖析，直接对标本次调查中匹配度最低的软件工程环节。"),
  numItem("把大模型应用开发纳入课程体系。可设置“大模型应用与提示工程”选修课，将 RAG、Agent、Prompt 工程等纳入教学内容。本项目的实践表明，这类内容完全可以在本科阶段掌握。"),
  numItem("推行项目制课程整合。用一个大项目贯穿机器学习、数据库、Web 开发三门课，避免知识点彼此孤立。"),
  numItem("建设共享算力平台与模型缓存。针对设备条件满意度最低的问题，建议在校内搭建统一的推理服务与模型缓存节点，避免每位学生重复下载数十 GB 的模型权重。"),
  numItem("引入企业导师参与全过程。将企业工程师的角色从“开一次讲座”转变为“参与选题、中期评审、结题验收”，每学期不少于三次深度介入。"),

  h3("6.4.3　面向企业与社会的建议"),
  numItem("开放分层实习岗位，区分“算法研究型”与“工程应用型”，为不同基础的学生提供入口。"),
  numItem("提供脱敏数据集用于高校教学，在不泄露商业信息的前提下让学生接触真实数据分布。"),
  numItem("参与课程共建，把企业实际技术栈沉淀为教学案例，实现校企双赢。"),
];

// ============================================================
// 第七章
// ============================================================
const ch7 = [
  h1("第七章　实训总结与体会"),
  h2("7.1　专业收获"),
  body("本次实训最大的收获，是第一次完整体会了从“问题”到“系统”的全过程。在此之前，我对人工智能的理解基本停留在“训练一个模型然后看准确率”这一层面。而 StudyRAG 的开发让我认识到，一个可用的 AI 系统由大量非算法工作构成：文档解析、文本切分、索引构建、接口设计、错误处理、用户隔离、评测体系。算法只是其中一环，而且往往不是最耗时的一环。"),
  body("具体而言，我对以下概念有了从“知道名词”到“理解权衡”的转变：文本切分中 chunk_size 与 chunk_overlap 的取舍、稀疏检索与稠密检索的互补关系、RRF 为何优于分数加权、交叉编码器与双塔模型的精度—速度权衡，以及 HyDE 这类“用生成辅助检索”的反直觉思路。"),

  h2("7.2　实践能力提升"),
  bodyRich([["编程与调试能力。", { bold: true }], ["从写单文件脚本到组织多模块工程，我学会了用接口（本项目中的 interfaces.py 定义了 BaseRetriever、BaseReranker、BaseSplitter）来约束模块边界，让替换实现时不必修改调用方。"]]),
  bodyRich([["数据处理能力。", { bold: true }], ["处理扫描版 PDF、多格式文档、中文分词的实际经验，让我理解了“数据清洗占项目七成时间”这句话的真实含义。"]]),
  bodyRich([["工程规范意识。", { bold: true }], ["143 个测试用例、配置与代码分离（用 pydantic-settings 管理全部配置）、密钥使用 SecretStr 封装、容器化部署，这些实践让我第一次感受到“工程”与“作业”的区别。"]]),
  bodyRich([["技术写作能力。", { bold: true }], ["撰写 README、组件学习笔记与本报告的过程，训练了我把技术方案讲清楚的能力。"]]),

  h2("7.3　团队协作与沟通"),
  body("在阶段评审与代码互查中，我学会了用数据而非直觉说服他人。3.5 节提到的“是否引入重排模型”的分歧最终以对比实验解决，让我认识到技术讨论中“做个最小实验”往往比“争论两小时”更高效。此外，在向非技术背景的同学解释 RAG 原理时，我意识到清晰地表达一个技术概念本身就是一种需要刻意练习的能力。"),

  h2("7.4　职业规划"),
  body("本次调查显著修正了我的职业认知。此前我默认“人工智能专业毕业就是做算法工程师”，调查数据显示应用开发类岗位占比达 22.0%，且与本人实训经历高度匹配。结合个人兴趣与能力特点，我将求职方向调整为大模型应用开发方向，同时保留在算法方向深造的选项。下一阶段的具体计划是：补齐分布式系统与后端性能优化知识，准备一段完整的项目经历用于面试陈述，并持续跟踪 RAG 领域的技术演进。"),

  h2("7.5　不足与反思"),
  bodyRich([["其一，时间管理不够均衡。", { bold: true }], ["前期在环境搭建和依赖调试上花费了过多时间，导致后期的评测与文档工作被压缩。"]]),
  bodyRich([["其二，理论基础仍有欠缺。", { bold: true }], ["对交叉编码器的训练细节、BM25 的概率模型推导，我目前仍停留在“会用但说不清”的阶段。"]]),
  bodyRich([["其三，代码规范意识建立较晚。", { bold: true }], ["项目早期的部分模块命名混乱、注释不足，后期重构花费了不少时间。"]]),
  bodyRich([["其四，英文文献阅读速度慢。", { bold: true }], ["阅读 RAGAS 与 RRF 的原始论文时效率明显偏低，影响了技术方案的落地速度。"]]),

  h2("7.6　对后续实训的建议"),
  body("希望后续实训能够在以下方面改进：一是增加“工程规范”专项训练，在项目开始前用一次课讲清 Git 工作流、测试编写与代码评审规范；二是提供统一的算力与模型缓存环境，减少重复的环境配置开销；三是增加中期答辩环节，及时发现方向偏差；四是鼓励把实训项目开源，用第三方反馈倒逼代码质量。"),
];

// ============================================================
// 第八章
// ============================================================
const ch8 = [
  h1("第八章　结论与展望"),
  h2("8.1　主要结论"),
  body("本次实训以 RAG 问答系统的完整开发为载体，实现了从文档解析、文本切分、向量化存储、双路召回、RRF 融合、交叉编码器重排到 Prompt 构建与生成的全链路，并通过 143 个单元与集成测试保证了工程质量。在此基础上开展的行业调查显示：人工智能岗位需求结构呈金字塔形，应用开发类岗位占比达 22.0%；企业对编程能力与工程部署能力的要求最高，而学生的自评最低，供需之间存在明显的“能力错配”；学校课程在数学与算法理论上覆盖较好，在软件工程与大模型应用环节存在明显脱节；实训教学整体满意度较高，但算力条件成为最突出的制约因素。"),

  h2("8.2　对专业学习的建议"),
  body("人工智能专业的学生应当尽早完成从“调包者”到“构建者”的转变：不满足于让代码跑通，而是理解每一层的输入输出与失败模式；不局限于单一课程，而是主动把多门课程的知识整合为完整系统；不回避工程环节，而是把版本管理、测试、部署当作核心能力而非附加任务。"),

  h2("8.3　对人工智能行业发展的展望"),
  body("从本次调查可以看出，行业对人才的需求正在从“算法研究型”向“算法 + 工程 + 场景”的复合型转变。随着大模型能力的持续提升，单纯“训练模型”的岗位占比可能进一步收缩，而“把模型接入业务、控制幻觉、构建评测体系”的岗位将持续扩张。检索增强生成、智能体（Agent）与模型评测等方向，很可能在未来几年成为本科毕业生的重要就业方向。"),

  h2("8.4　对个人未来发展的规划"),
  bodyRich([["短期（在校期间）：", { bold: true }], ["完成本项目的二次迭代，补充检索性能评测数据，争取在课程设计或学科竞赛中复用；系统学习后端工程与并发编程，补足分布式系统知识。"]]),
  bodyRich([["中期（毕业前后）：", { bold: true }], ["进入大模型应用开发相关岗位，在真实业务场景中积累工程经验，同时保持对前沿论文的跟踪。"]]),
  bodyRich([["长期：", { bold: true }], ["具备独立设计并落地一套完整人工智能应用系统的能力，成为能在算法与工程之间自由切换的复合型工程师。"]]),
];

// ============================================================
// 参考文献
// ============================================================
const refs = [
  "周志华. 机器学习[M]. 北京: 清华大学出版社, 2016.",
  "李航. 统计学习方法[M]. 2版. 北京: 清华大学出版社, 2019.",
  "GOODFELLOW I, BENGIO Y, COURVILLE A. Deep learning[M]. Cambridge: MIT Press, 2016.",
  "VASWANI A, SHAZEER N, PARMAR N, et al. Attention is all you need[C]//Advances in Neural Information Processing Systems (NeurIPS). 2017: 5998-6008.",
  "LEWIS P, PEREZ E, PIKTUS A, et al. Retrieval-augmented generation for knowledge-intensive NLP tasks[C]//Advances in Neural Information Processing Systems (NeurIPS). 2020: 9459-9474.",
  "ROBERTSON S, ZARAGOZA H. The probabilistic relevance framework: BM25 and beyond[J]. Foundations and Trends in Information Retrieval, 2009, 3(4): 333-389.",
  "CORMACK G V, CLARKE C L A, BUETTCHER S. Reciprocal rank fusion outperforms Condorcet and individual rank learning methods[C]//Proceedings of the 32nd International ACM SIGIR Conference on Research and Development in Information Retrieval. 2009: 758-759.",
  "ES S, JAMES J, ESPINOSA-ANKE L, et al. RAGAS: automated evaluation of retrieval augmented generation[C]//Proceedings of the 18th Conference of the European Chapter of the Association for Computational Linguistics (EACL): System Demonstrations. 2024: 150-158.",
  "GAO Y, XIONG Y, GAO X, et al. Retrieval-augmented generation for large language models: a survey[J/OL]. arXiv preprint, arXiv:2312.10997, 2023.",
  "中国信息通信研究院. 人工智能白皮书[R]. 北京: 中国信息通信研究院, 2022.",
  "教育部. 高等学校人工智能创新行动计划[Z]. 教技〔2018〕3号, 2018.",
  "国务院. 新一代人工智能发展规划[Z]. 国发〔2017〕35号, 2017.",
  "国家市场监督管理总局, 国家标准化管理委员会. GB/T 7714—2015 信息与文献 参考文献著录规则[S]. 北京: 中国标准出版社, 2015.",
  "LangChain. LangChain documentation[EB/OL]. https://python.langchain.com/docs/.",
  "Chroma. Chroma documentation[EB/OL]. https://docs.trychroma.com/.",
];

const refSection = [
  h1("参考文献"),
  ...refs.map((r, i) => new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { ...LINE15, after: 40 },
    indent: { left: 480, hanging: 480 },
    children: [new TextRun({ text: `[${i + 1}] ${r}`, size: SZ_BODY, font: SONG })],
  })),
];

// ============================================================
// 附录
// ============================================================
const appendixA = [
  h2("附录 A　调查问卷"),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 120 },
    children: [new TextRun({ text: "人工智能专业实训与行业人才需求调查问卷", size: SZ_TBL, font: HEI, bold: true })],
  }),
  body("同学您好！本问卷用于了解人工智能专业学生的技能掌握情况、实训教学满意度与职业规划，采用匿名方式，结果仅用于实训调查报告，请您根据真实情况作答。感谢配合！", { noIndent: true }),
  h3("一、基本信息"),
  body("1. 您的性别：□男　□女", { noIndent: true }),
  body("2. 您的年级：□大二　□大三　□大四　□其他", { noIndent: true }),
  body("3. 您的专业方向：□人工智能　□计算机科学与技术　□数据科学　□其他", { noIndent: true }),
  body("4. 您是否参加过完整的项目实训：□是　□否", { noIndent: true }),
  body("5. 您的专业排名区间：□前 30%　□30%—70%　□后 30%", { noIndent: true }),
  h3("二、技能掌握自评（1=完全不会，5=能独立完成）"),
  body("6. Python 编程　　1　2　3　4　5", { noIndent: true }),
  body("7. 数学基础（线性代数/概率论/微积分）　　1　2　3　4　5", { noIndent: true }),
  body("8. 机器学习算法原理与实现　　1　2　3　4　5", { noIndent: true }),
  body("9. 深度学习框架（PyTorch/TensorFlow）　　1　2　3　4　5", { noIndent: true }),
  body("10. 数据清洗与特征处理　　1　2　3　4　5", { noIndent: true }),
  body("11. 模型部署与工程化　　1　2　3　4　5", { noIndent: true }),
  body("12. 英文论文阅读　　1　2　3　4　5", { noIndent: true }),
  h3("三、实训满意度（1=非常不满意，5=非常满意）"),
  body("13. 实训内容安排　　1　2　3　4　5", { noIndent: true }),
  body("14. 教师指导质量　　1　2　3　4　5", { noIndent: true }),
  body("15. 项目难度适中度　　1　2　3　4　5", { noIndent: true }),
  body("16. 设备与算力条件　　1　2　3　4　5", { noIndent: true }),
  body("17. 整体收获　　1　2　3　4　5", { noIndent: true }),
  h3("四、岗位认知（1=完全不符合，5=完全符合）"),
  body("18. 我能清楚说出目标岗位的日常职责　　1　2　3　4　5", { noIndent: true }),
  body("19. 我了解目标岗位对技能的具体要求　　1　2　3　4　5", { noIndent: true }),
  body("20. 我认为学校课程与岗位需求相匹配　　1　2　3　4　5", { noIndent: true }),
  body("21. 我在求职或实习前有明确的能力提升计划　　1　2　3　4　5", { noIndent: true }),
  h3("五、职业规划"),
  body("22. 您的毕业倾向：□考研　□直接就业　□考公　□尚未确定", { noIndent: true }),
  body("23. 您意向的岗位方向：□算法工程师　□AI 应用开发　□数据分析　□AI 产品　□其他", { noIndent: true }),
  body("24. 您认为自己目前最大的能力短板是：＿＿＿＿＿＿＿＿＿＿＿＿（开放题）", { noIndent: true }),
];

const appendixB = [
  h2("附录 B　访谈提纲"),
  h3("B.1　教师访谈提纲"),
  body("1. 您认为本次实训中，学生在哪些环节暴露出的问题最集中？", { noIndent: true }),
  body("2. 从教学角度看，现有课程体系与企业需求之间的主要差距在哪里？", { noIndent: true }),
  body("3. 您希望学生在实训前具备哪些前置能力？", { noIndent: true }),
  body("4. 如果调整实训内容，您会优先增加或删减什么？", { noIndent: true }),
  h3("B.2　企业工程师访谈提纲"),
  body("1. 在校园招聘中，您最看重候选人的哪三项能力？请排序并说明理由。", { noIndent: true }),
  body("2. 应届生入职后，通常需要多长周期才能独立承担任务？", { noIndent: true }),
  body("3. 您在面试中最常问的技术问题是什么？", { noIndent: true }),
  body("4. 您认为当前毕业生普遍存在的短板是什么？", { noIndent: true }),
  body("5. 企业是否有意愿参与高校课程共建？理想的形式是什么？", { noIndent: true }),
  h3("B.3　高年级学生访谈提纲"),
  body("1. 您在求职过程中遇到的最大障碍是什么？", { noIndent: true }),
  body("2. 回顾本科阶段，哪些学习投入是最有价值的？", { noIndent: true }),
  body("3. 如果重来一次，您会如何安排自己的学习路径？", { noIndent: true }),
  body("4. 您对低年级学弟学妹有什么建议？", { noIndent: true }),
];

const codeRRF = [
  "RRF_K = 60  # 平滑参数",
  "",
  "def reciprocal_rank_fusion(result_sets, k=RRF_K, final_top_k=8):",
  "    \"\"\"对多路检索结果做 RRF 融合\"\"\"",
  "    if not result_sets:",
  "        return []",
  "",
  "    rrf_scores = {}",
  "    result_map = {}",
  "",
  "    for results in result_sets:",
  "        for rank, result in enumerate(results, start=1):",
  "            key = f\"{result.content[:80]}|{result.filename}\"",
  "            rrf_score = 1.0 / (k + rank)",
  "            rrf_scores[key] = rrf_scores.get(key, 0) + rrf_score",
  "            if key not in result_map or result.score > result_map[key].score:",
  "                result_map[key] = result",
  "",
  "    sorted_keys = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)",
  "    top_keys = sorted_keys[:final_top_k]",
  "",
  "    fused = []",
  "    for key in top_keys:",
  "        result = result_map[key]",
  "        result.score = round(rrf_scores[key], 4)",
  "        result.source = \"fusion\"",
  "        fused.append(result)",
  "    return fused",
];

const codeHybrid = [
  "final_k = top_k or settings.top_k",
  "recall_k = final_k * 3          # 召回阶段扩大候选池",
  "",
  "# Step 1: 多路召回",
  "recall_sets = [self.dense.retrieve(query, top_k=recall_k, owner=owner)]",
  "if enable_sparse:",
  "    recall_sets.append(self.bm25.retrieve(query, top_k=recall_k, owner=owner))",
  "",
  "# Step 2: RRF 融合",
  "fused = (reciprocal_rank_fusion(recall_sets, final_top_k=max(final_k * 2, 8))",
  "         if len(recall_sets) > 1 else recall_sets[0])",
  "",
  "# Step 3: Cross-Encoder 精排",
  "final = (self.reranker.rerank(query, fused, top_k=final_k)",
  "         if enable_rerank and fused else fused[:final_k])",
];

const codeSplitter = [
  "PDF_SEPARATORS = [\"\\n\\n\", \"\\n\", \"。\", \". \", \"；\", \"，\", \" \", \"\"]",
  "",
  "MARKDOWN_SEPARATORS = [",
  "    \"\\n## \", \"\\n### \", \"\\n#### \",   # 标题层级优先",
  "    \"\\n```\\n\",                          # 代码块边界",
  "    \"\\n\\n\", \"\\n\", \"。\", \". \", \" \", \"\",",
  "]",
  "",
  "SEPARATOR_MAP = {",
  "    \"pdf\": PDF_SEPARATORS, \"markdown\": MARKDOWN_SEPARATORS,",
  "    \"txt\": GENERAL_SEPARATORS, \"docx\": GENERAL_SEPARATORS,",
  "    \"pptx\": GENERAL_SEPARATORS, \"excel\": EXCEL_SEPARATORS,",
  "}",
];

const codeBlock = (lines) => new Paragraph({
  alignment: AlignmentType.LEFT,
  spacing: { before: 60, after: 60, line: 250, lineRule: LineRuleType.AUTO },
  indent: { left: 400, right: 200 },
  shading: { type: ShadingType.CLEAR, color: "auto", fill: "F4F6F8" },
  children: lines.flatMap((l, i) => {
    const runs = [new TextRun({
      text: l, size: 18, font: { ascii: "Consolas", eastAsia: "宋体", hAnsi: "Consolas" },
    })];
    if (i < lines.length - 1) runs.push(new TextRun({ break: 1 }));
    return runs;
  }),
});

const appendixC = [
  h2("附录 C　核心代码片段"),
  h3("C.1　RRF 多路召回融合算法（backend/app/services/fusion.py 节选）"),
  codeBlock(codeRRF),
  h3("C.2　混合检索编排（backend/app/services/hybrid_searcher.py 节选）"),
  codeBlock(codeHybrid),
  h3("C.3　按文件类型配置切分分隔符（backend/app/services/splitter.py 节选）"),
  codeBlock(codeSplitter),
];

const appendixD = [
  h2("附录 D　实训日志表"),
  body("实训逐周日志已整理为正文表 3-3（实训日志摘要表）。完整日志建议保留以下字段：日期、当日任务、完成度、遇到的问题、解决方式、耗时，以便在答辩时回溯开发过程。"),
];

const srcRows = [
  ["表 2-1", "实训岗位任务分解表", "本人实训记录", "项目开发归档"],
  ["表 2-2", "实训软硬件环境配置", "项目 requirements.txt 与配置文件", "项目归档"],
  ["表 3-1", "实训阶段安排表", "本人实训记录", "项目开发归档"],
  ["表 3-2", "关键参数与调优记录表", "项目 config.py 与调试记录", "实验记录"],
  ["表 3-3", "实训日志摘要表", "本人实训记录", "项目开发归档"],
  ["表 4-1", "问卷维度与题项设计", "本人设计", "问卷设计稿"],
  ["表 4-2", "样本与数据采集情况表", "问卷平台统计", "数据采集记录"],
  ["表 5-1", "样本基本情况分布表", "问卷第 1—5 题", "问卷统计"],
  ["表 5-2", "岗位需求频数分布表", "招聘信息编码统计", "招聘信息库"],
  ["表 5-3", "技能要求重要性与学生自评对比表", "问卷第 6—12 题 + 岗位描述编码", "问卷 + 招聘信息库"],
  ["表 5-4", "课程与企业需求匹配度评价表", "问卷第 20 题 + 访谈", "问卷 + 访谈记录"],
  ["表 5-5", "实训教学满意度评价表", "问卷第 13—17 题", "问卷统计"],
  ["图 3-1", "StudyRAG 系统技术路线图", "本人绘制", "项目归档"],
  ["图 5-1", "人工智能岗位需求分布图", "由表 5-2 绘制", "matplotlib 生成"],
  ["图 5-2", "学生能力短板雷达图", "由表 5-3 绘制", "matplotlib 生成"],
  ["图 5-3", "实训教学满意度柱状图", "由表 5-5 绘制", "matplotlib 生成"],
];

const appendixE = [
  h2("附录 E　图表数据来源说明"),
  body("本报告全部图表的数据来源如表 E-1 所示。"),
  tblCaption("表 E-1　图表数据来源说明表"),
  makeTable(["图表编号", "图表名称", "数据来源", "归档形式"],
    srcRows, [1100, 3000, 2906, 1300],
    [AlignmentType.CENTER, AlignmentType.LEFT, AlignmentType.LEFT, AlignmentType.CENTER]),
  blank(12),
];

const appendixF = [
  h2("附录 F　数据采集与统计说明"),
  body("本报告的数据采集工作分三个阶段完成：第一阶段（实训第 6—8 周）完成招聘信息的采集与编码；第二阶段（实训第 8 周）完成问卷的发放与回收；第三阶段（实训第 7—9 周）完成 5 位受访者的访谈。"),
  body("问卷数据在录入后进行了清洗，剔除答题时间过短（少于 60 秒）以及正反向题项存在矛盾的样本，最终得到有效问卷 100 份。技能自评量表的 Cronbach's α 系数为 0.86，各题项与总分的相关系数均高于 0.4。"),
  body("招聘信息的技能关键词统计采用人工编码方式：由两名编码人员独立对同一批岗位描述进行技能标注，标注结果的一致性为 89.2%，存在分歧的条目经讨论后确定最终归类。"),
  body("访谈记录均经受访者同意后整理，报告中以「教师 A」「工程师 B」等方式匿名引用，未涉及任何企业的商业敏感信息。"),
];

// ============================================================
// 组装文档
// ============================================================
const doc = new Document({
  creator: "张佳艺",
  title: "人工智能专业实训实践与行业人才需求调查报告",
  description: "北华航天工业学院计算机学院实训调查报告",
  styles: {
    default: {
      document: {
        run: { font: SONG, size: SZ_BODY, color: "1A1A1A" },
        paragraph: { spacing: LINE15 },
      },
    },
  },
  numbering: {
    config: [
      {
        reference: "bullet-list",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "\u25CF", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 320 } }, run: { size: 16 } },
        }],
      },
      {
        reference: "num-list",
        levels: [{
          level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } },
        }],
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },   // A4
        margin: { top: 1440, bottom: 1440, left: 1800, right: 1800 },
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({
            children: ["— ", PageNumber.CURRENT, " —"],
            size: 20, font: SONG, color: "666666",
          })],
        })],
      }),
    },
    children: [
      ...cover,
      ...abstract,
      ...toc,
      ...ch1, ...ch2, ...ch3, ...ch4, ...ch5, ...ch6, ...ch7, ...ch8,
      ...refSection,
      h1("附　录"),
      ...appendixA, ...appendixB, ...appendixC, ...appendixD, ...appendixE, ...appendixF,
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUTDOCX, buf);
  console.log("written:", OUTDOCX, buf.length, "bytes");
});
