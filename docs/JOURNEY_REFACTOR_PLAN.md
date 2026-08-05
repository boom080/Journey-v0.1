# Journey 系统性升级执行计划

> 版本：1.0
> 更新日期：2026-08-03
> 状态：阶段 8 Completed；阶段 9 食物图片 Closed / No-Go；阶段 10 Agent v2 与测试报告
> 增强已于 2026-08-03 完成，ADR-034 已转 Accepted。当前没有自动推进的新阶段。
> 本文件是唯一迁移计划；后续 Codex 必须一次只执行一个阶段。

## 0. 最终目标与范围

Journey 是 Agent 增强的跨平台健身、营养和生活方式管理应用：

- 三个一级入口：首页、Journey、我的。
- 首页统一输入自动识别饮食、运动、知识咨询、历史查询、画像和建议意图。
- 所有 Agent 写入由用户逐项确认。
- Expo Development Build + iOS Simulator 为主演示；Android Emulator 为跨平台验收；Web 为补充。
- FastAPI、PostgreSQL、Agent、RAG 和测试由各端共享。
- 本地 Docker 负责 API/数据库；模拟器运行在宿主机；生产打包后置。
- 产品不提供医疗诊断或治疗建议。

MVP 闭环：测试账号登录 → 画像与目标 → 首页自然语言记录饮食/运动 → 确认写入 → 首页/Journey 更新 → 个性化建议 → 周总结 → Agent 轨迹与量化评测报告。

## 1. 全局执行规则

- [ ] 开始阶段前阅读 `AGENTS.md`、`docs/README.md`、本计划和相关 ADR。
- [ ] 执行并展示 `pwd`、`git status`、`ls -la`，确认只操作当前目录。
- [ ] 检查用户未提交改动，不覆盖、不清理、不强制重置。
- [ ] 每次只把一个阶段标记为 `In Progress`。
- [ ] 每个已完成 Checklist 都附测试或审查证据。
- [ ] 阶段完成后更新 `docs/EXECUTION_LOG.md`、文档索引和必要 ADR。
- [ ] 验收失败时停止在当前阶段，不自行扩大范围。
- [ ] 未获单独授权时不 commit、不 push、不创建 PR。
- [ ] 不使用真实密钥或生产个人健康数据进行开发和测试。
- [ ] 完成阶段后停止，不自动开始下一阶段。

---

## 阶段 1：决策与基线固化

**Status: Completed（2026-07-15）**

### 阶段目标

把共同理解、旧代码事实、Agent 技术选择、阶段边界和后续 Codex 规则固化成单一事实源，不修改业务代码。

### 前置条件

- 用户已确认 grill-me 访谈中的架构、产品和执行决策。
- 当前目录是 Journey 仓库且 Git 状态已核对。

### 涉及目录

- `AGENTS.md`
- `docs/`

### 具体任务

- [x] 记录当前工作树和旧项目技术事实。
- [x] 建立根目录 `AGENTS.md`，定义 Codex 入口和安全规则。
- [x] 建立 `docs/README.md` 文档索引与阶段状态。
- [x] 建立本文件作为唯一迁移计划。
- [x] 建立 `docs/ARCHITECTURE_DECISIONS.md`，记录所有已确认决策。
- [x] 建立 `docs/CURRENT_PROJECT_AUDIT.md`，区分代码事实和未来目标。
- [x] 建立 `docs/AGENT_TECH_RESEARCH.md`，记录官方仓库、维护快照与选型边界。
- [x] 建立 `docs/EXECUTION_LOG.md` 并写入阶段 1 的实际证据。
- [x] 合并并退役平行的 `docs/JOURNEY_ROADMAP.md`。
- [x] 检查所有相对链接、状态和术语是否一致。
- [x] 用 Git 状态和 diff 确认没有业务代码改动。
- [x] 将阶段状态更新为 `Completed` 并明确阶段 2 的启动指令。

### 验收标准

- 六份核心文档和根目录规则文件均存在，链接可解析。
- 每项已确认决策有 ADR；未决定版本均标记 `Proposed`。
- 本计划每个阶段都有目标、前置、目录、任务、验收、测试、风险、回退、文件、禁止事项和下一阶段入口。
- Git diff 仅包含文档体系和用户此前已要求删除的旧文档，不含业务代码。

### 测试方式

- `rg --files AGENTS.md docs`
- `rg -n "Status: Proposed|Status: Accepted|Status: In Progress" docs AGENTS.md`
- 运行 Markdown 相对链接存在性检查。
- `git diff --stat` 与 `git diff --name-status`。

### 风险

- 多份计划并存导致后续 Codex执行错误。
- 把调研日维护状态写成永久事实。
- 将用户确认的方向误写成已经实施的代码状态。

### 回退方式

本阶段只改文档，可按文件逐项回退；不得借回退恢复用户明确删除的旧文档或触碰业务代码。

### 预计新增或修改文件

- `AGENTS.md`
- `docs/README.md`
- `docs/JOURNEY_REFACTOR_PLAN.md`
- `docs/ARCHITECTURE_DECISIONS.md`
- `docs/CURRENT_PROJECT_AUDIT.md`
- `docs/AGENT_TECH_RESEARCH.md`
- `docs/EXECUTION_LOG.md`
- 退役：`docs/JOURNEY_ROADMAP.md`

### 本阶段明确不做

- 不删除 Taro/微信源码或 SQLite 数据。
- 不创建 Expo、Docker 或 PostgreSQL。
- 不安装/升级依赖。
- 不修改后端、前端、数据库或密钥。

### 下一阶段如何开始

用户明确发送：“执行阶段 2：旧资产提取与微信端退役；先完成删除前清单，验收后再删除。”

---

## 阶段 2：旧资产提取与微信端退役

**Status: Completed（2026-07-16）**

### 阶段目标

保存仍有价值的品牌资产、产品语义和纯业务规则；通过删除前验收后，让
微信/Taro 客户端和任何实际旧 SQLite 数据文件退出当前工作树。后端微信身份、
SQLite 配置与 `_mini` 业务模块按 ADR-020 保留到新实现通过测试后的替换点。

### 前置条件

- 阶段 1 状态为 Completed，文档与 ADR 已验收。
- 用户明确授权执行阶段 2；资产验收后的旧端删除必须再次单独授权。
- Git 状态可解释；已有用户改动已保护。

### 涉及目录

- 读取：`src/`、`config/`、`dist/`、`project.config.json`、`package*.json`、`backend/`
- 计划新增：`docs/assets/`、`docs/product/`、`packages/design-tokens/`（仅在提取结果适合时）
- 计划删除：微信/Taro 表现层与旧 SQLite 文件；精确清单必须先生成

### 具体任务

#### 资产与产品基线

- [x] 再次执行目录/Git 安全检查并记录 commit SHA。
- [x] 列出 `src/assets/` 所有文件、尺寸、格式、哈希、引用位置和版权/来源状态。
- [x] 确认要保留的卡通人物、Logo、插画；只复制原始资产，不做重新设计。
- [x] 在微信开发者工具固定 iPhone 12/13 (Pro) `390×844` 视口，保存首页、Journey、我的、饮食、运动、登录、空态、错误态参考截图。
- [x] 记录旧页面仅作为风格参考，不设置像素级迁移门槛。
- [x] 从 SCSS 提取颜色、圆角、间距、阴影、字体层级候选表。
- [x] 记录首页/Journey/我的的产品语义与关键文案。

#### 业务规则提取

- [x] 逐项评审 `src/utils/`，标记“保留思想/可移植纯函数/淘汰”。
- [x] 记录热量、体重趋势、分页、日期和 AI 候选确认规则。
- [x] 记录旧 API 路由、请求/响应和后端应用服务映射，仅作为重构输入。
- [x] 记录 FastAPI 中可复用领域逻辑和微信耦合点。

#### 删除前验收门

- [x] 生成完整删除清单，区分前端、后端微信模块、构建产物、旧数据库和旧文档。
- [x] 使用 Git 确认所有待删源码均可从历史恢复。
- [x] 检查保留资产不依赖即将删除的路径或构建脚本。
- [x] 用户审阅资产清单、截图索引和删除清单。
- [x] 用户以“请按计划推进”授权执行已审阅的退役清单。

#### 微信端退役

