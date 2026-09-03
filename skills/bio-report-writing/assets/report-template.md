# DOCX-first slot worksheet

`report_template.docx` 是默认可复制模板；`portable_report_template.qmd` 仅为兼容
旧 Quarto 入口。正式模块由自己的 renderer 替换 DOCX bookmark 和同名 `[[...]]`
标记，不能把标记原样交付。

| slot | 固定位置 | 动态来源 | 缺失行为 |
|---|---|---|---|
| report.title | 文档标题 | `pack.title` | `EVIDENCE_NEEDED` |
| analysis.scope | 数据范围 | `analysis_points[].scope` | `EVIDENCE_NEEDED` |
| analysis.method | 材料与方法 | `method + parameters` | `EVIDENCE_NEEDED` |
| analysis.result | 分析结果 | `results[]` | `EVIDENCE_NEEDED` |
| figure.* | 固定 Figure slot | `figure_table_refs[]` | 条件省略或阻断 |
| table.* | 固定 Table slot | 已验证 result rows | 条件省略或阻断 |
| limitations | 解释边界 | `limitations[]` | `EVIDENCE_NEEDED` |

## DOCX 锚点

模板中的 bookmark 是稳定机器锚点；可复制 Figure F1 的三段整组来承载 F2…Fn，
仅对已发布图件保留。表格首行为重复表头，数据行带 `cantSplit`；renderer 替换
整张表或克隆数据行，不改变章节顺序。

| 内容 | bookmark | marker |
|---|---|---|
| 标题 | `slot_report_title` | `[[REPORT_TITLE]]` |
| 读者 | `slot_report_audience` | `[[REPORT_AUDIENCE]]` |
| 摘要 | `slot_report_summary` | `[[REPORT_SUMMARY]]` |
| 数据范围 | `slot_analysis_scope` | `[[ANALYSIS_SCOPE]]` |
| 材料与方法 | `slot_analysis_method` | `[[ANALYSIS_METHOD]]` |
| 质控（适用时） | `slot_analysis_qc` | `[[ANALYSIS_QC]]` |
| 结果与解读 | `slot_analysis_result` | `[[ANALYSIS_RESULT]]` |
| 方向/单位/边界 Note | `slot_note_direction` | `[[NOTE:DIRECTION]]` |
| 结果表标题/锚点 | `slot_table_results_caption` | `[[TABLE:RESULTS.CAPTION]]` |
| 综合结论 | `slot_analysis_conclusion` | `[[ANALYSIS_CONCLUSION]]` |
| 完整源图 | `slot_figure_f1_source` | `[[FIGURE:F1.SOURCE]]` |
| 图注 | `slot_figure_f1_caption` | `[[FIGURE:F1.CAPTION]]` |
| 局限/待验证 | `slot_analysis_limitations` | `[[ANALYSIS_LIMITATIONS]]` |
| 输出文件表标题/锚点 | `slot_table_outputs_caption` | `[[TABLE:OUTPUTS.CAPTION]]` |
| 参考文献 | `slot_references` | `[[REFERENCES]]` |
| 软件/资源版本表标题/锚点 | `slot_table_versions_caption` | `[[TABLE:VERSIONS.CAPTION]]` |

Note 默认使用独立 callout table（标签行与正文行分开）：边框 `#5B9BD5`、填充 `#DDEBF7`、标签
`#2F75B5`。Figure source 不是 callout，只是透明的普通图片段落，不得带边框、底色或缩进。Note 文本必须
紧邻首次相关结果，并在去掉颜色后仍能理解；没有真实 Note 事实时删除整块。

`F1` 图块（标题→完整源图→完整图注）是可复制单元；caption 字段仅供 renderer 组装和校验，不直接显示。
仅在证据包发布对应图件时
复制为 `F2`、`F3` 等并按发布顺序编号。`notes[]` 同理只克隆 Note 整块，不为缺失口径
生成空框；无结果时保留事实支持的中性状态句并按合同省略不适用图表。
