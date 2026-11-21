---
record: handoff
project: {{PROJECT_NAME}}
mode: {{MODE_KEY}}
mode_label: {{MODE_LABEL}}
branch: {{BRANCH}}
head: {{HEAD}}
updated_at: {{UPDATED_AT}}
---

# 开发进度交接记录 · {{PROJECT_NAME}}

> 用途：跨会话交接的唯一进度接口——新会话先读本文件，再读关联设计文档，不要依赖聊天记忆。
> 生成：`python scripts/handoff_record.py update <项目目录>`（阶段四流程与独立调用共用同一套生成逻辑）。
> 门禁：每次 commit 前更新本记录，或执行 `python scripts/handoff_record.py check <项目目录> --stamp`；pre-commit 钩子会强制校验。
> 必填七节：已完成内容 / 变更范围 / 关键决策 / 未完成事项 / 风险或阻塞 / 下一步计划 / 关联设计文档。

## 1. 已完成内容

<!-- AUTO:COMPLETED -->

## 2. 变更范围

<!-- AUTO:SCOPE -->

## 3. 关键决策

<!-- AUTO:DECISIONS -->

## 4. 未完成事项

<!-- AUTO:PENDING -->

## 5. 风险或阻塞

<!-- AUTO:RISKS -->

## 6. 下一步计划

<!-- AUTO:NEXT -->

## 7. 关联设计文档

<!-- AUTO:DESIGN -->

## 8. 更新记录

<!-- AUTO:HISTORY -->

## 9. 交接提示

<!-- AUTO:NOTES -->
