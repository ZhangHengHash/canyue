---
name: extract
description: Use when 处理 PDF/扫描件/图片/Office 文档、需要转 markdown 或知识库、提取公式 LaTeX、识别表格结构、切割版面图、据图补全失败表格、提炼参数映射表。触发：PDF 提取、扫描件 OCR、文档转知识库、MinerU、公式表格提取、据图补全、参数表提炼。
---

# 文档提取工作流（extract）

> **全流程**：提取（extract）→ 验证（verify）→ 结构映射（structure_scan）→ 参数扫描（param_scan）→ 整理进库（organizer）→ 沉淀。
> 脚本在 `scripts/`，引擎 MinerU 外部引用（`MINERU_BIN` 指向 mineru.exe）。
> **脚本管机械，agent 管理解**——结构划分、据图补全、参数提炼、规范整理必须 LLM 亲自做，不许脚本代劳。

## 流程（脚本 ↔ 代理分工）

| 步 | 动作 | 谁做 | 命令 |
|---|---|---|---|
| 1 提取 | MinerU 提 PDF → md+JSON+版面图 | 脚本 | `python scripts/extract.py <pdf> --out <dir>` |
| 2 验证 | 产物完整性 + 表格失败 + 漏页门禁 | 脚本 | `python scripts/verify.py <产物目录> --expect-pages N` |
| 3 结构映射 | 扫标题层级出「章节→页」结构清单 | 脚本 | `python scripts/structure_scan.py <产物目录>` |
| 4 参数扫描 | 扫出参数映射表候选 + 图-only 表 | 脚本 | `python scripts/param_scan.py <产物目录>` |
| 5 整理 | 写笔记 + 据图补全 + 保留公式 + 参数映射表/流程引导 | 代理 | `dispatch agents/extract-organizer.md` |
| 6 沉淀 | 建索引 + git 提交 | 脚本/代理 | 按知识库规范 |

## 依赖

- **引擎**：MinerU（`mineru[pipeline]` 环境），`MINERU_BIN` 指向 `mineru.exe`，`MINERU_MODEL_SOURCE=modelscope`（国内源）。
- **配置**：`MINERU_TOOLS_CONFIG_JSON` 指向 `E:\agentic_src\元能力\mineru.json`（元能力文件夹统一配置，不依赖 C 盘 `~/.mineru.json`）。
- **模型**：`mineru-models-download -s modelscope -m pipeline`（layout/公式/OCR/表格 7 个模型）。

## 铁律

1. 脚本是机械骨架，理解（结构划分、据图补全、参数提炼、规范整理）必须 LLM/代理亲自做。
2. **质量门禁**：verify.py 不过不许收尾；失败表格必须「据图补全」，公式 LaTeX 必须保留。
3. **参数表必须「提炼映射表」**：MinerU 把参数表切成 image，param_scan.py 扫出候选，organizer 提炼成「输入输出参数映射表」（参数名/中文含义/单位/输入来源/输出用途），不能只嵌图。
4. **结构映射用 structure_scan.py**：扫 content_list.json 标题层级出「章节→页」清单，供 organizer 拆分笔记；**禁止再用 pypdf 等外部代码做结构映射**。运行页眉（频次>2）自动过滤，剩余噪声由 organizer 判断。
5. **引擎外部引用不粘代码**：MinerU 是黑盒 subprocess 调（源码验证：backend↔model 互相耦合，无法拆出单独复用）。
6. **完整利用产物**：content_list.json（bbox/text_level/page_idx）是结构化层，别只用 markdown。

## 参考

- MinerU 源码理解：`E:\AI-KB\03_提取工作流\`（见 extract skill 沉淀笔记）
- 晓风（对标架构）：`E:\AI-KB\02_项目\16_源码理解插件.md`
