# 一次性材料报告

一次性模式适用于用户直接提供表格、图件、方法说明和来源，但没有要修改的模块。它不是
“让 AI 现场写一篇报告”：先建立材料 manifest，再运行与模块模式相同的 renderer/模板。

## 生命周期

1. 在独立工作目录复制 `assets/portable_report_template.qmd`、`assets/report-style-reference.docx`、
   `assets/report_slots.example.json` 和 `assets/material_manifest.example.json`，并按模板需要将样式副本命名为 `reference.docx`（或同步修改 QMD）；记录材料的相对路径、格式、单位、来源和许可。
   若使用 report plan，将 `mode` 设为 `one_off`；模块模式的正式文件必须位于 `report/`，一次性模式的输出留在独立 output 目录。
2. 将材料映射到固定 slot：正文章节/句式来自模板，数字、方向、阈值、图/表和版本来自
   manifest。无法证明的字段写 `EVIDENCE_NEEDED`，不从文件名、图片或常识补齐。
   需要机器校验时，把 manifest 的事实投影为同一 `analysis_evidence_pack` 字段；不要为一次性
   交付另造宽松的正文格式。
3. 用 `assets/generate_report.R.example` 或 `.py.example`（见
   [renderer-examples.md](renderer-examples.md)）渲染隔离工作目录；只复制最终 DOCX/PDF
   到交付目录，不回写输入。
4. 按 [acceptance.md](acceptance.md) 做结构、证据、no-crop 和目标阅读器视觉验收，保存
   一次性 receipt；`DRAFT` 不是交付，缺口则 `BLOCKED`。

## 与模块模式相同的门

一次性报告仍需陈述式标题、固定图表顺序、真实图件、完整图注、表头/单位、限制和来源闭环。
区别仅是没有 `run.sh report/full` 的长期入口，也不要求提交模块 renderer；不要因此省略
provenance、视觉检查或 standalone PNG/PDF 抽查。
