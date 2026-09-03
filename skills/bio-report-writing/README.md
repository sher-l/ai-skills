# bio-report-writing

这是一个**报告 coder** skill：开发阶段写好唯一报告模板、固定正文、图题图注、结果表和 R/Python
renderer；正式运行机械读取已发布结果和 provenance，填充 DOCX slots 并验收。它不是运行时 AI 写作器，
也不重算统计或按图片外观补事实。

## 默认 DOCX-first 目录

新模块的正式入口：

```text
MODULE/
├── report_templates/
│   └── report_template.docx       # 唯一生效模板：章节、锚点、表/图位置、Note 样式
└── scripts/report/
    └── generate_report.R|py       # 唯一正式 renderer：校验事实并填 slots
```

已有模块若已采用 `report_template.qmd|Rmd` + `reference.docx`，迁移完成前可继续由原 renderer 出具；它仍
遵守本合同，且不与 DOCX 模板形成第二套正文。一次性报告复制 `assets/report_template.docx` 和 renderer
到独立工作目录，生命周期不同但合同完全相同。

DOCX 锚点、marker 和每个动态字段的来源见 [slot-contract.md](references/slot-contract.md)；可复制模板的
槽位工作表见 [assets/report-template.md](assets/report-template.md)。

最小 DOCX 填充命令（正式模块应在此基础上加入自己的事实校验）：

```bash
python scripts/render_docx_template.py \
  --template report_template.docx --values slots.json --root . \
  --output report/MODULE_report.docx --final
# 等价的统一入口：python scripts/bio_report.py render-template ...
```

## 必须落地的内容

- 固定章节：标题/摘要、范围、方法与参数、适用时 QC、结果与解读、综合结论、局限/待验证、公开输出、
  参考文献、最后的软件与资源版本表；没有事实的可选节整节省略。
- 每个分析点：对象与范围 → 方法/版本/参数 → 推断单位与比较方向 → 数字/统计量 → Figure/Table/真实
  文件 → 领域解释 → 限制/阴性状态/下一步；读者结果段为结论 → 数字证据 → 领域解释 → 限制。
- 结果表、公开输出表、版本表和 `figures[]` 都是固定 slots；输出表只列有消费者的公开业务文件，
  `01.DEG_sig.csv` 等声明了消费者的结果合法保留，PNG/PDF 在报告中按逻辑图合并展示。
- 图使用完整真实源图、陈述式图题和紧邻自足图注；不裁剪、分幅、拉伸，显示宽高比误差 ≤0.1%。
- 关键方向、单位/变换或解释边界使用独立语义 Note：边框 `#5B9BD5`、填充 `#DDEBF7`、标签 `#2F75B5`；
  去色后仍可理解，色值不写入客户正文。
- 标题、正文、表头、图题、图注、摘要、结论和 Note 为自然中文陈述句；图内标题/轴/图例为英文；结论
  强度不超过 `interpretation_level`，不写问句、任务句、占位符或工程运行字段。

## 低推理模型执行顺序

1. 读取 [SKILL.md](SKILL.md) 和 [report-contract.md](references/report-contract.md)；
2. 读取 [slot-contract.md](references/slot-contract.md) 与 [analysis-evidence-pack.md](references/analysis-evidence-pack.md)，冻结 audience、术语来源、evidence targets 和每个 slot 的来源；
3. 读取 [renderer-examples.md](references/renderer-examples.md)，新模块只采用 DOCX-first；有图/表再读
   [figure-contract.md](references/figure-contract.md)，有正文再读 [language-and-claims.md](references/language-and-claims.md)；
4. 写唯一模板和固定 prose，再写显式校验/填充 renderer；运行期只填 typed slots；
5. 读取 [acceptance.md](references/acceptance.md)，按变更面选择 `report-only`、`plot` 或 `full`，完成机器、证据、目标阅读器三门并保存 receipt。

缺证据直接 `EVIDENCE_NEEDED`/`BLOCKED`，不提取文件名猜事实，不自行增加边界或第二套流程。

## 工具边界

本目录的 `scripts/` builder 只做 plan、slot 草稿和结构预检；generic key-value builder 不能成为正式报告
renderer。正式模块必须由 `generate_report.R|py` 从声明输入复制模板、填充锚点、发布最终 DOCX/PDF，并按
[acceptance.md](references/acceptance.md) 验收。规则与字段细节按需读取 references，完整锚点表见
[slot-contract.md](references/slot-contract.md)。
