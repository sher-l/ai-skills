# 报告验收

验收分三道独立门；一门通过不能替代另外两门。

## 机器门

- renderer 能在声明的 CWD 从固定输入重现同一正文、图序、表序和文件名；evidence schema、
  provenance、状态、相对路径、方法/参数/方向/单位和来源均通过。
- 正式文本没有问句、任务句、模板 marker、猜写数字、夸大因果/疗效/临床结论、乱码或营销文案。
- 每个已发布 Figure/Table 的 ID、文件、caption 和分析点一一对应；不适用产物完整省略；
  业务文件表不列报告、日志、cache、hash 或运行状态。
- DOCX 媒体为真实源图，等比嵌入；无非零 `a:srcRect`、裁剪/续图/拉伸；图题→整图→图注邻接，
  表头可重复且行不拆分。运行 `validate_report_contract.py --final` 和
  `validate_docx_structure.py REPORT.docx --final`。

## 视觉门

在目标阅读器（例如 LibreOffice）渲染最终 DOCX，逐页查看：无截断、溢出、tofu、空白页、孤立
图题/图注、表格跨页错位或不可读字号；图内轴、单位、图例、阈值线和分组在最终显示尺寸清晰。
对每张 standalone PNG/PDF 用同一比例、字体、颜色语义抽查；记录实际 renderer、尺寸、DPI 和
字体 fallback。视觉检查是人工/独立 reviewer 证据，不由像素或 hash 代替。

## 状态与 receipt

`draft` 输出只能是 `DRAFT` 或 `EVIDENCE_NEEDED`，允许继续填 slot；`release` 在三门全部通过
后才是 `PASS`。任一门失败是 `BLOCKED`，只修诊断 subject 后重跑；不要把脚本的成功退出码当成
正式交付。receipt 至少记录模式、renderer 命令、输入/输出相对路径、门结果、reviewer 和时间；
工程字段留在 receipt，不进入正文。
