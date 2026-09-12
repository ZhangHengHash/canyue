# 残月（文档提取元能力工作流）

> 「杨柳岸，晓风残月」——与晓风（源码理解）配套的元能力。拂晓的风散代码迷雾，残月照亮文档结构。

把「文档提取」固化成元能力工作流：MinerU 引擎外部引用（黑盒 subprocess 调），脚本管机械（提取/门禁），agent 管理解（据图补全）。

## 架构：1 skill + 1 agent + 5 script

| 层 | 文件 | 职责 |
|---|---|---|
| 引擎适配 | `scripts/mineru_client.py` | subprocess 调 mineru CLI + 产物解析 + 统计 |
| 提取脚本 | `scripts/extract.py` | PDF→md+content_list.json+版面图 |
| 质量门禁 | `scripts/verify.py` | 完整性 + 表格失败 + 漏页（实测抓 8 失败表格） |
| 结构映射 | `scripts/structure_scan.py` | 扫 content_list.json 标题层级出「章节→页」清单（替代 pypdf） |
| 参数扫描 | `scripts/param_scan.py` | 扫 content_list.json 出参数映射表候选 + 图-only 表 |
| 整理代理 | `agents/extract-organizer.md` | 结构划分 + 据图补全 + 保留公式 + 参数映射表/流程引导 + 规范整理 |
| skill 入口 | `SKILL.md` | 提取→验证→结构映射→参数扫描→整理→沉淀 |

## 依赖（引擎外部引用，不粘代码）

- MinerU（`mineru[pipeline]` 环境）：`MINERU_BIN` 指向 mineru.exe，`MINERU_MODEL_SOURCE=modelscope`
- 配置：`MINERU_TOOLS_CONFIG_JSON` 指向 `E:\agentic_src\元能力\mineru.json`（元能力文件夹统一配置，不依赖 C 盘）
- 模型：`mineru-models-download -s modelscope -m pipeline`（layout/公式/OCR/表格 7 模型）

## 用法

```bash
# 提取
python scripts/extract.py <pdf> --out <dir>
# 验证（质量门禁）
python scripts/verify.py <产物目录> --expect-pages N
# 结构映射（章节→页结构清单，替代 pypdf）
python scripts/structure_scan.py <产物目录>
# 参数扫描（扫出参数映射表候选 + 图-only 表）
python scripts/param_scan.py <产物目录>
# 整理（据图补全 + 参数映射表/流程引导 + 规范笔记）
dispatch agents/extract-organizer.md
```

## 源码理解

MinerU 70,734 行 / 216 文件，8 维度 file:line 地图见 `E:\AI-KB\03_提取工作流\01_MinerU源码理解.md`。
构建方法论见 `E:\AI-KB\03_提取工作流\02_构建方法论与教训.md`。