- [x] 按已确认清单删除 Taro 页面、组件、服务、配置和小程序项目配置。
- [x] 删除客户端微信登录与邀请码流程；后端微信身份和 `_mini` 业务模块按 ADR-020 保留到阶段 4 替换。
- [x] 确认没有旧 SQLite 数据文件；SQLite 配置和补列逻辑按 ADR-020 保留到阶段 3/4 的替换点。
- [x] 删除旧前端依赖、构建产物和脚本，但保留已提取资产。
- [x] 更新根 README、审计和执行日志，明确旧端已退役。

### 验收标准

- 卡通人物与保留品牌资产有清单、哈希、来源和新位置。
- 核心页面有参考截图和产品语义记录。
- 有明确的业务逻辑迁移矩阵。
- 当前工作树不再包含 Taro 客户端、客户端微信 API、`project.config.json` 或旧 SQLite 数据。
- 后端 `_mini` 与微信身份只作为 ADR-020 约束的短期迁移桥存在，阶段 4 新身份和 API 验收后删除。
- 可通过 Git 历史定位退役前源码。
- 没有误删 FastAPI 可复用领域逻辑。

### 测试方式

- `rg -n "@tarojs|Taro\.|wx\.|WECHAT_|openid|unionid|_mini"`，对每个剩余结果给出解释。
- 文件清单和资产哈希复核。
- `git diff --name-status` 与删除清单逐项比对。
- Python 静态导入检查，确保保留后端没有导入已删微信模块。

### 风险

- 未提取资产或规则便删除。
- `_mini` 文件混有可复用逻辑，整文件删除造成损失。
- 本地未跟踪文件不在 Git 历史中，无法回退。
- 删除旧前端后，在新骨架完成前仓库没有可视客户端。

### 回退方式

- 所有已跟踪旧源码由 Git 历史恢复。
- 保留资产使用哈希校验。
- 未通过删除后检查时，不进入阶段 3；按清单恢复误删文件。

### 预计新增或修改文件

- `docs/product/LEGACY_UI_REFERENCE.md`
- `docs/product/LEGACY_ASSET_INVENTORY.md`
- `docs/product/LEGACY_LOGIC_MIGRATION_MATRIX.md`
- `docs/product/WECHAT_RETIREMENT_CHECKLIST.md`
- `docs/assets/legacy-ui/`（参考截图）
- 保留品牌资产目录（阶段内 ADR 确定）
- `README.md`、审计、执行日志
- 删除清单列出的 Taro/微信/SQLite 文件

### 本阶段明确不做

- 不创建完整 Expo 页面。
- 不重新设计卡通人物。
- 不建立 PostgreSQL schema。
- 不接 Agent 框架或真实模型。
- 不把旧微信端打包进 Docker。

### 下一阶段如何开始

阶段 2 验收并确认旧端退役后，用户发送：“执行阶段 3：建立 Expo 骨架和最小 Docker/PostgreSQL 基线。”

---

## 阶段 3：新工程骨架与最小 Docker 基线

**Status: Completed（2026-07-17）**

### 阶段目标

建立可复现但最小的新工程：一套 Expo/React Native/TypeScript 客户端骨架，以及 Docker Compose 管理的 FastAPI + 全新 PostgreSQL。先连通健康检查，不迁核心业务。

### 前置条件

- 阶段 2 Completed。
- Docker Desktop、Xcode Simulator 和 Android 开发环境可用性已检查；不在本阶段安装大型 IDE。
- 已核对实施时 Expo、Node、Python、PostgreSQL、LangChain未来兼容矩阵。

### 涉及目录

- `apps/mobile/`
- `backend/`
- `packages/contracts/`
- `packages/design-tokens/`
- `infra/docker/`
- 根目录 `compose.yaml`、环境与工具版本文件

### 具体任务

- [x] 记录 Expo/RN/Node/包管理器/Python/PostgreSQL 版本选择 ADR。
- [x] 创建 `apps/mobile/` Expo Development Build + TypeScript 严格模式骨架。
- [x] 建立首页、Journey、我的三个空路由和主题 Provider。
- [x] 引入保留的品牌资产与初版 design token，不迁业务页面。
- [x] 建立移动端环境配置和 API base URL 抽象。
- [x] 验证 iOS Simulator 最小页面。
- [x] 验证 Android Emulator 最小页面。
- [x] 验证 Web 最小构建。
- [x] 整理 FastAPI 启动入口，使其不在 import 时修改数据库。
- [x] 固定 Python 版本和依赖 lock。
- [x] 创建后端多阶段/最小 Dockerfile、非 root 用户和健康检查。
- [x] 新增 `.dockerignore`，排除密钥、数据库、venv、node_modules、构建产物和媒体。
- [x] 新增 `compose.yaml`，只包含 `api` 与 `db`；使用命名 volume 和健康依赖。
- [x] 建立全新 PostgreSQL 连接和 Alembic 空基线。
- [x] 建立统一 `.env.example` 和必填 secret 校验。
- [x] 记录 iOS localhost、Android `10.0.2.2`、真机局域网/staging 地址差异。
- [x] 增加 API health smoke test 和客户端 API 连通性页面。

#### 环境验收进度

- [x] `docker compose config/up --build/health/restart/down` 全生命周期通过。
- [x] PostgreSQL 18.4 真库 `upgrade → downgrade → upgrade` 通过。
- [x] API 容器非 root 运行；live/ready 均返回 `200`，数据库状态为 `ok`。
- [x] iPhone 17 Pro（iOS 26.5）显示三个路由，并通过 `127.0.0.1:8000` 访问容器 API。
- [x] Pixel 9（Android 16/API 36.1 ARM64）显示三个路由，并通过 `10.0.2.2:8000`
  访问容器 API。

### 验收标准

- `docker compose up --build` 启动 API/PostgreSQL，健康检查通过。
- 空数据库由 Alembic 升级到当前版本；API import 不自动建表补列。
- 同一移动端代码在 iOS、Android 和 Web 显示三入口骨架。
- iOS/Android 均能调用容器 API 健康接口。
- 无真实密钥、无 Redis/Celery/向量数据库。

### 测试方式

- Compose config/build/up/health/down。
- Alembic upgrade/downgrade/upgrade 空库测试。
- FastAPI health API 测试。
- TypeScript、lint 和三平台最小构建检查。
- 手工记录模拟器访问后端证据。

### 风险

- Apple Silicon 镜像与原生依赖不兼容。
- Expo SDK/Node 版本漂移。
- Android 与 iOS 对 localhost 的解释不同。
- 一次加入过多工具导致骨架阶段失控。

### 回退方式

- 保留宿主机 Uvicorn 启动说明作为诊断路径。
- Expo 原生限制时使用 Prebuild/Bare Spike，不建立第二套 UI。
- PostgreSQL/Alembic 基线可通过空库重建；此阶段没有旧数据迁移。

### 预计新增或修改文件

- `apps/mobile/**`
- `backend/Dockerfile`
- `backend/pyproject.toml` 与 lock 文件
- `backend/alembic.ini`、`backend/alembic/**`
- `infra/docker/**`
- `compose.yaml`、`.dockerignore`、`.env.example`
- `packages/contracts/**`、`packages/design-tokens/**`
- README、ADR、执行日志

### 本阶段明确不做

- 不迁移完整页面或业务数据。
- 不实现登录、Food/Activity/Journey API。
- 不接 Agent/RAG/pgvector。
- 不制作生产镜像或 APK。

### 下一阶段如何开始

阶段 3 已通过全部门禁。只有用户明确发送阶段 4 启动指令后，才开始身份、画像与核心
业务 API；不得因为阶段 3 完成而自动启动阶段 4。

---

## 阶段 4：身份、画像与核心业务 API

**Status: Completed（2026-07-17）**

### 阶段目标

建立跨平台统一身份、全新 PostgreSQL schema 和稳定业务 API，为移动端与 Agent 工具提供同一应用服务。

### 前置条件

- 阶段 3 Completed。
- API 版本、错误格式、ID 类型和时间/时区规则已形成 Proposed ADR 并在本阶段确认。

### 涉及目录

- `backend/app/api/`
- `backend/app/domain/`
- `backend/app/services/`
- `backend/app/models/`、`schemas/`
- `backend/alembic/`
- `packages/contracts/`
- `backend/tests/`

### 具体任务

