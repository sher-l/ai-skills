# Slot contract：模板锚点与事实映射

报告模板是稳定的程序接口，不是每次运行重新写作的提示词。**固定 prose 由 coder 写一次，动态事实由
renderer 按 typed slot 填入。**字段名、类型、来源、条件和空值策略必须在模板与 renderer 中同时一致。

## 固定 prose 与动态 slot

| 层 | 位置 | 允许内容 |
|---|---|---|
| 固定 prose | `report_template.docx` 的章节/标签/脚注，或 legacy QMD/Rmd | 章节顺序、方法解释句、结论边界、引用顺序、Note 固定句式、表/图标题格式 |
| 动态 slot | renderer 参数、`analysis_evidence_pack`、provenance | 项目名、对象、n、分组/方向、阈值、效应量/P/FDR、版本、路径、caption 字段、表行 |

固定 prose 不从 evidence pack 任意遍历生成；renderer 不临场改句式。一个 slot 只能有一个权威来源，
来源冲突即 `BLOCKED`。

## DOCX-first 锚点（新模块默认）

`report_template.docx` 预置以下稳定锚点。锚点使用 bookmark，并保留同名 `[[...]]` marker 作为可移植
后备；同一模块的 renderer 必须按锚点填充，不按段落序号猜位置。marker 不能原样交付。

| 锚点 | canonical slot | 类型 | 来源 | 条件/空值策略 |
|---|---|---|---|---|
| `REPORT_TITLE` / `[[REPORT_TITLE]]` | `report.title` | string | `pack.title` 或批准项目标题 | 必需；缺失 `EVIDENCE_NEEDED` |
| `REPORT_AUDIENCE` / `[[REPORT_AUDIENCE]]` | `report.audience` | string | Gate 1 `audience` | 必需；不写“所有人” |
| `REPORT_SUMMARY` / `[[REPORT_SUMMARY]]` | `report.summary` | string | 固定 prose + 已确认结果 | 必需；不新增事实 |
| `ANALYSIS_SCOPE` / `[[ANALYSIS_SCOPE]]` | `analysis.scope` | string/object | `point.scope`, inputs, statistical unit | 必需 |
| `ANALYSIS_METHOD` / `[[ANALYSIS_METHOD]]` | `analysis.method` | object/text | `point.method`, parameters, comparison | 必需；版本/方向缺失阻断 |
| `ANALYSIS_QC` / `[[ANALYSIS_QC]]` | `analysis.qc` | string/rows | `point.qc`、结构化 QC | 无事实时删整节；不写空占位 |
| `ANALYSIS_RESULT` / `[[ANALYSIS_RESULT]]` | `analysis.result` | ordered prose/rows | `point.results`, interpretation | 必需；按固定结果段顺序 |
| `ANALYSIS_CONCLUSION` / `[[ANALYSIS_CONCLUSION]]` | `analysis.conclusion` | string | 已发布结果 + interpretation level | 必需；不引入新数字 |
| `ANALYSIS_LIMITATIONS` / `[[ANALYSIS_LIMITATIONS]]` | `analysis.limitations` | string[] | `point.limitations` | 必需；具体到受影响结论 |
| `NOTE:DIRECTION` / `[[NOTE:DIRECTION]]` | `notes[]` | ordered objects | comparison/units/plot provenance | 仅关键误读风险时出现；无则删整块 |
| `slot_table_results_caption` / `[[TABLE:RESULTS.CAPTION]]` | `result_table` | typed table | 公开结果表/显式 rows | target 需要时出现；长表按合同预览 |
| `FIGURE:F1.SOURCE` / `[[FIGURE:F1.SOURCE]]` | `figure.F1.source` | relative path | published PNG/PDF + plot provenance | 当前产物存在时出现；缺失即省略或阻断 |
| `FIGURE:F1.CAPTION` / `[[FIGURE:F1.CAPTION]]` | `figure.F1.caption` | declarative text | fixed caption builder | 与 source 成对出现 |
| `slot_table_outputs_caption` / `[[TABLE:OUTPUTS.CAPTION]]` | `output_table[]` | typed rows | 当前发布树 + consumers | 必须列所有公开业务文件 |
| `REFERENCES` / `[[REFERENCES]]` | `report.references` | typed rows | 实际术语/方法/资源来源 | 正文实际引用闭合 |
| `slot_table_versions_caption` / `[[TABLE:VERSIONS.CAPTION]]` | `version_table[]` | typed rows | calculation/plot/report provenance | 必须存在且是最后可见块 |

