# DEGs 正例：已有 QMD renderer 的迁移参考

DEGs 是本 skill 的存量参考实现，不要求其他模块复制其科学算法。它仍使用 QMD renderer；新模块应采用
DOCX-first 的 `report_template.docx` + `generate_report.R|py`，但两条实现必须遵守同一事实、slot、图表和验收语义，
不是两套可选规范。

```text
DEGs/report_templates/report_template.qmd
DEGs/report_templates/reference.docx
DEGs/scripts/report/generate_report.R
```

## 已落地的报告细则

- QMD 固定章节依次覆盖分析目的/范围、方法与参数、适用时 QC、结果概览、结果预览表、图件、解释边界、
  公开结果文件、参考文献和末尾软件/资源版本表；无事实的可选块整节省略。
- 参数来自 calculation/plot provenance 和真实公开文件：比较方向、阈值、校正方法、样本/分组计数、
  结果数量、颜色语义、布局和版本都显式传入，不从配置、日志或图像外观猜测。
- 结果表只预览公开显著表的固定前 10 行，完整表在输出文件表中作为业务文件；输出表按“文件名/内容/用途”
  组织，同一逻辑图的 PNG/PDF 合并成 `02.volcano.png(pdf)` 一行，磁盘上仍逐文件校验。
- 每个图按“编号陈述式图题 → 完整源图 → 紧邻业务图注”输出。图注解释对象、比较/分组、panel、坐标/单位/
  变换、颜色/线型、n/统计层级、阈值和阅读边界；热图的标准化、密度/分位面板和分组注释均来自 plot
  provenance。源图不裁剪、不分幅、不拉伸，宽高比误差不超过 0.1%。
- 方向、单位/变换或解释边界可能误读时，动态生成带可见标签的 `Note`，并在 DOCX 校验中检查其语义。默认
  天蓝样式为边框 `#5B9BD5`、填充 `#DDEBF7`、标签 `#2F75B5`；报告正文不显示色值代码，旧黄色仅为历史
  失败样式，不得作为该语义 Note 的替代。
- 标题、正文、表头、图题、图注、Note 和结论为自然中文陈述句；图内文字为英文；结论不超过实际
  `interpretation_level`，阴性结果写明当前数据和判定口径。
- 最终版本表是最后可见内容块；工程运行状态、路径哈希、cache、日志、模板和审核记录留在内部 receipt。

## R renderer 的迁移要点

`generate_report.R` 先验证 calculation/plot provenance，再验证 `01.DEG_all.csv`、`01.DEG_sig.csv`、
`02.volcano.png`/`.pdf`（有 findings 时验证 `03.heatmap.png`/`.pdf`），把明确参数写入隔离工作目录，
调用 QMD，最后检查 DOCX 图件数量、图题/图注编号和邻接、方向 Note、结果/输出/版本表和可见文本。
临时目录退出时清理，正式结果树不留下模板、scratch 或内部 provenance。

## 可迁移边界

1. 固定 prose 和动态 slots 分离；不要把模块正文退回通用 key-value loop。
2. Figure/Table、Note 和输出表与当前状态一一对应；缺失时按合同省略或阻断。
3. 报告只能消费实际代码和数据产生的公开事实；参考官网或论文只能作为术语/方法来源，不能另画一套图。
4. 新模块把同一内容迁移到 DOCX 锚点，不同时维护 QMD 和 DOCX 两份正文。
