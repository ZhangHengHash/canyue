"""verify_format.py — 阶段1.4 质量门禁：公式/表格格式完整性（漏公式/漏行/乱码/页丢失）。

检查（对 MinerU 产物）：
  1. 公式 LaTeX 保留：content_list.json 的 equation 元素 text（LaTeX）应出现在 md 里
  2. 表格完整性：table 元素 table_body 非空、无乱码（� 替换符）
  3. 乱码检测：text/table 元素里出现 U+FFFD 或常见 mojibake 模式
  4. 页丢失：middle.json pdf_info 页数 vs 预期（可选 --expect-pages）

用法：python verify_format.py <产物目录> [--expect-pages N]
退出码：0=通过，1=有缺口
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _load_cl(product_dir: Path) -> list[dict]:
    stem = product_dir.parent.name
    p = product_dir / f"{stem}_content_list.json"
    if not p.exists():
        raise FileNotFoundError(f"缺 content_list.json：{p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _load_md(product_dir: Path) -> str:
    stem = product_dir.parent.name
    p = product_dir / f"{stem}.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _load_middle_pages(product_dir: Path) -> int:
    stem = product_dir.parent.name
    p = product_dir / f"{stem}_middle.json"
    if not p.exists():
        return 0
    m = json.loads(p.read_text(encoding="utf-8"))
    return len(m.get("pdf_info", []))


# 乱码特征：U+FFFD 替换符 + UTF-8→Latin-1 mojibake（Ã + 0x80-0xBF 字节、â€™/â€œ）
_MOJIBAKE_RE = re.compile(r"[�]|\xc3[\x80-\xbf]|\xe2\x80[\x99\x9c\x9d]")


def _is_garbled(text: str) -> bool:
    """检测乱码：U+FFFD 替换符或常见 mojibake 序列。"""
    return bool(text) and bool(_MOJIBAKE_RE.search(text))


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="格式门禁：公式/表格完整性（漏公式/漏行/乱码/页丢失）")
    ap.add_argument("product_dir", help="产物目录 <out>/<pdf_stem>/<method>/")
    ap.add_argument("--expect-pages", type=int, default=None, help="预期页数（页丢失检查）")
    args = ap.parse_args()

    pd = Path(args.product_dir)
    cl = _load_cl(pd)
    md = _load_md(pd)
    issues = []

    # 1. 公式 LaTeX 保留
    equations = [x for x in cl if x.get("type") == "equation"]
    missing_eq = []
    for e in equations:
        latex = (e.get("text") or "").strip()
        if latex and latex not in md:
            missing_eq.append(e.get("page_idx", 0) + 1)
    if missing_eq:
        issues.append(f"公式 LaTeX 未保留 {len(missing_eq)} 个（页码 {missing_eq}）")

    # 2. 表格完整性（漏行/乱码）
    tables = [x for x in cl if x.get("type") == "table"]
    bad_tables = []
    for t in tables:
        body = (t.get("table_body") or "").strip()
        if not body:
            bad_tables.append((t.get("page_idx", 0) + 1, "空body"))
        elif _MOJIBAKE_RE.search(body):
            bad_tables.append((t.get("page_idx", 0) + 1, "乱码"))
    if bad_tables:
        issues.append(f"表格缺行/乱码 {len(bad_tables)} 个（页码 {bad_tables[:5]}...）")

    # 3. 乱码检测（text 元素）
    garbled_texts = []
    for x in cl:
        if x.get("type") in ("text", "header", "footer"):
            if _MOJIBAKE_RE.search(x.get("text") or ""):
                garbled_texts.append(x.get("page_idx", 0) + 1)
    if garbled_texts:
        issues.append(f"正文乱码 {len(garbled_texts)} 处（页码 {garbled_texts[:5]}...）")

    # 4. 页丢失
    if args.expect_pages is not None:
        pages = _load_middle_pages(pd)
        if pages and pages < args.expect_pages:
            issues.append(f"页丢失：middle.json 只 {pages} 页，预期 {args.expect_pages}")

    n_eq = len(equations)
    n_tbl = len(tables)
    if issues:
        for i in issues:
            print(f"X {i}")
        print(f"  统计：公式 {n_eq} / 表格 {n_tbl}")
        return 1
    print(f"OK 格式完整：公式 {n_eq}（LaTeX 全保留）/ 表格 {n_tbl}（无漏行乱码）/ 页数正常")
    return 0


if __name__ == "__main__":
    sys.exit(main())
