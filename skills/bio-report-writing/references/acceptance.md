# 报告验收：三道独立门

验收目标是证明**实际模板、renderer、数据和图件**共同生成了可读报告；一门通过不能替代另外两门。
先读本文件确定门禁，再实现，渲染后按同一清单复核。

## 运行场景

- 只改报告正文、图题、图注、表述或 DOCX 版式：使用已发布结果执行 `report-only`，只重渲染和验收报告。
- 只改作图代码的版式、字体、颜色或绘图实现，且不改变计算结果/科学逻辑：执行 `plot`，再用新图执行
  `report-only`；不重算。
- 改动科学计算、科学逻辑、配置、模块合同或输出结构：执行 `full`，重新计算、作图并生成报告。

`report-only` 不得重算统计或临时重画图；`plot` 不得重算；报告代码或纯绘图代码改动本身不等于科学结果改动。

## 机器门

逐项检查并保存命令输出：

- DOCX-first 新模块存在唯一 `report_template.docx`，锚点和 renderer slot 一一对应；存量 QMD/Rmd 只在迁移
  完成前由已有 renderer 使用，且必须满足同一合同；没有第二套隐藏正文模板。
- renderer 在声明 CWD 从固定输入重现相同正文、图序、表序、Note 顺序和文件名；evidence schema、
  provenance、状态、相对路径、方法/参数/方向/单位、受众、术语来源和引用均通过。
- 每个 target 都有结论、数字证据、领域解释、限制和 Figure/Table/公开文件来源；必需字段缺失返回
  `EVIDENCE_NEEDED`，不猜写。
- 正式可见文本没有问句、任务句、模板 marker、占位符、乱码、营销文案或越过
  `interpretation_level` 的强断言；数字、方向、阈值、单位、引用、版本和文件名四方一致。
- 每个 Figure/Table 的 ID、源文件、caption、分析点和输出记录一一对应；caption 覆盖对象、比较/分组、
  panel、轴/单位/变换、颜色/形状/线型、n/统计层级、阈值和边界。
- `result_table`、`output_table`、`version_table` 按固定列和顺序生成；输出表只列有消费者的公开业务文件，
  PNG/PDF 多格式合并显示，版本表是最后可见块；不出现无消费者副本或工程文件。
- 源图完整等比嵌入；DOCX 无非零 `a:srcRect`、裁剪、分幅、续图、拉伸；图题→整图→图注邻接；表头可
  重复、行不拆页；有 Note 时存在可见标签、独立框体和三色样式
  `#5B9BD5/#DDEBF7/#2F75B5`，无 Note 触发条件时不强行生成。

运行适用的机器检查：

```bash
python .agents/skills/bio-report-writing/scripts/validate_report_contract.py \
  --plan PLAN --evidence-pack PACK --markdown MARKDOWN --root INPUT_ROOT --final
python .agents/skills/bio-report-writing/scripts/validate_docx_structure.py \
  REPORT.docx --final
```

## 视觉门

先用代码和 OOXML 做确定性检查：模板调用链、slot 来源、图段是否透明、图片 extent 是否落在版心、
标题 direct formatting、Note 组件结构、`srcRect`、表格行规则和图题/图注顺序。机器门通过后，仅用一次
目标阅读器（例如 LibreOffice）渲染最终 DOCX，逐页检查：标题和 Note 可见且不孤立，正文无截断/溢出/
tofu，表头重复且字号可读，无空白页、错位、裁切、图片拉伸或图题/图注分离；宽图和 panel 在最终显示尺寸
仍能读出轴、单位、图例、阈值线、分组和颜色语义。逐个打开 standalone PNG/PDF，检查其完整性、尺寸、
DPI、字体和与报告相同的语义；像素、DPI 或 hash 不能替代人工目检。

模板、renderer 或固定 prose 的每次小改不重复渲染整份报告；只有机器检查通过后的最终候选才做这一次目标
阅读器冒烟。若冒烟失败，先修代码/模板并重新通过机器门，再生成新的候选。

视觉结论由未参与实现的独立 reviewer 记录；适用模块的最终 `full` 还须遵循 owning
`<Module>_test/testNN/full/visual-review.json` 合同。

## 证据门

从最终文本和媒体反向追踪：

1. 每个 `evidence_target` 映射到一个分析点和至少一个公开表/图或事实；
2. 每个可见数字、方向、单位、阈值、统计量、颜色语义、引用和版本映射到结果/provenance；
3. 结论只使用设计支持的证据层级，阴性状态和限制明确；
4. 输出文件表与当前发布树逐文件一致，路径、basename、格式和消费者可复核。

## 状态与 receipt

`draft` 只能写 `DRAFT` 或 `EVIDENCE_NEEDED`；`release` 在机器、视觉、证据三门全通过后才写 `PASS`。
任一门失败为 `BLOCKED`，修复诊断 `subject` 后重跑，不能以脚本成功退出码替代验收。

receipt 至少记录：模式、renderer 命令/版本、模板版本、输入和输出相对路径、evidence/provenance 来源、
三门结果、reviewer、时间、媒体尺寸/DPI/字体 fallback、逐文件视觉结论和失败诊断。工程字段留在
`run_record.json`，不进入客户正文或公开输出表。
