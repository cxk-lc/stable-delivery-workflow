# stable-delivery-workflow（稳定交付工作流）

> 让编程代理（Codex / Claude Code / Cursor 等）稳定交付高质量产品的五阶段闭环技能包。

## 这是什么

本仓库是一个可直接安装使用的**编程代理技能包**：把"用 AI 稳定交付高质量产品"的方法论落地为可执行流程。

它在 **可回退（Git）、可自检（代理自测）、可验收（人工验证）** 三重护栏内，用"规格 → 实现 → 验证"的闭环驱动编程代理工作，针对性解决三类高频失败：

- 交付物偏离预期——"做出来的不是我想要的"
- 无法运行或缺陷密集——"连启动都过不了"
- 越改越乱——"修好一个、坏了两个，还无法回退"

## 核心特性

- **五阶段闭环**：环境搭建 → 产品设计 → 技术设计 → 产品实现 → 人工验证
- **三重护栏（不可裁剪）**：Git 版本管理、代理自测能力、人工验证
- **开箱即用的工具**：项目初始化脚本 + 4 类文档模板 + 7 个提示词模板 + 风险诊断手册
- **按需伸缩**：简单需求走精简路径，复杂需求走完整流程
- **commit 语种可配置**：首次提交前确认，默认简体中文

## 目录结构

```
stable-delivery-workflow/
├── SKILL.md                         # 技能主文件：五阶段工作流与执行指令
├── scripts/
│   └── init_project.py              # 项目初始化脚本（目录 + Git + AGENTS.md + docs 骨架 + 首次提交）
├── references/
│   ├── methodology.md               # 完整方法论：阶段详解 / 通用原则 / 风险全表
│   ├── prompt-templates.md          # 各阶段提示词模板（C-1 ~ C-7，可直接粘贴给编程代理）
│   └── risk-playbook.md             # 风险诊断手册：症状 → 根因 → 动作
└── assets/
    ├── AGENTS.md.template           # 项目值班手册模板（交付硬规则）
    ├── product-design-template.md   # 产品设计文档模板
    ├── tech-design-template.md      # 技术方案文档模板
    └── acceptance-checklist.md      # 人工验收清单模板
```

## 快速开始

### 方式一：安装为技能

将本目录（或 Release 附件中的 `stable-delivery-workflow.zip` 解压后）放入目标软件的**技能目录**即可。技能遵循开放的 Agent Skills 规范（Anthropic 开源，已被主流工具广泛支持），各软件的目录约定如下：

| 软件 | 用户级目录（所有项目生效） | 项目级目录（仅该项目生效） |
|---|---|---|
| **WorkBuddy** | `~/.workbuddy/skills/stable-delivery-workflow/` | `<项目>/.workbuddy/skills/stable-delivery-workflow/` |
| **ChatGPT / Codex**（OpenAI） | `~/.agents/skills/stable-delivery-workflow/` | `<项目>/.agents/skills/stable-delivery-workflow/`（或 `.codex/skills/`） |
| **DeepSeek Harness**（DSH） | `~/.dsh/skills/stable-delivery-workflow/` | `<项目>/.dsh/skills/stable-delivery-workflow/`（或 `.agents/skills/`） |
| **Claude Code** | `~/.claude/skills/stable-delivery-workflow/` | `<项目>/.claude/skills/stable-delivery-workflow/` |
| **Cursor** | `~/.cursor/skills/stable-delivery-workflow/` | `<项目>/.cursor/skills/stable-delivery-workflow/` |
| **Gemini CLI** | `~/.gemini/skills/stable-delivery-workflow/` | `<项目>/.gemini/skills/stable-delivery-workflow/` |

> - `~/.agents/skills/` 是跨工具通用目录（Codex、Cursor、DSH、Gemini CLI 等均可识别）；多个工具共用一套技能时可只维护一份，或用软链接分发。
> - Windows 下 `~` 即 `C:\Users\<用户名>`；项目级目录相对于项目根目录。
> - ChatGPT 网页版可在应用内 Skills 面板 / 插件市场安装；上表本地目录适用于 Codex 与 ChatGPT 桌面版。
> - 安装后需**新开会话或重启软件**才会被识别；Cursor 还要求 SKILL.md 中的 name 与文件夹名完全一致。
> - Kimi、GLM 等其他支持 Agent Skills 的工具，按其官方文档将本目录放入对应的 skills 路径即可（各软件版本迭代可能调整路径，以官方文档为准）。

之后在对话中提到"用编程工具启动新项目""为新项目搭建 Git + AGENTS.md 环境""AI 产出不符合预期"等场景时，技能会自动生效。

### 方式二：直接使用初始化脚本

不安装技能，也可以用它一键搭好项目环境：

```bash
python scripts/init_project.py ./my-app --name "我的应用"
```

脚本自动完成：创建目录 → `git init`（main 分支）→ 写入 AGENTS.md（交付硬规则）→ 创建 docs 骨架 → 写入 .gitignore → 首次提交。

常用参数：

| 参数 | 说明 |
|---|---|
| `--name` | 项目名称（默认取目录名） |
| `--commit-lang` | commit 信息语种（默认简体中文；交互终端下会提示输入） |
| `--commit-msg` | 自定义首次提交信息（用于非中文语种） |
| `--remote` | 关联远端仓库 URL（git remote add origin） |
| `--no-commit` | 只搭建环境，不创建首次提交 |

## 五阶段一览

| 阶段 | 一句话 | 产出 |
|---|---|---|
| ① 环境搭建 | Git + AGENTS.md，一次性基座 | 受控项目环境 |
| ② 产品设计 | 砍到 MVP，写成文档 | 产品设计文档 |
| ③ 技术设计 | 只锁定大方向 | 技术方案文档 |
| ④ 产品实现 | 代理实现 + 自测 | 可运行版本 |
| ⑤ 人工验证 | 亲自试用，人签验收 | 验收结论 |

> 完整方法（阶段详解、通用原则、风险清单、执行清单）见 [`references/methodology.md`](references/methodology.md)。

## 版本

当前版本：**v1.0.0**

## 来源与致谢

方法论源自 B 站视频《我的 AI 编程全流程：如何使用 AI 稳定交付一个高质量的产品》（UP 主：马克的技术工作坊）的内容提炼与体系化整理。
