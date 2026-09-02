---
name: module-development-scheduler
description: 为生信模块开发任务生成确定的阶段路由、领域 skill 加载计划、检查清单和阻断条件，并把执行交回既有生命周期 owner。Use internally from develop-module when a module is new, migrated, optimized, substantially changed, reviewed, or needs code/report domain adapters.
---

# 模块开发调度

这是一个可独立发布的路由适配器，也是 `develop-module` 的内部工具。人只需调用 `$develop-module`；本 skill 不创建第二套 Goal、phase、commit 或 receipt。默认 `effort_profile=mechanical`，路由脚本决定检查集合，不让模型临时扩展范围。

`develop-module` 是组合入口和生命周期 owner；本 skill、`bio-code-standard`、
`bio-report-writing` 是三个可独立发布的 leaf skill。route plan 单独记录
`entry_skill`、`owner`、`adapter_skills`，不会把 owner 或组合入口递归当成 adapter。

## 路由顺序

1. 识别模块、任务类型、批准状态、当前阶段和实际变更路径。
2. 选择唯一 Matt 路径：未形成 SPEC 时回到 planning；单次 SPEC READY 走 Fork/spec-executor；跨会话 frontier 走 Goal/executor；缺少权限或决策时返回 `BLOCKED`。
3. 依据变更面加载领域适配器：源码/配置/算法/绘图加载 `bio-code-standard`；报告/图注/DOCX/结果解释加载 `bio-report-writing`；公开 full 同时加载两者。代码任务的 `source_review` 永远排在 `analysis_coder` 之前；同时有报告时 `report_coder` 在其后。
4. 输出 `route_plan.json`，包含 route、phase、development-plan 映射、quality/effort profile、round counters、leaf adapters、required_checks 和 blocked_reasons；执行、review、commit 和 receipt 仍由 Matt executor 完成。
5. 在每个 hook 只推进一个 frontier；领域 skill 返回 `PASS`、`EVIDENCE_NEEDED` 或 `BLOCKED`，调度器负责传回，不替领域做判断。

默认 `quality_profile=draft`、`effort_profile=mechanical`、`max_repair_rounds=2`；
`checkpoint_round`（范围决策）和 `regression_round`（完整复测）与
`repair_round` 分开记录。`max_regression_rounds=0` 表示不设人工上限，不是跳过回归。
只有已批准的交付阶段才把质量档位切换为 `release`；新增检查必须先进入当前 scope。
能明确判断时用 `--work-kind code|report|both|review`，`auto` 只作为缺省回退。

`mechanical` 档只按 `required_checks` 路由，不允许模型临时增加检查、文件、依赖或安全边界；
`scientific_review` 必须由 scope 明确选择，发现歧义时返回具体 `EVIDENCE_NEEDED`，不自行改路由。

## Tight loop（固定完成判据）

`route → load declared adapters → run required checks → return one owner/one frontier`。
路由完成只表示计划有效；只有 Matt executor receipt 和领域 adapter receipts 都齐全时，
才可进入下一 phase。路由脚本非零或 `BLOCKED` 时停止在当前 phase。

## 单一入口接线

```text
$develop-module
  → module-development-scheduler/scripts/route_module_task.py
  → Matt ask-matt / to-spec / execute-spec-in-fork / to-goal
  → develop-module hooks
  → bio-code-standard 与 bio-report-writing
```

调度器只返回计划，不运行生信程序、不读取临时参考目录、不修改模块源码。
`--has-full/--no-full` 与 `--requires-review/--no-review` 只声明当前合同能力；
未声明时按 work kind 给出保守默认。独立使用时可直接运行 route 脚本验证路由。

## 可运行工具

```bash
python scripts/module_scheduler.py route \
  --module my_module --task-type new \
  --changed-path scripts/calculate.R --changed-path scripts/report.py \
  --has-report --report-context module-reusable --phase scope
```

详细映射见 [route-contract.md](references/route-contract.md)，Matt 接口边界见 [matt-integration.md](references/matt-integration.md)。
输出字段定义见 [route_plan.schema.json](assets/route_plan.schema.json)。
诊断字段定义见 [diagnostic-contract.md](references/diagnostic-contract.md)。
档位和修复边界见 [execution-profile.md](references/execution-profile.md)。
