# Matt 集成边界

上游路线：

```text
ask-matt → grill/to-spec → SPEC READY
                         ↘ execute-spec-in-fork → spec-executor
                          ↘ to-tickets → to-goal → executor
```

本 skill 只生成输入和领域加载计划。route plan 的 `owner` 始终是 Matt
executor；`adapter_skills` 只列 scheduler、code 和 report 三个 leaf skill，
不把 `develop-module` 或 `matt-executor` 当 adapter。Matt 负责会话、任务顺序、
Messenger、review 调度、自动 commit 和 receipt。没有原生 Fork harness 时，使用
上游 documented manual fallback，不模拟新的权限系统。

当 `coder_order` 同时包含 `analysis_coder` 和 `report_coder` 时，报告 coder
只能消费分析 coder 已签发的 evidence pack；one-off 与 module-reusable report
context 使用同一检查集合。`execution_scope=plot` 时改由 `plot_coder` 产出图件
证据，`report_coder` 仍只能消费其已发布结果；`report-only` 不启动 code coder。

建议保存上游 URL、固定版本和本地适配差异；升级时先验证路由输出，再更新适配器。领域 skill 的科学验收和报告验收不能由 receipt 单独替代。
