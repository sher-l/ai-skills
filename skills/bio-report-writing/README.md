# bio-report-writing

这是一个报告 coder skill：帮助开发者把模块的已发布结果做成可重复的 reader-facing
报告 renderer。正式入口属于模块自己的 `report`/`full` 命令；本目录的 Python 工具只做
草稿、结构预检和小型演示，不替代模块 renderer。

## 模块模式

最小目录：

```text
MODULE/
├── report_templates/
│   ├── report_template.qmd   # 固定章节/句式；只声明 params slot
│   └── reference.docx        # Word 样式，不承载运行事实
└── scripts/report/
    └── generate_report.R|py  # 唯一正式 renderer
```

renderer 从指定成功运行的 `result/`、图件和 provenance 组装显式参数，检查路径、类型、
方向、单位和适用条件，然后调用 Quarto/R Markdown 或 Python 文档渲染。它不重算统计，
不从配置、日志或文件名猜数字，不让语言模型在每次运行临场改正文。固定 prose 留在模板，
动态事实留在 typed slot；详情见 [slot-contract.md](references/slot-contract.md)。

DEGs 可作为正例：

```text
DEGs/report_templates/report_template.qmd
DEGs/report_templates/reference.docx
DEGs/scripts/report/generate_report.R
```

该 renderer 先验证 calculation/plot provenance 和 `01.DEG_all.csv`、`01.DEG_sig.csv`，
再把真实 PNG 复制到隔离渲染目录，显式传入阈值、比较方向、颜色语义、表格行和版本，
最后检查 DOCX 图题/图注与输出文件表。不要把 generic key-value skeleton 当作此模式的实现。

## 一次性模式

给定材料（表、图、方法和来源）时，复制 `assets/portable_report_template.qmd`、
`assets/report-style-reference.docx`、`assets/report_slots.example.json`、
`assets/material_manifest.example.json` 与一个 R/Python renderer
示例到独立工作目录；绑定同一
slot contract（将样式文件按模板要求命名为 `reference.docx`），运行一次并交付。一次性模式不改模块源码、不写回输入，缺材料返回
`DRAFT`/`EVIDENCE_NEEDED`，不会补猜。生命周期不同，正文、图注、表格和验收标准完全相同；
见 [one-off.md](references/one-off.md)。

## 快速检查

```bash
# 仅草稿/结构预览；输出明确为 DRAFT/EVIDENCE_NEEDED（退出码非 0），不是正式报告
python .agents/skills/bio-report-writing/scripts/bio_report.py run \
  --evidence-pack ./analysis_evidence_pack.json --output-dir ./report-work --root .

# 模块 renderer 产出正式 DOCX 后
python .agents/skills/bio-report-writing/scripts/validate_report_contract.py \
  --plan ./report-work/report_plan.json --evidence-pack ./analysis_evidence_pack.json \
  --markdown ./report-work/report_draft.md --root . --final
python .agents/skills/bio-report-writing/scripts/validate_docx_structure.py \
  ./result/report/MODULE_report.docx --final
```

新建/重写模块使用 `result_layout=flat` 的 `result/` 单层编号文件；迁移旧模块先完成路径迁移审定。机器门只证明结构/证据条件；正式交付还要在目标阅读器逐页检查 DOCX，并抽查最终显示尺寸
下的 standalone PNG/PDF。规则和示例按需加载：

- [slot-contract.md](references/slot-contract.md)：固定 prose、动态 slot、条件产物与 evidence 映射；
- [renderer-examples.md](references/renderer-examples.md)：R/Python `generate_report` 最小模式（也可复制 `assets/generate_report.R.example` / `.py.example`）；
- [degs-example.md](references/degs-example.md)：DEGs 模板、参数、图注和隔离渲染拆解；
- [figure-contract.md](references/figure-contract.md)：真实图件、表格、no-crop 和 DOCX 关系；
- [acceptance.md](references/acceptance.md)：机器门、视觉门、状态和 receipt；
- [analysis-evidence-pack.md](references/analysis-evidence-pack.md)：v0.1.0 证据字段。

`draft`/`release` 是证据状态，不是审计等级：只有 `release` 且所有门通过才可写 `PASS`。
