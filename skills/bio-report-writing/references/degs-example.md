# DEGs 正例

DEGs 的报告链路是本 skill 的参考实现，不要求其他模块复制其科学算法：

```text
DEGs/report_templates/report_template.qmd
DEGs/report_templates/reference.docx
DEGs/scripts/report/generate_report.R
```

## QMD 的可移植做法

- YAML `params` 列出项目/作者、reference/target、method/version、阈值、样本/分组计数、
  结果预览、颜色语义、图宽度、公开文件和软件版本；这些是动态 slots。
- 章节和句式写在 QMD：分析目的、方法、结果概览、显著基因表、火山图、条件热图、结果文件、
  解释边界、参考文献和版本表；这些是固定 prose。
- `knitr::include_graphics()` 引入 renderer 已复制的真实 PNG；`knitr::kable()` 在固定位置
  插入分组/结果/文件/版本表。图题、整图和图注保持邻接；`newpage` 只为版式，不改变语义。
- `valid_no_findings` 对已声明且需要 schema 连续性的表保留表头空表，对不适用热图整项省略并如实说明当前阈值下无记录；不生成空图或虚构候选。

## R renderer 的可移植做法

`generate_report.R` 先读取并校验成功的 calculation/plot provenance，再校验
`01.DEG_all.csv`、`01.DEG_sig.csv` 和 `02.volcano.png`（有 findings 时再校验
`03.heatmap.png`）。它检查方法、比较顺序、p/FDR 口径、颜色/布局、输出表列和图件存在性，
把明确参数写入隔离 `params.yml`，复制 `report_template.qmd`、`reference.docx` 与真实图，
调用 Quarto，最后检查 DOCX 图件数量、图注编号/邻接、方向 Note、语义文字和公开文件表。

路径以调用者声明的结果/图件根解析；临时 render 目录退出时清理，正式 `result/` 不留下
`.report_template*`、`reference.docx` 或 scratch。工程 provenance 只在内部记录。

## 可迁移检查

复制到其他模块时保留三个边界：

1. **固定/动态分离**：不要把模块特有固定正文退回通用 key-value loop；
2. **条件真实**：每个 Figure/Table 与当前结果状态一一对应，缺失则省略或阻断；
3. **完整图件**：整张源图等比嵌入，no-crop；宽度由源图/页面布局解决。

DEGs 的具体参数名和科学解释只属于 DEGs；其他模块应写自己的 slot contract 和 renderer。
