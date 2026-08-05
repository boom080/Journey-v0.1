# 微信端退役执行清单

> 基线 commit：`06b52f024547e76e1cd216e27f3ac41717dd3671`
> 生成日期：2026-07-16
> 当前状态：**Completed**
> 授权记录：用户在审阅截图、真实登录失败事实和本清单后指示“请按计划推进”。

## 1. 退役目标

从活动工作树移除微信小程序表现层、Taro 构建链和任何实际旧 SQLite 数据文件，
不在仓库保留 `legacy/miniapp` 副本。后端微信身份与 `_mini` 业务模块按照
ADR-020 保留为阶段 3/4 的短期迁移桥，待新身份、PostgreSQL 和 `/api/v1`
契约通过测试后删除。保留品牌资产、业务规则文档、FastAPI 可复用代码和 Git 历史。

## 2. 删除前门禁

只有以下项目全部完成后，才能请求最终删除确认：

- [x] 记录基线 commit 和工作树状态。
- [x] 完成全部品牌资产尺寸、哈希、引用和来源状态清单。
- [x] 将 4 个品牌资产逐字节复制到 `assets/brand/` 并校验。
- [x] 完成旧页面结构、设计 token、关键文案和状态矩阵。
- [x] 完成全部 `src/utils/` 和后端核心逻辑迁移矩阵。
- [x] 生成前端、生成物、数据库和后端耦合模块的删除/替换清单。
- [x] 验证全部待删已跟踪前端文件可从基线 commit 恢复。
- [x] 验证被忽略的 `dist/`、`node_modules/`、`.swc/` 均为可重建生成物。
- [x] 检查当前没有旧 SQLite `.db/.sqlite/.sqlite3` 文件。
- [x] 使用微信开发者工具完成 14 张运行截图并逐张检查；明确记录真实微信登录不可用，受保护页面仅通过虚拟本地会话进入。
- [x] 用户审阅本清单并明确授权实际删除。

## 3. 已保留，不得删除

- `assets/brand/`：4 个已校验品牌资产及说明。
- `docs/`：单一计划、ADR、审计、技术调研、执行日志和本阶段提取文档。
- `AGENTS.md`：Codex 规则。
- `.git/`：唯一旧源码回退来源。
- `backend/` 中的 FastAPI 可复用领域/AI 逻辑，直到对应的新模块和测试完成。
- `.gitignore`：阶段 3 更新后继续使用。

## 4. 第一批删除候选：微信/Taro 客户端

以下内容可以在真实截图门禁和用户确认后一次性退出活动工作树。

### 4.1 Git 跟踪的前端源码（57 个文件）

- [x] 删除整个 `src/`（49 个已跟踪文件）。
- [x] 删除整个 `config/`（4 个已跟踪文件）。
- [x] 删除 `package.json`。
- [x] 删除 `package-lock.json`。
- [x] 删除 `babel.config.js`。
- [x] 删除 `project.config.json`。

`src/` 删除范围明确包含：

- Taro app 入口和 tabBar 配置。
- 7 个页面及页面配置。
- Taro 组件、services、store、router、page guard。
- 旧 SCSS；其 token 已记录，但不作为 React Native 样式直接保留。
- 14 个 JS utility；其规则已写入迁移矩阵，后续按测试重建。
- 原 `src/assets/`；所有视觉文件已复制到 `assets/brand/` 并校验。

### 4.2 Git 忽略的本地生成物/缓存

这些目录不在 Git 历史中，但均可重建；删除前仍需先展示精确文件列表和目录大小：

- [x] `dist/`：已删除；可由基线 commit 的源码和 lock 重建。
- [x] `.swc/`：已删除。
- [x] `node_modules/`：已删除；包括截图阶段临时自动化 SDK。

删除时不得使用 `rm -rf`。应先展示目标清单，再使用仅作用于上述精确路径的可审查删除方式。

### 4.3 根环境示例和 README

- [x] 删除根 `.env.example` 中唯一的 `TARO_APP_API_BASE_URL`；阶段 3 写入新的统一模板。
- [x] 重写根 `README.md`，说明微信端已退役、当前阶段和后续启动方式。

## 5. 旧 SQLite 数据

当前检查结果：`backend/` 下没有 `.db`、`.sqlite` 或 `.sqlite3` 文件。

- [x] 确认当前无可删除数据库文件。
- [ ] 如果实际删除前运行旧后端产生 `backend/journey_miniapp.db`，先展示路径和大小，再经同一确认删除；不迁移内容。
- [ ] 阶段 3 用 PostgreSQL/Alembic 替换默认 SQLite 连接。
- [ ] 阶段 3 删除 `core/bootstrap.py` 的 SQLite 补列逻辑。

## 6. 后端微信/mini 耦合：分批替换，而非现在整块删除

### 为什么不能与前端同时整块删除

现有 FastAPI 的全部业务路由都依赖 `deps_mini.py` 和微信 `User`，而可复用的首页、Journey、Food、Activity 与 AI 逻辑也位于 `_mini` 文件中。现在整块删除会让后端完全不可导入，并违反 ADR-006“保留 FastAPI、渐进重构”。