- [x] 定义 `/api/v1`、统一错误码、request/trace ID、分页和 OpenAPI 契约。
- [x] 设计统一 User、Identity、Profile、Goal 数据模型，消除 User/Profile 双事实源。
- [x] 支持邮箱或用户名 + 密码登录。
- [x] 实现安全密码哈希、access/refresh token、注销和令牌撤销策略。
- [x] 设计未来手机号身份扩展点，不实现短信流程。
- [x] 仅在 local/test/staging 明确配置下生成测试账号。
- [x] 建立 FoodRecord、ActivityRecord、WeightRecord、Journey 聚合 schema。
- [x] Food 补充份量、单位、宏量营养和来源字段；Activity 补充时长、强度等字段。
- [x] 建立 Profile、Food、Activity、Journey 应用服务和仓储边界。
- [x] 写接口支持幂等键、事务、所有权校验和审计事件。
- [x] 建立首页今日聚合 API 和 Journey 日期范围/分页 API。
- [x] 生成/校验共享契约，避免客户端复制不一致类型。
- [x] 收紧 CORS、环境配置和日志脱敏。
- [x] 为所有 schema 编写首个 Alembic migration 和 downgrade。

### 验收标准

- 邮箱和用户名可登录同一用户；重复邮箱/用户名正确拒绝。
- 测试账号仅在允许环境生成。
- Profile/Food/Activity/Weight/Journey API 权限与校验通过。
- 重复幂等请求不产生重复记录。
- 首页与 Journey 聚合结果由确定性测试验证。
- 全新空库可 upgrade/downgrade/upgrade。

### 测试方式

- 后端单元、API、数据库、权限、参数、异常与并发/幂等测试。
- 独立 PostgreSQL 测试库和事务/清库隔离。
- OpenAPI schema snapshot/contract 测试。
- 禁止测试调用真实模型。

### 风险

- 身份与画像模型过度设计。
- 时区和记录日期导致首页/Journey 跨日错误。
- token/refresh 实现不安全。
- API 与移动端并行开发造成契约漂移。

### 回退方式

- Alembic downgrade 回退 schema；测试数据可整体重建。
- API 保持版本化，破坏性变化新增 migration/契约版本。
- 不依赖旧 SQLite，因此无需数据回迁。

### 预计新增或修改文件

- `backend/app/domain/**`
- `backend/app/api/v1/**`
- `backend/app/models/**`、`schemas/**`、`services/**`
- `backend/alembic/versions/**`
- `backend/tests/**`
- `packages/contracts/**`
- 环境、README、ADR、执行日志

### 本阶段明确不做

- 不接 LangChain/LangGraph。
- 不做图片、语音、视频或手机号登录。
- 不部署 staging。
- 不拆微服务。

### 下一阶段如何开始

阶段 4 已通过全部门禁。只有用户明确发送阶段 5 启动指令后，才迁移移动端核心页面；
不得因为后端完成而自动开始阶段 5，也不得提前进入阶段 6 Agent/RAG。

---

## 阶段 5：移动端核心页面

**Status: Completed（2026-07-17）**

### 阶段目标

完成首页、Journey、我的和必要表单，建立可在 Agent 不可用时工作的结构化健康应用；使用新品牌设计系统而非照搬旧页面。

### 前置条件

- 阶段 4 核心 API 和契约可用。
- 旧品牌资产、design token 和三入口信息架构已确认。

### 涉及目录

- `apps/mobile/src/`
- `packages/contracts/`
- `packages/design-tokens/`
- 移动端测试目录

### 具体任务

- [x] 建立认证会话、安全存储、刷新和注销流程。
- [x] 完成登录、注册、测试账号入口和基础资料/目标设置。
- [x] 首页实现统一输入区域、今日摘要、卡通人物状态和快捷手动记录。
- [x] 先用 Mock Agent 事件实现候选确认卡片，不接真实模型。
- [x] 完成饮食、运动、体重手动表单及编辑/删除确认。
- [x] Journey 完成日期范围、历史、趋势、周总结占位和详情编辑。
- [x] 我的完成账号、画像、目标、单位、隐私与离线知识入口。
- [x] 建立本地缓存、同步状态和有限离线写入队列。
- [x] 内置版本化饮食/运动/安全常识包和关键词检索/固定计算。
- [x] 完成 loading、empty、error、弱网、断网、token 过期和重试状态。
- [x] 适配安全区、键盘、滚动、动态字体和常见手机尺寸。
- [x] 保证深浅主题策略一致；若 MVP 不做深色模式，明确 ADR 和 UI 行为。
- [x] 为 Agent 流式事件预留稳定 UI 协议，不绑定具体模型 SDK。

### 验收标准

- iOS/Android 可完成登录、画像、手动饮食/运动/体重、首页更新和 Journey 查看。
- 首页统一输入在 Mock 下可展示多意图候选并逐项确认。
- 无网络时 Agent 明确不可用，但缓存、本地知识、固定计算和手动记录可用。
- 三入口清晰，卡通资产可辨识，UI 不依赖 Taro/微信。
- Web 可完成补充构建，已知差异有记录。

### 测试方式

- 组件测试、页面流程测试和 API Mock。
- iOS/Android 手工兼容矩阵。
- 尺寸、键盘、安全区、弱网/断网和错误状态测试。
- 核心页面截图/视觉回归基线。
- 可访问性标签与基本键盘/读屏检查。

### 风险

- 页面开发提前绑定未稳定 Agent 返回格式。
- 为追求新 UI 破坏三入口简洁性。
- 离线同步造成重复记录。
- iOS/Android 样式与键盘行为不一致。

### 回退方式

- Agent UI 使用 Mock 协议，可独立于真实框架回退。
- 手动表单始终是核心降级路径。
- 视觉变更通过 design token 和截图基线逐项回退。

### 预计新增或修改文件

- `apps/mobile/src/features/auth/**`
- `apps/mobile/src/features/home/**`
- `apps/mobile/src/features/journey/**`
- `apps/mobile/src/features/profile/**`
- `apps/mobile/src/features/records/**`
- `apps/mobile/src/components/agent/**`
- `apps/mobile/src/offline/**`
- `apps/mobile/tests/**`
- design token、契约、README、执行日志

### 本阶段明确不做

- 不接真实 Agent、RAG 或多模态。
- 不做手机号、HealthKit/Health Connect。
- 不做纯聊天一级页。
- 不开始生产发布。

### 下一阶段如何开始

结构化应用闭环和 Mock Agent UI 通过后，执行阶段 6 Agent 与 RAG；真实模型接入只有在
供应商、数据政策、预算和密钥均获确认后才启用。

---

## 阶段 6：Agent 与 RAG

**Status: Completed（2026-07-20）**

### 阶段目标

把固定 LLM 接口升级为可测试、可解释、模型可替换的业务 Agent：统一入口、显式工具、用户确认、结构化记忆、受控 RAG、轨迹和降级。

### 前置条件

- 阶段 4/5 的业务服务、契约和确认 UI 稳定。
- 实施时重新核对 LangChain/LangGraph/Pydantic 与 Python 兼容性和许可证。
- 若接真实模型，首个供应商、预算与数据政策必须先确认，密钥只存在安全环境；用户已明确
  授权本阶段以 Mock、空 key、零外部预算完成，其余保持 Proposed。

### 涉及目录

- `backend/app/agent/`
- `backend/app/knowledge/`
- `backend/app/observability/`
- `backend/tests/agent/`、`backend/tests/rag/`
- `evals/`
- `apps/mobile/src/components/agent/`

### 具体任务

#### 基础契约与路由

- [x] 固定 LangChain、按需 LangGraph 和 Pydantic 兼容版本。
- [x] 定义统一 Agent request/event/result/error schema。
- [x] 实现 Intent Router：food、activity、profile、history、knowledge、recommendation、weekly_summary、clarify。
- [x] 支持多意图拆分、置信度和低置信度澄清。
- [x] 实现自研 Model Router 配置、能力映射和供应商 Adapter。
- [x] 实现 Fake/Mock Model，确保测试零真实调用。

#### 工具与确认

- [x] 定义 Food、Activity、Profile、Journey、Nutrition Knowledge 工具。
- [x] 所有业务工具复用阶段 4 应用服务，不执行模型生成 SQL。
- [x] 查询工具直接返回；写工具只生成候选或验证确认令牌后写入。
- [x] 增加幂等、权限、审计和重复提交保护。
- [x] 客户端支持有序状态事件、多个候选、逐项编辑/确认/取消；v1 使用单响应事件序列，真正增量传输待有真实流式模型需求时评估。

#### Context Builder 与工作流

