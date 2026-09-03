# 诊断格式

renderer、报告合同检查和 DOCX 检查共用诊断对象：`code`、`severity`、`message`、`subject`、`evidence`、
`supportedFixes`。诊断必须指出一个可修复的模板、slot、来源、媒体或样式对象；不要用泛化建议替代失败事实。

## 常用阻断代码

| code | 触发 |
|---|---|
| `TEMPLATE_SLOT_MISSING` | 必需 bookmark/marker 或固定章节不存在 |
| `SLOT_SOURCE_UNBOUND` | 动态值没有唯一 evidence/provenance 来源 |
| `EVIDENCE_MISSING` | 必需事实、路径、版本或引用不可复核 |
| `NOTE_STYLE_INVALID` | Note 缺框体/标签，或三色不是 `#5B9BD5/#DDEBF7/#2F75B5` |
| `FIGURE_SEMANTICS_MISSING` | caption 缺对象、方向、轴/单位、编码、n、阈值或边界 |
| `FIGURE_GEOMETRY_INVALID` | 裁剪、分幅、拉伸、邻接或宽高比超过 0.1% |
| `TABLE_CONTRACT_INVALID` | 列/行/单位/精度/表头分页或输出消费者不符合合同 |
| `VISIBLE_ENGINEERING_FIELD` | 正文出现 run ID、hash、cache、日志、QA 或治理字段 |
| `NON_DECLARATIVE_TEXT` | 标题/正文出现问句、任务句、marker、占位或过强断言 |

草稿缺口使用 `DRAFT`/`EVIDENCE_NEEDED` 并返回非零；`--final`/`release` 将同一缺口升级为 error/`BLOCKED`。
修复只触及诊断的 `subject`，不让通用 scaffold 自行改写正文。
