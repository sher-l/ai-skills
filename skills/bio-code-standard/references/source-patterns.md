# 语料提炼索引

这些是已脱离临时目录仍然有效的规则摘要；它们不是运行时输入，也不要求
复制原始客户文件。

## 正例能力

- 源码审查：从实际 R/Python 树生成清单，锁定官方版本并以运行 receipt 交叉核对定义；
- 阶段契约：一个模型阶段明确输入矩阵方向、队列边界、算法组合、输出模型和 AUC；
- 数据清洗：按参照 ID 顺序合并、记录重复/缺失数量，并同时保存 RDS 与 CSV；
- CLI 分支：根据样本重复数选择 DESeq2 或 edgeR，按消费者声明发布完整结果、筛选结果和下游输入；
- 绘图 helper：统一 Cairo PDF/PNG、物理尺寸、DPI、字体和设备关闭；
- Rmd 绑定：变量、chunk 尺寸、结果路径、解释文字和 session 信息同源。

## 反模式触发器

平行 `project_code`/`r-code`、绝对路径、链式 `setwd`、无计数 `na.omit`、全局 warning
抑制、结果变量覆盖、静默空图、注释掉的实际命令、未断言的单位/方向和占位文本，
都要求回到核心合同逐项核对。反模式只作为 validator fixture 或 review 提示，不进入
正式证据包。

## 生信语义重点

pySCENIC 的 regulon 活性、RSS/TF 排名和 TF–target 候选边是三层证据；CellChat
不同方法的 score 不自动可比；GBD 的 Incidence/Prevalence 必须由名称、单位和公式
共同断言；MR、虚拟 KO、对接和 MD 的输出保持候选/模型提示层级。
