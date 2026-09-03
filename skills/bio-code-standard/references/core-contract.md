# calculate / plot 核心合同

先通过 [source review](source-review.md)，再把已确认的源码行为写成合同。默认
`effort_profile=mechanical`、最多两轮聚焦修复；科学歧义仅在 scope 明确授权的
`scientific_review` 中提出。

## 阶段边界

每个 `calculate` 或 `plot` stage 声明：

| 字段 | 必填内容 |
|---|---|
| `purpose` | 这一步唯一的科学目的 |
| `inputs` | artifact、格式、行列方向、ID namespace、单位、推断单位和身份 |
| `outputs` | 发布表/模型/图、Schema、用途和至少一个消费者 |
| `method` | 实际算法、实现版本、官方引用和选择理由 |
| `parameters` | 阈值、contrast、资源、seed 和实际表达式 |
| `non_degenerate` | 最小样本/特征、空结果和停止条件 |
| `lineage/provenance` | 来源、变换、运行命令、环境和上游 run id |
| `error_policy` | 必须停止的输入/资源失败、重试和部分状态处理 |

`calculate` 只消费输入或上游发布物并产生科学事实；`plot` 只读取已发布科学表或
合同声明的 cache，不重算、补猜或覆盖计算对象。没有图能力时省略 plot 合同和 manifest。

## 配置与数据

- 从配置文件所在目录解析相对路径；`help` 说明每个命令的参数、输出和零副作用；
  配置键必须有唯一消费者，未知键直接报错。
- 运行时不安装 R/Python 包；解释器、包、数据库、参考资源、源码 commit 和 seed
  写入 provenance。环境合同负责安装，阶段只检查版本。
- 在 Scientific Core 前断言物种、genome build（适用时）、ID namespace、矩阵方向、
  样本/供体顺序、分组、单位、重复 ID、缺失和资源版本。关键不匹配结构化失败。
- 去重、ID 映射、过滤、NA 处理、批次校正、合并和切分都记录 `before`、`after`、
  `dropped` 及规则；不能用无计数的 `na.omit` 或覆盖原对象隐藏损失。

## 统计与模型

每个统计事实携带推断单位（sample/donor/cell 等）、target/reference、可计算方向、
设计矩阵或 contrast、效应量、区间（适用时）、原始 p、校正 method/family、阈值和
实际公式。完整表、筛选表或其他视图只在各自有明确消费者时发布；例如 `DEG_all`
与 `DEG_sig` 可以同时存在，但不能为了“方便检查”再造无消费者副本。合法无发现
使用 `valid_no_findings`：已声明且下游需要 schema 连续性的表保留表头和零数据行，
不适用产物省略；绝不生成占位图或伪造阳性。

训练、验证和外部验证的对象、切分、预处理拟合边界、特征选择、seed、超参数和性能
区间分开记录；外部验证不得静默重拟合。算法同名不等于语义相同，以 source review
和执行证据为准。

## 结果与失败

- 新模块公开业务文件默认单层 `result/<NN>.<semantic_name>.<ext>`；表、模型和图共用
  该层，同一逻辑图的 PNG/PDF 仅改变扩展名。
- 存量模块的嵌套路径只作为迁移输入记录；发布前迁移到同一平铺合同，脚本不能临时决定第二种布局。
  `cache/` 只放真实下游消费者需要的对象。
- 错误返回 `code/subject/evidence/supportedFixes`，保留 attempt、error 和部分状态；
  禁止静默 fallback、全局 warning 抑制、`setwd` 链和运行时依赖安装。
- 成功发布前扫描绝对路径、占位符、任务句、乱码、错误指标标签和未声明输出；源代码
  与配置变更必须重新运行 source review 和受影响阶段。
- 新增或修改的业务代码注释使用简体中文，写清目的、原因和边界；函数/变量/包名、公式和标准技术术语
  保留英文，不用英文自然语言注释替代中文说明。

## 交付判据

`code_contract`、适用的 `figure_manifest` 和 `analysis_evidence_pack` 均由 validator
检查；draft 只暴露缺口，release/final 才能 PASS。报告、图注、章节和 DOCX 不属于本
skill 的 coder 职责。
