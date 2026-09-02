# module-development-scheduler

独立的模块开发路由 skill。它解决“当前任务该走哪条 Matt 路径、要加载哪些领域规范、哪些检查是前置条件”，不负责实现算法或写报告。

## 设计边界

- 人类入口仍是 `$develop-module`；调度器作为内部 adapter 使用；
- Matt executor 是唯一生命周期 owner；
- `module-development-scheduler`、`bio-code-standard` 和 `bio-report-writing` 可以独立发布、独立调用；`develop-module` 只负责组合；
- 路由结果是 JSON，便于 AI、人类和外部编排器复核；
- 新模块的公开业务结果默认由领域 adapter 写入平铺的 `result/` 根目录；调度器只记录该选择，不替领域命名文件；
- 缺少 SPEC、权限、模块身份或必要证据时输出 `BLOCKED`，不猜测。

## 命令

```bash
python scripts/module_scheduler.py route --module demo --task-type new --phase scope
python scripts/module_scheduler.py validate route_plan.json --json
```

`--changed-path` 可以重复。优先提供 `--work-kind code|report|both|review`；未提供时才根据路径做保守推断。`new`、`migrate`、`optimize`、`substantial_change` 默认加载 code adapter，即使没有路径。报告上下文可选 `one-off` 或 `module-reusable`，两者检查完全相同。

## 输出字段

```json
{
  "schema_version": "0.1.0",
  "module": "demo",
  "task_type": "new",
  "work_kind": "both",
  "report_context": "module_reusable",
  "quality_profile": "draft",
  "effort_profile": "mechanical",
  "max_repair_rounds": 2,
  "max_checkpoint_rounds": 1,
  "max_regression_rounds": 0,
  "repair_round": 0,
  "checkpoint_round": 0,
  "regression_round": 0,
  "route": "ask-matt",
  "phase": "scope",
  "entry_skill": "develop-module",
  "owner": "matt-executor",
  "adapter_skills": ["module-development-scheduler", "bio-code-standard", "bio-report-writing"],
  "loaded_skills": ["module-development-scheduler", "bio-code-standard", "bio-report-writing"],
  "execution_order": ["source_review", "analysis_coder", "report_coder"],
  "coder_order": ["analysis_coder", "report_coder"],
  "finish_policy": {"requires_review": false, "requires_full": false},
  "development_plan": {"path": "MODULE/docs/development-plan.md", "phase": "start"},
  "required_checks": ["module_identity", "scope_review", "source_review", "code_contract"],
  "blocked_reasons": [],
  "next_owner": "matt-executor"
}
```

来源与独立发布说明见 [NOTICE.md](NOTICE.md)。