- [x] 实现模型无关 Context Builder 和 Token 预算策略。
- [x] 接入结构化画像、今日/近期确定性聚合；本阶段不保存自由对话记忆。
- [x] 实现 Recommendation Workflow。
- [x] 实现 Weekly Summary Workflow。
- [x] 实现超时、有限重试、标准错误和确定性 fallback。
- [x] 禁止全量聊天灌入 Prompt 和模型推断静默写画像。

#### 受控 RAG

- [x] 建立知识源登记、许可、版本和适用地区清单。
- [x] 实现 ingestion、清洗、Chunk、metadata、确定性 embedding 和索引管道。
- [x] 用 PostgreSQL JSON 向量与主题词混合检索建立小规模基线；当前数据未证明需要 pgvector。
- [x] 实现 Retriever、引用、no-answer；第一版只检索公共受控知识，不混入个人数据。
- [x] 建立版本切换、重复摄取稳定 ID、来源停用和删除级联路径。

#### 轨迹与成本

- [x] 定义 OpenTelemetry spans 和自有 Agent run/tool run 表。
- [x] 记录模型、Prompt/Schema/知识版本、Token、延迟、重试和估算成本。
- [x] 日志脱敏，只持久化输入 hash/长度和最小工具摘要，不保存原始对话、Token 或密钥。
- [x] 提供按用户隔离的 `/api/v1/agent/runs/{run_id}` 调试轨迹接口。

### 验收标准

- 首页输入能正确分类、拆分、调用工具并展示确认卡片。
- 未经确认无法产生任何业务写入。
- 不同配置模型接收统一上下文和 schema。
- Recommendation/Weekly Summary 可追踪每个节点及引用。
- 模型、RAG 或网络失败时返回可解释降级，不影响手动记录。
- 轨迹包含模型/Prompt/Token/延迟/成本且不泄漏敏感信息。

### 测试方式

- Router、工具选择、参数、Schema、节点和确认中断单元测试。
- Mock 超时、限流、非法 JSON、错误工具、部分失败和重试测试。
- RAG ingestion/Chunk/metadata/Recall@k/引用/no-answer/隔离测试。
- Prompt snapshot 与固定数据集回归。
- 手工真实模型 smoke 只在受保护环境运行并限制预算。

### 风险

- LangChain 类型渗透业务层造成锁定。
- Graph 过度复杂，简单操作难调试。
- 模型路由降低成本却损害结构化准确率。
- 个人记忆与公共知识混检导致隐私泄漏。
- 重试触发重复写入。

### 回退方式

- Agent 层可关闭，移动端回退手动表单和确定性 API。
- Model Router 可固定到单一已验证模型。
- RAG 可关闭并明确 no-answer，不回退到无来源自由生成。
- Graph 节点逐步退回普通 Python 控制流。

### 预计新增或修改文件

- `backend/app/agent/**`
- `backend/app/knowledge/**`
- `backend/app/observability/**`
- Agent/RAG 数据库 migrations
- `evals/datasets/**`、`evals/prompts/**`
- `backend/tests/agent/**`、`backend/tests/rag/**`
- 移动端 Agent event/confirmation 组件
- 环境、ADR、README、执行日志

### 本阶段明确不做

- 不制造多 Agent 对话。
- 不让模型直接 SQL 写入。
- 不接自由网络搜索。
- 不同时部署全部可观测性平台。
- 不实现图片、语音或视频。

### 下一阶段如何开始

Agent/RAG 核心路径可测且轨迹可见后，执行阶段 7 量化评测和全栈 CI 门禁。

---

## 阶段 7：量化评测、自动化测试与 CI

**Status: Completed（2026-07-20）**

### 阶段目标

将后端、移动端、Agent、RAG 和构建质量变成可重复执行的门禁，并形成可展示的“失败—改进—回归”证据。

### 前置条件

- 阶段 6 具备稳定 Agent 事件、工具和 Prompt 版本。
- 测试数据不含真实个人健康信息或真实密钥。

### 涉及目录

- `backend/tests/`
- `apps/mobile/tests/`
- `evals/`
- `.github/workflows/`
- Compose test profile 和报告目录

### 具体任务

#### 后端测试

- [x] 领域单元测试。
- [x] API、数据库、认证、权限、参数和错误码测试。
- [x] 事务、幂等、并发、迁移和测试数据隔离。
- [x] 外部模型与 Embedding 全部 Mock；当前无 Object Storage 集成或外部调用。
- [x] 超时、限流、依赖故障和降级测试。

#### Agent 测试

- [x] 建立 100 条路由、50 条食物、50 条运动、20 条混合意图样本。
- [x] 测试工具选择、工具参数、工作流节点和结构化输出。
- [x] 建立 20 条高风险安全样本和 20 条失败/降级样本。
- [x] 验证未确认写入为 0。
- [x] 记录 Prompt/模型/Schema 版本、Token、延迟和成本。
- [x] 保存首轮 39 个失败与最终 0 失败的改进前后报告。

#### RAG 测试

- [x] 建立 36 条金标问题（24 可回答、12 no-answer）与相关文档数据集。
- [x] 测试 ingestion、Chunk、metadata 和公共知识/个人上下文隔离。
- [x] 计算 Recall@3、引用支持率和 no-answer 准确率。
- [x] 检查错误引用、无依据生成和知识版本回归。

#### 移动端与 E2E

- [x] 组件、页面、API Mock、弱网/断网、空/错/加载状态测试。
- [x] iOS/Android 尺寸、安全区、键盘和主题兼容静态契约检查。
- [x] Web E2E：资料/目标 → 饮食 → 运动 → 首页/Journey → 建议 → 周总结。
- [x] Agent 失败时验证手动表单与本地知识降级。

#### CI

- [x] GitHub Actions 执行格式、lint、类型检查、单元、API、移动端和评测。
- [x] 执行 Alembic upgrade/downgrade/check 和 Docker test/runtime build 检查。
- [x] 执行 Web 静态构建与 iOS/Android JS bundle 检查；原生构建留到阶段 8。
- [x] 上传测试、覆盖率、评测和 Web/E2E 报告。
- [x] PR/CI 明确固定 Mock、空 key、零预算。
- [x] 不创建真实模型任务；其供应商、数据政策和正预算获批后才可新增受保护流程。

### 验收标准

- 意图路由 ≥ 90%，写工具选择 ≥ 95%，Schema 合法率 100%。
- 未确认写入 0，高风险规则通过率 100%。
- RAG 门槛由首轮金标基线正式记录，不能无数据拍定。
- CI 从干净环境可复现，默认不需要真实 Key。
- 报告能展示至少一个问题如何通过数据反馈得到改进。

### 测试方式

本阶段本身以测试和 CI 为交付物；同时在本机和 GitHub Actions 运行同一命令，比较结果与制品。

### 风险

- 使用 LLM judge 形成循环偏差。
- 数据集过小或只覆盖成功案例。
- 随机模型结果导致 CI 不稳定。
- 真实评测失控消耗预算。

### 回退方式

- CI 门禁分层启用，先确定性测试、后统计型评测。
- 不稳定评测先报告不阻塞，但必须有负责人和转门禁条件。
- 真实模型任务可关闭，Mock 回归始终可运行。

### 预计新增或修改文件

- `backend/tests/**`
- `apps/mobile/tests/**`
- `evals/**`
- `.github/workflows/**`
- `compose.yaml` test profile
- 测试/评测报告模板、README、执行日志

### 本阶段明确不做

- 不为提高数字修改或泄漏测试答案给 Prompt。
- 不在普通 CI 使用真实密钥。
- 不把录屏或人工演示当作自动化测试替代品。

### 下一阶段如何开始

全部门禁通过并形成评测报告后，执行阶段 8 的 staging、构建和展示交付。

---

## 阶段 8：staging、构建与秋招展示

**Status: Completed**

### 阶段目标

形成可从新环境复现的 staging、iOS/Android/Web 构建路径和 3—5 分钟面试展示，同时保留故障降级与备用录屏。

### 前置条件

- 阶段 7 门禁通过。
- staging 验收形态、预算、隐私和密钥策略已确认；本阶段采用本机隔离环境。
- 应用标识、图标、版本和签名策略形成 ADR。

### 涉及目录

- `infra/`
- `.github/workflows/`
- `apps/mobile/` 原生/构建配置
- `docs/deployment/`、`docs/demo/`
- 根 README

### 具体任务

#### staging

- [x] 用户确认阶段 8 采用本机隔离 FastAPI + PostgreSQL staging；不创建 Render 或公网资源，
  未来自租服务器发布作为单独任务（当前未启用 pgvector，保持 ADR-024 受控检索方案）。
