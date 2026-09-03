/*
 * ai-skills 技能清单
 * ------------------------------------------------------------------
 * 在这里添加你自己的技能，页面（技能卡片、分类筛选、统计数字）会自动生成。
 *
 * 字段说明：
 *   name      技能目录名（等宽字体展示，如 bulk-rna-seq）
 *   cat       分类 id（自动汇总成筛选按钮，板块随技能沉淀逐步细分）
 *   catLabel  分类的显示名（同一 cat 只需写一次，之后可省略）
 *   status    beta | draft | stable（页面显示中文状态）
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
 *     status: "beta",
 *     tags: ["DESeq2", "GSEA"],
 *     repo: "https://github.com/sher-l/ai-skills/tree/main/skills/bulk-rna-seq",
 *     zh: { t: "转录组差异分析", d: "DESeq2 差异表达、富集分析、预后矩阵制备。" },
 *     en: { t: "Bulk differential analysis", d: "DESeq2 DE, enrichment, matrix prep." }
 *   }
 * ];
 */

window.AI_SKILLS = [
  {
    name: "bio-code-standard",
    cat: "bio",
    catLabel: "生信分析",
    status: "beta",
    tags: ["R", "Python", "源码审查", "统计", "可复现", "v2.2"],
    repo: "https://github.com/sher-l/ai-skills/tree/main/skills/bio-code-standard",
    zh: {
      t: "生信分析代码规范",
      d: "持续更新的 v2.2 代码规范：先核对官方定义、源码实现与真实执行证据，再规范 R/Python 计算、统计、绘图、配置和结果交接。"
    },
    en: {
      t: "Bioinformatics code standard",
      d: "Source-first review, R/Python contracts, statistics, plots, and reproducible evidence."
    }
  },
  {
    name: "bio-report-writing",
    cat: "bio",
    status: "beta",
    tags: ["报告 coder", "DOCX", "模板", "图注", "验收"],
    repo: "https://github.com/sher-l/ai-skills/tree/main/skills/bio-report-writing",
    zh: {
      t: "生信报告 coder",
      d: "持续更新的 v2.2 报告 coder：编写 DOCX-first 可复用模板与 R/Python renderer，插入真实表格和图件，生成图注并完成验收。"
    },
    en: {
      t: "Bioinformatics report coder",
      d: "Reusable report templates, renderers, tables, captions, and evidence-aware DOCX QA."
    }
  },
  {
    name: "module-development-scheduler",
    cat: "bio",
    status: "beta",
    tags: ["路由", "Matt", "工作流", "门禁", "report-only", "plot", "full"],
    repo: "https://github.com/sher-l/ai-skills/tree/main/skills/module-development-scheduler",
    zh: {
      t: "生信模块开发调度",
      d: "持续更新的 v2.2 调度器：把新建、迁移、优化和审查任务编译为确定的阶段、report-only/plot/full coder 顺序、领域门禁与唯一生命周期 owner。"
    },
    en: {
      t: "Module development scheduler",
      d: "Deterministic routing, coder order, domain checks, and one lifecycle owner for bioinformatics modules."
    }
  }
];
