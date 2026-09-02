# Slot contract

报告模板是稳定的程序接口，不是每次运行重新写作的提示词。先列出固定 prose 和动态
slots，再写 renderer；每个动态 slot 必须能回到一个 evidence field 或实际文件。

## 两层内容

| 层 | 放置位置 | 例子 |
|---|---|---|
| 固定 prose | `report_template.qmd`/Rmd 或 Python renderer | 章节顺序、方法解释句、结论边界、引用顺序、Note 文案 |
| 动态 slot | renderer 参数/typed manifest | 项目名、样本/细胞 n、组别与方向、阈值、效应量/P/FDR、版本、文件路径、图注数据、表行 |

固定 prose 不从 evidence pack 生成；evidence pack 只提供事实。避免通用
`for key, value` 标签循环，因为它会把内部字段名变成客户正文并破坏版式。模块可有
多个分析点，但每个 slot 名称、类型和插入位置固定。

## 最小 slot 表

```text
slot_id              type/shape       source                         condition
report.title         string           pack.title                     always
analysis.scope       string           point.scope                    always
analysis.method      object           point.method + parameters       always
analysis.result      rows             point.results                   always
analysis.limitations string[]         point.limitations                always
figure.F1.source     relative path    point.figure_table_refs[path]    published
figure.F1.caption    declarative text renderer-built caption fields   published
table.T1.rows        typed rows       point.outputs/result sources     published
```

每个 slot 写明空值策略：必需值缺失时 `EVIDENCE_NEEDED` 并停止正式渲染；条件值不适用时
省略整个章节/图/表并记录原因；不要写“暂无”“待确认”占位句。数值保留原始单位、
精度和统计口径，方向由 `comparison.target/reference/direction` 明确表达。

## 正式 renderer 的接口

1. 接收显式 `input_root`、`evidence_pack/provenance`、`template_dir` 和 `output_dir`；
   所有相对路径都以声明的 input root 解析，拒绝绝对路径与越界 `..`。
2. 先校验 schema、文件存在性、图/表 ID 唯一性、条件分支和字段长度，再写隔离的
   `params.json|yml`；输出只发布最终报告。
3. 用固定函数逐个组装 slot（例如 `build_caption_F1()`、`make_result_table()`），
   不在模板中读取日志、配置、cache 或运行环境来推断事实。
4. 记录 renderer 版本、输入/输出路径和内部 checksum 到 provenance/receipt；这些工程
   字段不进入读者可见正文或业务文件表。

`analysis_evidence_pack` v0.1.0 的字段映射见 [analysis-evidence-pack.md](analysis-evidence-pack.md)。
