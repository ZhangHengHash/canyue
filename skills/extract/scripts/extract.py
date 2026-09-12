"""extract.py — 提取主脚本：调 MinerU 提取 PDF → 产物目录 + 质量统计。

用法：
    python extract.py <pdf> [--out 输出目录] [--method auto] [--lang ch]
产物：<out>/<pdf_stem>/<method>/{md, content_list.json, middle.json, model.json, images/*}
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import mineru_client


def main() -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="文档提取：MinerU 引擎外部引用（PDF→md+JSON+图）")
    ap.add_argument("pdf", help="PDF 路径（或图片/office）")
    ap.add_argument("--out", default=".", help="输出目录")
    ap.add_argument("--method", default="auto", choices=["auto", "txt", "ocr"], help="auto=文字优先/ocr=强制OCR")
    ap.add_argument("--lang", default=None, help="OCR 语言（如 ch）")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    if not pdf.is_file():
        print(f"错误：{pdf} 不存在", file=sys.stderr)
        return 1

    print(f"[1/2] 提取 {pdf.name} ...")
    product_dir = mineru_client.extract(pdf, Path(args.out), method=args.method, lang=args.lang)

    print("[2/2] 统计产物 ...")
    st = mineru_client.stats(product_dir)
    print(f"完成 → {product_dir}")
    print(f"  正文 {st['text']} / 表格 {st['table']} / 公式 {st['equation']} / 图 {st['image']} / 图表 {st['chart']}")
    if st["failed_tables"]:
        print(f"  ⚠️ 表格提取失败 {len(st['failed_tables'])} 个（页码 {st['failed_tables']}），需据图补全")
    return 0


if __name__ == "__main__":
    sys.exit(main())
