# analysis_evidence_pack v0.1.0

这是 code coder 与 report coder 共用的事实交接包。它属于开发/验收控制面，不是配置文件、报告模板或公开
业务产物；正式运行事实仍写入 `log/run_record.json`，pack 不能放入 `result/`。

## 顶层字段

必须有：

```text
schema_version / module / quality_profile / result_layout / evidence_targets / analysis_points
```

其中 `result_layout` 在 v2.2 固定为 `flat`，`evidence_targets` 使用陈述式标题并映射
`analysis_point_ids`。可选字段为 `title`、`audience`、`terminology_sources`、`references`、
`versions`、`notes`、`result_table`、`output_table`、`version_table`。

## analysis_points[]

每项至少记录：

```text
id / title / scope / inputs / method / parameters / results / outputs /
figure_table_refs / limitations / status
```

适用时增加 `qc`、`statistical_unit`、`comparison`、`interpretation_level`、
`interpretation`、`next_step` 和 `notes`。

- `inputs[]`：`id/path/identity`，以及适用的类型、单位、方向；路径相对模块根。
- `method`：实际方法和版本，适用时带引用；不能用软件宣传文字替代执行事实。
- `comparison`：有向比较必须写 `target/reference/direction`，并明确 `metric = target − reference`。
- `results[]`：`name/value/unit/source`；数字、精度和统计口径能回到实际结果表。
- `outputs[]`：`id/path/kind/published/purpose/consumers`；只有有消费者的业务文件进入报告。
- `figure_table_refs[]`：`id/kind/path/caption`；图注字段来自 plot provenance，不能从图片外观猜。
- `notes[]`：仅在真实方向、单位/变换或边界易被误读时记录 `id/title/text/kind`；不写泛化占位。
- `status`：`complete`、`valid_no_findings`、`evidence_missing` 或 `blocked`。
  release 只接受前两者；`valid_no_findings` 可保留合同要求的表头空表，但不生成假图或假行。
- `interpretation_level`：`descriptive`、`association`、`prediction`、`candidate` 或
  `mechanistic_hint`，限制可见结论强度。

## 路径与交接

renderer 先校验 Schema、相对路径、文件存在性、ID、方向、单位和 provenance，再写隔离工作副本。
v2.2 公开结果示例为 `result/01.DEG_all.csv`、`result/01.DEG_sig.csv`、
`result/02.volcano.png`、`result/02.volcano.pdf`；同一逻辑图多格式并列，不创建无消费者的
filtered/top/gene-list 副本。

官方 URL/DOI 只保存在 source review、references 或内部交接中，不自动写入正文。旧
`reader_questions` 只能在迁移输入中出现，必须先转换成陈述式 target；无法安全转换就阻断。