- [x] 配置 migration、健康检查、日志、备份/恢复和最小监控。
- [x] 使用独立数据库、Mock/空模型 Key/零预算和非生产测试账号。
- [x] 验证本机端口、CORS、网络策略和环境隔离；公网真机访问与 HTTPS 证书明确延期到未来
  服务器发布任务，不作为阶段 8 验收项。
- [x] 为离线健康记录队列确定并验证本地加密、保留期限、注销清除和设备备份策略。

#### 构建

- [x] iOS Simulator 使用 Xcode/Expo Development Build 可复现运行。
- [x] Android Emulator 可复现运行。
- [x] 构建可安装 Android APK；记录 AAB/发布签名前置要求。
- [x] 生成 Web production build；可选容器镜像因 Docker Hub OAuth TLS timeout 保留为回退项。
- [x] 记录 iOS archive/TestFlight/App Store 前置条件；不声称 Linux Docker 构建 iOS。
- [x] 为安装包、Web 文件和报告生成版本与校验信息。

#### 展示与文档

- [x] 编排 3—5 分钟主演示：登录 → 画像 → 食物/运动 → 确认 → 首页/Journey → 建议/周报 → 评测。
- [x] 准备 seed/reset 脚本和稳定演示数据。
- [x] 准备模型失败、无网或 staging 故障时的降级演示。
- [x] 录制备用演示视频并记录版本。
- [x] 绘制系统架构图、Agent 工作流图和测试金字塔。
- [x] 完善 README、一键启动、模拟器说明和常见故障。
- [x] 编写简历项目描述与常见面试问答依据。

### 验收标准

- 新开发设备按文档能启动 Docker 后端和至少一个模拟器客户端。
- iOS Simulator 主流程完整，Android 核心流程通过，APK 可安装。
- Web 构建可用但不作为主演示。
- 本机隔离 staging 可通过模拟器/Web 访问并有备份恢复方案；公网真机访问已按用户确认延期。
- 3—5 分钟演示可重复，Agent 失败时不阻断核心记录。
- 架构和评测陈述均有代码/报告证据。

### 测试方式

- 干净环境安装演练。
- staging smoke、migration、备份恢复和限额测试。
- iOS/Android/Web 构建与制品安装测试。
- 主演示与降级演示各至少完整演练一次。

### 风险

- 云平台、证书、签名和商店账号外部依赖。
- staging 真实模型成本和隐私。
- 演示依赖网络造成现场失败。
- iOS/Android 发布规则变化。

### 回退方式

- 本地 Docker + 模拟器作为主回退。
- 使用 Mock/fallback 和 seed 数据完成离线式演示。
- 使用版本匹配的备用录屏。
- staging 可从备份或 IaC/部署文档重建。

### 预计新增或修改文件

- `infra/**`
- `.github/workflows/**`
- `apps/mobile/app.json`/构建配置及必要原生文件
- `docs/deployment/**`
- `docs/demo/**`
- 架构图、测试报告、README、执行日志

### 本阶段明确不做

- 不要求实际付费上架 App Store/Google Play。
- 不引入 Kubernetes 或复杂高可用集群。
- 不在生产/展示环境使用开发默认 secret。
- 不把 Web 改为主要产品形态。

### 2026-07-31 最终交付复验 Checklist

- [x] 在临时 PostgreSQL 18 数据库中完成 65 条后端测试，覆盖率 91.07%。
- [x] 完成 `0003 → 0002 → 0003` migration 回环、`alembic check`、Ruff check/format。
- [x] 以 Mock/空模型 Key/零预算完成 318 条 Agent/RAG 样本和 17 项门禁。
- [x] 完成 5 条移动逻辑测试、31 条 Jest 测试、TypeScript、Expo lint 和三变体校验。
- [x] 在独立 Compose/API/数据库上完成 2 条 Web 核心 E2E。
- [x] 完成 Web、iOS、Android JS 构建；Web 当前为 13 条静态路由。
- [x] 完成 iOS Release Simulator build、安装、启动和截图。
- [x] 完成 Android ARM64 Release APK build、签名检查、Pixel 9 安装、启动和截图。
- [x] 扫描 Git 跟踪文件和生成 bundle，不发现模型 Key；确认 `.env` 被 Git 忽略。
- [x] 更新开发、测试开发、产品和售前岗位的简历、STAR 案例和问答依据。
- [ ] Web Nginx 镜像本轮复验：Docker Hub 基础镜像元数据连续两次网络超时；静态 export、
  E2E 和历史 Dockerfile 验证保留，待外部网络恢复后重跑，不伪标通过。
- [ ] npm 高危传递依赖告警：当前自动修复要求破坏性降级 Jest/改变 Expo 链路；在独立依赖
  升级任务中处理，不执行 `npm audit fix --force`。

### 2026-08-01 真实模型验收口径修订 Checklist

- [x] 用户确认当前新增能力范围暂时收敛为“文字 Agent + 食物图片候选”，不把语音、视频、
  手机号、HealthKit/Health Connect 或通知并入本次验收。
- [x] 新增 ADR-033：普通 CI 继续使用 Mock；发布验收必须分别调用文字和图片对应真实模型，
  Mock 通过不得替代真实模型质量通过。
- [x] 通过 DeepSeek 与 Qwen `/models` 只读探测确认 `deepseek-v4-flash` 和
  `qwen3.7-flash` 当前可用；未输出密钥，模型目录探测不消耗推理 Token。
- [x] 完成真实 API E2E 冒烟：DeepSeek 生成 food/activity 两个候选且无 fallback；Qwen 对
  已授权苹果图生成候选、强制用户校正、图片不保留且无 fallback。
- [x] 新增并测试 `evals/run_text_provider_acceptance.py`；dry-run 保持 Provider 调用 0，
  首轮 28 次 DeepSeek 为路由 94.44%、饮食/运动 100%，发现“我的体重是多少”被误判为
  weight；Router Prompt 升级至 `1.0.1` 后同集复验为路由/饮食/运动 100%、0 retry/fallback、
  p95 1768 ms、费用 `$0.00246372`，全部文字门禁通过，修正前后报告均保留。
- [x] 重建本机 API 后通过公开 `/api/v1/agent/runs` 回归“我的体重是多少”：真实 DeepSeek
  返回 `profile`、0 候选、存在画像回答且无 fallback。
- [x] 重跑完整 Compose 门禁：69 条后端/评测测试通过，后端覆盖率 91.07%，318 条 Mock
  样本与 17 项门禁继续全部通过。
- [x] 继续引用 ADR-031 的 60 张真实图片质量报告：图片 API 冒烟通过不改变 Top-3 67.27%、
  中国家庭餐 60%、Schema 98.33% 的失败结论，不重跑密封集。
- [x] 总体发布验收标记为 Conditional / 未通过：文字 PASS、图片功能 smoke PASS、图片质量
  FAIL；Development 可实验性演示图片候选，Preview/Production/staging 继续关闭。
- [x] 更新验收报告、文档索引、演示口径和执行日志；不自动启动新的功能阶段。

### 下一阶段如何开始

当前没有自动下一阶段。MVP 和秋招展示完成后，用户可以单独授权本地 Git 提交、服务器部署、
签名发布或上游依赖升级；当前范围只包含文字与食物图片候选，其他阶段 9 能力仍须从 Backlog
中逐项立项，不批量启动。

---

## 阶段 9：后续多模态与平台集成

**Status: Closed / No-Go（仅获授权的食物图片单项执行完毕；估重与 ADR-031 识别门禁均失败；2026-07-31）**

### 阶段目标

在 MVP 指标和真实反馈证明价值后，逐项扩展图片、语音、视频、手机号和健康平台能力。每项均需独立 ADR、隐私评审、评测集和回退策略。

### 前置条件

- 阶段 8 Completed。
- 用户只选择一个明确能力进入实施。
- 目标模型、设备、权限、成本、隐私和数据保留政策已确认。

### 涉及目录

- `apps/mobile/src/features/media/`（预计）
- `backend/app/media/`、`backend/app/agent/`（预计）
- 对象存储/异步任务配置（仅有真实需求时）
- 专项 `evals/` 数据集与隐私文档

### Backlog Checklist

