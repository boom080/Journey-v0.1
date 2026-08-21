# Journey 下一项任务

> Status: Proposed — 需要用户单独确认后执行
> 本文件只描述最近一个工程任务，不是第二份路线图。长期阶段仍以
> `docs/JOURNEY_REFACTOR_PLAN.md` 为唯一事实源。

## 任务名称

**建立阶段 8/12/13 的本地 Git 交付基线（默认不 push）**

## 当前前置事实

- 阶段 13 已完成，ADR-039 有限 Multi-Agent 与 RAG Eval 已为 Accepted；阶段 12 的 ADR-036
  local-first 与 ADR-037 生活灵感同样保持 Accepted；
- 当前分支为 `codex/journey-migration-baseline`，HEAD `2654c4308279`；
- 2026-08-13 封板维护后有 120 项未提交变化：90 项已跟踪修改、30 项未跟踪，覆盖服务器
  Docker、local-first、生活灵感、有限 Multi-Agent、RAG Eval、静息能量口径、测试和文档；
- ADR-040 已 Accepted：真实 Agent 客户端超时/Resume 对账和静息能量估算完成；真实 DeepSeek
  v4 Pro 周总结 smoke 20.4 秒返回 HTTP 200、3 条引用、无降级；
- 当前全量证据为后端 100/100、覆盖率 90.69%，移动 Jest 48/48 + 逻辑 5/5、Mock 与真实复合 Requests 黑盒、
  Mock Web E2E 2/2、RAG v2 真实 60 题门禁、Web 14 路由、iOS/Android Hermes export 与
  Alembic `0007` head；
- 本任务不包含新功能、远程 push、PR、公网部署或商店发布。

## 启动条件

用户明确回复授权“复核并创建本地提交”。如果用户同时要求 push，必须把远端和分支写清楚；
否则只允许本地 commit。

## 操作步骤

- [ ] 重新执行并展示 `pwd`、`git status`、`ls -la`，确认仍在当前 Journey 根目录。
- [ ] 按阶段 8 production、ADR-036、ADR-037、ADR-039、Eval 与文档分组审查 `git diff`，确认
  没有无关或生成文件。
- [ ] 复核 `.env`、真实模型 Key、Token、私钥、签名文件、数据库 dump、原始健康文本和用户图片
  均未被跟踪；不读取或输出密钥值。
- [ ] 运行 `git diff --check`、Markdown 链接检查、Compose config、Alembic head/check、后端全量、
  移动 typecheck/lint/test 和必要的 Mock E2E；若代码未变化可引用本阶段相邻证据，但敏感信息与
  diff 检查必须重跑。
- [ ] 更新 `docs/EXECUTION_LOG.md`、`PROJECT_STATUS.md` 和 `qiuzhaomianshi.md`，记录最终文件数、
  测试结果、提交边界与未完成风险。
- [ ] 只 stage 已审查的项目文件，复核 staged diff 和敏感信息扫描，再创建一个语义清晰的本地
  提交；不得自动 push 或创建 PR。

## 验收标准

- staged 文件与阶段 8/12/13 范围一致，生成文件、密钥、机器报告、原生构建缓存进入提交的
  数量为 0；版本化的匿名 Eval Dataset/报告除外；
- 所有文档对阶段状态、测试数量、Alembic head 和生活灵感边界表述一致；
- 本地提交成功，提交后工作区干净，或只剩用户明确要求保留的未提交文件；
- 未向任何远端 push，未创建 PR，未修改 GitHub 仓库设置；
- 提交失败或发现敏感信息时立即停止，不通过 reset/clean 隐藏问题。

## 不在本任务内

- 不新增 Agent、RAG、图片、语音、视频、健康平台或社交平台能力；只允许修复审查发现的问题；
- 不修改数据库业务 Schema，不升级全部依赖，不执行 `npm audit fix --force`；
- 不租服务器、不部署公网、不创建签名或商店制品；
- 不执行 `git reset --hard`、`git clean`、强制 checkout、push 或 PR。
