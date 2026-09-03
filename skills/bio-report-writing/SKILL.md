---
name: bio-report-writing
description: 为 R/Python 生信项目编写可复用的机械报告模板与 renderer：以 DOCX 模板为默认正式入口，固定正文、动态 slots、结果/输出/版本表、真实图件和语义 Note，并完成证据、路径、结构与目标阅读器验收；也用于按同一合同从已给材料生成一次性报告。Use when creating or changing a module report template/generator, or rendering a one-off report from supplied evidence and figures.
---

# 生信报告 coder

这个 skill 的交付物是**报告代码**：开发阶段由 report coder 写好固定模板、图题图注、表格定义和
R/Python renderer；正式运行只由 renderer 把已确认事实填入 slots。运行时不调用 AI 改写正文、不重算
统计、不临时重画图、不从文件名、日志、配置或图片外观猜事实。缺证据时保留 `EVIDENCE_NEEDED` 或
`BLOCKED`，不以一段看似完整的文字代替事实。

算法、统计正确性和实际作图逻辑由 source review/code coder 先确认；本 skill 只核对公开 provenance 与
报告映射。代码、数据、provenance 或图件冲突时停止并返回 `BLOCKED`，不另画一套参考图。

## 模式与唯一模板

模块和一次性报告使用同一内容、slot、样式和验收合同，只有生命周期不同。

| 模式 | 新建/正式默认 | 兼容入口 |
|---|---|---|
| `module_reusable` | `MODULE/report_templates/report_template.docx` + `MODULE/scripts/report/generate_report.R|py` | 存量 QMD/Rmd renderer 迁移前可继续运行，但必须遵守本合同 |
| `one_off` | 复制 `assets/report_template.docx` 和一个 R/Python renderer 到独立工作目录 | 仅在迁移存量实现时暂时调用其 QMD/Rmd renderer；不形成第二套规则 |

一个模式只保留一个生效模板。DOCX-first 模板承载章节、锚点、表格位置、图件位置和 Note 样式；renderer
承载事实校验、条件分支和 slot 填充。QMD/Rmd 是已有模块的兼容路径，不为新模块并行维护第二套正文。

## 固定加载顺序（低推理模型照做）

按顺序读取，完成一项再进入下一项；不自行增加流程，也不把未声明的建议变成阻断条件。

1. **必读** [report-contract.md](references/report-contract.md)：唯一的读者、章节、结果段、图表、Note、语言和验收合同。
2. **必读** [slot-contract.md](references/slot-contract.md) 与 [analysis-evidence-pack.md](references/analysis-evidence-pack.md)：字段、锚点、来源、类型、条件和空值策略。
3. **实现 renderer 时**读取 [renderer-examples.md](references/renderer-examples.md)；新模块先看 DOCX-first，复制
   `scripts/render_docx_template.py` 作为最小填充器；存量 QMD/Rmd 只作为迁移接线。
4. **有 Figure/Table 时**读取 [figure-contract.md](references/figure-contract.md)；**有正文/结论时**读取 [language-and-claims.md](references/language-and-claims.md)。
5. **模块模式**按需读取 [degs-example.md](references/degs-example.md)（仅 DEGs 或需借鉴其机械链路），以及 [source-patterns.md](references/source-patterns.md)。**一次性模式**读取 [one-off.md](references/one-off.md)。
6. **开始和结束都读取** [acceptance.md](references/acceptance.md)；发生失败时再读取 [diagnostic-contract.md](references/diagnostic-contract.md) 和 [audit-qa.md](references/audit-qa.md)。

## 固定执行清单

### 1. 冻结读者与证据范围

先检查当前模块的实际源码、已发布结果和已有研究索引；需要外部方法/术语依据时，在模块批准的
`docs/research/`（或等价长期文档）归档 URL/DOI、访问日期、采用结论和冲突处理，避免依赖临时参考目录。
记录一个主要 `audience` 及其决策场景、实际采用的 `terminology_sources`（路径/URL/DOI/批准记录）、
陈述式 `evidence_targets`，并把每个 target 映射到分析点、结果表/图和公开文件。旧
`reader_questions` 只做迁移输入，转换为陈述句后才进入新计划；问句不进入标题、图题、图注、摘要或结论。

完成条件：每个 target 都有唯一事实来源；术语冲突和缺失事实已有记录。不能证明的字段标为
`EVIDENCE_NEEDED`，不猜写。

### 2. 盘点真实执行产物

沿 canonical `calculate → plot → report` 入口核对实际执行代码、成功 run、结果表、PNG/PDF、provenance
和输出根。报告只消费已发布业务产物和明确 provenance；保留真实对象、推断单位、比较方向、单位、
阈值、校正方法、样本/分组计数、版本和警告事实。新建/重写模块的 `result/` 使用编号平铺文件；不为
报告另造无消费者的 filtered/top/gene-list 副本。

完成条件：每个动态 slot 都有唯一 `source/path`，路径相对声明的 input root，且能在实际结果或 provenance
中复核。

