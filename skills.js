/*
 * ai-skills 技能清单
 * ------------------------------------------------------------------
 * 在这里添加你自己的技能，页面（技能卡片、分类筛选、统计数字）会自动生成。
 *
 * 字段说明：
 *   name      技能目录名（等宽字体展示，如 bulk-rna-seq）
 *   cat       分类 id（自动汇总成筛选按钮，板块随技能沉淀逐步细分）
 *   catLabel  分类的显示名（同一 cat 只需写一次，之后可省略）
 *   status    stable | beta | draft（徽章颜色不同）
 *   tags      工具/关键词标签，可省略
 *   repo      技能目录的链接，可省略
 *   zh / en   中英文标题（t）与描述（d）；只写 zh 也可以
 *
 * 示例（照抄一条改内容即可）：
 *
 * window.AI_SKILLS = [
 *   {
 *     name: "bulk-rna-seq",
 *     cat: "bio",
 *     catLabel: "生信分析",
 *     status: "stable",
 *     tags: ["DESeq2", "GSEA"],
 *     repo: "https://github.com/sher-l/ai-skills/tree/main/skills/bulk-rna-seq",
 *     zh: { t: "转录组差异分析", d: "DESeq2 差异表达、富集分析、预后矩阵制备。" },
 *     en: { t: "Bulk differential analysis", d: "DESeq2 DE, enrichment, matrix prep." }
 *   }
 * ];
 */

window.AI_SKILLS = [];
