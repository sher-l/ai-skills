# 图件、表格与 DOCX 合同

## 图件

每个业务图在模板中固定为：

```text
陈述式图题 → 一个完整源图/已独立发布 panel → 紧邻图注 → 正文解释
```

renderer 只嵌入当前发布树的真实 PNG/JPEG（或目标引擎明确支持的完整矢量图）；不临时重画，
也不从 PDF 截图冒充源图。图注由显式 slot 组装，至少说明对象、比较/分组、panel、轴和
单位/变换、颜色/形状/线型、n 或统计层级、阈值和阅读边界，顺序与源图一致。

单一 composite source 对应一个 drawing。按源宽高比缩放，DOCX 内不得出现非零 OOXML
`a:srcRect`，不得裁剪、竖切为续图或拉伸。宽图通过源端重排、增大画布、横向页面或独立
发布 panel 解决；图题/整图/图注用 keep-with-next/keep-lines 保持邻接。

## 表格

renderer 在固定 slot 读取已验证结果表或显式 typed rows，并固定列、顺序、显示名、单位、
精度和脚注。长表只展示合同声明的预览行并指向完整业务文件；不要靠任意 key-value loop
决定列。表头跨页重复，行不可拆分，列宽在目标阅读器中可读。

输出文件表单独列业务文件 basename、内容与用途；报告、日志、cache、hash 和内部 provenance
不进入表格。空结果按 `valid_no_findings` 的固定分支处理：声明为下游输入的表保留表头空表，
不适用的图/章节整项省略，不生成假行或占位图。

## 独立三门

1. **结构**：媒体、图/表 ID、文件、slot 和 caption 一一对应；
2. **视觉**：无裁切、拉伸、重叠、tofu、空白页、孤立标题/图注或表格溢出；
3. **证据**：图表中的对象、数量、方向、单位和结论由结构化结果支持。

PNG/PDF 记录物理尺寸、DPI、renderer 与字体 fallback；像素/DPI/hash 不能替代目标阅读器
逐页检查。完整 release 门见 [acceptance.md](acceptance.md)。