- [ ] 食物图片识别、份量估算和用户校正（当前唯一获授权单项；真实视觉质量门禁通过后勾选）。
  - [x] Proposed ADR、隐私边界、量化标准和回退矩阵先于实现固化。
  - [x] Expo 相机/相册、预览、明示上传、Mock 候选、宽区间和用户校正流程。
  - [x] FastAPI 独立视觉 Provider、内存处理、输入校验、脱敏 Trace 和确认后写入。
  - [x] DeepSeek 文本 Provider 与图片 Provider 分离；已有 DeepSeek Key 未接收图片。
  - [x] Feature Flag、权限/取消/离线/超限/超时/非食物回退和手动记录不受影响。
  - [x] 22 条合成图片契约、API/组件/Web E2E、iOS/Android/Web 构建与执行证据。
  - [x] 独立 Qwen Key、北京端点、启用当日价格、每日人民币 1 元预算和合成图片 Smoke。
  - [x] 复核供应商保留/训练/删除边界，并建立 100 张授权标注图片集；官方未公布精确
    调用保留时长，作为 Proposed ADR 的残余风险保留。
  - [ ] 真实 Provider 的 Top-3、份量误差、区间覆盖、拒答、p95 和成本全部达到门槛；
    v1.2 当前 Top-3 84.44%（门槛 85%）、份量中位误差 37.48%（门槛 ≤30%），其余门禁
    通过；全部达标后再将 ADR-030 转为 Accepted 并勾选父项。
  - [x] 基于失败指标选择尺度参照路线，固化 Journey 9×5 cm 参照卡、已知盘/碗直径、
    数据最小化、配对评测与回退规则；不直接启用未经评审的新视觉模型。
  - [x] 实现 v1.3 可选尺度参照请求、三端拍摄引导、Prompt、Schema、Trace 和回归测试。
  - [x] 建立 30 张独立无参照泛化 holdout，与 100 张调参集 source/hash/id 零重叠；
    Qwen v1.3 得到 Top-3 76.67%、份量误差中位数 36.36%，两项仍未达标。
  - [x] 互联网筛选尺度数据候选并核验许可/金标边界：SNAPMe 可做 CC BY-SA 4.0 次级真实
    场景配对，但其 ASA24 份量不是实验室称重；MetaFood3D 更接近硬门禁但为 CC BY-NC 4.0
    且需申请密码；ECUSTFD/SimpleFood45 许可不足，均未下载或混入现有 holdout。
  - [x] 将用户确认获作者允许取用的 16 张小红书图片保存为 Git 忽略的候选资产；无生成式
    修改地拆出 88 个单格，识别出 30 个带尺子/电子秤的尺度配对候选，排除 1 张重复总览。
    用户最终确认可以使用；帖子链接无法恢复，状态记为
    `user_attested_final / source_links_unavailable`，仅内部使用且不冒充开放数据。
  - [x] 为 30 个带尺候选生成遮挡答案文字和秤读数的 `with_ruler`/`without_ruler` 配对，
    共 60 张同尺寸确定性遮挡图；未生成或补画食物。
  - [x] 人工逐格转录并核对 30 个实际秤读数，完成全部 30 组 contact sheet 与疑难格放大
    视觉 QA；固定哈希并密封为 `journey-food-image-scale-holdout-v1`，禁止用于 Prompt 调整。
  - [x] 建立 30 组用户确认授权、实际称重且尺子共视的内部尺度配对 holdout；固定哈希、
    金标、视觉 QA 和禁止调参标记。来源链接不可恢复，因此仅内部使用、不作为开放数据分发。
  - [x] 用户确认采用隔离厘米尺评测适配器：不修改正式 App/API，独立版本化 Prompt/
    Schema，预注册门禁并禁止根据密封集调参。
  - [x] dry-run、区域/预算/哈希检查通过后，对密封集完成唯一一次 60 调用 Qwen 配对评测；
    24 个完整配对的有尺份量误差 47.82%、无尺 48.87%、改善 2.17%，Schema/参照判断
    53/60，门禁失败且禁止据此调参。
  - [x] 完成失败收尾：正式定位为实验性辅助候选，移动端明确“不能准确称重/不是称重值”；
    Development 可显式启用，Preview/Production/staging 继续关闭；厘米尺路线标记 No-Go。
  - [x] 新建 ADR-031 Proposed，提出“视觉模型只给食物名称候选、份量由用户确认”的解耦
    方向；不修改正式 App/API/Prompt/Schema，不调用真实 Provider。
  - [x] 预注册 `journey-food-image-recognition-holdout-v2` 的 60 张分层、零重叠、授权、
    隐私与量化门禁；确认当前缺少合格新图片，因此只建立规格、不伪造清单或金标。
  - [x] 用户接受 ADR-031 的“识别候选 + 手动确认份量”产品方向；本确认不代表候选模型
    质量通过，也不授权修改正式产品。
  - [x] 从 Wikimedia Commons 取得 60 张全新图片，完成逐文件许可、标签、隐私、哈希和
    五组联系表视觉 QA；与既有三套数据在来源/source ID/SHA-256 上零重叠并密封为
    `journey-food-image-recognition-holdout-v2`，Provider 调用 0。
  - [x] 重新确认候选视觉模型、区域、数据政策、价格、独立 Key 与人民币 1 元/日预算：
    北京端点、Qwen `qwen3.7-flash-2026-07-15`、低于 32K 的人民币 0.2/0.8 元每百万
    输入/输出 Token 与不用于训练声明已复核；精确保留期未公开的残余风险继续记录。
  - [x] 建立只读、可断点续跑且不可覆盖的一次性评测器；冻结 Prompt/Schema/评分器，
    dry-run 为 Provider 调用 0 后，对密封集完成唯一一次 60 调用，不修改正式 App/API
    或数据库。
  - [x] ADR-031 唯一评测结论固定为 No-Go：总体 Top-3 37/55（67.27%，门槛 85%）、
    中国家庭餐 12/20（60%，门槛 80%）、Schema/强制校正 59/60；非食物拒答 5/5、
    p95 3416 ms、Token/成本记录和零自动写入通过。不得重跑或用失败样本调整现有 Prompt。
  - [ ] 真实 Provider 父项仍需份量误差 ≤30%、相对无参照改善 ≥15%、参照判断 ≥95% 且
    全部原门禁通过；当前继续 Mock/强制校正/手动记录回退，不得宣称图片份量已验收。再次
    启动自动估重前仍必须另有新的 Proposed ADR、新称重配对 holdout 和已复核的视觉模型；
    ADR-031 不满足或绕过该门禁。
- [ ] 身体进度照片私密对比。
- [ ] 娱乐性体脂宽区间估算；禁止伪精确值和未成年人使用。
- [ ] 语音转文字输入和后续 Realtime Agent Spike（Deferred / 当前范围外；用户于
  2026-07-31 明确决定不做，后续不得默认启动）。
- [ ] 视频动作阶段/姿态提示；禁止伤病诊断和安全保证。
- [ ] 手机号身份绑定和安全找回。
- [ ] HealthKit/Health Connect 授权、同步和撤销。
- [ ] 通知、提醒和用户可控频率。

### 验收标准

由被选中的单项能力另建 Proposed ADR 和专项计划后确定；不得以本 Backlog 直接授权开发全部功能。

当前单项的专项验收口径见 `docs/product/FOOD_IMAGE_PRIVACY_AND_EVAL.md`，架构门禁见
ADR-030/ADR-031。食物图片单项已经完成执行但未达到验收阈值，因此以 Closed / No-Go
停止，不把未通过项勾成成功；该文档是产品/测试规格，不是第二份迁移路线图。

### 测试方式

必须包含真实设备、权限拒绝、上传失败、删除、隐私、模型偏差、不同人群和成本/延迟测试。

### 风险

- 生物/健康媒体隐私、身体形象伤害和模型偏差。
- 安装包、上传、对象存储和推理成本增长。
- 平台权限与模型能力快速变化。

### 回退方式

每个多模态能力必须可由 Feature Flag 关闭；关闭后文字 Agent、手动记录和核心 Journey 不受影响。

### 预计新增或修改文件

在单项 ADR 中列出；本阶段不预创建空架构。

### 本阶段明确不做

- 不一次实现全部 Backlog。
- 不默认上传媒体或用于模型训练。
- 不输出精确体脂、医疗诊断或绝对动作安全判断。

### 下一阶段如何开始

没有自动下一阶段。根据 MVP 反馈、求职展示价值和成本选择单一专项。

---

## 阶段 10：Agent v2 与测试报告增强

**Status: Completed（2026-08-03）**

### 阶段目标

