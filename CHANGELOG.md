# Changelog

本项目遵循 Keep a Changelog 精简风格；版本语义见 README「维护者指引」：
**patch** = 勘误 / 死链 / 措辞修复；**minor** = 能力新增；**major** = 阶段模型或护栏规则变更。

## [v1.3.0] - 2026-10-17

### Added
- `init_project.py` 新增 `--dry-run`：只演练不落盘，输出「将执行」步骤
- 回归测试扩展至 T1–T8（干跑 / 语种优先级 / 非交互 / 已有仓库 / 参数组合 / assets 缺失降级）
- `assets/release-record-template.md`：发布记录模板（版本号 / 变更摘要 / 验证证据 / 已知问题 / 回滚指令）
- SKILL.md 阶段五 DoD 增补「若发布」条件项；methodology 阶段五与 7.3 清单联动

### Changed
- README 维护者指引补充发布纪律（lint + tests → CHANGELOG → 版本号 → tag）

## [v1.2.0] - 2026-10-17

### Added
- DoD 可执行校验器 `scripts/check_project.py`（G1-G3 / A1 / D1 / V1 + C1 提示）
- 问题反馈模板 `assets/issue-report-template.md`；验证工具矩阵 `references/tooling-matrix.md`
- 引用完整性 lint `scripts/lint_references.py`

### Changed
- SKILL.md 去重瘦身至 6,138 字节（-39%），明确与 methodology 的权威关系
- README 新增维护者指引

## [v1.1.1] - 2026-10-17

### Fixed
- 分发死链：`assets/AGENTS.md.template` → `assets/AGENTS.template.md`（保住 .md 后缀以通过打包过滤），同步全部引用

### Added
- 验收清单随初始化落地（`docs/acceptance-checklist.md`，含 `ACCEPTANCE_FALLBACK` 兜底）
- 最小回归测试 T1/T2（`scripts/tests/`）

### Changed
- 模板权威源统一：`assets/` 为唯一权威源，4 个兜底常量逐字对齐
- methodology 附录 B 补齐「边界约定」

## [v1.1.0] - 2026-10-16

### Added
- commit 语种默认值改为跟随用户系统语言（Windows LANGID / `LC_*` / locale 三级检测）

## [v1.0.0] - 2026-10-15

### Added
- 首版：五阶段闭环 + 三重护栏、初始化脚本、模板体系、提示词模板 C-1~C-7、风险诊断手册
