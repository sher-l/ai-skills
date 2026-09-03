# Step 0：源码审定合同

`doc/source-review.md` 是模块内、可携带的唯一来源审查记录。它不是报告，也不替代
`code_contract.json`。任何 R、Rmd 或 Python 源码、算法、统计阈值、配置或绘图变更都
先刷新这份记录，再进入 coder 阶段。

## 固定动作

1. 对给定源码树运行 `source-review init`。清单至少包含相对路径、语言、SHA-256、行数、
   作用和 `canonical` 标记；不要把 `backup`、`new`、`final` 或平行副本当作执行源。
2. 实际打开并记录官方定义来源：官方文档/API、论文、发布源码、数据库说明或版本锁定的
   教程。只写真实 URL、版本/tag/commit、访问日期和适用范围；搜索结果摘要不是资料。
   同时把关键规则和短摘录保存到 `doc/source-review/OFF-*.md`（受版权限制时不复制全文），
   让后续 coder 直接复用本地科学资料，不重复搜索。
3. 以可测试的 claim 填写 cross-check matrix。每行必须同时指向 `official_id`、
   `source_path`/函数位置和 `execution_id`/artifact，并写出观察到的定义、实现和运行事实。
4. 选择且只选择一个 `canonical_source`，使 metadata、清单和实际执行命令一致。源码 hash
   变化后必须重新 init 或修订清单，不能沿用旧证据。

## 状态门禁

| 状态 | 含义 | 后续动作 |
|---|---|---|
| `DRAFT` / `EVIDENCE_NEEDED` | 缺官方资料、canonical、运行记录或交叉核对 | 返回缺失字段；不改科学 coder 逻辑 |
| `DECISION_REQUIRED` | 官方定义、源码行为和执行证据存在冲突，或 hash 已漂移 | 暂停；只返回最小决策问题和冲突证据 |
| `PASS` | 清单、官方资料、执行证据和每条 matrix 均完整且无冲突 | 才能建立/修改 `code_contract` |

`source-review validate --final` 只在 `PASS` 时退出 0。`DECISION_REQUIRED` 不是普通
warning，也不能靠把 `review_status` 改成 `PASS` 绕过；validator 会交叉检查表格和实际文件。

## 文档最小结构

```text
metadata: schema_version=2.2, module, source_root, canonical_source, review_status
## 源码清单
## 官方资料
## 实际执行证据
## 三方交叉核对矩阵
```

矩阵状态使用 `MATCH`、`CONFLICT`、`MISSING`、`PENDING` 或 `NOT_APPLICABLE`。只有
`MATCH`/有理由的 `NOT_APPLICABLE` 可进入 PASS；`CONFLICT` 必须带 decision，但带了
decision 也只表示已记录，是否继续由用户/科学负责人决定。

## 证据写法

- 官方定义写可核对的参数、公式、输入假设和版本，不写泛泛“方法正确”；
- 源码证据写路径、函数/行和实际分支，不以函数名猜行为；
- 执行证据写精确命令、run id、日志/结果路径、关键观测值和状态；
- 差异必须保留原文定义、实现行为、运行观察和最小待决策项，禁止静默选边。

权威关系：官方文档/方法论文定义应实现的科学语义；源码和运行记录定义本次实际做了什么。
源码能运行不等于科学语义正确。以官方定义判定科学正确性，但不能把官方示例当作本次结果；冲突未审定前不改算法、不出新图、不写报告；审定后若新增
官方方法图件，仍须修改并重新执行真实绘图代码，不能直接复制官网图片。
