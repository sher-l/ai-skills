# 诊断格式

renderer、报告合同检查和 DOCX 检查共用诊断对象：`code`、`severity`、`message`、
`subject`、`evidence`、`supportedFixes`。结构、视觉和证据是三个独立门；一个
维度通过不替代另外两个。

草稿缺口使用 `DRAFT`/`EVIDENCE_NEEDED` 并返回非零；`--final`/`release` 将同一缺口
升级为 error/`BLOCKED`。修复只触及诊断的 `subject`，不要让通用 scaffold 自行改写正文。