### 3. 写模板合同（先固定 prose，再列动态 slots）

在 `report_template.docx` 中物理放置固定章节、锚点和表/图位置；在模板或 renderer 中写一次固定的
业务句式。至少包含：标题/摘要、范围、方法与参数、适用时的质控、结果与解读、综合结论、局限/待验证、
公开输出、参考文献、最后的软件与资源版本表。可选章节没有事实时整节省略，不写空章节或占位句。

模板必须同时有 `result_table`、`output_table`、`version_table` 和 `figures[]` 的位置；有关键方向、单位/
变换或解释边界时有 `notes[]` 位置。规则只写在文档而未写进模板锚点、样式或 renderer，不算落地。

完成条件：固定 prose 与动态 slot 分离，模板可在无运行事实时检查结构，且一个模式没有第二份生效正文。

### 4. 写机械 renderer

renderer 接收显式 `input_root`、evidence/provenance、模板和输出目录；先校验 schema、来源、路径、ID、类型、
长度、方向和条件，再写隔离工作副本并填充命名 slots。使用固定函数生成每个图注、结果表、输出表、版本表
和 Note；禁止 `for key,value` 自动把内部字段变成正文。条件产物只按事实出现，固定顺序和文件名保持稳定。

完成条件：同一输入重复运行得到相同正文、图序、表序、Note 顺序和文件名；正式输出目录只留下最终报告。

### 5. 实现读者版内容与版式

每个分析点按“对象与范围 → 方法/版本/参数 → 推断单位与比较方向 → 结果数字/统计量 → Figure/Table/真实
文件 → 领域解释 → 限制/阴性状态/下一步用途”写入。结果段再呈现“结论 → 数字证据 → 领域解释 → 限制”。

图按“编号陈述式图题 → 一张完整源图 → 紧邻自足图注”；结果表、公开输出表和版本表按合同字段填充。Note
只用于关键口径，采用默认天蓝样式：边框 `#5B9BD5`、填充 `#DDEBF7`、标签 `#2F75B5`；标签和文字即使
去掉颜色仍可理解。源图等比嵌入，禁止裁剪、分幅、拉伸，宽高比误差不超过 0.1%。

完成条件：正文、表、图注和 Note 的数字/方向/颜色语义都来自同一事实链，且正文不出现工程字段或问句。

### 6. 渲染、验收与交付

先按变更面选择运行场景：**只改报告正文、图题、图注、表述或 DOCX 版式时，用已发布结果执行
`report-only`；只改作图代码的版式、字体、颜色或绘图实现且不改变计算结果/科学逻辑时，只执行
`plot`，再用新图执行 `report-only`；只有改动科学计算、科学逻辑、配置、合同或输出结构时，才执行
`full`。**报告层改动不得被误判为科学结果变更，`plot` 也不得重算；随后运行机器门，再由目标阅读器逐页检查 DOCX，并逐个打开 standalone PNG/PDF；保存 renderer 命令、输入/
输出相对路径、门结果、reviewer、时间和逐文件视觉结论。`draft` 只能输出 `DRAFT`/`EVIDENCE_NEEDED`；
`release` 只有结构、视觉和证据三门都通过才可写 `PASS`。任一门失败即 `BLOCKED`，修复后重跑，不把脚本
成功退出码当作交付。

## 模板必须实现的固定字段

DOCX-first 的标准锚点和字段见 [slot-contract.md](references/slot-contract.md)。最低实现集合为：

```text
[[REPORT_TITLE]]  [[REPORT_AUDIENCE]]  [[REPORT_SUMMARY]]
[[ANALYSIS_SCOPE]]  [[ANALYSIS_METHOD]]  [[ANALYSIS_QC]](适用时)
[[ANALYSIS_RESULT]]  [[ANALYSIS_CONCLUSION]]  [[ANALYSIS_LIMITATIONS]]
[[NOTE:DIRECTION]](适用时)  [[TABLE:RESULTS.CAPTION]]
[[FIGURE:F1.SOURCE]]  [[FIGURE:F1.CAPTION]]
[[TABLE:OUTPUTS.CAPTION]]  [[REFERENCES]]  [[TABLE:VERSIONS.CAPTION]]
```

`result_table` 保留回答 target 所需的最小列和行（长表可固定展示前 10 行并指向完整业务表）；
`output_table` 只列读者可获得的业务文件、内容、用途和消费者，同一逻辑图的 PNG/PDF 在报告中合并为
`name.png(pdf)`，磁盘上仍逐文件验证；`version_table` 是最后一个可见内容块，不写 `NA`、run ID、hash、
cache、日志或治理状态。

## 运行边界

通用 `scripts/` builder 只用于 plan、slot 草稿和结构预检；它不能替代模块正式 renderer。正式 renderer
必须来自模块（或一次性工作目录中的复制品），读取实际结果和模板，保留工程追溯在 `run_record.json` 与
owning `testNN/visual-review.json`，不把这些字段写进客户正文。完成判据、诊断代码和 receipt 字段以
[acceptance.md](references/acceptance.md) 为准。
