# analysis_evidence_pack v0.1 handoff

这是 code 与 report adapter 之间的共享机器协议，不是运行时配置，也不是报告模板。
代码层只写已经执行并能回溯的事实；报告层可在自己的合同中组织章节和自然语言。

## 最小字段

```json
{
  "schema_version": "0.1.0",
  "module": "example",
  "quality_profile": "draft",
  "result_layout": "flat",
  "evidence_targets": [{"id": "ET-01", "title": "声明式分析目标"}],
  "analysis_points": [{
    "id": "AP-01",
    "title": "声明式分析主题",
    "scope": "数据与对象范围",
    "qc": "输入和质量控制事实",
    "inputs": [{"id": "IN-01", "path": "input/input.tsv", "identity": "dataset-id"}],
    "method": {"name": "method", "version": "1.0", "citation": "official source"},
    "parameters": {"threshold": "actual expression"},
    "statistical_unit": "sample",
    "comparison": {"target": "case", "reference": "control", "metric": "effect", "direction": "case - control"},
    "results": [{"name": "n", "value": 1, "unit": "item", "source": "result/01.result.csv"}],
    "outputs": [{"id": "OUT-01", "path": "result/01.result.csv", "kind": "table", "published": true}],
    "figure_table_refs": [],
    "interpretation_level": "descriptive",
    "interpretation": "仅写已执行数据支持的事实",
    "next_step": "明确的后续验证",
    "limitations": ["本次数据范围"],
    "status": "complete"
  }]
}
```

新建或重写模块的 `result_layout` 固定为 `flat`，要求 `result/` 单层编号路径。
迁移旧模块时可在审定记录中登记既有 `module_contract` 路径，但不能把它当作新输出的
另一套默认。`status` 使用 `complete`、`valid_no_findings`、
`evidence_missing` 或 `blocked`；后两者可在 draft 暴露缺口，但 final 必须阻断。

每个结果项带 `name/value/unit/source`，每个输出项带 `id/path/kind/published/purpose/consumers`，路径相对
模块根且指向真实产物。`qc`、`statistical_unit`、`comparison` 和解释字段只在该分析
适用时声明；一旦声明就必须完整且可核对。`references`/`versions` 使用
`{name, version, source?, purpose?}`，并与 source review 中的官方资料和实际环境一致。

不要在 pack 中写读者问句、任务句、占位符、因果/疗效结论或未执行数字；这些是报告
适配器和科学负责人另行处理的内容。代码 validator 不替报告 validator 做章节或 DOCX 检查。
