# Draft slot worksheet

此文件为旧工具保留的草稿入口，不是客户报告模板。正式模块请复制
`portable_report_template.qmd` 的模式，编写模块自己的固定 prose 和 renderer。

| slot | 固定位置 | 动态来源 | 缺失行为 |
|---|---|---|---|
| report.title | 文档标题 | `pack.title` | `EVIDENCE_NEEDED` |
| analysis.scope | 数据范围 | `analysis_points[].scope` | `EVIDENCE_NEEDED` |
| analysis.method | 材料与方法 | `method + parameters` | `EVIDENCE_NEEDED` |
| analysis.result | 分析结果 | `results[]` | `EVIDENCE_NEEDED` |
| figure.* | 固定 Figure slot | `figure_table_refs[]` | 条件省略或阻断 |
| table.* | 固定 Table slot | 已验证 result rows | 条件省略或阻断 |
| limitations | 解释边界 | `limitations[]` | `EVIDENCE_NEEDED` |
