"""mineru_client.py — MinerU 引擎调用封装（外部引用，不粘源码）。

MinerU CLI 是外部引擎（mineru[pipeline] 环境），通过 MINERU_BIN 定位。
产物结构：<output>/<pdf_stem>/<method>/{*.md, *_content_list.json, *_middle.json, *_model.json, images/*}
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

MINERU_BIN = os.environ.get("MINERU_BIN", r"D:\Anaconda\envs\mineru\Scripts\mineru.exe")
# 国内模型源（无需代理），海外可设 huggingface
DEFAULT_MODEL_SOURCE = os.environ.get("MINERU_MODEL_SOURCE", "modelscope")
# MinerU 配置（元能力文件夹，不依赖 C 盘 ~/.mineru.json）
MINERU_CONFIG = os.environ.get("MINERU_TOOLS_CONFIG_JSON", r"E:\agentic_src\元能力\mineru.json")


def _check_bin():
    if not os.path.isfile(MINERU_BIN):
        raise RuntimeError(f"引擎缺失：{MINERU_BIN} 不存在，请设置 MINERU_BIN 指向 mineru.exe")


def extract(pdf: Path, output_dir: Path, method: str = "auto", backend: str = "pipeline",
            lang: str | None = None) -> Path:
    """调 MinerU 提取一个 PDF，返回产物目录 <output>/<pdf_stem>/<method>/。

    method: auto（文字优先）/ txt（纯文字）/ ocr（强制 OCR）
    backend: pipeline（默认）/ vlm
    """
    _check_bin()
    cmd = [MINERU_BIN, "-p", str(pdf), "-o", str(output_dir), "-b", backend, "-m", method]
    if lang:
        cmd += ["-l", lang]
    env = dict(os.environ)
    env.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    env.setdefault("MINERU_MODEL_SOURCE", DEFAULT_MODEL_SOURCE)
    env.setdefault("MINERU_TOOLS_CONFIG_JSON", MINERU_CONFIG)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    product_dir = output_dir / pdf.stem / method
    if p.returncode != 0 or not (product_dir / f"{pdf.stem}.md").exists():
        raise RuntimeError(f"提取失败：{pdf}\nstdout={p.stdout[-500:]}\nstderr={p.stderr[-500:]}")
    return product_dir


def parse_products(product_dir: Path) -> dict:
    """解析产物目录，返回 {md, content_list, content_list_v2, middle, model, images: [Path], n_images}。"""
    stem = product_dir.parent.name
    def _f(suffix):
        p = product_dir / f"{stem}{suffix}"
        return p if p.exists() else None
    images = sorted((product_dir / "images").glob("*.jpg")) if (product_dir / "images").is_dir() else []
    return {
        "md": _f(".md"),
        "content_list": _f("_content_list.json"),
        "content_list_v2": _f("_content_list_v2.json"),
        "middle": _f("_middle.json"),
        "model": _f("_model.json"),
        "images": images,
        "n_images": len(images),
    }


def load_content_list(product_dir: Path) -> list[dict]:
    """读 content_list.json，返回元素列表（type/text_level/bbox/page_idx）。"""
    stem = product_dir.parent.name
    p = product_dir / f"{stem}_content_list.json"
    if not p.exists():
        raise FileNotFoundError(f"缺 content_list.json：{p}")
    return json.loads(p.read_text(encoding="utf-8"))


def stats(product_dir: Path) -> dict:
    """统计产物：正文/标题/表格/公式/图片数量（质量门禁用）。"""
    cl = load_content_list(product_dir)
    from collections import Counter
    types = Counter(x.get("type") for x in cl)
    failed_tables = [x for x in cl if x.get("type") == "table" and not x.get("img_path")]
    return {
        "total": len(cl),
        "types": dict(types),
        "text": types.get("text", 0),
        "table": types.get("table", 0),
        "equation": types.get("equation", 0),
        "image": types.get("image", 0),
        "chart": types.get("chart", 0),
        "failed_tables": [x.get("page_idx") for x in failed_tables],
    }


def download_models(source: str = "modelscope", model_type: str = "pipeline"):
    """下载 MinerU 模型（pipeline 含 layout/公式/OCR/表格 7 个模型）。"""
    _check_bin()
    dl_bin = str(Path(MINERU_BIN).parent / "mineru-models-download.exe")
    env = dict(os.environ)
    env.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    subprocess.run([dl_bin, "-s", source, "-m", model_type], env=env, check=True)
