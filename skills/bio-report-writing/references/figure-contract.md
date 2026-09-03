# Figure、表格与 DOCX-first 合同

本文件只定义媒体和表格的可见语义；事实来源、章节顺序和 Note 触发条件见
[report-contract.md](report-contract.md)，字段锚点见 [slot-contract.md](slot-contract.md)。

## 图件顺序与 caption

每个业务图在 `FIGURES` 锚点中固定为：

```text
连续编号的陈述式图题 → 一张完整真实源图 → 紧邻、自足、编号图注 → 正文解释
```

一个 composite source 对应一个 drawing；源图已有 panel 时在同一图注内按源顺序说明 panel。caption
必须由 renderer 的固定函数组装，至少覆盖：

| 字段 | 说明 |
|---|---|
| `object` | 数据对象、特征或队列 |
| `comparison` / `groups` | target/reference、分组和方向 |
| `panel` | panel 数量、顺序和各 panel 内容 |
| `axes` / `units` | 坐标、单位和变换（如 log、Z-score） |
| `encoding` | 颜色、形状、线型及其通俗语义 |
| `n` / `statistics` | 样本/特征数、统计单位和统计层级 |
| `threshold` / `boundary` | 筛选阈值、阅读边界和不能推断的含义 |

值必须来自 plot provenance、结果表或 evidence pack；不从 PNG/PDF 外观、OCR 或文件名补齐。图题、图注、
正文中的对象、方向、数字和颜色语义必须与同一事实链一致。

## 完整嵌图与格式

- 报告消费已发布 PNG/PDF（或合同明确支持的完整矢量源），不临时重画、不截屏、不用 PDF 截图冒充源图。
- 源图完整等比嵌入；DOCX 不含非零 OOXML `a:srcRect`，不裁剪、竖切续图、拼接半图或拉伸。
- 显示框与源图宽高比误差不超过 0.1%。宽图通过源端重排、增大画布、横向页面或独立完整 panel 解决，
  不靠裁剪。
- 图题、整图、图注用 keep-with-next/keep-lines 或等价布局保持相邻；不得让图题孤立在上一页、图注孤立在
  下一页或跨页丢失语义。
- PNG/PDF 是同一逻辑图的不同发布格式时，报告输出表合并为 `name.png(pdf)`；磁盘合同仍逐文件检查存在性、
  尺寸、DPI、renderer 和字体 fallback。

## Note 与 Figure source 的组件边界

`callout-note` 和 `figure source` 是两种不同的排版组件，不能共用段落装饰：

- `callout-note` 是独立提示框。模板用专用 callout table/组件承载标签行和正文行；天蓝填充、边框和标签色只
  写在该组件内部。没有真实 `notes[]` 事实时，renderer 删除整个 callout。
- `figure source` 是居中的普通图片段落，只包含一张完整 drawing。该段落没有 `w:pBdr`、`w:shd` 或额外
  `w:ind`，不使用 Note 的底色、边框、图标或缩进。旧模板若带这些属性，renderer 在插图前清除并由结构门报错。

机器门分别检查两者：Note 检查标签/正文/组件样式；Figure 检查完整媒体、版心 extent 和题→图→注顺序。
通过 Note 样式检查不能替代 Figure 版心检查。

## 结果表与输出表

`RESULT_TABLE` 由固定列定义和 typed rows 生成：列顺序、显示名、单位、精度、脚注固定；文本列左对齐，
数值列右对齐，表头跨页重复，单条数据行不拆页。长结果只展示合同声明的预览行（例如前 10 行），完整
业务表在 `OUTPUT_TABLE` 指向。

`OUTPUT_TABLE` 每行对应读者可取得的业务文件，显示 basename、内容、用途和消费者。报告、模板、日志、cache、
hash、run record、QA 和治理状态不占行；没有消费者的 filtered/top/gene-list 副本不生成也不列出。

## 三道独立门

1. **结构门**：Figure/Table ID、源文件、caption、slot 和输出记录一一对应，条件产物与状态一致；
2. **视觉门**：无裁剪、拉伸、重叠、tofu、空白页、孤立标题/图注、表格溢出或不可读字号；
3. **证据门**：对象、数量、方向、单位、阈值、统计和结论都能由结构化结果支持。

机器结构检查不能替代目标阅读器逐页检查，也不能用像素、DPI 或 hash 代替语义证据。