在不引入多 Agent 和复杂微服务的前提下，把既有固定分支升级为可解释、可恢复、可量化的
单 Agent 计划—执行—校验闭环，并让首页能够展示真实计划轨迹；同时为现有 Pytest 体系增加
Allure 报告，但继续保留 HTTPX/TestClient、JUnit 和 Coverage。

### 前置条件

- 阶段 6—8 已完成，现有 `/api/v1`、人工确认、RAG、模型路由和测试基线可复用。
- ADR-034 必须先保持 Proposed，验收通过后才能转 Accepted。
- CI 使用 Mock/零真实密钥；真实 DeepSeek 只作为显式低频发布门禁。

### 涉及目录

- `backend/app/agent/`、`backend/app/services/agent.py`
- `backend/app/models/agent.py`、`backend/app/schemas/agent.py`
- `backend/alembic/versions/`
- `backend/tests/`、`evals/`
- `packages/contracts/`、`apps/mobile/`
- `.github/workflows/ci.yml`、`docs/`

### Checklist

- [x] 固化 ADR-034、隐私边界、量化指标和回退方案。
- [x] 新增类型化工具注册表和服务端工具白名单，不允许模型构造任意工具名。
- [x] 新增结构化 `AgentPlan`、依赖关系、风险/确认标记和计划版本。
- [x] 建立 LangGraph Planner → Policy Guard → Executor → Verifier 条件执行循环。
- [x] 限制每次最多 6 个步骤、最多 1 次重规划，并为超时、失败、无效计划提供可解释降级。
- [x] 保持饮食、运动、体重候选必须经用户确认、所有权校验和幂等写入。
- [x] 新增 PostgreSQL `agent_threads` 与最小结构化回合记忆，不保存原始输入正文。
- [x] 首页复用三个一级入口，展示计划步骤、执行状态和当前线程，不重新设计完整 UI。
- [x] 扩充共享 TypeScript/OpenAPI 契约和 API 文档。
- [x] 增加 Planner、Policy、工具序列、参数、重规划、记忆、确认恢复和 Trace 测试。
- [x] 增加 Agent v2 量化数据集及门禁；Mock 外部调用/费用保持 0。
- [x] 增加 `allure-pytest`、脱敏附件和 CI Allure artifact；保留 JUnit/Coverage。
- [x] 完成 `0004 → 0003 → 0004` migration 回环和 `alembic check`。
- [x] 完成后端、Agent/RAG、移动端、Web E2E、三端 JS 构建回归。
- [x] 使用当前确认的 DeepSeek 文字模型运行新的 v2 发布门禁；记录成本并禁止密钥进入报告。
- [x] 更新 ADR、文档索引、审计、演示/简历材料和执行日志后停止。

### 验收标准

- `AgentRunResponse` 可返回 `thread_id`、结构化计划、步骤状态和验证结果；旧客户端关键字段
  保持兼容。
- 组合任务能在一个 Run 内按依赖执行多个工具；工具失败不会造成未确认写入或无限循环。
- 同一线程可读取有上限的结构化摘要，切换模型不丢失业务事实；不同用户线程严格隔离。
- ADR-034 的全部量化门禁和现有阶段 7/8 门禁通过；真实 DeepSeek v2 报告通过。
- Allure、JUnit、Coverage 和 Agent JSON 报告都可由 CI 生成，且不包含真实密钥。

### 测试方式

- Pytest 单元/API/数据库/migration；Mock 外部模型失败注入；Agent v2 专项数据集和门禁。
- Jest/React Native Testing Library 验证首页计划轨迹；Playwright 验证组合任务主路径。
- iOS/Android/Web JS 构建，iOS 主模拟器与 Android AVD 最小运行。
- 显式真实 DeepSeek 门禁只使用预注册文字集、预算上限和脱敏报告。

### 风险

- 额外 Planner 调用增加延迟和费用；通过步骤/重规划/预算上限控制。
- 模型规划不稳定；服务端白名单、Pydantic Schema 和确定性回退必须先于执行。
- 线程摘要可能累积隐私信息；不保存原文、限制条数并只引用既有事实。
- API 契约扩展影响旧客户端；所有新字段保持向后兼容并先更新共享契约测试。

### 回退方式

- 配置关闭 v2 后回到既有固定分支；手动记录和 v1 人工确认链不受影响。
- Alembic downgrade 只移除 v2 线程/计划元数据；不删除核心业务表。
- Allure 失败不得阻塞已有 JUnit/Coverage 结果读取，可独立移除插件和 CI 参数。

### 预计新增或修改文件

- `backend/app/agent/planner.py`、`policy.py`、`tool_registry.py`、`execution_graph.py`、`memory.py`
- `backend/alembic/versions/0004_agent_v2.py`
- Agent 模型、Schema、服务、API、测试和评测数据
- 共享契约、首页及其测试
- CI、API/ADR/执行日志和演示材料

### 本阶段明确不做

- 不引入多 Agent 对话、微服务、后台自主任务或无限循环。
- 不启动语音、视频、手机号、健康平台或新的图片质量评测。
- 不允许 Agent 绕过用户确认写入，不保存原始对话正文或客户端模型密钥。
- 不执行公网部署、商店签名、提交、push 或 PR。

### 下一阶段如何开始

本阶段验收后停止。任何公网部署、商店发布、图片模型复评或新多模态能力仍需用户单独授权。

---

## 阶段 11：Agent v3 人工确认检查点、Observation 重规划与网络黑盒测试

**Status: Completed（2026-08-04）**

### 阶段目标

修复 Agent v2 在人工确认和失败恢复处的两个闭环断点：组合任务必须等待用户确认后再使用最终
业务数据继续执行；可恢复工具失败必须经过 Observation、Verifier 和受限 Replanner 选择安全
替代路径。同时补齐 Requests + Pytest + Allure 的 Docker 网络黑盒测试。

### 前置条件

- 阶段 10、ADR-034 和现有 79 条测试/342 条样本/22 项门禁基线可复用。
- ADR-035 在验收前保持 Proposed；CI 继续 Mock、空真实 Key和零预算。

### 涉及目录

- `backend/app/agent/`、`backend/app/services/agent.py`、Agent API/Schema/Model
- `backend/alembic/versions/`、`backend/tests/blackbox/`、`evals/`
- `packages/contracts/`、`apps/mobile/`
- `compose.yaml`、`.github/workflows/ci.yml`、`docs/`

### Checklist

- [x] 新增 ADR-035、隐私边界、量化标准和回退策略。
- [x] 新增 v3 checkpoint/observation 数据模型和 Alembic migration。
- [x] `awaiting_confirmation` 时暂停依赖步骤并进入 `waiting_for_user`。
- [x] Confirmation 返回进度；全部确认后允许显式恢复并防止重复/跨用户恢复。
- [x] 新增 Observation 与 Verifier 决策 Schema，不保存原始输入或思维链。
- [x] 新增最多 2 次的模型 Replanner，并对重规划结果再次执行 Policy Guard。
- [x] 增加知识安全摘要和规则建议两条确定性替代工具。
- [x] 更新 API/OpenAPI/TypeScript 契约和移动端确认恢复体验。
- [x] 增加 checkpoint、暂停/恢复、失败替代、终止、隐私和兼容回退测试。
- [x] 新增 Requests + Pytest + Allure Docker 网络黑盒套件。
- [x] 扩充 Agent v3 量化数据集与门禁，普通 CI 外部费用保持 0。
- [x] 完成 migration 回环、后端、移动端、E2E 和三端构建回归。
- [x] 使用确认的 DeepSeek 文字模型执行 v3 小预算发布门禁并保存脱敏报告。
- [x] 更新 ADR、审计、技术研究、API、演示材料和执行日志后停止。

### 验收标准

- 组合“记录 + 建议”在候选确认前不会执行建议；确认全部候选后恢复并读取更新后的数据。
- 可恢复故障可以选择预注册替代工具；不可恢复故障会澄清/停止，绝不无限循环。
- 未确认写入、跨用户恢复、重复恢复和 checkpoint 原文泄露均为 0。
- Mock 全量、Requests 黑盒、Agent v3 量化门禁、移动端流程和真实 DeepSeek v3 门禁通过。

### 测试方式

- Pytest/TestClient 验证状态机、数据库、Policy、幂等、恢复、错误与隐私。
- Requests/Pytest/Allure 对 Compose API 执行登录、Run、确认、Resume、Trace 和错误码黑盒。
- Jest/RNTL 与 Playwright 验证等待确认和恢复提示；Web/iOS/Android 构建检查。
- 真实 Provider 只运行固定脱敏小数据集、正预算和显式 `--execute`。

