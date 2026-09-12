"""verify.py — 质量门禁：检查 MinerU 提取产物的完整性 + 格式门禁。

检查规则：
- 产物完整性：md / content_list.json / middle.json / model.json / images 缺一即 fail
- 表格提取失败：content_list 里 table 无 img_path 的（需据图补全）
- 页丢失：middle.json 的 pdf_info 页数 vs 预期页数（可选）
用法：
    python verify.py <产物目录> [--expect-pages N]
退出码：0 = 通过，1 = 有缺口。
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
    ap = argparse.ArgumentParser(description="提取质量门禁：产物完整性 + 表格/公式统计")
    ap.add_argument("product_dir", help="产物目录 <out>/<pdf_stem>/<method>/")
    ap.add_argument("--expect-pages", type=int, default=None, help="预期页数（漏页检查）")
    args = ap.parse_args()

    pd = Path(args.product_dir)
    if not pd.is_dir():
        print(f"错误：{pd} 不存在", file=sys.stderr)
        return 1

    products = mineru_client.parse_products(pd)
    issues = []
    for key, label in [("md", "markdown"), ("content_list", "content_list.json"),
                       ("middle", "middle.json"), ("model", "model.json")]:
        if products[key] is None:
            issues.append(f"缺产物：{label}")
    if not products["images"]:
        issues.append("缺图片（images/ 为空）")

    st = mineru_client.stats(pd)
    if st["failed_tables"]:
        issues.append(f"表格提取失败 {len(st['failed_tables'])} 个（页码 {st['failed_tables']}），需据图补全")

    if args.expect_pages is not None:
        actual_pages = len(st["types"])  # 用 content_list 元素数粗略判断，middle.json 更准
        # 精确页数从 middle.json 的 pdf_info 取
        if products["middle"]:
            import json
            middle = json.loads(products["middle"].read_text(encoding="utf-8"))
            actual_pages = len(middle.get("pdf_info", []))
            if actual_pages < args.expect_pages:
                issues.append(f"漏页：middle.json 只 {actual_pages} 页，预期 {args.expect_pages}")

    if issues:
        for i in issues:
            print(f"X {i}")
        print(f"  统计：正文 {st['text']} / 表格 {st['table']} / 公式 {st['equation']} / 图 {st['image']}")
        return 1

    print(f"OK 产物完整：正文 {st['text']} / 表格 {st['table']} / 公式 {st['equation']} / 图 {st['image']} / 图表 {st['chart']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
