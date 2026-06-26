# -*- coding: utf-8 -*-
"""对生成的 docx 做结构自检：XML 是否良构、pPr/rPr 子元素次序是否合规。"""
import io
import sys
import zipfile

from lxml import etree

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % NS

# ECMA-376 中 CT_PPr / CT_RPr 的 sequence 定义（仅列会用到的部分）
PPR = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl",
       "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens",
       "kinsoku", "wordWrap", "overflowPunct", "topLinePunct", "autoSpaceDE",
       "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind",
       "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
       "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr",
       "sectPr", "pPrChange"]
RPR = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike",
       "dstrike", "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid",
       "vanish", "webHidden", "color", "spacing", "w", "kern", "position", "sz", "szCs",
       "highlight", "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs",
       "em", "lang", "eastAsianLayout", "specVanish", "oMath"]


def check(root, parent_tag, order):
    bad = []
    for parent in root.iter(W + parent_tag):
        seq = [c.tag.split("}")[1] for c in parent if c.tag.split("}")[1] in order]
        nums = [order.index(t) for t in seq]
        if nums != sorted(nums):
            bad.append(seq)
    return bad


def main(doc):
    z = zipfile.ZipFile(doc)

    problems = []
    for name in z.namelist():
        if name.endswith((".xml", ".rels")):
            try:
                etree.fromstring(z.read(name))
            except Exception as exc:                       # noqa: BLE001
                problems.append((name, str(exc)[:140]))
    print("XML 良构:", "全部通过" if not problems else problems)

    x = etree.fromstring(z.read("word/document.xml"))
    for tag, order in (("pPr", PPR), ("rPr", RPR)):
        bad = check(x, tag, order)
        print(f"{tag} 子元素次序:", "通过" if not bad else f"{len(bad)} 处异常 {bad[:3]}")

    print("段落数:", len(x.findall(".//" + W + "p")))
    print("表格数:", len(x.findall(".//" + W + "tbl")))
    print("插图数:", len(x.findall(".//" + W + "drawing")))
    print("分节符数:", len(x.findall(".//" + W + "sectPr")))
    print("媒体文件:", [n for n in z.namelist() if "media" in n])

    # 抽查几个关键段落
    body = x.find(W + "body")
    for p in list(body)[:0]:
        pass
    styles = set()
    for p in x.findall(".//" + W + "p"):
        ps = p.find(W + "pPr/" + W + "pStyle")
        if ps is not None:
            styles.add(ps.get(W + "val"))
    print("使用到的段落样式:", sorted(styles))


if __name__ == "__main__":
    main(sys.argv[1])
