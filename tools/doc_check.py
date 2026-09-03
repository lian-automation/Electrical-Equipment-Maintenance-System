#!/usr/bin/env python3
"""文档包一致性检查（文档体系包 CI 适配版，仓库无代码故不设可运行测试）：
1. 全部 Markdown 相对链接可解析（防断链回归，覆盖第三/四轮修补转正的 13 处交叉引用）；
2. UTF-8 编码健康（严格解码 + U+FFFD 替换字符/私用区字符扫描）；
3. 篇数统计，并与 README 顶部 Docs 徽章数字核对。
用法：python tools/doc_check.py（全部通过退出码 0，否则打印问题清单并退出码 1）
"""
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
LINK_RE = re.compile(r"\[[^\]]*\]\(([^()\s]+)\)")
BADGE_RE = re.compile(r"img\.shields\.io/badge/Docs-[^)_]*_(\d+)")
EXTERNAL = ("http://", "https://", "mailto:")


def iter_docs():
    """仓库内全部 Markdown 文档（跳过 .git）。"""
    return [p for p in sorted(ROOT.rglob("*.md")) if ".git" not in p.parts]


def main():
    problems = []
    docs = iter_docs()
    total_links, ok_links = 0, 0

    for p in docs:
        rel = p.relative_to(ROOT)
        try:
            text = p.read_text(encoding="utf-8")  # 严格解码：编码损坏即抛异常
        except UnicodeDecodeError as exc:
            problems.append(f"{rel}: UTF-8 严格解码失败（{exc}）")
            continue
        if "\ufffd" in text:
            problems.append(f"{rel}: 含 U+FFFD 替换字符（疑似编码损坏）")
        pua = sorted({f"U+{ord(c):04X}" for c in text if 0xE000 <= ord(c) <= 0xF8FF})
        if pua:
            problems.append(f"{rel}: 含私用区字符 {' '.join(pua)}")
        for target in LINK_RE.findall(text):
            if target.startswith(EXTERNAL):
                continue  # 外链不做网络校验（CI 离线可重复）
            total_links += 1
            path = urllib.parse.unquote(target.split("#", 1)[0])
            if path and not (p.parent / path).exists():
                problems.append(f"{rel}: 断链 -> {target}")
            else:
                ok_links += 1

    module_docs = [p for p in docs if p != README and "resume" not in p.parts]
    by_dir = {}
    for p in module_docs:
        by_dir.setdefault(p.parent.name, []).append(p.name)

    print("== 篇数统计 ==")
    for d in sorted(by_dir):
        print(f"  {d}/  {len(by_dir[d])} 篇")
    resume_n = len(docs) - len(module_docs) - (1 if README.exists() else 0)
    print(f"  模块文档 {len(module_docs)} 篇 + resume {resume_n} 篇 + README 1 篇 = 全包 {len(docs)} 个 Markdown")

    if README.exists():
        m = BADGE_RE.search(README.read_text(encoding="utf-8"))
        if not m:
            problems.append("README.md: 未找到 Docs 徽章（img.shields.io/badge/Docs-...）")
        elif int(m.group(1)) != len(module_docs):
            problems.append(
                f"README.md: Docs 徽章篇数（{m.group(1)}）与实际模块文档数（{len(module_docs)}）不一致"
            )
    else:
        problems.append("缺少 README.md")

    print("== 相对链接 ==")
    print(f"  共 {total_links} 个相对链接，可解析 {ok_links} 个（外链不校验）")
    print("== 编码健康 ==")
    print(f"  {len(docs)} 个文档均按 UTF-8 严格解码通过，无 U+FFFD/私用区字符" if not any(
        "解码失败" in x or "U+FFFD" in x or "私用区" in x for x in problems) else "  存在编码问题，见下方清单")

    if problems:
        print(f"\n[FAIL] 发现 {len(problems)} 个问题：")
        for x in problems:
            print(f"  - {x}")
        return 1
    print("\n[OK] 文档一致性检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
