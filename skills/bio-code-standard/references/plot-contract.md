# plot 与 figure provenance

`plot` 是消费层，不是第二个 calculate。它只能复用 calculate 已发布的结果表或声明的
cache；若上游结果不存在，应返回带类型/内容/修复建议/退出码的错误，而不是重算。
每个逻辑图使用稳定 `figure_id`，并把真实
来源写入 manifest：

- 发布表/模型路径、筛选表达式、分组、样本/细胞数量、单位和统计映射；
- 产生图的 R/Python `source_code`、实际 `data_sources`、`run_record`/命令和参数；
- 画布宽高、DPI、字体、renderer、颜色/线型语义、panel 身份和输出路径。

`source` 是实际存在的主图文件；`formats` 中的 PNG/PDF 必须共享同一 basename、数据、
比例、字体和颜色语义。release/final 逐文件检查两种格式、路径边界和 companion 文件。
不能把截图、报告裁剪图或手工重绘当作科学来源；空图、非法值、缺图例或静默 fallback
进入失败状态。

逻辑图的 PNG/PDF 文件应在 `result/` 同一目录并列输出（例如 `result/02.network.png` 与
`result/02.network.pdf`），并在 manifest 中共享同一数据、代码和运行记录；不要创建
`figures/` 子目录。
图只读取已发布科学表或合同声明的 cache。绘图 helper 应显式设置设备、尺寸和字体，
并只关闭设备一次；不要依赖当前工作目录或默认 renderer。密集标签通过分面、重排或
增大画布处理，不在报告/DOCX 阶段切片或改变科学语义。

manifest 的最小形状见 `assets/figure_manifest.example.json`；字段校验使用：

```bash
python scripts/bio_code.py figure FIGURE_MANIFEST --root MODULE --json
python scripts/bio_code.py figure FIGURE_MANIFEST --root MODULE --final
```
