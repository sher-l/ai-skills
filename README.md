# bio-dev · 生信数据分析技能库

> 让 AI 成为你的生信分析伙伴。

**bio-dev** 是一套面向 AI Agent（Codex / Claude Code / ZCode / OpenCode 等）的生物信息学技能库，从 **60+ 份真实交付的数据分析报告**与 **900+ 个 R 分析脚本**中提炼而成，覆盖转录组、单细胞、GBD 疾病负担、孟德尔随机化、网络药理学、机器学习标志物筛选与免疫微环境等主流分析场景。

在线页面：<https://sher-l.github.io/bio-dev/>

## 技能索引

| 技能 | 领域 | 状态 |
| --- | --- | --- |
| `bulk-rna-seq` | 转录组差异分析（DESeq2 / limma / GSEA） | stable |
| `sc-rna-seq` | 单细胞转录组（Seurat / 注释 / 细胞通信） | beta |
| `gbd-analysis` | GBD 疾病负担（趋势 / APC / 预测） | stable |
| `mendelian-randomization` | 两样本 MR / 中介 / 敏感性分析 | stable |
| `network-pharmacology` | 成分-靶点 / PPI / 分子对接 | beta |
| `ml-biomarker` | LASSO / RF / 列线图 | beta |
| `immune-microenvironment` | 浸润估计 / TMB / 免疫分型 | beta |
| `cell-death-landscape` | 程序性细胞死亡与代谢景观 | draft |
| `fig-publish` | 出版级图表规范 | draft |
| `report-writer` | 交付报告结构与语言规范 | draft |

## 安装

```bash
# 通过 skills 注册表全局安装
npx skills add sher-l/bio-dev -g

# 或手动克隆
git clone https://github.com/sher-l/bio-dev ~/.claude/skills/bio-dev
```

## 仓库结构

```
bio-dev/
├── index.html      # 落地页（单文件，无构建依赖）
├── skills/         # 技能目录（建设中，逐版本填充）
└── README.md
```

技能本体按 `skills/<name>/SKILL.md` 的契约组织，随路线图逐步落地。

## 路线图

- **v0.1** 技能框架与语料整理（当前）
- **v0.2** 转录组 + 单细胞 + 机器学习标志物
- **v0.3** GBD 与孟德尔随机化
- **v1.0** 全域稳定版 + 英文文档

## 部署页面

仓库根目录的 `index.html` 即为完整页面，GitHub Pages 开启后自动可用：

Settings → Pages → Deploy from a branch → `main` / root。

## 致谢

页面设计参考了 [nature-skills](https://yuan1z0825.github.io/nature-skills/) 与 [archify](https://tt-a1i.github.io/archify/) 的技能库落地页风格。

## License

MIT
