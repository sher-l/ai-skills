# analysis_evidence_pack v0.1.0

报告侧复用 `bio-code-standard` 交接的 schema，不另造一份叙事 schema。pack 是事实来源，
不是正文模板；renderer 把字段显式映射到模块 slot，不能遍历任意 key 自动生成客户段落。

顶层使用 `module`、`quality_profile`、`result_layout`（新建/重写模块固定为 `flat`）、`title`、`audience`、`references`、
`versions`、`evidence_targets` 和 `analysis_points`。每个 `analysis_points[]` 至少包含：
`id/title/scope/inputs/method/parameters/results/outputs/figure_table_refs/limitations/status`；
`qc`、`statistical_unit`、`comparison`、`interpretation_level` 和 `interpretation` 按模块适用性声明；
release 还需每个分析点的 `next_step`。

- `results[]`：`name/value/unit/source`，数字必须能回到实际结果表；
- `outputs[]`：稳定 `id/path/kind/published/purpose/consumers`，路径相对显式 input root；
- `figure_table_refs[]`：唯一 `id/kind/path/caption`，图注仍由模块固定 caption 函数组装；
- `status`：`complete`、`valid_no_findings`、`evidence_missing` 或 `blocked`；
- `interpretation_level`：`descriptive/association/prediction/candidate/mechanistic_hint`。

`evidence_missing` 允许初始化草稿，但 validator 必须报告 `DRAFT`/`EVIDENCE_NEEDED` 且非零；
release 只接受 `complete`/`valid_no_findings`，并验证所有相对路径存在且未越过 input root。
新建/重写模块的 `result_layout=flat` 要求 `result/` 根目录的编号文件名；迁移旧模块时先完成
路径现状审定和合同升级，不能把旧嵌套路径作为新 renderer 的默认。

Schema 与示例位于 `assets/analysis_evidence_pack.schema.json` 和
`assets/analysis_evidence_pack.example.json`。
