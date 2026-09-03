# 一次性材料报告

一次性模式适用于用户直接提供表格、图件、方法说明和来源，但没有要修改的模块。它仍由 report coder
先写/套用同一 DOCX 模板、再由 renderer 机械填充；不是运行时让 AI 临场写一篇报告。章节、slots、Note、图表、语言、
证据和验收与 `module_reusable` 完全相同，只有生命周期和目录不同。

## 固定步骤

1. 在独立工作目录复制 `assets/report_template.docx`、`assets/report_slots.example.json`、
   `assets/material_manifest.example.json` 和一个 R/Python renderer；模板副本保持 `report_template.docx`
   文件名。存量 QMD 只有在迁移既有模块时才保留，不能形成第二套正文。
2. 建立材料 manifest：记录每个表、图、方法、版本、单位、来源、许可、相对路径和实际消费者；把材料投影
   到同一 `analysis_evidence_pack`，不为一次性报告另造宽松正文格式。
3. 读取 [report-contract.md](report-contract.md) 和 [slot-contract.md](slot-contract.md)，将固定 prose
   写入模板锚点，将数字、方向、阈值、图注字段、结果行、公开文件行和版本行绑定到 manifest/evidence。
   缺材料字段写 `EVIDENCE_NEEDED`，不从文件名、图片或常识补齐。
4. renderer 在隔离工作目录打开模板，按锚点填充 `REPORT_TITLE`、`SUMMARY`、`SCOPE`、`METHOD`、`QC`、
   `RESULT_TEXT`、`CONCLUSION`、`NOTES`、`RESULT_TABLE`、`FIGURES`、`OUTPUT_TABLE` 和 `VERSION_TABLE`；
   只复制最终 DOCX/PDF 到 output，不回写输入或把临时文件列入业务输出。
5. 按 [acceptance.md](acceptance.md) 完成结构、证据、no-crop、三色 Note 和目标阅读器视觉验收，保存
   一次性 receipt；`DRAFT`/`EVIDENCE_NEEDED` 不是交付，缺口则 `BLOCKED`。

## 一次性目录边界

```text
one-off-work/
├── report_template.docx       # 唯一生效模板
├── generate_report.R|py       # 一次性 renderer
├── material_manifest.json     # 输入材料和来源
├── analysis_evidence_pack.json
└── output/                    # 仅最终报告和声明的公开业务文件
```

不存在模块长期入口时，不要求提交模块 renderer；仍要求固定结果段、完整图注、结果/输出/版本表、语义
Note、provenance 和 standalone PNG/PDF 抽查。一次性输出不得生成无消费者的 filtered/top/gene-list 副本。
