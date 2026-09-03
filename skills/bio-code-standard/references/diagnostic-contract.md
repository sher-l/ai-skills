# 诊断与状态协议

每个 validator 输出 JSON：

```json
{
  "status": "PASS|EVIDENCE_NEEDED|DECISION_REQUIRED|BLOCKED",
  "errors": [],
  "warnings": [],
  "diagnostics": [{
    "code": "contract/missing-field",
    "error_type": "CONFIG_ERROR",
    "severity": "error",
    "message": "当前事实",
    "content": "当前事实",
    "subject": {"path": "..."},
    "evidence": {},
    "supportedFixes": ["只修改 subject 指向的内容"]
  }]
}
```

非 JSON 输出先打印 `错误类型`、`错误内容` 和 `修复建议`，最后打印退出码；stderr 与当前阶段日志必须同时保留这三项。
退出码固定为：`0` 成功；`1` 一般运行或输出错误；`2` 输入、配置、证据或人工决策校验失败；`3` 依赖或环境异常。退出码只是机器分支，不能代替错误类型和具体内容。混合错误按依赖/环境→输入配置证据→运行输出的优先级选择一个主退出码。
- `PASS`：仅 release/final 且所有声明检查通过，退出码 0；
- `EVIDENCE_NEEDED`：草稿、缺字段或待运行证据，退出码 2，不得推进 release；
- `DECISION_REQUIRED`：source review 的官方定义、源码行为和执行证据冲突，退出码 2，
  只返回最小决策项；
- `BLOCKED`：按具体错误类型返回 1、2 或 3，不得统一硬编码为 2。

修复循环只消费 `subject` 和 `supportedFixes`，每轮只修改一个已诊断主题，最多两轮；
没有新的证据就保持原状态。warning 不可在文本中冒充科学通过。
