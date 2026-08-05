# Journey 下一项任务

> Status: Completed — 2026-08-05 已由用户明确授权并执行
> 本文件只描述一个交接后的最近任务，不是第二份路线图。长期阶段仍以
> `docs/JOURNEY_REFACTOR_PLAN.md` 为唯一事实源。
>
> 用户本次将原定的“仅本地提交、不 push”授权扩展为：创建 GitHub 私有仓库
> `boom080/journey_v1` 并推送基线；仍未创建 PR。

## 任务名称

**建立迁移后的 Git 可回滚基线（新分支 + 单次提交 + 私有 GitHub 备份）**

## 为什么这是下一项

当前 `main` 的 HEAD 仍是旧微信版提交，工作区有 171 项未提交变化：16 Modified、87 Deleted、
68 Untracked（其中 2 项是本轮新增的根目录交接文档）。阶段 1—12 的新客户端、后端、数据库
迁移、Agent/RAG、测试、CI 和文档尚未进入
版本历史。继续开发完整 local-first 数据层之前，应先建立一个经过验证、无密钥、可审查、可
回滚的本地基线。

## 启动条件

用户必须在新对话中明确授权以下动作：

1. 创建本地分支 `codex/journey-migration-baseline`；
2. stage 当前已确认的迁移文件和旧微信端删除；
3. 创建一个本地 commit；
4. **不 push、不创建 PR、不修改 GitHub 远端**。

未经上述授权，只能继续只读审计，不得 stage、commit 或切换分支。

建议下一条 Codex 指令：

```text
执行 NEXT_TASK.md：建立迁移后的本地 Git 可回滚基线。允许创建
codex/journey-migration-baseline 分支、stage 已确认迁移文件并创建一次本地 commit；
禁止 push、PR 和远端修改。先复验测试与敏感信息边界，展示 staged 文件摘要后再提交。
```

## 操作步骤

- [ ] 阅读 `AGENTS.md`、`docs/README.md`、`PROJECT_STATUS.md` 和本文件。
- [ ] 执行并展示 `pwd`、`git status --short`、`ls -la`，确认仍是 Journey 工作区。
- [ ] 重新记录当前分支、HEAD、remote 和当前 171 项变化分类；若数量变化，先解释来源。
- [ ] 只读核对 `.gitignore`：`.env`、reports、artifacts、原生生成目录、dist、coverage、缓存和
  模型评测原始图片不得进入提交。
- [ ] 确认 `git ls-files .env` 无输出；只检查是否跟踪，不读取或打印 Key。
- [ ] 对将提交的文本运行 whitespace/密钥模式检查；不得把示例占位符误删，也不得打印真实
  secrets。
- [ ] 运行 `docker compose config --quiet` 和 Alembic `upgrade → downgrade → upgrade` 空库循环；
  不修改开发数据库。
- [ ] 使用隔离测试库运行后端 85 项测试、90.49% 覆盖率门禁、362 样本/26 项评测门禁。
- [ ] 运行 Requests + Pytest + Allure 独立黑盒，必须使用 Mock、空 Key、零预算。
- [ ] 运行移动端 TypeScript、Expo lint、33 项 Jest、5 项逻辑测试和 2 项 Web E2E。
- [ ] 至少运行 Web/iOS/Android JS export；任何真实 Provider 调用必须为 0。
- [ ] 创建 `codex/journey-migration-baseline` 本地分支。
- [ ] 分批 stage：先新架构/文档，再旧微信端删除；每批检查 `git diff --cached --name-status`。
- [ ] 明确排除 `.env`、`reports/`、`artifacts/`、`apps/mobile/ios/`、`apps/mobile/android/`、
  `apps/mobile/dist*`、coverage、缓存和密钥/签名文件。
- [ ] 展示最终 `git diff --cached --stat`、文件状态分类和敏感文件检查结果。
- [ ] 创建一次本地提交，建议消息：`refactor: migrate Journey to cross-platform agent app`。
- [ ] 验证提交存在、工作区无非预期未提交源码；不要 push，不要创建 PR。

## 验收标准

- 本地分支名为 `codex/journey-migration-baseline`；
- 产生一个包含完整迁移事实的本地 commit，父提交为当前旧微信版基线或其可解释后继；
- `git status --short` 不再出现应纳入迁移的源码/文档变化；
- `.env`、任何 API Key、报告、截图、原生构建缓存、签名材料均未被跟踪；
- Alembic 当前 head 仍为 `0005_agent_v3`，空库 upgrade/downgrade/upgrade 通过；
- 后端 85/85、黑盒 1/1、移动 Jest 33/33、逻辑 5/5、Web E2E 2/2 全部通过；
- 362 条 Mock 样本的 26 项门禁全部通过，外部调用和费用为 0；
- Web/iOS/Android JS export 通过；
- 没有 push、PR 或任何远程变更；
- `docs/EXECUTION_LOG.md` 记录命令、结果、提交哈希和未解决问题。

## 风险与回退

- **风险：误提交真实密钥。** 提交前必须验证 `.env` 未跟踪并检查 staged diff；发现即停止，
  不得用重写历史代替预防。
- **风险：误把生成目录加入 Git。** 只按 `.gitignore` 和 staged name-status 审查，不使用
  `git add -f`。
- **风险：旧微信删除范围判断错误。** 以阶段 2 退役清单和当前 87 个 tracked deletions 为依据；
  不恢复旧端，也不新增删除。
- **风险：测试失败。** 不创建 commit，保留工作区并记录失败；不得 reset/clean。
- **回退：** 分支或 commit 创建前可停止且不改变文件；commit 后如需撤销，必须由用户另行授权
  使用非破坏性 `git revert` 或新提交修正，禁止 `reset --hard`。

## 完成后才可开始的产品任务

本地 Git 基线完成后，下一产品任务应是 ADR-036 的单项实现规划：确认完整本地数据范围、账户
隔离、退出清理、版本冲突和 migration/测试方案。不得把该任务与小红书/Web Research 同时启动。
