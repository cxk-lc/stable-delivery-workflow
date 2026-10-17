# 发布记录 · {{PROJECT_NAME}}

> 用途：为每个对外发布的版本留存可追溯记录（阶段五"若需发布"的产出物）。
> 归档位置：`docs/release-record.md`（每个版本追加一节）；验收通过后再发布。

## vX.Y.Z · YYYY-MM-DD

### 1. 版本号

（语义：patch = 勘误 / 死链 / 措辞；minor = 能力新增；major = 流程或护栏规则变更）

### 2. 变更摘要

- 

### 3. 验证证据

- 测试：（命令 + 结果摘要）
- 人工验收：`docs/acceptance-checklist.md` 结论（通过 / 有条件通过）、验收人、日期

### 4. 已知问题

- 

### 5. 回滚指令

```bash
git checkout <上一个稳定 tag>
```
