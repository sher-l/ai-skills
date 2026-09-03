# bio-code-standard v2.2

发布状态：开发中（非稳定版）。

独立可发布的 R/Python 生信 coder skill：先做源码/官方资料/执行证据的三方审查，再
规范 init/calculate/plot/report/full 五阶段、统计与数据语义、失败处理、INI 配置、结果 provenance 和机器
证据。报告写作、图注、章节和 DOCX 属于另一个 skill。

## 固定路径

```bash
python scripts/bio_code.py source-review init --module MODULE --source-root MODULE
# 编辑 MODULE/doc/source-review.md，填真实官方 URL、源码位置和运行 receipt；URL 只作科学来源记录，不进入结果正文
python scripts/bio_code.py source-review validate MODULE/doc/source-review.md --source-root MODULE --final
python scripts/bio_code.py init --module MODULE --output MODULE/.code-contract --config MODULE/module.config.ini --languages r,python
python scripts/bio_code.py validate MODULE/.code-contract/code_contract.json --source-root MODULE --json
python scripts/bio_code.py evidence MODULE/.code-contract/analysis_evidence_pack.json --root MODULE --json
python scripts/bio_code.py figure MODULE/.code-contract/figure_manifest.json --root MODULE --final
python scripts/bio_code.py stage calculate -c MODULE/module.config.ini --module-root MODULE --json
# 模块运行入口（只运行已声明的阶段）
run.sh init -c module.config.ini
run.sh calculate -c module.config.ini -o OUTPUT
run.sh plot -c module.config.ini -o OUTPUT
run.sh report -c module.config.ini -o OUTPUT
run.sh full -c module.config.ini -o OUTPUT
```

`module.config.ini` 是唯一用户配置入口；标准脚手架固定按 `init/calculate/plot/report/full` 顺序声明五阶段。
脚手架把 `module.config.ini` 放在模块根并补齐 `run.sh` 和 `scripts/` 入口；配置中的 `[module].language` 决定使用 R 或 Python；公开命令的 `init` 只校验配置，
不计算且不生成日志；目标文件不存在时从模块根模板直接生成该单个文件，不创建 `config/` 目录。
每次业务命令只写一个同名日志；`full` 只写
`log/full.log`，不另写 `calculate.log`、`plot.log` 或 `report.log`。
`calculate` 可在 `scripts/calculate/` 下拆成多个文件；`plot` 只复用 calculate 已发布结果，
`report` 只复用 calculate+plot，`full` 只串联 `calculate → plot → report`，不把 init 算入 full。
新建/重写模块固定使用 `result_layout=flat`，即 `result/` 单层编号文件；同一逻辑图的 PNG/PDF
以同一 `figure_id` 并列输出。迁移旧模块时只能把既有嵌套路径作为待审定现状记录，最终仍迁移到平铺合同。
完整代码目录和阶段依赖见 [stage-contract.md](references/stage-contract.md)。
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
- `scripts/`：固定 CLI、INI/阶段边界、source-review inventory 和 validator；
- `assets/`：合同、共享 evidence pack 与 figure manifest Schema/样例；
- `templates/`：run.sh、R/Python 阶段和 INI 起始文件；脚手架把它们放到模块根的对应目录。
- `references/stage-contract.md`：五阶段、目录、复用、日志和命名的可执行合同。
