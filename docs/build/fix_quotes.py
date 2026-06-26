# -*- coding: utf-8 -*-
"""
修复 build_report.js 中被规范化成 ASCII 的中文引号。

第一步：把上一轮误转的 “ ” 全部还原为 ASCII 双引号（幂等，可重复运行）。
第二步：按语法上下文判定哪些双引号是 JS 字符串分隔符，其余还原为中文引号。

判定规则：一个双引号若是 JS 字符串分隔符，则它左侧必为 ( [ , : = + 或空格，
或右侧（跳过空格后）必为 ) ] } , ; : 或行尾。正文中的中文引号在同一行内成对
出现，按出现顺序交替还原为开引号“和闭引号”。
"""
import io

PATH = "build_report.js"

OPEN_PREV = set('([,: =+')
CLOSE_NEXT = set(')]},;:')


def is_delimiter(s, i):
    b = s[i - 1] if i > 0 else ''
    if b in OPEN_PREV:
        return True
    j = i + 1
    while j < len(s) and s[j] == ' ':
        j += 1
    if j >= len(s):
        return True
    return s[j] in CLOSE_NEXT


def fix_line(line):
    out = []
    open_next = True
    changed = 0
    for i, ch in enumerate(line):
        if ch != '"':
            out.append(ch)
            continue
        if i > 0 and line[i - 1] == '\\':        # 转义引号保持原样
            out.append(ch)
            continue
        if is_delimiter(line, i):
            out.append(ch)
            continue
        out.append('“' if open_next else '”')
        open_next = not open_next
        changed += 1
    return ''.join(out), changed


def main():
    with io.open(PATH, encoding='utf-8') as f:
        text = f.read()

    # 第一步：还原上一轮的错误转换
    text = text.replace('“', '"').replace('”', '"')

    # 第二步：按上下文重新还原
    lines = text.split('\n')
    total = 0
    new_lines = []
    for ln in lines:
        new, n = fix_line(ln)
        total += n
        new_lines.append(new)

    with io.open(PATH, 'w', encoding='utf-8', newline='') as f:
        f.write('\n'.join(new_lines))
    print('converted %d content quotes' % total)


if __name__ == '__main__':
    main()
