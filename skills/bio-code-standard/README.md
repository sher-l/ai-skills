# bio-code-standard v2.2

独立可发布的 R/Python 生信 coder skill：先做源码/官方资料/执行证据的三方审查，再
规范 calculate、可选 plot、统计与数据语义、失败处理、配置、结果 provenance 和机器
证据。报告写作、图注、章节和 DOCX 属于另一个 skill。

## 固定路径

```bash
python scripts/bio_code.py source-review init --module MODULE --source-root MODULE
# 编辑 MODULE/doc/source-review.md，填真实官方 URL、源码位置和运行 receipt；URL 只作科学来源记录，不进入结果正文
python scripts/bio_code.py source-review validate MODULE/doc/source-review.md --source-root MODULE --final
python scripts/bio_code.py init --module MODULE --output MODULE/.code-contract --languages r,python --with-plot
python scripts/bio_code.py validate MODULE/.code-contract/code_contract.json --source-root MODULE --json
python scripts/bio_code.py evidence MODULE/.code-contract/analysis_evidence_pack.json --root MODULE --json
python scripts/bio_code.py figure MODULE/.code-contract/figure_manifest.json --root MODULE --final
```

新建/重写模块固定使用 `result_layout=flat`，即 `result/` 单层编号文件；迁移旧模块时
只能把既有 `module_contract` 布局作为待审定的现状记录，最终仍迁移到同一平铺合同，不能由 skill
静默采用另一套发布布局。
`source-review validate` 在官方定义、源码实现和执行证据冲突时返回
`DECISION_REQUIRED`；缺证据返回 `EVIDENCE_NEEDED`。草稿 validator 不输出 PASS，只有
`quality_profile=release` 的最终检查可以 PASS。所有脚本只用 Python 标准库，运行时不安装
R/Python 依赖。

新写或修改的 R/Python/Shell 业务代码注释统一使用简体中文；仅保留函数名、变量名、包名、公式和标准
技术术语的英文原文。随包模板已经按此约定编写。

校验失败先打印“错误类型 + 错误内容 + 修复建议”，再打印退出码；同一内容写入 stderr、
当前阶段日志和 JSON（`error_type`、`content`）。退出码只用于机器分支：`0` 成功，`1` 一般运行或输出错误，
`2` 输入/配置/证据/决策校验失败，`3` 依赖/环境异常。

## 包内容

- `SKILL.md`：最小执行顺序和命令；
- `references/`：按需加载的阶段、统计、数据、失败、绘图和证据规则；
- `scripts/`：固定 CLI、source-review inventory 和 validator；
- `assets/`：合同、共享 evidence pack 与 figure manifest Schema/样例；
- `templates/`：R/Python/config 起始文件。
