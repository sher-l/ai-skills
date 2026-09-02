# 报告内容合同

正式报告由模块 renderer 和固定模板生成。模板固定一组语义槽位：标题/摘要、范围、方法
与参数、质控（适用时）、结果与解释、综合结论、局限/待验证、公开输出、参考文献和软件/资源
版本。模块可以合并显示相邻槽位，但不得丢失语义，也不得生成空章节；一次性报告使用同一槽位合同。

每个分析点按同一证据顺序写入固定 prose：

```text
对象与范围 → 方法/版本/参数 → 推断单位与比较方向 → 结果数字/统计量
→ Figure/Table/真实文件 → 领域解释 → 限制/阴性状态/下一步用途
```

正文使用“观察/结论 → 数字证据 → 领域解释 → 限制”，结论强度不超过
`interpretation_level`。摘要与综合结论只回收正文已有事实，不引入新数字或方向。

输出文件表由当前发布树和合同共同生成，只列读者可获得的业务文件。新建/重写模块在
`result/` 下使用稳定编号和语义 basename；报告自身、cache、log、run record、
checksum、QA 和治理状态不作为业务文件行。

固定正文/动态参数/条件产物的实现规则见 [slot-contract.md](slot-contract.md)，措辞与结论强度见
[language-and-claims.md](language-and-claims.md)，图件和表格见 [figure-contract.md](figure-contract.md)。
