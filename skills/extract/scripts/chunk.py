"""chunk.py — 阶段1.5 切块：把知识库笔记切成 chunk，供阶段3 ainsert（LLM 抽取，辅助线）。

策略：
  1. 粒度：每篇笔记 = 1 chunk（笔记已按主题组织，4-8KB 适合 LLM）
  2. 超长拆分：笔记正文 > max_chars（默认 1500）时，按 ## 节拆成多 chunk
  3. 元数据：source（笔记名）+ 页码（从「> 出自...P<起>-P<止>」提取）

用法：python chunk.py <vault_dir> [--subdirs 领域目录,逗号分隔] [--max-chars 1500] [--out chunks.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_PAGE_RE = re.compile(r"P(\d+)\s*[-–]\s*P?(\d+)")


def _split_frontmatter(text: str) -> tuple[str, str]:
    """拆 frontmatter 与正文。返回 (frontmatter, body)。"""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[1], parts[2]
    return "", text


def _extract_page(body: str) -> str:
    """从出处行提取页码。"""
    for line in body.splitlines()[:15]:
        if line.strip().startswith(">") and "P" in line:
            m = _PAGE_RE.search(line)
            if m:
                return f"P{m.group(1)}-P{m.group(2)}"
    return ""


def chunk_note(md_path: Path, max_chars: int) -> list[dict]:
    """把一篇笔记切成 chunk 列表。"""
    text = md_path.read_text(encoding="utf-8")
    _, body = _split_frontmatter(text)
    page = _extract_page(body)
    source = md_path.stem

    # 去掉 frontmatter + 原文页面 引用块（图片链接不算正文）
    body_lines = [l for l in body.splitlines()
                  if not l.strip().startswith("![[assets/")]
    body_clean = "\n".join(body_lines).strip()

    if len(body_clean) <= max_chars:
        return [{"content": body_clean, "source": source, "page": page}]

    # 超长：按 ## 节拆
    chunks = []
    sections = re.split(r"(?m)^## ", body_clean)
    head = sections[0].strip()
    if head:
        chunks.append({"content": head[:max_chars], "source": source, "page": page})
    for sec in sections[1:]:
        sec_text = "## " + sec
        chunks.append({"content": sec_text[:max_chars * 2], "source": source, "page": page})
    return chunks


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="切块：笔记 → chunk（供 ainsert）")
    ap.add_argument("vault_dir", help="知识库根目录")
    ap.add_argument("--subdirs", default=None, help="领域目录（逗号分隔，默认全部含笔记的子目录）")
    ap.add_argument("--max-chars", type=int, default=1500, help="单 chunk 最大字符数（超长按##节拆）")
    ap.add_argument("--out", default="chunks.json", help="输出 json 路径")
    args = ap.parse_args()

    vault = Path(args.vault_dir)
    if args.subdirs:
        subdirs = [vault / d.strip() for d in args.subdirs.split(",") if d.strip()]
    else:
        subdirs = [d for d in vault.iterdir() if d.is_dir()
                   and any(d.glob("*.md")) and d.name != "assets"]

    all_chunks = []
    for sub in subdirs:
        for p in sorted(sub.glob("*.md")):
            if p.name.startswith(("data_structure", "00_")):
                continue  # 跳过索引和总览
            all_chunks.extend(chunk_note(p, args.max_chars))

    out = Path(args.out)
    out.write_text(json.dumps(all_chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"切块完成 → {out}")
    print(f"  {len(subdirs)} 领域目录 → {len(all_chunks)} chunks")
    # 统计超长拆分的
    sources = set(c["source"] for c in all_chunks)
    multi = [s for s in sources if sum(1 for c in all_chunks if c["source"] == s) > 1]
    print(f"  超长拆分（>1 chunk）的笔记 {len(multi)} 篇")
    return 0


if __name__ == "__main__":
    sys.exit(main())
