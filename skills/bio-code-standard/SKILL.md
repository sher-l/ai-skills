---
name: bio-code-standard
description: 为 R/Python 生物信息学 coder 提供 v2.2 的源码审查、init/calculate/plot/report/full 阶段合同、统计与数据语义、错误处理、INI 配置、结果 provenance 和 evidence 校验。涉及生信源码、算法、配置、Schema、统计或绘图变更时使用；不负责报告写作。
---

# bio-code-standard v2.2

发布状态：开发中（非稳定版）；本文件和随包合同仍会继续修订。

这是代码层适配器：输出可追溯的结构化表、图件和运行证据，供报告层消费；
`analysis_evidence_pack` 属于控制面，不是 `result/` 业务文件。

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
   `code_contract`，再按五阶段合同实现。标准脚手架固定按 `init`、`calculate`、`plot`、
   `report`、`full` 顺序声明五个 stage；`init` 独立做配置，`full` 只串联后三个业务阶段。
   阶段日志仍按实际调用生成，`init` stage 不得声明日志。
4. 每个阶段冻结 purpose、输入/输出 artifact、格式、行列方向、ID namespace、单位、
   方法/版本、参数、seed、非退化条件、lineage 和错误策略。配置路径相对配置文件，
   运行时不安装依赖。
5. 统计结果记录推断单位、target/reference、可计算方向、效应量、区间（适用时）、
   原始/校正 p、family、阈值和实际公式；过滤、去重、对齐、缺失和批次处理记录
   before/after 与 dropped 清单。
6. 新建/重写模块的公开结果固定使用 `result/<NN>.<semantic_name>.<ext>` 单层平铺布局
   （`result_layout=flat`）；迁移旧模块先记录并审定既有路径，再迁移到同一平铺合同。
   `calculate` 可在 `scripts/calculate/` 下拆分多个文件；`plot` 只读已发布表或声明的
   cache，不重算科学结果；`report` 只读 calculate 结果和 plot 图件；`full` 只串联
   `calculate → plot → report`，不把 `init` 算入 full。每个逻辑图绑定真实 source code、
   data source、run record、尺寸、DPI、字体、renderer、颜色语义和 PNG/PDF 输出。
   每次命令只写一个同名日志：`calculate.log`、`plot.log`、`report.log` 或 `full.log`；
   `init` 不写日志，`full` 的子阶段进度只写入 `full.log`，不创建三个子阶段日志。
7. 交接时填写与报告侧兼容的 `analysis_evidence_pack`。它只保存机器事实和来源，不
   生成读者问句、章节或 DOCX。运行 validator 的结构化状态作为完成判据。

**注释语言**：新增或修改的 R/Python/Shell 业务代码注释统一使用简体中文，说明目的、原因和边界；
函数名、变量名、参数名、包名、公式、文件名和标准技术术语保留其规范英文写法。模板注释也遵守此规则。

## 固定命令

```bash
python scripts/bio_code.py source-review init --module MODULE --source-root MODULE
python scripts/bio_code.py source-review validate MODULE/doc/source-review.md --source-root MODULE --json
python scripts/bio_code.py source-review validate MODULE/doc/source-review.md --source-root MODULE --final
python scripts/bio_code.py init --module MODULE --output MODULE/.code-contract --config MODULE/module.config.ini --languages r,python
python scripts/bio_code.py validate MODULE/.code-contract/code_contract.json --source-root MODULE --json
python scripts/bio_code.py evidence MODULE/.code-contract/analysis_evidence_pack.json --root MODULE --json
python scripts/bio_code.py figure MODULE/.code-contract/figure_manifest.json --root MODULE --final
python scripts/bio_code.py stage calculate -c MODULE/module.config.ini --module-root MODULE --json
# 模块运行入口（按声明的能力执行；所有阶段使用同一个 INI）
run.sh init -c module.config.ini
run.sh calculate -c module.config.ini -o OUTPUT
run.sh plot -c module.config.ini -o OUTPUT
run.sh report -c module.config.ini -o OUTPUT
run.sh full -c module.config.ini -o OUTPUT
```

公开命令 `run.sh init -c PATH` 直接生成或幂等校验 PATH 指向的单个 INI 文件（不创建 `config/` 目录），不计算且不生成日志；脚手架补齐根目录入口并只产生
`DRAFT`。未完成的 validate 返回 `EVIDENCE_NEEDED`（退出 2），冲突返回 `DECISION_REQUIRED`（退出 2），只有
`quality_profile=release` 且 `--final` 全部通过才返回 `PASS`/0。脚手架入口和配置在模块根，合同 JSON/evidence/manifest
仅放在 `MODULE/.code-contract/`；发布结果必须使用平铺编号路径。

## 错误输出

失败时先输出错误类型、具体内容和修复建议，再输出退出码；同样内容写入 stderr、被调用阶段日志和 JSON。
JSON 保留 `code`、`message`、`subject`、`evidence`、`supportedFixes`，并增加 `error_type` 与 `content`；未调用阶段不创建日志。

标准类型为 `INPUT_ERROR`、`CONFIG_ERROR`、`DEPENDENCY_ERROR`、`RUNTIME_ERROR`、
`OUTPUT_ERROR`、`EVIDENCE_ERROR` 和 `DECISION_REQUIRED`。退出码固定为：`0` 成功，`1` 一般运行或输出错误，
`2` 输入/配置/证据/决策校验失败，`3` 依赖/环境异常。例如：

```text
错误类型: INPUT_ERROR
错误内容: [calculate] 找不到 input.expression：data/expression.tsv
修复建议: 检查 module.config.ini 中的相对路径和文件编码
退出码: 2
```

## 按需读取

- Step 0、官方资料和冲突门禁：见 [source-review.md](references/source-review.md)。
- 五阶段、INI、目录、数据流和日志边界：见 [stage-contract.md](references/stage-contract.md)。
- 阶段、配置、统计、数据、错误、结果布局：见 [core-contract.md](references/core-contract.md)。
- 图件真实来源与 manifest：见 [plot-contract.md](references/plot-contract.md)。
- 交接字段：见 [analysis-evidence-pack.md](references/analysis-evidence-pack.md)。
- DEG/scRNA/CellChat/pySCENIC/Milo：见 [rna-single-cell.md](references/rna-single-cell.md)。
- MR、生存、机器学习、GBD：见 [models-and-gbd.md](references/models-and-gbd.md)。
- 诊断协议与修复轮次：见 [diagnostic-contract.md](references/diagnostic-contract.md)。

只运行当前 scope 声明的检查；科学歧义使用 `effort_profile=scientific_review`，不得自行扩大范围。
五阶段入口和复用边界以 `stage-contract.md` 为准，低模型按上述命令和模板执行。
