# 五阶段执行合同（v2.2）

本文件是低模型可直接执行的阶段边界。v2.2 标准合同固定列出 `init`、`calculate`、`plot`、`report`、`full` 五个入口；`init` 是独立配置入口，`full` 只编排三个业务阶段。

## 唯一配置入口

- 用户运行配置固定为模块根目录的 `module.config.ini`，格式为 INI；不要把 YAML 当作用户运行配置。
  仓库已有的 `module_contract.yaml` 仍是机器合同，和用户配置是两种不同文件。
- `[module].language` 明确阶段实际使用 `python` 或 `r`；即使同时保留两套模板，入口也只能调用这一种。
- 所有阶段统一接收同一个配置参数：`run.sh <stage> -c module.config.ini`。
- 脚手架阶段创建根目录的 `module.config.ini`；运行 `init -c PATH` 在父目录已存在时直接生成或幂等校验
  这一个配置文件，不创建 `config/` 目录，不读取数据做计算，也不生成 `calculate`、`plot`、`report` 或
  `full` 的阶段日志。
- 配置中的相对路径以 `module.config.ini` 所在目录为基准；禁止在源码中 `setwd`、硬编码绝对路径或运行时安装依赖。

## 模块目录

新模块按以下公开骨架组织；复杂计算继续在对应目录拆文件，不把多份平行脚本放在根目录：

```text
MODULE/
├── run.sh
├── module.config.ini
├── scripts/
│   ├── init.R 或 init.py
│   ├── calculate/       # main、输入检查、统计核心和可复用中间对象
│   ├── plot/            # 只消费 calculate 已发布结果
│   └── report/          # 只组装 calculate + plot 事实
├── result/              # 直接放编号业务结果
├── report/              # 正式报告
├── cache/               # 只有真实下游会复用的缓存
├── log/                 # 当前命令的一个日志和 run_record
└── doc/                 # 源码审查、官方资料和模块说明
```

`init.R|py` 只处理配置和入口检查；`full` 不新增另一套脚本，而是调用同一套
`calculate/`、`plot/`、`report/` 实现。
脚手架初始化时只创建 `run.sh`、`module.config.ini` 和 `scripts/` 下的入口文件；`result/`、
`report/`、`cache/`、`log/`、`doc/` 等运行目录按阶段首次调用时再创建，避免 init 产生空目录或日志。

## 阶段及依赖

| 阶段 | 允许的工作 | 必须消费 | 可写出的阶段日志 |
| --- | --- | --- | --- |
| `init` | 生成/校验单个配置、检查输入和依赖 | `-c` 指定的配置文件 | 不生成日志 |
| `calculate` | 执行科学计算并发布可复用结果 | 输入数据、配置 | 仅 `log/calculate.log` |
| `plot` | 从已发布的 calculate 结果渲染图件 | calculate 的结果表或声明的 cache | 仅 `log/plot.log` |
| `report` | 组装事实、表格和图件 | calculate 结果 + plot 图件/manifest | 仅 `log/report.log` |
| `full` | 串联 `calculate → plot → report` | 同上三阶段输入 | 仅 `log/full.log`；不得把 `init` 算入 full |

每次业务入口把同一个 `-o/--output` 传给实际阶段脚本，并只生成一个与命令同名的日志：`full` 的三个子阶段进度写入 `full.log`，不另生成
`calculate.log`、`plot.log` 或 `report.log`。阶段未被调用时，不得创建其专属日志、结果、图件或报告目录。
`full` 是编排入口，不是新的科学计算阶段；它不能绕过单阶段合同，也不能重复计算。

## 代码目录和数据流

- `calculate` 可以拆成多个文件，但全部放在 `scripts/calculate/`（例如 `main.R`、`io.R`、`statistics.R`）；入口顺序和依赖必须在合同中写明。
- `plot` 只能读取 calculate 已发布的表或明确声明的 cache；禁止在绘图脚本中重新拟合、筛选或改变统计阈值。
- `report` 只能读取 calculate 的事实和 plot 的真实图件/manifest；禁止在报告阶段重新计算或凭空补数。
- 每个公开结果声明 `id`、相对 `path`、`purpose` 和 `consumers`，并保留运行记录、版本和输入 hash 以便 provenance 回溯。

## 结果与图件命名

- 表格等公开结果使用 `result/NN.semantic_name.ext` 的平铺路径（`NN` 从 `01` 起）；不要在 `result/` 下再建目录。
- 一个逻辑图的 PNG/PDF 是同一 `figure_id` 的并列文件，例如 `result/02.network.png` 与 `result/02.network.pdf`；manifest 必须同时声明两种格式及同一数据、代码和运行记录来源。
- 图件应保留真实来源和语义尺寸、字体、dpi；禁止用截图、裁剪或拆图掩盖数据问题。

## 错误和注释

- 失败时同时输出：`错误类型`、`错误内容`、`修复建议` 和 `退出码`；人读文本写入 stderr，机器接口可提供同字段 JSON。
- 退出码约定：`0` 成功，`1` 运行/输出错误，`2` 合同、配置、证据或决策阻断，`3` 依赖/环境错误。
- R/Python 源码中的解释性注释使用中文；变量名、函数名和标准 API 可保留英文。不要用注释隐藏未实现逻辑或静默吞掉异常。

## 最小验收顺序

1. `run.sh init -c module.config.ini`
2. `run.sh calculate -c module.config.ini -o CALCULATE_OUTPUT`，确认结果、provenance 和 `log/calculate.log`。
3. 运行 `run.sh plot -c module.config.ini -o PLOT_OUTPUT`，确认它只复用 calculate 结果。
4. 运行 `run.sh report -c module.config.ini -o REPORT_OUTPUT`，确认它只复用 calculate + plot。
5. `run.sh full -c module.config.ini -o FULL_OUTPUT` 只验证上述三阶段串联；不要把 init 当作 full 的计算步骤。
