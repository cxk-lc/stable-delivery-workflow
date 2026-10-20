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
- **开箱即用的工具**：项目初始化脚本 + 7 份文档模板 + 7 个提示词模板 + 风险诊断手册
- **按需伸缩**：简单需求走精简路径，复杂需求走完整流程
- **commit 语种可配置**：首次提交前确认；未手动指定时默认采用用户当前系统语言（自动检测，检测失败回退简体中文）
- **存量仓库安全**：初始化只提交本次创建的文件；已有暂存改动时跳过自动提交，不把 WIP / 未跟踪文件卷进首提

## 目录结构

```
stable-delivery-workflow/
├── SKILL.md                         # 技能主文件：五阶段工作流与执行指令
├── .github/workflows/ci.yml         # CI：lint + 回归测试（Linux / Windows）
├── scripts/
│   ├── init_project.py              # 项目初始化脚本（目录 + Git + AGENTS.md + docs 三份骨架 + 仅提交本次创建文件）
│   ├── check_project.py             # DoD 可执行校验器（护栏信号自查）
│   ├── lint_references.py           # 引用 / 占位符 / frontmatter lint（维护者发布前检查）
│   ├── build_release_zip.py         # 发布包构建：固定排除 .gitignore / .git / .github / 缓存
│   └── tests/                       # 脚本回归测试（T1-T13 / B1 / C1-C6 / L1-L5）
├── references/
│   ├── methodology.md               # 完整方法论：阶段详解 / 通用原则 / 风险全表
│   ├── prompt-templates.md          # 各阶段提示词模板（C-1 ~ C-7，可直接粘贴给编程代理）
│   ├── risk-playbook.md             # 风险诊断手册：症状 → 根因 → 动作
│   └── tooling-matrix.md            # 验证工具适配矩阵（能力 × 工具 + 能力齐备三问）
└── assets/                          # 模板唯一权威源
    ├── AGENTS.template.md           # 项目值班手册模板（交付硬规则）
    ├── product-design-template.md   # 产品设计文档模板
    ├── tech-design-template.md      # 技术方案文档模板
    ├── acceptance-checklist.md      # 人工验收清单模板
    ├── issue-report-template.md     # 问题反馈单模板（C-7 完整版）
    ├── release-record-template.md   # 发布记录模板（阶段五·发布）
    └── self-test-report-template.md # 自测报告模板（阶段四证据归档）
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

不安装技能，也可以用它一键搭好项目环境（前置依赖：Python 3.9+、Git；脚本只用标准库）：

```bash
python scripts/init_project.py ./my-app --name "我的应用"
```

脚本自动完成：创建目录 → `git init`（main 分支）→ 写入 AGENTS.md（交付硬规则）→ 创建 docs/ 三份骨架（产品设计 / 技术方案 / 验收清单）→ 写入 .gitignore → **仅提交本次创建的文件**。在已有仓库上运行时，不会覆盖已有文件、不会重复 init，也不会把已有未提交改动卷进首提；若检测到已有暂存改动，会跳过自动提交并提示手动处理。

初始化后可运行 `python scripts/check_project.py <项目目录>` 自查护栏信号（G1-G3 / A1 / D1 / V1 / A2 / V2；A2、V2 在对应阶段才纳入检查）。

常用参数：

| 参数 | 说明 |
|---|---|
| `--name` | 项目名称（默认取目录名） |
| `--commit-lang` | commit 信息语种（未指定时默认跟随用户当前系统语言，脚本自动检测；交互终端下会提示输入，回车采用默认值；支持 locale 代码如 `en-GB` / `zh-TW`） |
| `--commit-msg` | 自定义首次提交信息（用于 English / 简体中文 / 繁體中文之外的语种，或自定义文案） |
| `--remote` | 关联远端仓库 URL（git remote add origin） |
| `--no-commit` | 只搭建环境，不创建首次提交 |
| `--dry-run` | 只演练不落盘，输出将执行的步骤 |

> **commit 语种规则**：优先采用用户手动指定的语种（`--commit-lang` 或交互输入）；**仅当用户未手动指定时**，默认值生效——默认值为「用户当前系统所使用的语言」，由脚本自动检测（判断依据：Windows 取系统 UI 语言；macOS / Linux 取 `LANG`、`LC_ALL`、`LC_MESSAGES` 环境变量），检测失败回退简体中文。内置首次提交模板支持 English / 简体中文 / 繁體中文；其他语种请加 `--commit-msg`，或先用 `--no-commit` 搭环境后手动提交。

## 五阶段一览

| 阶段 | 一句话 | 产出 |
|---|---|---|
| ① 环境搭建 | Git + AGENTS.md，一次性基座 | 受控项目环境 |
| ② 产品设计 | 砍到 MVP，写成文档 | 产品设计文档 |
| ③ 技术设计 | 只锁定大方向 | 技术方案文档 |
| ④ 产品实现 | 代理实现 + 自测 | 可运行版本 |
| ⑤ 人工验证 | 亲自试用，人签验收 | 验收结论 |

> 完整方法（阶段详解、通用原则、风险清单、执行清单）见 [`references/methodology.md`](references/methodology.md)。

## 维护者指引

发布前运行两项检查（均为标准库实现，零依赖；CI 也会跑）：

```bash
python scripts/lint_references.py                 # 路径 / 占位符 / frontmatter 检查
python -m unittest discover -s scripts/tests -v   # 25 个回归测试（T/B/C/L）
python scripts/build_release_zip.py --output stable-delivery-workflow.zip
```

版本语义：**patch** = 勘误 / 死链 / 措辞修复；**minor** = 能力新增；**major** = 阶段模型或护栏规则变更。

### 发布命名约定（固定）

| 对象 | 规则 | 示例 |
|---|---|---|
| Release 标题 | `<包名>-v<版本>` | `stable-delivery-workflow-v1.4.0` |
| Release 附件 | 固定 `<包名>.zip` | `stable-delivery-workflow.zip` |
| Git tag | `v<版本>` | `v1.4.0` |

附件内顶层目录固定为 `<包名>/`（如 `stable-delivery-workflow/`），确保 Cursor 等要求“目录名与 `name` 一致”的工具可以直接使用。

**附件固定不包含 `.gitignore`**（以及 `.git/`、`.github/`、`__pycache__/` 等缓存）；请用 `scripts/build_release_zip.py` 生成，避免手工打包带入。

发布纪律：`lint + 测试 → 更新 CHANGELOG → 升版本号 → 打 annotated tag → build_release_zip → gh release create`；变更记录见 [CHANGELOG.md](CHANGELOG.md)。

```bash
python scripts/build_release_zip.py --output stable-delivery-workflow.zip
gh release create vX.Y.Z stable-delivery-workflow.zip \
  --title "stable-delivery-workflow-vX.Y.Z" --verify-tag
```

## 版本

当前版本：**v1.4.0**

## 来源与致谢

方法论源自 B 站视频《我的 AI 编程全流程：如何使用 AI 稳定交付一个高质量的产品》（UP 主：马克的技术工作坊）的内容提炼与体系化整理。
