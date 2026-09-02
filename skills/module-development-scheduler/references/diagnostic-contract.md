# 调度诊断格式

路由错误也返回 `code`、`severity`、`message`、`subject`、`evidence` 和
`supportedFixes`。调度器只修正任务类型、阶段、权限或加载计划，不修改领域
事实；领域错误回传给对应 adapter。
