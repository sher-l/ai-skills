# `analysis_evidence_pack` v0.1.0：报告事实包

报告侧复用 `bio-code-standard` 交接的事实 schema，不另造叙事 schema。pack 是事实来源，不是正文模板；
renderer 必须把字段显式映射到固定 slot，不能遍历任意 key 自动生成客户段落。

## 顶层字段

| 字段 | 用途 | 报告映射 |
|---|---|---|
| `module` | 模块身份 | 内部校验、标题上下文 |
| `quality_profile` | `draft` 或 `release` | 决定状态和门禁 |
| `result_layout` | 新建/重写固定为 `flat` | 解析 `result/` 编号文件 |
| `title` | 批准的分析标题 | `report.title` |
| `audience` | 主要读者及决策场景 | Gate 1；必要时摘要范围 |
| `terminology_sources` | 采用的术语来源 | Gate 1、参考文献/内部映射 |
| `references` | 方法、术语、数据库和资源来源 | `references`、版本表 |
| `versions` | 实际软件/资源版本 | `version_table` |
| `evidence_targets` | 陈述式交付目标 | 结果章节与覆盖矩阵 |
| `analysis_points` | 每个分析点的事实集合 | scope/method/result/figure/output/limit slots |

`terminology_sources` 是当前 schema 的可选字段；旧 `reader_questions` 仅可作为迁移别名，必须先转换为
不带问号的陈述式 `evidence_targets`，且 release pack 不得保留该旧字段。

## `analysis_points[]` 最小事实

每项至少包含：

```text
id / title / scope / inputs / method / parameters / results / outputs /
figure_table_refs / notes(适用时) / limitations / status
```

适用时再声明 `qc`、`statistical_unit`、`comparison`、`interpretation_level`、`interpretation` 和
`next_step`。报告不能从缺失字段推测默认值。

- `inputs[]`：`id/path/identity`，适用时有 kind、unit、orientation；路径相对 input root。
- `method`：至少 `name/version`，有 citation 时一并呈现。
- `comparison`：`target/reference/direction` 必须明确；若有 metric，写出
  `metric = target − reference`。
- `results[]`：`name/value/unit/source`；数字能回到真实结果表，保持原单位、精度和统计口径。
- `outputs[]`：`id/path/kind/published/purpose/consumers`；只有 `published=true` 且有消费者的业务文件
  进入公开输出表。
- `figure_table_refs[]`：唯一 `id/kind/path/caption`；图的完整 caption 字段由 renderer 从 plot provenance
  映射，不从外观猜。
- `notes[]`：适用时为 `id/title/text/kind/border/fill/label_color`；`kind` 取 `direction`、`unit`、
  `boundary` 或 `interpretation`，三色必须为 `#5B9BD5/#DDEBF7/#2F75B5`。
- `status`：`complete`、`valid_no_findings`、`evidence_missing` 或 `blocked`；release 只接受前两者。
- `interpretation_level`：`descriptive`、`association`、`prediction`、`candidate` 或 `mechanistic_hint`，
  决定正文可用的结论强度。

## 路径、状态与可复核性

renderer 先检查所有相对路径存在且未越过 input root，再写隔离工作目录；正式 `result/` 只保留当前合同
声明的编号业务文件，例如 `01.DEG_all.csv`、`01.DEG_sig.csv`、`02.volcano.png`、`02.volcano.pdf`。
报告不创建无消费者的 filtered/top/gene-list 副本，也不把报告、日志、cache、hash 或 provenance 当作
业务输出。

`evidence_missing` 允许初始化草稿，但机器门必须返回 `DRAFT`/`EVIDENCE_NEEDED` 和非零；
`valid_no_findings` 保持成功状态，按 [report-contract.md](report-contract.md) 的空结果分支渲染，不生成
假图、假行或候选。Schema 与示例位于 `assets/analysis_evidence_pack.schema.json` 和
`assets/analysis_evidence_pack.example.json`。
