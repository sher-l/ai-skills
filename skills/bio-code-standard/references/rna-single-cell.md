# DEG 与单细胞模块规则

## bulk DEG 与富集

明确样本重复数、设计矩阵、contrast、效应方向、过滤条件、p/FDR 列和多重检验 family。DESeq2、edgeR、limma 的分支选择和实际调用写入 provenance；完整表、`DEG_sig`、up/down 视图只在各自有明确消费者时发布（例如 `01.DEG_all.csv` 与 `01.DEG_sig.csv` 可以同时存在）。富集结果记录数据库版本、背景集、方向（上调/下调）、NES/ES、p 和 FDR。裸 p 值不能替代校正值。

## scRNA

固定输入矩阵方向、样本/供体标签、QC 阈值、归一化、特征选择、PCA/Harmony 参数和对象 checkpoint。每一步记录细胞数和样本组成变化。聚类/marker 的细胞级描述与供体级统计分开，不能从 UMAP 外观推出组间显著性。

## CellChat 与通讯分析

固定 sender/receiver 方向、count/weight 指标、数据库版本、最小细胞数、分组和显著性口径。CellChat、CellPhoneDB、LIANA 等方法的分数不自动横向比较。候选通讯优先级是当前数据和规则下的候选，不是因果关系。

## pySCENIC

将三层证据分开发布：

1. regulon 活性（AUC/阈值）；
2. 细胞类型特异性或 RSS 排名；
3. TF–target 候选边及 importance/支持来源。

RSS 前几名不能直接写成已验证的优先 TF–target 关系。边表必须包含 TF、target、方向/分数、来源和筛选条件。

## Milo 与网络

记录 kNN、nhood、样本级设计和 SpatialFDR；网络输出同时保留节点表和边表。图中的密度、颜色或边宽只表达已声明变量，不能把可视拥挤解释成生物学强度。
