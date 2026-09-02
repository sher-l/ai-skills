# bio-dev

> 我的生信 AI 技能库 —— sher-l 的生物信息学分析技能，供 Codex / Claude Code / ZCode 等 Agent 直接调用。

在线页面：<https://sher-l.github.io/bio-dev/>

## 页面维护

页面是**零构建依赖**的单文件静态站：

```
bio-dev/
├── index.html   # 页面框架（设计参考 nature-skills / archify）
├── skills.js    # 技能清单 —— 在这里添加你自己的技能
└── README.md
```

添加技能只需编辑 `skills.js`，往 `window.BIO_DEV_SKILLS` 数组里加一条记录（文件内有字段说明和示例），技能卡片、分类筛选、首页统计数字都会自动生成。

技能本体建议放在仓库的 `skills/<技能名>/` 目录下，每个技能一个自包含目录（`SKILL.md` 契约 + 参考实现），页面卡片可通过 `repo` 字段链接到对应目录。

## 安装（技能库充实后）

```bash
# 通过 skills 注册表全局安装
npx skills add sher-l/bio-dev -g

# 或手动克隆
git clone https://github.com/sher-l/bio-dev ~/.claude/skills/bio-dev
```

## 部署页面

GitHub Pages 开启后自动可用：Settings → Pages → Deploy from a branch → `main` / root。

## 致谢

页面设计参考了 [nature-skills](https://yuan1z0825.github.io/nature-skills/) 与 [archify](https://tt-a1i.github.io/archify/) 的技能库落地页风格。

## License

MIT