后端分为“纯微信身份，阶段 4 首先替换”和“业务 `_mini`，新 API 验收后删除”两组。该桥接策略已由 ADR-020 接受。

### 6.1 纯微信/邀请码模块：阶段 4 身份替换后删除

- [ ] `backend/app/core/wechat.py`
- [ ] `backend/app/api/routes/auth_mini.py`
- [ ] `backend/app/api/deps_mini.py`
- [ ] `backend/app/crud/user_mini.py`
- [ ] `backend/app/crud/invite_code.py`
- [ ] `backend/app/models/invite_code.py`
- [ ] `backend/app/schemas/auth.py`
- [ ] `backend/scripts/manage_invite_codes.py`
- [ ] `backend/app/models/user.py` 中的 `openid`、`unionid`、邀请码和 activated 字段：由全新 User/Identity schema 替换，不直接原地删列。
- [ ] `backend/.env.example` 中的 `WECHAT_*` 配置。

### 6.2 业务 `_mini` 模块：中性应用服务/API 通过测试后删除

- [ ] `backend/app/api/routes/food_records_mini.py`
- [ ] `backend/app/api/routes/activity_records_mini.py`
- [ ] `backend/app/api/routes/profile_mini.py`
- [ ] `backend/app/api/routes/home_mini.py`
- [ ] `backend/app/api/routes/journey_mini.py`
- [ ] `backend/app/api/routes/ai_mini.py`
- [ ] `backend/app/schemas/food_record_mini.py`
- [ ] `backend/app/schemas/activity_record_mini.py`
- [ ] `backend/app/schemas/profile_mini.py`
- [ ] `backend/app/schemas/home_mini.py`
- [ ] `backend/app/schemas/journey_mini.py`
- [ ] `backend/app/schemas/ai_mini.py`
- [ ] `backend/app/services/home_mini.py`
- [ ] `backend/app/services/journey_mini.py`
- [ ] `backend/app/main.py` 中全部旧 router 注册和旧阶段文案。

这些文件不是长期保留项。对应能力必须先迁入中性 `api/v1`、domain/service 和 Agent 模块，并有 characterization/contract 测试，随后在同一阶段删除旧模块。

### 6.3 适配后保留的后端候选

- `backend/app/services/ai_client.py`
- `backend/app/services/ai_service.py`
- `backend/app/services/ai_fallback.py`
- `backend/app/crud/food_record.py`
- `backend/app/crud/activity_record.py`
- `backend/app/models/food_record.py`
- `backend/app/models/activity_record.py`
- `backend/app/core/logging.py`

“保留”指提取思想或重构代码，不表示这些旧文件名永久存在。

## 7. Git 可恢复性证据

| 范围 | 已跟踪文件数 | 恢复来源 | 结果 |
|---|---:|---|---|
| `src/` | 49 | 基线 commit | 可恢复 |
| `config/` | 4 | 基线 commit | 可恢复 |
| 4 个根构建文件 | 4 | 基线 commit | 可恢复 |
| `backend/` | 45 | 基线 commit | 可恢复 |
| `dist/` | 0 | 由基线源码和 lock 重建 | 可重建，不是唯一资产 |
| `node_modules/` | 0 | 由基线 lock 重建 | 可重建 |
| `.swc/` | 0 | 编译产生 | 可重建 |

检查结果：`src/`、`config/`、`backend/app/`、`backend/scripts/` 当前没有未跟踪源码文件。新建的 `assets/brand/` 和本阶段文档尚未提交，因此实际删除前仍应再次确认它们存在且哈希正确。

## 8. 计划修正提案

原阶段 2 验收写有“工作树不再包含 `_mini`”。这与 ADR-006 的渐进后端重构存在冲突。建议修正为：

> 阶段 2 完成后不再包含微信/Taro 客户端和活动微信登录能力；业务 `_mini` 后端代码可以作为短期迁移桥保留到阶段 4，但不得继续新增功能，并必须在新 API 验收后删除。

- **Status: Accepted**
- [x] 用户审阅并接受该修正；ADR 和唯一计划已更新。

## 9. 实际删除后的验证

- [x] 活动客户端范围内 `@tarojs|Taro\.|wx\.` 无结果。
- [x] `WECHAT_|openid|unionid|wechat-login|verify-invite|_mini` 只存在于明确保留的后端迁移桥和历史/审计文档。
- [x] `git diff --name-status` 显示 58 个已授权退役文件删除；另有用户此前删除的两份旧文档和本阶段文档/README 变更。
- [x] `assets/brand/` 四个视觉文件 SHA-256 与资产清单一致。
- [x] `backend/.venv/bin/python -m compileall -q -f backend/app backend/scripts` 通过。
- [x] 更新 `CURRENT_PROJECT_AUDIT.md`、`EXECUTION_LOG.md`、计划、ADR 和文档索引。
- [x] 停止，不自动开始 Docker、PostgreSQL 或 Expo 阶段。
