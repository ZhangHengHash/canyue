"""build_index.py — 分层索引：生成 data_structure.md（根索引 + 各领域子索引）。

借鉴 ConardLi/rag-skill 分层索引：根目录 data_structure.md 说明领域目录及用途，
每个领域目录下也有 data_structure.md 说明子文档，LLM 逐层读索引导航（渐进式披露），
不全文加载。机械部分（扫目录/读标题）脚本化，用途标注 LLM 后续补。

用法：python build_index.py <vault_dir> [--subdirs 领域目录,逗号分隔] [--skip 跳过目录]
产物：<vault_dir>/data_structure.md + 每个领域目录/data_structure.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _first_h1(md_path: Path) -> str:
    """读笔记首行 # 标题（H1）。"""
    try:
        for line in md_path.read_text(encoding="utf-8").splitlines()[:30]:
            s = line.strip()
            if s.startswith("# ") and not s.startswith("## "):
                return s[2:].strip()
    except Exception:
        pass
    return md_path.stem


def _first_quote(md_path: Path) -> str:
    """读笔记首行引用块（> 出自...），作用途线索。"""
    try:
        for line in md_path.read_text(encoding="utf-8").splitlines()[:30]:
            s = line.strip()
            if s.startswith("> "):
                return s[2:].strip()[:100]
    except Exception:
        pass
    return ""


def build_subindex(subdir: Path) -> str:
    """生成领域目录的 data_structure.md（子索引）。"""
    mds = sorted(p for p in subdir.glob("*.md") if not p.name.startswith("data_structure"))
    lines = [f"# {subdir.name} 目录结构", ""]
    lines.append("> 本目录的子文档索引，供 RAG 逐层导航（不全文加载）。用途由 LLM 按需补。")
    lines.append("")
    lines.append("| 笔记 | 标题 | 出处 |")
    lines.append("|---|---|---|")
    for p in mds:
        title = _first_h1(p)
        quote = _first_quote(p)
        lines.append(f"| {p.name} | {title} | {quote} |")
    lines.append("")
    lines.append(f"共 {len(mds)} 篇笔记。")
    return "\n".join(lines)


def build_root(vault: Path, subdirs: list[Path], top_level: list[Path]) -> str:
    """生成根目录 data_structure.md（根索引）。"""
    lines = ["# 知识库 目录结构", ""]
    lines.append("> 根索引：说明领域目录及用途，供 RAG 先读根索引再进子目录（渐进式披露）。")
    lines.append("")
    lines.append("## 领域目录")
    lines.append("")
    for sub in subdirs:
        lines.append(f"- `{sub.name}/` — 见 `{sub.name}/data_structure.md`（{_count_md(sub)} 篇笔记）")
    lines.append("")
    lines.append("## 顶层文件")
    for p in top_level:
        lines.append(f"- `{p.name}` — {_first_h1(p)}")
    lines.append("")
    return "\n".join(lines)


def _count_md(subdir: Path) -> int:
    return len([p for p in subdir.glob("*.md") if not p.name.startswith("data_structure")])


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="分层索引：生成 data_structure.md（根+子索引）")
    ap.add_argument("vault_dir", help="知识库根目录")
    ap.add_argument("--subdirs", default=None, help="领域目录列表（逗号分隔，默认自动识别含笔记的子目录）")
    ap.add_argument("--skip", default="assets", help="跳过的目录（逗号分隔，默认 assets）")
    args = ap.parse_args()

    vault = Path(args.vault_dir)
    if not vault.is_dir():
        print(f"错误：{vault} 不存在", file=sys.stderr)
        return 1

    skip = set(args.skip.split(","))
    if args.subdirs:
        subdirs = [vault / d.strip() for d in args.subdirs.split(",") if d.strip()]
    else:
        subdirs = [d for d in vault.iterdir() if d.is_dir() and d.name not in skip
                   and any(d.glob("*.md"))]

    # 子索引
    for sub in subdirs:
        content = build_subindex(sub)
        (sub / "data_structure.md").write_text(content, encoding="utf-8")
        print(f"子索引 → {sub / 'data_structure.md'}")

    # 根索引
    top_level = sorted(p for p in vault.glob("*.md") if p.name != "data_structure.md")
    root_content = build_root(vault, subdirs, top_level)
    (vault / "data_structure.md").write_text(root_content, encoding="utf-8")
    print(f"根索引 → {vault / 'data_structure.md'}（{len(subdirs)} 领域目录 + {len(top_level)} 顶层文件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