### 风险与回退

- checkpoint 增加状态复杂度：使用明确状态转换、行锁、过期时间和幂等恢复控制。
- Replanner 增加延迟/费用：仅可恢复错误触发，最多 2 次，不跨供应商自动转发。
- 关闭 `AGENT_V3_ENABLED` 回到 v2；downgrade 仅移除 v3 元数据。

### 本阶段明确不做

- 不实现多 Agent、无限自主循环、后台定时任务或自动写健康记录。
- 不启动长期偏好学习、语音、视频、手机号、健康平台或新图片评测。
- 不公网部署、不商店签名、不提交、push 或创建 PR。

### 下一阶段如何开始

本阶段完成后停止；长期偏好学习或主动教练能力必须另建 Proposed ADR 并由用户确认。

---

## 阶段 12：本地优先与 AI 原生体验

**Status: In Progress（方案 C 视觉子项已实现；本地数据与小红书仍待确认）**

### 阶段目标

针对用户指出的离线能力割裂和首页复古、方正、不够智能的问题，完成离线能力矩阵、同步边界、
首页信息架构、视觉提案和量化标准；同时核对当前 Agent 浏览器权限及小红书可行接入路径。
用户确认方案 C 后，本阶段范围仅扩展到首页视觉子项；本地数据、数据库/API、Agent 工具和
小红书接入仍不得自动实施。

### 前置条件

- 阶段 11 已完成，现有 Agent、核心业务 API 和移动端页面作为事实基线；
- ADR-036/037 在各自完整实现验收前保持 Proposed；方案 C 的视觉子决策已单独确认；
- 任何小红书或通用网页能力都不能使用账号密码、Cookie、自动登录或未经确认的抓取方式。

### 涉及目录

- `docs/product/LOCAL_FIRST_AI_UI_PROPOSAL.md`
- `docs/ARCHITECTURE_DECISIONS.md`
- `docs/CURRENT_PROJECT_AUDIT.md`
- `docs/README.md`、`docs/EXECUTION_LOG.md`、`AGENTS.md`
- `apps/mobile/src/app/(tabs)/index.tsx`
- `apps/mobile/src/components/home-overview.tsx`、`screen-shell.tsx`
- `apps/mobile/src/theme/theme-provider.tsx`
- `apps/mobile/tests/`、`apps/mobile/e2e/core-flow.spec.ts`、`apps/mobile/package.json`
- 不涉及 `backend/`、`packages/`、API 契约或数据库 migration

### Checklist

- [x] 审计用户提供的当前首页截图，明确首屏输入、卡片层次、角色融入和离线提示问题。
- [x] 基于当前代码建立在线/离线能力矩阵、账户隔离、同步冲突和退出清理边界。
- [x] 定义首页信息架构、AI 状态语言和三个一级入口的保留原则。
- [x] 交付“温和 AI 健康伙伴”与“轻量数据智能”两套可交互高保真方向稿。
- [x] 根据用户反馈否决第一轮 A/B：记录“过暗、偏灰、吉祥物重画失败”，不得继续实施。
- [x] 基于旧版色彩 token 和原版行走叶子资产交付方案 C“暖白薄荷 Journey”修订稿。
- [x] 为首屏、无障碍、离线读写、同步一致性和 Web Research 建立量化验收标准。
- [x] 核对当前 Agent 工具白名单，确认没有浏览器或通用网页搜索能力。
- [x] 调研小红书当前公开平台能力、数据使用边界及用户主动分享链接的合规候选路径。
- [x] 新建 ADR-036/037，全部保持 Proposed，未把方案推测写成已实现事实。
- [x] 用户确认方案 C“暖白薄荷 Journey”并授权继续完成首页视觉子项。
- [x] 落地固定暖白＋明亮薄荷浅色主题，复用原版叶子角色，不恢复已否决的暗色 A/B 方向。
- [x] 把统一输入、快捷提示、今日指标和轻量 Agent 状态落到首页，保留现有确认写入与三个一级入口。
- [x] 准确区分在线 Agent 与离线手动记录，不把尚未实现的完整 local-first 能力写入 UI。
- [x] 更新移动单测、布局契约、覆盖率范围和 Web E2E 首页断言。
- [x] 完成 320/390 pt 视觉核对、TypeScript、lint、33+5 条移动测试、2 条 Web E2E 与三端 export。
- [ ] 用户确认本地保存全部规范化记录、退出清理和显式冲突策略。
- [ ] 用户确认小红书近期采用“主动分享链接”，或仅保留未来官方 API 规划。
- [ ] 用户单独授权后再把剩余两项拆为实现任务；不得由视觉子项自动扩大范围。

### 验收标准

- 产品文档能明确回答哪些能力离线可用、哪些必须联网、冲突和退出时如何处理；
- 已确认方案 C 在 320 pt 以上主标题、输入和指标不截断，统一输入位于首屏，在线/离线文案准确；
- 小红书结论有当前公开来源依据，且明确区分 Codex 的浏览工具与 Journey App Agent 的工具；
- ADR、计划、文档索引、审计与执行日志保持同一状态：视觉子项已实现，local-first 与小红书仍 Proposed；
- 首页视觉以外的业务代码、依赖、数据库、真实 Provider、远程仓库均无变化。

### 测试方式

- Markdown 链接和标题检查、`git diff --check`；
- 对话稿与实际 App 在 390 × 844、320 × 844 视口人工核对；
- `npm --workspace @journey/mobile run typecheck`、`lint`、`test:logic`、`test:ci`；
- `npm run mobile:e2e:web`，并在执行前强制 Mock/零模型 Key、执行后恢复本机 Provider；
- Web、iOS、Android Expo export；
- 代码只读核对工具注册表、共享契约和移动端离线存储实现；
- 对小红书官方/平台文档进行日期、能力和数据边界复核。

### 风险

- 把已实现首页误解为完整 local-first；文案和状态必须继续基于真实离线能力；
- 本地副本若无加密、账户隔离和冲突处理会扩大健康数据风险；
- 小红书平台能力和协议可能变化，实施时必须重新调研；
- 社交内容新颖但可信度不稳定，不能进入健康事实层或替代受控 RAG。

### 回退方式

若首页视觉回归失败，只回退 `home-overview.tsx`、首页装配和固定浅色主题，不回退现有 API、
Agent、数据模型或用户记录；ADR-036/037 继续 Proposed。

### 预计新增或修改的文件

- 新增 `docs/product/LOCAL_FIRST_AI_UI_PROPOSAL.md`
- 修改 `docs/ARCHITECTURE_DECISIONS.md`、`docs/CURRENT_PROJECT_AUDIT.md`
- 修改 `docs/JOURNEY_REFACTOR_PLAN.md`、`docs/README.md`、`docs/EXECUTION_LOG.md`、`AGENTS.md`
- 新增对话内可视化 `journey-home-concepts.html` 与 `journey-warm-mint-home.html`
- 新增 `apps/mobile/src/components/home-overview.tsx`
- 修改首页、ScreenShell、主题、移动测试、E2E 和覆盖率配置

### 本阶段明确不做

- 不实现完整本地数据副本、编辑/删除 Outbox、冲突 UI、数据库或 API 变更；
- 不实现小红书账号绑定、自动登录、Cookie 复用、网页抓取或 Web Research；
- 不安装框架、不调用真实模型、不进行图片复评；
- 不提交、push、创建 PR、公网部署或商店签名。

### 下一阶段如何开始

首页视觉子项到此停止。下一步只等待用户选择：是否实施完整本地数据副本，以及小红书近期
是否只做主动分享链接。任一选择都必须先拆为新的单一实现任务并再次确认，不自动开始。

---

## 2. 阶段状态变更模板

每次完成阶段必须同步修改：

```text
docs/README.md              当前阶段与状态
JOURNEY_REFACTOR_PLAN.md    Checklist 和阶段状态
EXECUTION_LOG.md            命令、结果、问题、下一条指令
ARCHITECTURE_DECISIONS.md   新决策或 Superseded 关系（如有）
CURRENT_PROJECT_AUDIT.md    代码事实发生实质变化时
AGENT_TECH_RESEARCH.md      技术维护/版本结论变化时
```

任何“完成”都必须附可重复验证证据；不能只修改状态文本。
