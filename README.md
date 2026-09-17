# 残月（文档提取工作流）

把「文档提取」固化成可复用工作流：MinerU 引擎外部引用（黑盒 subprocess 调），脚本管机械（提取/门禁），agent 管理解（据图补全）。

## 快速开始

前置条件：Python 3.12、conda（或 venv）。

```bash
# 1. 装 MinerU 引擎（独立环境）
conda create -n mineru python=3.12 pip
conda activate mineru
pip install "mineru[pipeline]" six

# 2. 下载模型（约 2.5G）
mineru-models-download -s modelscope -m pipeline

# 3. 配环境变量
export MINERU_BIN=/path/to/mineru              # 指向 mineru 可执行文件
export MINERU_MODEL_SOURCE=modelscope           # 国内源；海外可设 huggingface

# 4. 提取
python skills/extract/scripts/extract.py <pdf> --out <dir>
```

## 架构：1 skill + 1 agent + 8 script

| 层 | 文件 | 职责 |
|---|---|---|
| 引擎适配 | `scripts/mineru_client.py` | subprocess 调 mineru CLI + 产物解析 + 统计 |
| 提取脚本 | `scripts/extract.py` | PDF→md+content_list.json+版面图 |
| 质量门禁 | `scripts/verify.py` | 完整性 + 表格失败 + 漏页 |
| 格式门禁 | `scripts/verify_format.py` | 公式 LaTeX 保留 + 表格空 body/乱码 + 页丢失 |
| 结构映射 | `scripts/structure_scan.py` | 扫 content_list.json 标题层级出「章节→页」清单 |
| 参数扫描 | `scripts/param_scan.py` | 扫 content_list.json 出参数映射表候选 + 图-only 表 |
| 分层索引 | `scripts/build_index.py` | 生成 data_structure.md（根+子索引，渐进式披露） |
| 切块 | `scripts/chunk.py` | 笔记→chunk（每篇 1 chunk，超长按 ## 节拆） |
| 整理代理 | `agents/extract-organizer.md` | 结构划分 + 据图补全 + 保留公式 + 参数映射表/流程引导 |
| skill 入口 | `SKILL.md` | 提取→验证→格式门禁→结构映射→参数扫描→整理→分层索引→切块 |

## 依赖（引擎外部引用，不粘代码）

- MinerU（`mineru[pipeline]` 环境）：`MINERU_BIN` 指向 mineru 可执行文件，`MINERU_MODEL_SOURCE=modelscope`
- 配置：可选 `MINERU_TOOLS_CONFIG_JSON`，默认用 `~/.mineru.json`
- 模型：`mineru-models-download -s modelscope -m pipeline`（layout/公式/OCR/表格 7 模型）

## 用法

```bash
python skills/extract/scripts/extract.py <pdf> --out <dir>
python skills/extract/scripts/verify.py <产物目录> --expect-pages N
python skills/extract/scripts/verify_format.py <产物目录> --expect-pages N
python skills/extract/scripts/structure_scan.py <产物目录>
python skills/extract/scripts/param_scan.py <产物目录>
# 整理（派子代理，prompt = agents/extract-organizer.md，框架无关）
python skills/extract/scripts/build_index.py <vault_dir> --subdirs <领域目录>
python skills/extract/scripts/chunk.py <vault_dir> --subdirs <领域目录>
```

## 说明

- MinerU 引擎与模型是外部依赖，按「快速开始」安装后设 `MINERU_BIN` 即可。
- 产物三层（markdown 正文 / JSON 结构化 / 版面图），工作流强制完整利用 JSON 层，不降级成纯 markdown。
