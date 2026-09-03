# ai-skills

> 我的 AI 技能库 —— 供 Codex / Claude Code / ZCode 等 Agent 直接调用。

在线页面：<https://sher-l.github.io/ai-skills/>

当前生信 skill 按 v2.2 规范发布：代码 coder、DOCX-first 报告 coder 和模块调度器彼此独立；secure_dev 的
`develop-module` 负责把它们组合到同一个生命周期。

## 页面维护

页面是**零构建依赖**的单文件静态站：

```
ai-skills/
├── index.html   # 页面框架
├── skills.js    # 技能清单 —— 在这里添加你自己的技能
└── README.md
```

添加技能只需编辑 `skills.js`，往 `window.AI_SKILLS` 数组里加一条记录（文件内有字段说明和示例），技能卡片、分类筛选、首页统计数字都会自动生成。

技能本体建议放在仓库的 `skills/<技能名>/` 目录下，每个技能一个自包含目录（`SKILL.md` 契约 + 参考实现），页面卡片可通过 `repo` 字段链接到对应目录。

## 安装（技能库充实后）

```bash
# 通过 skills 注册表全局安装
npx skills add sher-l/ai-skills -g

# 或手动克隆
git clone https://github.com/sher-l/ai-skills ~/.claude/skills/ai-skills
```

## 部署页面

GitHub Pages 开启后自动可用：Settings → Pages → Deploy from a branch → `main` / root。

## License

MIT
