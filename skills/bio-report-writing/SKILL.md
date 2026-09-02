---
name: bio-report-writing
description: 为 R/Python 生信项目编写机械报告 renderer、QMD/DOCX 模板、正文 slot、图题图注和结果表，并完成证据、路径与视觉验收；也用于用已给材料生成一次性报告。Use when creating a reusable module report generator or a one-off report from supplied evidence and figures.
---

# 生信报告 coder

本 skill 负责报告代码，不是把 JSON 临时拼成客户正文的 validator。正式报告由模块自己的
renderer（R/Python）读取已发布表、图和 provenance，填入固定模板；运行时不调用 AI 写作、
不重算统计、不从文件名/日志/配置猜事实。一次性报告也使用同一模板、slot 和验收合同，
区别只有交付生命周期。
开发阶段 coder 可以直接编写模块正文、图题图注和表格函数；这些内容冻结后由 renderer 机械执行。

## 先定模式

- **模块模式**：在模块内维护 `report_templates/report_template.qmd`、`reference.docx` 和
  `scripts/report/generate_report.R|py`；`report`/`full` 是正式入口，输入来自指定成功运行。
- **一次性模式**：把可移植模板、slot manifest 和给定材料放入独立工作目录，运行一次 renderer；
  不改模块源码，不把临时文件或报告自身列入业务输出。

两种模式都先读 [slot-contract.md](references/slot-contract.md)，再按需读
[renderer-examples.md](references/renderer-examples.md)、[degs-example.md](references/degs-example.md)、
[one-off.md](references/one-off.md)、[report-contract.md](references/report-contract.md) 和
[acceptance.md](references/acceptance.md)。

## 实施顺序

1. 沿 canonical report 入口追踪结果表、图件、provenance、输出根和 CWD；冻结相对路径及
   `analysis_evidence_pack`（v0.1.0）映射。完成条件：每个 slot 都有唯一 source/path。
2. 写 slot contract：固定正文（章节、句式、解释边界、引用顺序）与动态参数（数字、方向、
   阈值、版本、图/表路径、caption 数据）分离；字段有类型、单位、适用条件和缺证据状态。
3. 写 renderer：显式组装命名参数，校验长度/类型/来源，条件产物按事实省略；模板只消费参数。
   完成条件：同一输入重复运行得到同一正文、图序、表序和文件名。
4. 写 QMD/Rmd 或 Python 文档，并把 `reference.docx` 当样式输入；图用真实源文件完整等比嵌入，
   表在固定 slot 插入，图题/图注紧邻且自足。不要让通用 key-value builder 成为正式 renderer。
5. 运行 [acceptance.md](references/acceptance.md) 的机器门、目标阅读器逐页视觉门和 standalone
   PNG/PDF 抽查。`draft` 只能报告 `DRAFT`/`EVIDENCE_NEEDED`；只有证据完整的 `release` 才报告 `PASS`。

## 不变合同

- 标题、章节、图题、图注和摘要是陈述式主题；动态文本只来自已确认字段，缺失即显式缺口，不猜写。
- 每个结论绑定分析点、统计单位、比较方向、效应/显著性、阈值、限制和真实结果文件。
- 每个 Figure/Table 有稳定 ID、源路径、对象/分组/轴/单位/图例/颜色或线型、n/统计层级和阅读边界。
- 源图不裁剪、不分幅、不拉伸；DOCX 不含非零 OOXML `srcRect`，宽图通过源端或页面布局解决。
- 正文只列读者可获得的业务文件；run ID、hash、cache、日志、审核状态和报告自身留在内部记录。

## 可运行脚本的边界

`scripts/bio_report.py`、`build_report_skeleton.py` 和 `build_docx.py` 仅用于 plan/slot 草稿、
结构预检或本地演示；其输出不是模块正式报告。模块 renderer 产出正式 DOCX/PDF 后，再运行
`validate_report_contract.py` 与 `validate_docx_structure.py --final`。

完成判据：模块/一次性 renderer 可从声明输入重现固定正文和动态事实，所有机器门与视觉门均有
receipt；任一缺口保留 `DRAFT` 或 `BLOCKED`，不以通用 builder 的成功消息代替交付。

一次性计划可用 `init_report_plan.py --mode one_off` 生成；正式模块仍由模块自己的
`generate_report.R|py` 作为唯一 renderer。
