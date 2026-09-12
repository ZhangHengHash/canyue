"""structure_scan.py — 结构映射：扫 content_list.json 的标题层级，产出「章节→页」结构清单。

背景：残月原缺「文档结构映射」（PDF 页 → 子文档/章节边界）能力，曾临时用 pypdf 干这活。
本脚本扫 content_list.json 里 text_level 1/2 的标题元素（H1/H2），产出结构清单，
供 organizer 按章节拆分成笔记，彻底替代 pypdf。

产物：<product_dir>/structure_scan.json + 终端报告
用法：python structure_scan.py <产物目录>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_cl(product_dir: Path) -> list[dict]:
    stem = product_dir.parent.name
    p = product_dir / f"{stem}_content_list.json"
    if not p.exists():
        raise FileNotFoundError(f"缺 content_list.json：{p}")
    return json.loads(p.read_text(encoding="utf-8"))


def scan(product_dir: Path) -> dict:
    """扫 content_list.json 的 text_level 1/2 标题元素，返回结构清单（过滤运行页眉）。"""
    cl = _load_cl(product_dir)

    # 标题元素：type=text 且 text_level in (1,2)
    headers = []
    for x in cl:
        if x.get("type") != "text":
            continue
        lv = x.get("text_level", 0)
        if lv not in (1, 2):
            continue
        txt = (x.get("text") or "").strip()
        if not txt:
            continue
        headers.append({
            "level": lv,  # 1=H1(#) 2=H2(##)
            "text": txt,
            "page": (x.get("page_idx") or 0) + 1,  # 1-based 供人读
        })

    # 运行页眉/页脚 = 同一文本反复出现（每页一次），非章节标题。频次 > 2 视为页眉。
    from collections import Counter
    freq = Counter(h["text"] for h in headers)
    running = {txt for txt, c in freq.items() if c > 2}
    for h in headers:
        h["is_running"] = h["text"] in running

    # 章节 = 非运行页眉的 H1；子节 = 非运行页眉的 H2
    h1 = [h for h in headers if h["level"] == 1 and not h["is_running"]]
    h2 = [h for h in headers if h["level"] == 2 and not h["is_running"]]

    sections = []
    for i, h in enumerate(h1):
        start = h["page"]
        end = (h1[i + 1]["page"] - 1) if i + 1 < len(h1) else None  # 最后一章到文档末
        sections.append({
            "title": h["text"],
            "start_page": start,
            "end_page": end,
        })

    return {
        "n_h1": len(h1),
        "n_h2": len(h2),
        "n_running_headers": len(running),
        "h1": h1,
        "h2": h2,
        "sections": sections,
    }


def main() -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="结构映射：扫 content_list.json 标题层级出「章节→页」清单")
    ap.add_argument("product_dir", help="产物目录 <out>/<pdf_stem>/<method>/")
    ap.add_argument("--out", default=None, help="输出 json 路径（默认 <product_dir>/structure_scan.json）")
    args = ap.parse_args()

    pd = Path(args.product_dir)
    if not pd.is_dir():
        print(f"错误：{pd} 不存在", file=sys.stderr)
        return 1

    result = scan(pd)

    out = Path(args.out) if args.out else (pd / "structure_scan.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"结构映射完成 → {out}")
    print(f"  H1 章节 {result['n_h1']} 个 / H2 子节 {result['n_h2']} 个")
    if result["sections"]:
        print("\n  H1 章节（页范围）：")
        for s in result["sections"]:
            end = s["end_page"] if s["end_page"] is not None else "末页"
            print(f"    P{s['start_page']:>3}-{end:>3}  {s['title'][:50]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