## 动态字段形状

### `notes[]`

每项至少有 `id`、`title`、`text`、`kind`、`border`、`fill`、`label_color`。`kind` 取
`direction`、`unit`、`boundary` 或 `interpretation`；`text` 只陈述实际口径。
默认三色为 `border=#5B9BD5`、`fill=#DDEBF7`、`label_color=#2F75B5`。renderer 应把颜色写入
模板样式/OOXML，不把十六进制值写入可见正文；无色打印仍必须有标签和完整文字。
模板至少预置方向 Note；需要单位、边界或解释 Note 时，复制同一独立框体并使用稳定的
`[[NOTE:<KIND>]]` marker/对应 bookmark，按首次相关结果顺序渲染。

### `result_table`

至少定义 `caption`、`columns`、`rows`、`align`、`source`。每列声明显示名、单位、精度和语义；行顺序
来自公开结果，不由模型排序。只展示回答 evidence target 所需的最小内容；完整表作为公开文件列入
`output_table`。文本列左对齐、数值列右对齐，表头跨页重复，数据行不拆页。

### `figures[]`

每项至少有 `id`、`path`、`title`、`caption`、`caption_fields` 和 `width`。`caption_fields` 固定为：
`object`、`comparison`、`groups`、`panel`、`axes`、`units`、`encoding`、`n`、`statistics`、
`threshold`、`boundary`。caption 由固定函数组装，不能从图片 OCR 或颜色外观补齐；这些字段用于组装和校验，
不直接显示为“字段清单”或工程说明。

### `output_table[]` 与 `version_table[]`

`output_table[]` 至少有 `id`、`path`、`kind`、`description`、`purpose`、`consumers`；只列读者取得的
业务文件，报告/log/cache/hash/provenance/template/QA 不占行。PNG/PDF 属于同一逻辑图时在正文合并为
`name.png(pdf)`，磁盘上仍分别存在并分别校验。

`version_table[]` 至少有 `name`、`version`、`purpose`、`source`；列出实际软件、数据库和参考资源，
不填 `NA`、内部运行字段或色值；表格是文档最后一个可见内容块。

## 输入与空值规则

所有路径相对显式 `input_root`，拒绝绝对路径和越界 `..`；先校验 schema、文件、ID 唯一性、类型、长度、
方向、单位和适用条件，再写隔离 params/工作副本。必需 slot 缺失返回 `EVIDENCE_NEEDED` 并停止正式渲染；
条件 slot 不适用时删整个章节/图/表并在内部 receipt 记录原因；不写“暂无”“待确认”或空占位。

新 schema 使用 canonical 名称；`reader_questions`、旧 `note`/`caption_metadata` 等别名只用于迁移兼容，
renderer 输出仍统一为上述 slot。未知字段、重复 ID、隐式默认值或第二套正文模板均阻断。

## Renderer 接口完成条件

1. 接收 `input_root`、evidence/provenance、`template_dir`、`output_dir` 和显式模式；
2. 使用固定 `build_caption_*`、`make_result_table`、`make_output_table`、`make_version_table`、
   `make_note` 函数逐项组装；
3. 将模板复制到隔离目录并按锚点写入，输出目录只发布最终 DOCX/PDF；
4. 同一输入重复运行得到相同文本、顺序、样式和文件名；
5. 通过 [report-contract.md](report-contract.md) 与 [acceptance.md](acceptance.md) 的三门验收。
