---
name: bio-code-standard
description: 为 R/Python 生物信息学 coder 提供 v2.2 的源码审查、calculate/plot 阶段合同、统计与数据语义、错误处理、配置、结果 provenance 和 evidence 校验。涉及生信源码、算法、配置、Schema、统计或绘图变更时使用；不负责报告写作。
---

# bio-code-standard v2.2

这是代码层适配器。它输出可追溯的结构化表、图件和运行证据，并把
`analysis_evidence_pack` 作为开发/验证控制面的交接记录；报告层消费这些事实，
不会把 evidence pack 当作 `result/` 业务文件。

## 固定顺序

1. **Step 0 source review（不可跳过）**：以给定模块源码为输入运行
   `source-review init`，建立 R/Rmd/Python 文件清单和 hash；把实际阅读的官方文档、
   论文、发布源码或 API 资料写入 module-local `doc/source-review.md`。
   需要资料时先查官方站点/原始论文/版本源码，再把关键规则和短摘录存入
   `doc/source-review/`；搜索结果摘要不能代替原始资料。
2. 在同一文档的 cross-check matrix 中逐条绑定
   `official_definition ↔ source_evidence ↔ execution_evidence`。官方定义、源码行为和
   执行观察冲突时立即返回 `DECISION_REQUIRED`，暂停 coder 变更；缺资料返回
   `EVIDENCE_NEEDED`。只有无冲突且证据齐全才把 `review_status` 改为 `PASS`。
3. 运行 `source-review validate ... --final`；通过后才建立/修改
   `code_contract`，再按声明的 `calculate → plot` 顺序实现。没有 plot 能力就省略 plot
   合同和 manifest，不凭模板强加。
4. 每个阶段冻结 purpose、输入/输出 artifact、格式、行列方向、ID namespace、单位、
   方法/版本、参数、seed、非退化条件、lineage 和错误策略。配置路径相对配置文件，
   运行时不安装依赖。
5. 统计结果记录推断单位、target/reference、可计算方向、效应量、区间（适用时）、
   原始/校正 p、family、阈值和实际公式；过滤、去重、对齐、缺失和批次处理记录
   before/after 与 dropped 清单。
6. 新建/重写模块的公开结果固定使用 `result/<NN>.<semantic_name>.<ext>` 单层布局
   （`result_layout=flat`）；迁移旧模块先记录并审定既有路径，再完成到同一平铺合同的接口迁移。plot 只读已发布表或声明的 cache，不重算科学结果；每个
   逻辑图绑定真实 source code、data source、run record、尺寸、DPI、字体、renderer、
   颜色语义和 PNG/PDF 输出。
7. 交接时填写与报告侧兼容的 `analysis_evidence_pack`。它只保存机器事实和来源，不
   生成读者问句、章节或 DOCX。运行 validator 的结构化状态作为完成判据。

## 固定命令

在 skill 根目录或复制后的 skill 包中执行：

```bash
python scripts/bio_code.py source-review init --module MODULE --source-root MODULE
python scripts/bio_code.py source-review validate MODULE/doc/source-review.md --source-root MODULE --json
python scripts/bio_code.py source-review validate MODULE/doc/source-review.md --source-root MODULE --final
python scripts/bio_code.py init --module MODULE --output MODULE/.code-contract --languages r,python --with-plot
python scripts/bio_code.py validate MODULE/.code-contract/code_contract.json --source-root MODULE --json
python scripts/bio_code.py evidence MODULE/.code-contract/analysis_evidence_pack.json --root MODULE --json
python scripts/bio_code.py figure MODULE/.code-contract/figure_manifest.json --root MODULE --final
```

`init`/scaffold 只产生 `DRAFT` 并退出 0；任何未完成的 validate 返回
`EVIDENCE_NEEDED`（退出 2），冲突返回 `DECISION_REQUIRED`（退出 2），只有
`quality_profile=release` 且 `--final` 全部通过才返回 `PASS`/0；历史
`module_contract` 布局只能在迁移审查阶段读取，不能作为 v2.2 发布布局。

## 按需读取

- Step 0、官方资料和冲突门禁：见 [source-review.md](references/source-review.md)。
- 阶段、配置、统计、数据、错误、结果布局：见 [core-contract.md](references/core-contract.md)。
- 图件真实来源与 manifest：见 [plot-contract.md](references/plot-contract.md)。
- 交接字段：见 [analysis-evidence-pack.md](references/analysis-evidence-pack.md)。
- DEG/scRNA/CellChat/pySCENIC/Milo：见 [rna-single-cell.md](references/rna-single-cell.md)。
- MR、生存、机器学习、GBD：见 [models-and-gbd.md](references/models-and-gbd.md)。
- 诊断协议与修复轮次：见 [diagnostic-contract.md](references/diagnostic-contract.md)。

只在当前 scope 声明的检查上运行；科学歧义使用 `effort_profile=scientific_review`，
不得由 coder 自行扩大范围。详细规则保持在 references，低模型按上述命令和模板执行。
