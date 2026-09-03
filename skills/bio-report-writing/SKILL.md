---
name: bio-report-writing
description: 为 R/Python 生信项目编写可复用的机械报告模板和 renderer，并把真实结果、表格、图件与图注填入 DOCX 完成验收。涉及报告模板、报告生成代码、图注、结果表、DOCX 或一次性报告时使用；不重算科学结果。
---

# 生信报告 coder

发布状态：开发中（非稳定版）；模板、renderer 和门禁仍会继续修订。

本 skill 的交付物是报告代码：开发期写好唯一模板、固定正文、表格、图题/图注和 R/Python renderer；
运行期只读取已发布的 calculate/plot 事实并机械填充。运行期不调用 AI 改写正文、不重算统计、不临时
重画图、不从文件名、日志、配置或图片外观猜事实。缺证据返回 `EVIDENCE_NEEDED` 或 `BLOCKED`。

## 固定合同

1. **唯一模板**：新模块使用 `report_templates/report_template.docx` 和一个
   `scripts/report/generate_report.R|py`。一次性报告复制同一模板和接口；两种模式规则完全相同。
   存量 QMD/Rmd 只作为迁移接线，不能与 DOCX 并行维护第二份正文。
2. **固定顺序**：标题与摘要 → 数据范围与分析边界 → 材料与方法 → 质控与异常（有事实才出现） →
   分析结果与解读 → 综合结论 → 局限/未完成/待验证 → 输出文件说明 → 参考文献 → 最后软件与资源版本表。
   可选节无事实时整节删除，不写空节或占位句。
3. **分析点段落**：对象/范围 → 方法、版本、参数 → 推断单位和比较方向 → 数字/统计量 →
   Figure/Table/真实文件 → 领域解释 → 限制和下一步。结果先写结论，再给数字证据、解释和边界。
4. **事实边界**：每个可见数字、方向、单位、阈值、版本和文件名都来自同一 evidence/provenance。
   官方资料只定义应实现的语义；实际代码和数据定义本次结果；冲突暂停并交人工审定。
5. **语言**：标题、正文、表头、图题、图注和 Note 用自然中文陈述句；图内标题、坐标轴、图例和标注用
   英文。正文不出现问句、任务句、营销文案、模板 marker、工程状态、URL/DOI（来源地址只在参考文献或
   内部资料记录中出现）。结论强度不超过 `interpretation_level`。

## 图件与提示框

- 每幅图固定为“连续编号陈述式图题 → 一张完整真实源图 → 紧邻自足图注”。源图等比嵌入，版心内显示，
  禁止裁剪、分幅、续图、拉伸；宽高比误差不超过 0.1%。图注由 renderer 从实际 provenance 组装，至少写
  对象、比较/分组、panel、轴/单位、编码、n/统计层级、阈值和边界。
- `callout-note` 与 `figure source` 是不同组件。Note 是独立提示框（模板中的标签行/正文行和单元格样式）；
  只有存在真实方向、单位/变换或边界事实时才插入。Figure source 是透明普通图片段落，不含段落边框、
  底色或缩进。详细字段见 [figure-contract.md](references/figure-contract.md)。
- 结果表固定列和顺序，文本左对齐、数值右对齐、表头跨页、数据行不拆页；输出表只列有消费者的业务文件，
  同图 PNG/PDF 在正文合并成 `name.png(pdf)`；版本表是最后可见内容块。

## 固定执行顺序

1. 读取 [report-contract.md](references/report-contract.md)、[slot-contract.md](references/slot-contract.md) 和
   [analysis-evidence-pack.md](references/analysis-evidence-pack.md)，冻结 audience、targets、章节和每个 slot 的来源。
2. 先核对实际源码、已发布 calculate/plot 结果、研究资料和 provenance；把采用的官方资料归档到模块 `doc/`
   或 `docs/research/`，不依赖临时目录。
3. 写唯一 `report_template.docx` 和固定 prose，再写一个显式 slot map 的 R/Python renderer；禁止任意遍历
   JSON 键值生成正文。
4. 先运行 Schema、路径、事实、表/图/Note 结构门，再填隔离模板副本；正式输出目录只保留最终报告。
5. 按 [acceptance.md](references/acceptance.md) 完成证据门、结构门和一次目标阅读器最终冒烟；机器检查先于
   视觉检查，不为每次小改反复渲染整份报告。

## 运行边界

- 只改正文、图题、图注、表述或 DOCX 版式：用已发布结果执行 `report-only`。
- 只改不影响科学结果的绘图实现、字体、颜色或版式：执行 `plot`，再用新图执行 `report-only`；不重算。
- 触及计算、科学逻辑、配置、合同或输出结构：执行 `full`，即 `calculate → plot → report`；`init` 独立，
  不属于 `full`。
- `draft` 只能返回 `DRAFT/EVIDENCE_NEEDED`；只有 `release` 的结构、证据和视觉三门全通过才返回 `PASS`。

通用 `scripts/` builder 只做计划、slot 草稿和结构预检，不能替代模块正式 renderer。详细合同、R/Python
示例和验收清单按需读取 [renderer-examples.md](references/renderer-examples.md)、[language-and-claims.md](references/language-and-claims.md)、
[acceptance.md](references/acceptance.md)。
