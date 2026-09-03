# 路由合同

## 任务类型

| task type | 默认路径 | 领域加载 |
|---|---|---|
| `new` | `ask-matt` → SPEC | code；有公开报告时加 report |
| `migrate` | `ask-matt` → SPEC | code；迁移报告时加 report |
| `optimize` | `ask-matt` → SPEC | code；结果/图件受影响时加 report |
| `substantial_change` | `ask-matt` → SPEC | code；公开产物受影响时加 report |
| `review` | `ask-matt` → review | 由变更路径决定 |

`new`、`migrate`、`optimize` 和 `substantial_change` 在 `work_kind=auto`
时默认是 code，即使尚未给出 changed path；显式 `work_kind=report` 才覆盖该
默认。`review` 仍须由 changed path 或显式 work kind 说明审查面。

## 阶段钩子

- `scope`：确认模块、目标、输入、非目标和所需领域适配器；代码任务先做
  `source_review`，再进入分析 coder；
- `build`：只推进当前 frontier；`full` 按 `source_review → analysis_coder → report_coder`，
  `plot` 按 `source_review → plot_coder → report_coder`，`report-only` 只走
  `report_coder`；
- `draft`：代码和报告草稿都通过各自 validator，缺证据保持 `EVIDENCE_NEEDED`；
- `finish`：仅当 route plan 声明 `requires_review`/`requires_full` 时加入相应
  独立 review、测试或 full 检查；领域 skill 只提供验收谓词。

## 路由原则

每次只返回一个 route。`single_session=true` 且 `spec_ready=true` 才返回 `fork`；
`multi_session=true` 且 `spec_ready=true` 才返回 `goal`；其余返回 `ask-matt` 或
`BLOCKED`。`plan_phase`/`development_plan.phase` 只是台账映射，不是第二套 Matt 状态。

`report_context` 可为 `one_off` 或 `module_reusable`；两者使用同一报告合同和
检查集合，区别只记录上下文的复用范围。finish 的独立 review/full 要求由
route plan 的 `finish_policy` 明确声明，不从“报告”一词臆测。

`execution_scope` 是能力边界而非生命周期：`report-only` 仅改报告正文/图题/图注/DOCX
版式，`plot` 仅改作图实现且不改科学结果，`full` 覆盖计算、科学逻辑、配置、合同或
输出结构。省略时按路径保守推断，无法确定时应由调用者显式指定。
