"""param_scan.py — 参数表扫描：从 content_list.json 机械扫出「输入输出参数映射表」候选。

背景：MinerU 把大量参数表切成 image 或 table。organizer 若只嵌图不提炼，参数就丢了。
本脚本机械扫出三类，供 organizer（LLM）复核后提炼成标准化参数映射表：

  1. candidate_params —— table/image 的 caption 或 body 含参数关键词的候选（最可能是参数表）
  2. image_only_tables  —— table 有 img_path 但 body 缺失/过短，需「据图补全 + 参数提炼」
  3. table_inventory / image_inventory —— 全量清单（按页码），供复核不漏

产物：<product_dir>/param_scan.json + 终端报告
用法：python param_scan.py <产物目录> [--keywords 关键词文件] [--out 输出json]
"""
from __future__ import annotations

import argparse
import html as htmlmod
import json
import re
import sys
from collections import Counter
from pathlib import Path

# 参数表关键词（中英 + SWAT 常见参数字段）。可 --keywords 覆盖。
DEFAULT_KEYWORDS = [
    "参数", "变量", "字段", "名称", "含义", "单位", "说明", "变量名", "参数名",
    "中文名", "英文名", "取值", "默认值", "输入", "输出", "来源", "用途", "范围",
    "variable", "parameter", "field", "unit", "value", "description",
    "snam", "nlayers", "hydgrp", "sol_", "userwgn", "usersoil", "crop",
    "cn2", "awc", "usle", "slsubbsn", "slope",
]

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    """去 HTML 标签 + 反转义，得到纯文本（table_body 是 HTML）。"""
    if not s:
        return ""
    return htmlmod.unescape(_TAG_RE.sub("", s)).strip()


def _to_text(v) -> str:
    """归一化 str | list[str] | None → 纯文本。caption/footnote 是 list，body/text 是 str。"""
    if v is None:
        return ""
    if isinstance(v, list):
        return " ".join(_strip_html(str(item)) for item in v if item)
    return _strip_html(str(v))


def _load_cl(product_dir: Path) -> list[dict]:
    stem = product_dir.parent.name
    p = product_dir / f"{stem}_content_list.json"
    if not p.exists():
        raise FileNotFoundError(f"缺 content_list.json：{p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _element_text(x: dict) -> str:
    """取元素的文本线索：table_body 纯文本 + caption + text + image_caption。"""
    parts = []
    for key in ("table_body", "table_caption", "image_caption", "text", "chart_body"):
        v = _to_text(x.get(key))
        if v:
            parts.append(v)
    return " ".join(parts)


def _hits_keyword(text: str, kws: list[str]) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in kws)


def scan(product_dir: Path, keywords: list[str]) -> dict:
    cl = _load_cl(product_dir)
    types = Counter(x.get("type") for x in cl)

    candidate_params = []
    image_only_tables = []
    table_inventory = []
    image_inventory = []

    for x in cl:
        typ = x.get("type")
        page = (x.get("page_idx") or 0) + 1  # 1-based 供人读
        caption = _to_text(x.get("table_caption") or x.get("image_caption"))
        body = _to_text(x.get("table_body"))
        img = x.get("img_path")

        if typ == "table":
            row = {
                "page": page,
                "caption": caption,
                "has_body": bool(body),
                "body_len": len(body),
                "has_img": bool(img),
                "img_path": img or "",
            }
            table_inventory.append(row)
            if img and len(body) < 20:  # 图-only：有切图但没提取出表格文本
                image_only_tables.append(row)
            if _hits_keyword(body + " " + caption, keywords):
                row["_hit"] = True
                candidate_params.append(row)
        elif typ == "image":
            row = {
                "page": page,
                "caption": caption,
                "img_path": img or "",
            }
            image_inventory.append(row)
            if _hits_keyword(caption, keywords):
                row["_hit"] = True
                candidate_params.append({**row, "has_body": False, "body_len": 0})

    return {
        "types": dict(types),
        "n_tables": types.get("table", 0),
        "n_images": types.get("image", 0),
        "n_candidate_params": len(candidate_params),
        "n_image_only_tables": len(image_only_tables),
        "candidate_params": candidate_params,
        "image_only_tables": image_only_tables,
        "table_inventory": table_inventory,
        "image_inventory": image_inventory,
    }


def main() -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="参数表扫描：扫 content_list.json 出参数映射表候选")
    ap.add_argument("product_dir", help="产物目录 <out>/<pdf_stem>/<method>/")
    ap.add_argument("--keywords", default=None, help="关键词文件（每行一个，覆盖默认）")
    ap.add_argument("--out", default=None, help="输出 json 路径（默认 <product_dir>/param_scan.json）")
    args = ap.parse_args()

    pd = Path(args.product_dir)
    if not pd.is_dir():
        print(f"错误：{pd} 不存在", file=sys.stderr)
        return 1

    kws = DEFAULT_KEYWORDS
    if args.keywords:
        kws = [ln.strip() for ln in Path(args.keywords).read_text(encoding="utf-8").splitlines() if ln.strip()]

    result = scan(pd, kws)

    out = Path(args.out) if args.out else (pd / "param_scan.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"参数表扫描完成 → {out}")
    print(f"  类型分布：{result['types']}")
    print(f"  表格 {result['n_tables']} / 图 {result['n_images']}")
    print(f"  ★ 候选参数表 {result['n_candidate_params']} 个（需提炼输入输出参数映射表）")
    print(f"  ⚠️ 图-only 表 {result['n_image_only_tables']} 个（需据图补全）")
    if result["candidate_params"]:
        print("\n  候选参数表（页码 → caption）：")
        for c in result["candidate_params"][:40]:
            cap = c.get("caption") or "(无标题)"
            print(f"    P{c['page']:>3} [{c.get('type', 'table')}] {cap[:50]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
