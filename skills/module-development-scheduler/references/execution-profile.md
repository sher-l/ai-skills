# 执行档位

档位是行为开关，不是让模型自由选择的建议：

| 字段 | 行为 |
|---|---|
| `quality_profile=draft` | 允许结构缺口，产出草稿和具体诊断，不得声称可交付 |
| `quality_profile=release` | 仅在所有声明的门禁通过后交付 |
| `effort_profile=mechanical` | 只运行 route plan 的 `required_checks`，不加新检查、不扩展范围 |
| `effort_profile=scientific_review` | scope 明确授权后才提出科学歧义；缺证据返回具体 `EVIDENCE_NEEDED` |

固定规则：

1. 模型不能因为“可能更安全/更完整”自行添加安全策略、依赖、章节、分析或 reviewer；
2. 模型不能因为“看起来足够”跳过已声明检查；
3. 修复只改诊断 `subject`，最多两轮；没有改善就保留 `BLOCKED`；
4. 用户或 SPEC 修改范围后递增 `scope_revision`，重新生成 route plan。

`repair_round`、`checkpoint_round`、`regression_round` 是三个不同计数器：

- `repair_round` 只表示针对已报告诊断的代码/文档修复批次；
- `checkpoint_round` 只表示需要用户或批准者决定的范围/证据检查点；
- `regression_round` 只表示修复后按原验收矩阵复测的轮次。

它们不能互相抵扣或驱动第二套 phase；`max_regression_rounds=0` 表示不设
人工上限，但每轮仍须有可复核证据。

这个文件只约束调度行为；科学、代码和报告内容分别由领域 adapter 负责。
