# Journey 架构决策记录

> 文档类型：ADR 汇总
> 更新日期：2026-07-17
> 规则：已接受决策不得静默改写；变更时新增 ADR，并将旧项标记为 `Superseded`。

## 状态定义

- `Proposed`：尚未最终确认。
- `Accepted`：用户已确认，后续实施应遵守。
- `Superseded`：已被更新决策替代，保留历史原因。
- `Rejected`：评估后明确不采用。

## ADR-001：微信小程序退出目标架构

**Status: Accepted**
**Date: 2026-07-15**

### 背景

旧前端使用 Taro 和微信小程序 API。新产品目标是 iOS、Android 和补充 Web，不再发布或维护微信端。

### 决策

先完成卡通人物、品牌资产、业务规则和参考截图提取；通过删除前验收后，从当前工作树移除 Taro、微信配置、微信登录和小程序页面。Git 历史作为唯一旧源码回退手段，不在仓库保留 `legacy/miniapp` 副本。

### 后果

- 降低新架构长期维护噪音。
- 删除前必须形成资产清单和证据，禁止提前清理。
- 不再为微信端建立 Docker、测试或新功能。

## ADR-002：保留品牌气质，不做像素级 UI 迁移

**Status: Accepted**
**Date: 2026-07-15**

### 决策

保留卡通人物、Logo、插画和品牌气质；从旧样式提取颜色、圆角、间距、阴影和字体层级作为参考。新跨平台端允许重新组织页面和组件，尤其是 Agent 输入、确认卡片、引用、降级和同步状态。

### 原因

旧 UI 是微信小程序形态，无法完整覆盖 Agent 化交互；完全推倒品牌资产又会失去项目延续性。

## ADR-003：三个一级入口，Agent 融入首页

**Status: Accepted**
**Date: 2026-07-15**

### 决策

一级入口固定为：首页、Journey、我的。首页提供统一自然语言输入和今日数据，不增加独立 Agent 一级页。Intent Router 自动识别饮食、运动、知识咨询、历史查询、画像更新和建议等意图。

多意图允许拆分为多个候选操作；低置信度先澄清；写操作逐项确认。

## ADR-004：采用 Expo Development Build 的跨平台客户端

**Status: Accepted**
**Date: 2026-07-15**

### 决策

新客户端采用实施时稳定的 Expo + React Native + TypeScript，并使用 Development Build，而不是依赖 Expo Go 作为完整运行环境。

### 平台优先级

1. iOS Simulator：主要开发和面试演示。
2. Android Emulator：跨平台验收和 APK 路径。
3. Web：补充发布和备用演示。

### 回退

遇到原生能力限制时使用 Expo Prebuild/Bare 工作流；不因此建立两套业务前端。具体 Expo SDK、路由和状态库版本在阶段 3 Spike 时确定。

## ADR-005：混合开发环境与两段式 Docker

**Status: Accepted**
**Date: 2026-07-15**

### 决策

后端和 PostgreSQL 尽早建立最小 Docker Compose 基线；移动端开发服务器、iOS Simulator 和 Android Emulator 在宿主机运行。业务稳定后再制作生产镜像、Web 镜像和发布构建。

### 原因

- 模拟器依赖宿主图形、虚拟化和原生工具链。
- iOS 构建需要 macOS/Xcode、macOS CI 或 EAS，不能依靠普通 Linux Docker。
- 后端早期容器化能及时暴露依赖、路径和环境差异。

## ADR-006：保留 FastAPI，重构而非整体重写

**Status: Accepted**
**Date: 2026-07-15**

### 决策

保留 FastAPI 和可复用的饮食、运动、画像、首页、Journey 与 AI fallback 领域逻辑。移除微信身份、`_mini` 路由/Schema、启动时建表补列和供应商耦合，重建稳定的 API 与应用服务边界。

### 不采用

不删除整个后端后从零重写，也不拆微服务。

## ADR-007：全新 PostgreSQL，不迁移旧 SQLite 数据

**Status: Accepted**
**Date: 2026-07-15**

### 决策

新应用使用全新 PostgreSQL schema 和 Alembic 迁移。旧 SQLite 数据无业务价值，不迁移；旧数据库文件在阶段 2 删除清单验收后移除。后续 RAG 需要向量检索时优先评估 pgvector。

## ADR-008：邮箱/用户名密码身份体系

**Status: Accepted**
**Date: 2026-07-15**

### 决策

第一版支持邮箱或自定义用户名加密码登录，两者映射到同一个用户主体。开发和演示环境生成测试账号，生产环境禁止自动测试账号。手机号登录后置，并复用同一用户身份模型。

### 安全要求

密码强哈希、令牌过期与刷新、安全存储、注销、速率限制、权限测试和日志脱敏进入验收范围。

## ADR-009：Agent 增强的结构化应用，而非纯聊天应用

**Status: Accepted**
**Date: 2026-07-15**

### 决策

首页和 Journey 始终保留结构化数据视图与手动表单。Agent 负责理解自然语言、选择工具和生成候选操作；所有写入、修改、删除、目标与画像更新必须经用户确认。查询和确定性计算可以直接执行。

## ADR-010：LangChain + 按需 LangGraph + Pydantic + 自研 Model Router

**Status: Accepted**
**Date: 2026-07-15**

### 决策

- LangChain：模型供应商、消息、工具与流式接口适配。
- LangGraph：只用于 Recommendation、Weekly Summary、人工确认等确有状态需求的工作流。
- Pydantic：工具参数、事件和最终输出的强校验。
- 自研 Model Router：根据任务能力、成本、延迟和可用性选择配置模型。
- Fake/Mock Model：仅用于测试，不作为生产回答来源。
- 确定性 fallback：模型失败时转表单、固定计算或明确错误。

### 约束

不构造无意义的多 Agent 对话，不让 Agent 直接执行 SQL，不把全部业务写成难以测试的 Chain。

## ADR-011：模型无关的 Context Builder 与结构化记忆

**Status: Accepted**
**Date: 2026-07-15**

### 决策

模型不拥有唯一会话真相。Context Builder 每次从 PostgreSQL、业务聚合和个人检索中组装最小必要上下文：系统规则、当前任务、必要画像、近期数据、少量相关记忆、工具权限和输出 Schema。

数据库事实优先；Prompt 不保存动态用户数据；禁止全量聊天灌入 Prompt。模型建议写入长期画像时必须再次让用户确认。

## ADR-012：受控 RAG，网络搜索后置

**Status: Accepted**
**Date: 2026-07-15**

### 决策

第一版只使用有来源、版本、适用地区和授权记录的营养与运动资料。回答必须关联检索依据；无可靠知识时明确无答案。公共知识与个人数据隔离。自由互联网搜索作为后续独立工具评估，不直接进入第一版健康依据链路。

## ADR-013：健康管理边界与安全降级

**Status: Accepted**
**Date: 2026-07-15**

### 决策

Journey 提供一般健身、营养和生活方式建议，不诊断疾病、不开处方、不替代医生或营养师。高风险输入触发安全提示和专业帮助建议。评测必须覆盖危险建议、错误引用、越权写入和不确定性表达。

## ADR-014：离线确定性能力，不内置本地模型

**Status: Accepted**
**Date: 2026-07-15**

### 决策

离线时 Agent 明确不可用；应用保留缓存查看、手动记录、固定计算和版本化本地常识包。联网后同步记录和更新知识包。第一版不打包端侧大模型。

## ADR-015：媒体本地优先与多模态后置

**Status: Accepted**
**Date: 2026-07-15**

### 决策

第一版文字 Agent 优先，图片、语音、视频后置。人体照片和训练视频默认本地保存；云端分析需逐次授权、临时上传、生命周期清理和可彻底删除。不得默认用于模型训练。

体脂以测量数据为准；照片最多提供娱乐性宽区间和置信度，不输出伪精确值。视频用于姿态提示，不提供伤病诊断或绝对安全保证。

## ADR-016：量化评测是发布门禁和展示成果

**Status: Accepted**
**Date: 2026-07-15**

### 决策

建立版本化评测数据、Prompt 和结果。记录意图准确率、工具选择、Schema 合法率、未确认写入、高风险规则、RAG 引用、延迟、Token 和成本，并展示“失败分析—改进—回归对比”的闭环。

## ADR-017：低成本 staging，暂不建设复杂生产架构

**Status: Accepted**
**Date: 2026-07-15**

### 决策

开发使用本地 Docker，CI 使用隔离测试环境。核心流程稳定后部署一个 HTTPS staging 供真机和备用演示访问。采用模块化单体 API + PostgreSQL；暂不引入 Kubernetes、服务网格、Redis、Celery或复杂微服务，除非有可验证需求。

## ADR-018：MVP 范围

**Status: Accepted**
**Date: 2026-07-15**

### 必须完成

测试账号登录、画像与目标、首页自然语言记录饮食/运动、候选确认、首页更新、Journey 历史、个性化建议、周总结、Agent 轨迹和量化评测报告。

### 后续版本

图片体脂娱乐估算、视频动作提示、语音 Agent、手机号、Apple/Google 登录、HealthKit/Health Connect、社交、复杂提醒和正式商店上架。

## ADR-019：文档作为后续 Codex 的单一事实源

**Status: Accepted**
**Date: 2026-07-15**

### 决策

`JOURNEY_REFACTOR_PLAN.md` 是唯一迁移计划；根目录 `AGENTS.md` 是任务入口；审计、技术调研和执行日志分别承担事实、选择依据和执行证据。每次只推进一个阶段，验收后停止。

## ADR-020：业务 `_mini` 后端作为短期迁移桥

**Status: Superseded by ADR-022（2026-07-17）**
**Date: 2026-07-16**

### 背景

所有旧业务 API 都依赖微信用户和 `deps_mini.py`，而首页、Journey、Food、Activity 和 AI 的可复用逻辑也混在 `_mini` 文件中。阶段 2 直接整块删除会让 FastAPI 无法导入，并与 ADR-006 的渐进重构冲突。

### 决策

阶段 2 在截图门禁和用户确认后删除微信/Taro 客户端，但业务 `_mini` 后端暂时作为只读迁移桥保留到阶段 4，不再新增功能。阶段 4 先建立新身份、应用服务和 `/api/v1` 契约，通过 characterization/contract 测试后，在同一阶段删除旧 `_mini` 路由、Schema 和服务。

纯微信身份、OpenID/UnionID、邀请码和 SQLite 补列也必须由新身份与 Alembic 基线替换后再删除，避免出现不可导入的中间状态。

### 备选

阶段 2 同时删除全部 `_mini` 文件。该方案能立即清理命名，但会故意破坏后端基线并迫使阶段 2 承担业务重构，因此不推荐。

### 结果

用户在审阅截图、登录失败事实和删除清单后指示“请按计划推进”。阶段 2
据此删除微信/Taro 客户端；后端 `_mini` 业务模块保留到阶段 4，不再新增功能。阶段 4
的新身份、`/api/v1`、PostgreSQL migration 和回归测试通过后，旧 `_mini`、微信身份、
邀请码、SQLite 补列和旧 AI 迁移桥已按本决策退役。

## ADR-021：固定阶段 3 工程版本与最小容器边界

**Status: Accepted**
**Date: 2026-07-17**

### 背景

阶段 3 需要一套可复现的跨平台骨架，同时避免使用过时 Expo/Node 组合和在骨架期
引入完整业务、Agent 或生产部署复杂度。实施日官方 Expo SDK 57 文档给出的核心
组合为 React Native 0.86、React 19.2.3、React Native Web 0.21，并要求 Node
22.13.x 或更高版本。

### 决策

- 客户端固定为 Expo SDK `57`、React Native `0.86`、React `19.2.3`、
  TypeScript `6.0`、Expo Router 和 `expo-dev-client`。
- 工具链固定为 Node `22.23.1`、npm `10.9.8`；采用 npm workspaces 管理
  `apps/*` 与 `packages/*`，只保留一份根 lock。
- 后端固定 Python `3.12`；生产与开发依赖分别使用带哈希的 lock，解析解释器为
  CPython `3.12.11`。
- 数据库基线固定为 PostgreSQL `18.4`，迁移使用 Alembic `1.18.x`。阶段 3 仅创建
  空 Alembic revision，不提前设计阶段 4 业务 schema。
- Compose 只包含 `api` 与 `db`；移动端、Metro、iOS Simulator 和 Android
  Emulator 继续运行在宿主机。
- 客户端 bundle id/package 暂用 `com.boom080.journey.dev` 作为开发标识；正式发布
  标识在阶段 8 单独确认。

### 后果

- `apps/mobile/` 可以从一套源码导出 iOS、Android 与 Web bundle。
- FastAPI import 不再执行 `create_all` 或 SQLite 补列；数据库就绪由 `/health/ready`
  和 Alembic 管理。
- 不在阶段 3 引入状态库、请求缓存库、Agent、RAG、Redis 或业务数据表。
- Docker Desktop、Compose 和 PostgreSQL/Alembic 真库验收已通过。阶段 3 首次执行时
  Xcode 与 Android SDK 缺少 Runtime/AVD；用户完成安装后，iPhone 17 Pro 与 Pixel 9
  双模拟器门禁已于 2026-07-17 通过。

### 依据

- [Expo SDK 57 版本说明](https://docs.expo.dev/versions/v57.0.0/)
- [Expo Router 说明](https://docs.expo.dev/router/introduction/)
- [PostgreSQL 官方镜像](https://hub.docker.com/_/postgres)
- [Alembic 官方文档](https://alembic.sqlalchemy.org/en/latest/)

## ADR-022：阶段 4 统一身份、API 与核心数据契约

**Status: Accepted**
**Date: 2026-07-17**

### 背景

旧后端以微信 OpenID、邀请码、SQLite 补列和重复的 User/Profile 字段为核心，无法作为
iOS、Android、Web 与未来 Agent 工具共享的稳定业务层。阶段 4 需要在不过度设计的
前提下形成可测试、可回退的新事实源。

### 决策

- API 固定使用 `/api/v1`；OpenAPI `1.0.0` 快照是客户端契约基线。
- 主体、登录标识、密码、画像、目标分别建模为 `User`、`Identity`、
  `PasswordCredential`、`Profile`、`Goal`。邮箱和用户名映射到同一 User；
  `Identity.kind=phone` 只作为未来扩展点，本阶段不实现短信。
- 业务主键使用 UUID；数据库时间戳使用 UTC `TIMESTAMPTZ`。记录接收带时区时间，
  后端按 Profile 的 IANA timezone 派生 `record_date`，首页与 Journey 支持显式日期查询。
- access token 有效期默认 15 分钟；refresh token 默认 30 天，绑定数据库 session，
  每次刷新轮换。旧 refresh 重放会撤销整条 session；注销立即撤销 session。
- 密码使用 bcrypt cost 12，限制 10—72 UTF-8 bytes；已知账号连续失败 5 次锁定
  5 分钟。错误响应不区分账号不存在或密码错误。
- 统一错误格式为 `error.code/message/details + request_id`；响应回传
  `X-Request-ID`。列表使用 `limit/offset/total`，Journey 使用日期 cursor。
- 饮食、运动和体重写入支持 `Idempotency-Key`，请求 hash 不同返回冲突；幂等记录、
  业务记录和审计事件在同一事务提交，并处理并发唯一键竞争。
- `FoodRecord`、`ActivityRecord`、`WeightRecord` 是原始事实；首页与 Journey 是确定性
  聚合，不单独保存重复汇总。Profile 的最新体重由 WeightRecord 查询得到。
- local/test/staging 只有在 `SEED_TEST_ACCOUNT=true` 时才生成测试账号；production
  配置若启用会直接拒绝启动。Compose 本地开发明确启用该设置。
- 测试使用独立 `journey_test` PostgreSQL 数据库和逐测试清空隔离；不使用 SQLite，
  不调用模型。

### 后果

- 移动端和未来 Agent 工具共用同一应用服务与所有权规则，不允许直接操作 SQL。
- 旧微信/邀请码/SQLite/`_mini`/旧 AI 代码按 ADR-020 正式退役。
- 当前登录失败限制是账号级数据库状态；IP/设备级网关限流留到 staging 发布边界，
  不为本阶段引入 Redis。
- OpenAPI 破坏性变化必须新增 API 或明确版本迁移，不得静默覆盖快照。

### 回退

Alembic 可从 `0002_core_api` downgrade 到阶段 3 空基线；当前只含测试账号和无价值
开发数据，可以重建。旧实现只从 Git 历史恢复，不重新放回活动工作树。

## ADR-023：阶段 5 移动端状态、存储、离线与主题边界

**Status: Accepted**
**Date: 2026-07-17**

### 背景

阶段 5 需要在 iOS、Android 和补充 Web 构建中复用一套页面与 API 契约，同时保证令牌、
服务器缓存、离线手动写入和页面临时状态各有清晰归属。项目不需要为了几个核心流程引入
多套全局状态框架。

### 决策

- 继续使用 Expo Router；根 Stack 通过 `Stack.Protected` 划分登录页与三个受保护 Tab。
- React Context 只管理认证会话和刷新/注销；不复制服务器业务数据。
- TanStack Query 管理 `/api/v1` 服务器状态、失效、重试和最近一次成功结果。
- iOS/Android 的 access/refresh token 使用 Expo SecureStore；Web 仅为补充开发形态，
  使用 `sessionStorage`，关闭标签页即清除，并在界面标注不作为主要演示路径。
- AsyncStorage 保存待同步新增记录、同步元数据和本地偏好；不保存密码或令牌。健康记录
  payload 仍属于敏感业务数据，生产发布前必须在阶段 8 明确本地加密、保留期限和清除策略。
- NetInfo 的连接状态管理在线/离线 UI；不把 Android 对公共互联网的 `VALIDATED`
  结果当作局域网 API 是否可达的唯一依据。实际请求失败仍进入降级路径。离线时允许新增
  饮食、运动和体重记录，使用稳定 `Idempotency-Key` 按用户隔离排队并在恢复联网后串行
  提交；编辑、删除、画像和目标修改要求联网。
- 第一版使用系统明暗模式，品牌 mint/rose token 在两种模式中保持语义一致；不提供手动
  主题切换，避免出现第三个主题事实源。
- 页面表单使用局部 React state 和共享校验函数；当前范围不引入 Zustand、Redux 或复杂
  表单框架。
- Mock Agent 仅在客户端做确定性关键词分类和候选预填，不调用模型、不写入 Agent/RAG
  接口，用户仍需在手动表单中确认后写入。

### 后果与回退

原生令牌与普通缓存隔离；服务器数据仍以 `/api/v1` 为唯一事实源。离线队列只覆盖可安全
幂等重放的新增操作，范围可解释。若 TanStack Query 或 NetInfo 出现版本兼容问题，可回退
为现有 API client + React state，不改变后端契约或业务数据。

## 待阶段内确定的 Proposed 决策

以下内容尚未最终确定，不得提前写成事实：

- Expo SDK、React Native、Node 和包管理器版本已由 ADR-021 接受。
- 客户端导航、状态管理、请求缓存和安全存储已由 ADR-023 接受。
- Python 版本与依赖锁定方式已由 ADR-021 接受。
- PostgreSQL 主版本已由 ADR-021 接受；**Status: Proposed**：pgvector 启用时点。
- DeepSeek 与 Flash/Pro 能力映射已由 ADR-029 接受；**Status: Proposed**：个人健康数据发送
  政策、旧 Key 轮换确认及未来 Qwen/GLM/Kimi 的真实启用。
- **Status: Proposed**：OpenTelemetry 后端采用自托管方案还是托管平台。
- 阶段 8 本机 staging、production id 与商店签名边界已由 ADR-027 接受。
- **Status: Proposed**：未来自租服务器的平台、地区、域名、费用和上线日期。
- **Status: Proposed**：未来 Apple Developer Program、Android upload key 与 EAS 云构建账号/预算。

## ADR-024：阶段 6 Agent 运行边界、受控检索与外部模型默认关闭

**Status: Accepted**
**Date: 2026-07-20**

### 背景

阶段 6 需要证明 Agent 确实具备路由、工具、工作流、结构化输出、引用、轨迹和降级，
但用户尚未选定真实模型供应商，也明确要求 API key 暂时留空。健康数据在选择供应商前
不能被默认发送到第三方。

### 决策

- 当时生产依赖锁定 LangChain `1.3.14`、langchain-openai `1.3.5`、LangGraph `1.2.9`、
  Pydantic `2.13.4` 和 OpenTelemetry API `1.43.0`；其中直接 `langchain-openai` 适配细节
  已由 ADR-029 的 `langchain-litellm` Router 取代，业务边界不变。
- `AGENT_PROVIDER=mock`、空 `AGENT_API_KEY`、每日预算 `$0` 是默认且已验收配置。
  任何外部 provider 必须同时配置 key、具体模型、正预算和实际输入/输出单价；
  OpenAI-compatible 自定义供应商还必须配置 base URL，否则应用拒绝启动。
- 首个真实供应商与能力到模型的映射仍为 **Status: Proposed**。在用户确认供应商、
  地区可用性、数据政策、价格与预算前，不进行真实 smoke，不把 Mock 冒充在线 AI。
- Agent 原始输入只在请求内存中处理；自有 run 表仅保存 SHA-256、字符数、意图、
  provider/model、版本、Token、耗时、重试、估算成本和错误码。工具轨迹不保存候选名称、
  确认 JWT 或原始健康文本。
- 写入采用两步协议：Agent 只返回 15 分钟候选与签名确认令牌；用户可编辑字段，随后由
  `/agent/confirmations/{candidate_id}` 验证当前用户、run、kind、token hash、过期、幂等键
  和单次使用状态，再复用阶段 4 service 写入和审计。
- 第一版公共知识规模仅 4 个版本化 Project-authored paraphrase 文档。使用 PostgreSQL
  JSON 存储确定性向量，并以主题词加权形成可测试混合排序；不启用 pgvector、网络抓取或
  独立向量服务。公共知识检索与个人画像/聚合使用不同代码路径，不建立个人向量索引。
- API v1 返回有序事件数组。当前 Mock/确定性链路耗时短，移动端使用单响应事件序列；
  SSE/增量流式传输只有在真实模型延迟与跨平台行为证明必要时再决定。

### 后果与回退

无 key 环境仍能完整演示路由、候选确认、引用、周总结和轨迹，且外部费用为零。关闭
Agent 时手动表单、阶段 4 API 与离线本地常识不受影响；可回退 `0003_agent_rag` migration
而不影响 `0002_core_api` 业务 schema。pgvector 启用时点、真实供应商和 OTel exporter
继续保留为 Proposed 决策。

## ADR-025：确定性质量门禁、Web 核心 E2E 与零密钥 CI

**Status: Accepted**
**Date: 2026-07-20**

### 背景

阶段 7 需要在真实模型供应商、数据政策和预算尚未确认时，把阶段 6 的 Prompt、Schema、
知识库与基线样本变成可重复的质量门禁。CI 既不能依赖随机外部响应，也不能持有真实模型
密钥；Linux runner 也不适合替代阶段 8 的 Xcode 签名与原生安装包验收。

### 决策

- 版本化 296 条确定性合成样本，并以意图、工具、参数、Schema、安全、失败降级、
  Recall@3、引用支持、no-answer、延迟和成本作为量化门禁。金标不进入运行时 Prompt。
- 普通 CI 固定 `AGENT_PROVIDER=mock`、空 key、零预算和零单价；不创建真实模型的
  PR、nightly 或 manual job。真实评测只有在用户确认供应商、数据政策和正预算后另行 ADR。
- 后端覆盖率最低门槛为 70%；移动端门槛为 statements/lines 65%、branches 55%、
  functions 60%。当前实测高于门槛，但不得通过降低门槛掩盖回归。
- GitHub Actions 分为 backend、mobile、web-e2e 三个 job；使用锁文件、独立 PostgreSQL、
  Alembic 循环、Docker target、测试/覆盖率/评测制品和失败日志。
- 核心用户闭环由 Playwright 在 Web 静态构建上自动执行；iOS/Android 在 CI 验证 JS bundle。
  原生编译、签名、安装包和模拟器/真机发布验收明确属于阶段 8。
- 不引入 LLM judge 作为当前硬门禁，避免同源模型偏差和外部费用。首轮失败与修复后的完整
  回归同时保留，作为量化改进证据。

### 后果与回退

PR 可以在无密钥、零费用条件下重现 Agent/RAG、后端、移动端和核心 E2E 门禁。确定性
100% 只表示当前合成数据集，不宣称真实用户分布或真实模型达到同等质量。若某统计型门禁
未来出现不稳定，应先保留报告并记录转为阻塞门禁的条件；Mock 回归与安全门禁始终保留。

## ADR-026：阶段 8 构建变体、敏感离线队列与本地发布基线

**Status: Accepted**
**Date: 2026-07-20**

### 背景

阶段 8 需要同时支持本机模拟器、HTTPS staging 和未来商店包，且健康记录离线队列不能继续
以 AsyncStorage 明文长期保存。不同环境如果共用标识或网络策略，也容易把开发数据、明文
localhost 和生产配置混在一起。

### 决策

- `development`、`preview`、`production` 使用独立名称、scheme 与 application id；最终
  production id 为用户确认的 `com.boom080.journey`。
- 只有 development Android 允许 `10.0.2.2` 明文 HTTP；preview/production 强制禁止
  cleartext 并只连接用户确认的 HTTPS 地址。Web production export 总是清空 Metro cache，
  防止旧 API 地址被复用进新制品。
- 原生待同步健康记录使用 AES-256-GCM；随机密钥存 SecureStore，密文 24 小时过期、最多
  50 条并按用户清除。Web 不持久化该队列，只保留进程内存。
- Simulator/Emulator/本地 debug certificate 仅证明可构建和安装，不等同于 Distribution/
  upload key 或商店发布。EAS profile 固化路径，但未经账号和预算确认不执行云构建。
- `artifacts/` 为忽略的本机证据目录；版本化备用录屏与说明放 `docs/demo/`。

### 后果与回退

开发环境仍可连接本机 API，Preview/Production 不会因演示方便而放宽网络策略；清除 SecureStore
密钥会使旧密文不可解并触发安全清理。若原生加密库出现兼容性回归，可临时禁用离线排队，
不能回退为明文健康队列。

## ADR-027：阶段 8 本机演示、production 标识与发布签名边界

**Status: Accepted**
**Date: 2026-07-21**

### 决策

- 阶段 8 接受本机隔离 Docker staging、模拟器/本地 APK 和自动化录屏为完整验收证据；不创建
  Render 或其他公网资源。用户未来可能自租一年期服务器，届时作为单独发布任务确认平台、
  域名、HTTPS、预算、备份、监控与数据政策。现有 `render.yaml` 仅保留为未启用参考。
- production id 确认为 `com.boom080.journey`；iOS 与 Android 共用反向域名，不与 Dev/
  Preview 数据混用。
- 用户当前没有付费 Apple Developer Program，因此阶段 8 只验收 iOS Simulator，不制作
  archive、TestFlight 或 App Store 包。
- Android APK 必须带数字签名，用来证明安装包来源并保证后续更新来自同一发布者。当前 APK
  使用自动生成的 debug certificate，仅适合模拟器/本机安装；现阶段不创建 Play upload key，
  不制作商店 AAB。未来发布时必须创建并安全备份长期 upload key，任何凭据不得进入仓库。
- `mock` 作为现有模型路由中的零外部调用 provider 保留。未来真实模型可通过 LangChain/
  LangGraph 适配层配置切换，但仍须确认 provider、模型、base URL（如需）、服务端密钥、
  价格、预算和数据政策，并重新通过阶段 7 评测；客户端不得持有模型密钥。
- 正式隐私政策、发布地区、数据保留期、App Store 隐私标签和 Play Data safety 必须在外部
  staging/签名前由用户确认。

### 证据与后果

本地隔离 staging 已完成 migration、Ready、Mock smoke、幂等 reset、备份恢复；三端本机构建
已通过。本机 Apple code-signing identity 为 0，未创建 Render 资源、长期服务器或商店包。
本机演示足以关闭阶段 8，但不代表公网生产、真机分发或商店发布已经完成；这些能力必须由
未来明确任务重新验收。

## ADR-028：DeepSeek V4 双模型映射与真实调用启用门禁

**Status: Accepted**
**Date: 2026-07-22**

### 背景

用户选择 DeepSeek，最初只启用 `deepseek-v4-flash`，随后明确确认同一 API 也可调用
`deepseek-v4-pro`。官方文档同时列出 V4 Flash/Pro、OpenAI-compatible Base URL、结构化
输出和工具调用能力。用户曾在聊天中直接发送一枚 Key；该 Key 视为已暴露，不得写入项目，
用户仍须确认已经完成轮换。

### 决策

- 不引入 DeepSeek 专属 SDK；具体模型适配已由 ADR-029 的 LangChain/LiteLLM Router 取代
  直接 `ChatOpenAI`。
- 默认模型为 Flash，用于高频路由、解析和知识回答，并关闭思考模式；仅
  `recommendation` 与 `weekly_summary` 映射到 Pro，开启思考模式与 `high` effort。
- Mock 始终是仓库、测试、CI 和无 Key 环境的默认 provider。真实模型失败、超时或超过预算
  时返回现有确定性 fallback，不影响手动记录。
- Key 只允许存放在根目录被 Git 忽略的 `.env` 或未来服务器 secret manager；客户端、
  `.env.example`、日志、测试、制品和 Git 均不得出现真实 Key。
- 成本按模型记录 Flash/Pro cache-miss 单价，而不是共用一组价格；切换模型前重新核对官方
  价格并更新快照。非 Mock 环境必须设置正数每日硬预算，并执行有限 smoke 和阶段 7 回归。

### 转为 Accepted 的条件

- 用户在供应商控制台撤销已经暴露的旧 Key，并只在本机 `.env` 填入新 Key。
- 用户明确接受哪些健康字段会发送给 DeepSeek，并确认供应商数据保留/训练政策。
- 用户确认每日美元预算；随后只执行获授权的小额 smoke，并记录 Token、延迟、费用、结构化
  输出、工具选择和降级证据。

### 当前技术证据

- 本机 `.env` 使用 Flash、每日 `$0.10` 门禁与 Flash cache-miss 单价；Key 值未输出。
- 合成饮食 Smoke：2.872 秒，Food 候选、无 fallback、无重试，保守估算 `$0.00065337`；该次
  仍使用调整前的 Pro 费率上界。
- 调整为 Flash 费率后的合成运动 Smoke：2.294 秒，Activity 候选、无 fallback、无重试，
  估算 `$0.00017038`。两次 AgentRun 累计记录 `$0.00082375`。
- 不可达 Base URL 验证暴露并修复了未捕获 `APIConnectionError`；修复后返回
  `provider_unavailable`、确定性 fallback、1 次重试、费用 0。Mock 全量回归保持通过。
- Pro 首次合成结构化请求暴露 thinking 与 `tool_choice=required` 不兼容；调整为 Pro thinking
  + JSON Output + Pydantic JSON Schema 后通过：208 input / 115 output Token，2812 ms，估算
  `$0.00019053`，结构化校验有效、引用 0。该证据不包含个人健康数据。

技术链路已经验证，但在 Key 轮换和个人健康数据政策确认前，本 ADR 保持 Proposed。仓库、
CI 和未配置本机环境的默认值仍为 `AGENT_PROVIDER=mock`。

## ADR-029：采用 LangChain + 嵌入式 LiteLLM Provider Router

**Status: Accepted**
**Date: 2026-07-22**

### 背景

用户要求采用主流模型切换框架，并希望当前 DeepSeek Flash/Pro 与未来 Qwen、GLM、Kimi
共用一套 Agent 业务代码。原 `ChatOpenAI` 适配器可以修改 Base URL，但 Provider 配置、
凭据隔离、模型注册和后续回退需要项目自行重复实现。Journey 已使用 LangChain/LangGraph，
不应再增加一套平行 Agent 框架。

### 决策

- 保留 LangChain 的消息、结构化输出和工具边界，以及 LangGraph 的业务工作流；外部模型
  统一改由 `langchain-litellm==0.7.0` 的 `ChatLiteLLMRouter` 与 `litellm==1.86.2` 路由。
- LiteLLM 以 Python SDK 嵌入 FastAPI 模块化单体，不部署 LiteLLM Proxy、不增加容器、
  Redis、虚拟 Key 或网关控制面。未来确有多个后端消费者时再单独评估 Proxy。
- `AGENT_PROVIDER` 只在服务端切换 `deepseek`、`qwen`、`glm`、`kimi`、`openai`、
  `openai_compatible` 或 `mock` Profile。各真实供应商使用独立 Key 变量；Qwen/GLM/Kimi
  不允许回退读取旧 `AGENT_API_KEY`，防止凭据发送到错误端点。
- DeepSeek 默认 Flash，Recommendation/Weekly Summary 使用 Pro。Qwen、GLM、Kimi 只建立
  无 Key 占位 Profile；各自数据政策、价格和同一契约评测通过前不得真实启用。
- DeepSeek Flash 非思考结构化输出使用 function calling；Pro thinking 路径使用官方 JSON
  Output 并注入 Pydantic JSON Schema，避免强制 `tool_choice` 冲突。所有外部 deployment
  设置默认 2048 的单次最大输出 Token 上限，可用 `AGENT_MAX_OUTPUT_TOKENS` 收紧。
- 每个已启用模型必须有正数价格快照；Token 成本按实际 model 映射计算。缺 Key、模型、
  Base URL（自定义兼容端点）、正预算或价格时 Settings fail-fast。Mock/CI 保持零网络、零费用。
- 不把 Provider 选择开放给普通移动端用户。Key 只在 Git 忽略的本机 `.env` 或未来服务端
  secret manager 中；客户端只调用 `/api/v1`。
- LiteLLM 曾披露 PyPI `1.82.7`/`1.82.8` 供应链事件，因此精确避开受影响版本，生产与开发
  锁保存哈希，Docker 强制 `--require-hashes`。任何升级必须重新审计、锁定并跑全量测试。

### 后果与回退

业务 Agent、Pydantic Schema、Prompt、RAG、确认写入和 API 契约不依赖具体供应商；新增
Provider 主要变为配置、定价、政策和契约评测工作。嵌入式 Router 增加了依赖体积和供应链
审计责任，但没有增加运行服务。若 LiteLLM 出现不可接受的安全或兼容问题，可将
`LangChainLiteLLMAdapter` 回退为单一 OpenAI-compatible Adapter，Mock、业务工作流与 API
契约无需回退。

## ADR-030：食物图片候选采用独立视觉 Provider、内存处理和强制用户校正

**Status: Proposed**
**Date: 2026-07-22**

### 背景

用户单独授权阶段 9 的食物图片识别、份量估算和用户校正，不授权其他多模态能力。现有
DeepSeek Key 已存放在本机 `.env`，但 DeepSeek 官方 V4 API 发布资料只给出 OpenAI
ChatCompletions/Anthropic 文本消息接口，没有图片输入契约；Journey 因此把它视为
text-only。Key 已配置不代表具备图片识别能力，也不构成向第三方发送个人照片的授权。

Expo SDK 57 官方 `expo-image-picker` 同时支持 iOS、Android 与 Web 的相册选图和相机拍照，
并可只请求必要权限、返回压缩 base64；本项目解析为 `57.0.5`。现有 Agent 候选与确认写入
协议可复用，不需要图片自动写库或新增对象存储。

### Proposed 决策

- 文本 Agent 继续由 `AGENT_PROVIDER` 管理；图片识别使用独立的
  `FOOD_IMAGE_PROVIDER`。默认和 CI 均为 `mock`，不把 DeepSeek 文本模型伪装成视觉模型。
- 初始真实视觉候选为 Qwen `qwen3.7-plus`。2026-07-28 北京区域模型 API 已提供
  `qwen3.7-flash`，独立 Key、图片输入、非思考 JSON、LangChain/LiteLLM/Pydantic 适配和
  `/api/v1` 均完成无个人信息合成 Smoke，因此当前 Proposed 候选更新为
  `qwen3.7-flash`。这不是静默替换：`qwen3.7-plus` 仍可作为质量回退基线；OpenAI 或其他
  OpenAI-compatible 视觉模型仍只作为备选。
- 客户端只在用户点击“拍照”或“从相册选择”后取得单张图片；不后台读取相册、不默认上传、
  不请求麦克风、不读取 EXIF。权限拒绝、取消、离线或 Feature Flag 关闭时保留手动饮食记录。
- 客户端压缩后发送 JPEG base64；服务端仅接受 JPEG/PNG/WebP、最多 5 MiB、尺寸声明最多
  4096×4096。图片只在请求内存中存在，不进入 PostgreSQL、日志、Trace、对象存储、备份或
  RAG。持久化 Trace 只记录字节数、媒体类型、尺寸、Provider、模型、延迟、Token 和费用。
- 输出必须是 Pydantic 结构化候选，包含食物项、份量、总热量宽区间、低/中置信度、假设与
  `needs_user_correction=true`。不输出“精确识别”，不做医疗结论，也不从照片分析身份、脸、
  身体、年龄、体脂或健康状况。
- 图片分析永不直接写入饮食记录。用户必须进入现有饮食表单核对名称、餐别、份量和热量；
  确认后才写入，来源标记为 `image`。原图不随记录保存。
- `FOOD_IMAGE_ANALYSIS_ENABLED` 是服务端 Feature Flag。真实 Provider 超时、拒绝、结构化
  输出失败或预算不足时不伪造识别结果，返回 `manual_required`；Mock 结果必须显著标注为演示
  候选。关闭开关不影响文字 Agent、手动记录、首页和 Journey。

### 隐私与数据保留边界

- 禁止上传包含他人面孔、未成年人、身份证件、病历、家庭地址或其他无关敏感信息的照片；
  UI 在选择前提示用户裁剪为食物区域。
- 普通自动化和 CI 只使用程序生成的非个人图片或固定二进制夹具，不使用真实模型 Key。经用户
  授权的本机质量评测使用公开许可图片、独立 Qwen Key 和预算门禁，不使用用户个人照片。
- 服务端不得记录 base64、原始字节、文件名、EXIF 或可跨系统比对的原图哈希。请求级审计只
  保存非内容元数据；用户取消后不留图片副本，因此没有单独的图片删除任务。
- 2026-07-28 已复核阿里云百炼服务协议：供应商应按指示处理，不得自行使用/披露或在未获
  授权时训练，并在服务终止缓冲期后删除副本；隐私声明同时说明调用数据会在满足法律要求的
  范围内保存，但公开页面未给出精确保留天数。北京端点、Key、每日人民币 1 元预算和逐次
  同意已确认；精确保留期不透明与真实质量未达标继续阻止本 ADR 转为 Accepted。

### 评测与转为 Accepted 的条件

量化指标、数据集分层和回退矩阵以
`docs/product/FOOD_IMAGE_PRIVACY_AND_EVAL.md` 为准。至少需要：Schema 有效率和“禁止自动
写入”均为 100%；非食物拒答率不低于 95%；能量真实值落入估算宽区间不低于 80%；单份食物
份量相对误差中位数不高于 30%；端到端 p95 不高于 8 秒；权限拒绝、超限、离线、超时和预算
失败全部可回退到手动记录。

### 当前实施状态

Mock/契约实现、独立 Provider Adapter、图片内存处理、候选校正、Feature Flag、三端构建、
Web E2E、22 条图片契约评测、供应商政策复核和
`journey-food-image-real-v1` 100 张授权图片集均已完成。真实集来自 Nutrition5k 70 张、
Open Food Facts 20 张和 Openverse 开放许可非食物 10 张；清单固定许可、来源、哈希和金标，
图片二进制不进入 Git、CI、数据库或应用包。

同一锁定数据集完成 Qwen `qwen3.7-flash` 三轮本机评测。v1.1 长 Prompt 使 Schema 有效率降至
40%、p95 增至 12.207 秒；据此回退为精简 JSON Prompt，并在 v1.2 增加双语规范名和有限的
确定性 Schema 归一化。v1.2 达到 Schema 100%、强制校正 100%、热量区间覆盖 84.44%、
非食物拒答 100%、p95 2945 ms、零 fallback、零自动写入与零隐私标记；但名称 Top-3
84.44% 未达到 85%，单一食物份量相对误差中位数 37.48% 未达到 30%。因此
`gate_passed=false`，ADR 继续 Proposed，阶段 9 本单项不能被描述为完整质量验收通过。

### 2026-07-29 Proposed 增补：显式尺度参照，不以换模型掩盖单目歧义

v1.2 名称 Top-3 只差 1 个有效样本达到门槛，而单一食物份量误差中位数仍高出门槛
7.48 个百分点。公开研究同样把单张 2D 图片丢失三维和物理尺度列为份量估算的核心问题，
并使用已知尺寸的 fiducial marker 做图像校正。Journey 因此先改善输入质量，不立即启用
未经评审的更强/更贵视觉模型：

- 请求新增可选 `scale_reference_type`：`none`、`journey_card`、`plate_diameter`、
  `bowl_diameter`。`journey_card` 固定为 Journey 自制的 9×5 cm 高对比参照卡；餐盘/碗口
  模式必须由用户输入 8—60 cm 的真实直径。
- 不建议使用真实银行卡、证件或带个人信息的卡片作为参照。Journey 参照卡只包含尺寸、
  棋盘格和品牌文字，必须按 100% 比例打印；盘/碗参照要求完整边缘可见、与食物处于同一
  平面并尽量俯拍。
- 参照信息只进入单次视觉 Prompt 和脱敏 Trace（类型、尺寸），不进入饮食记录、RAG 或
  用户画像。模型必须输出 `scale_reference_used`；参照不可见或几何关系不可信时为 false，
  保持低置信度并要求用户校正，不得因用户填了直径就伪造精确克重。
- Prompt/Schema 升为 v1.3/schema-3，但原请求不传参照时保持向后兼容。Mock 和 CI 只验证
  契约，不宣称参照改善了真实质量。
- 新建独立、密封的 holdout，必须与调参集在 source ID、图片 SHA-256 和样本 ID 上零重叠。
  可先建立至少 30 张未见过的无参照泛化集以检测 Prompt 过拟合；`journey_card`/已知直径
  的尺度收益只有在另有至少 30 张开放许可、真实称重且参照尺寸可核验的配对图片后才能评测。
  SimpleFood45 虽包含物理参照、重量与能量，但其公开仓库未提供清晰数据许可，因此当前
  不纳入 Journey holdout。

2026-07-29 的进一步公开数据调研不降低上述硬门禁：

- [SNAPMe](https://doi.org/10.15482/USDA.ADC/1528346) 是当前最适合做“真实场景尺度提示”
  的公开候选。官方数据集采用 CC BY-SA 4.0，明确用于模型评测而非训练；非包装食物照片带
  1.5×1.5 英寸（3.81×3.81 cm）棋盘格，关联 ASA24 食物记录。它可用于同图“不给尺寸”
  与“告知棋盘格尺寸”的次级配对测试，但 ASA24 份量是参与者录入的饮食记录，不是实验室
  秤重，因此不能替代“真实称重”的份量误差硬门禁。
- [MetaFood3D](https://lorenz.ecn.purdue.edu/~food3d/) 提供食物重量、营养、RGB-D 视频和
  fiducial marker 资料，许可为 CC BY-NC 4.0，是更接近硬门禁的候选；但必须填写申请表并
  获得密码，而且在取得数据前还不能确认食物帧与已知尺寸 marker 是否同时可见。只允许将其
  用于非商业本机评测，图片不得进入 Git、应用包或未来商业发布物。
- ECUSTFD 虽声明为 free public 并提供 25 mm 一元硬币、质量和体积，但仓库没有正式数据
  许可证；SimpleFood45 同样没有清晰数据许可证。二者继续排除。Nutrition5k 虽为 CC BY
  4.0 且有称重金标，但 RGB 图没有可核验的已知尺寸 2D 参照，只能继续作为无参照基线。
- 小红书等内容社区默认只用于发现常见食物、拍摄方式和用户用语，不直接保存帖子截图或纳入
  训练/评测集。帖子中的克重通常是作者自报，不能证明称重过程、皮重、可食部和图片中的食物
  一一对应；公开可见也不等于授予图片再利用许可，截图还可能包含用户名、头像、位置等个人
  信息。只有作者明确授权 Journey 使用、去除个人标识，并且食物与电子秤读数或已知尺寸
  参照可以核验的样本，才可在密封前作为候选；仍须标注 `weighed` 或 `self_reported`，
  后者不得用于份量误差硬门禁。

用户随后提供 16 张图片并确认作者允许 Journey 取用。它们以
`journey-food-image-scale-candidate-v0` 保存于 Git 忽略目录：1 张仅作份量参考、1 张重复
总览排除，其余拆为 88 个单格，其中 30 个同时包含食物、尺子和电子秤。该批仍只标记为
`user_attested_final / source_links_unavailable`：用户再次确认可以使用，但帖子已经关闭，
不能恢复可独立核验的来源链。它们只允许 Journey 内部研发/展示，不作为开放数据集再分发。
画面直接显示名称、声明克重或秤读数，原样输入模型会造成答案泄露，因此已为 30 个尺度候选
生成同图、同尺寸的 `with_ruler` 与 `without_ruler` 共 60 张确定性遮挡图；不生成或修改
食物内容。30 个电子秤实际读数已经逐格人工核对，全部 60 张遮挡输入已通过 contact sheet
与疑难格放大视觉 QA，并固定为内部
`journey-food-image-scale-holdout-v1`；密封后禁止用于 Prompt 调整。

该 holdout 的参照是厘米尺，而当前公开请求契约只有 `none`、`journey_card`、
`plate_diameter`、`bowl_diameter`。现有真实评测器严格走 `/api/v1`，不能公平表达
“有尺”条件；以 `none` 发送还会明确要求模型不得假设未声明物体尺寸。因此当前不运行 Qwen，
不改变尺度收益 `Not evaluated`。是否增加 `centimeter_ruler` 或仅建立隔离试验适配器必须
先以 Proposed ADR 确认，不能为了得到评测数字静默改公开产品契约。

### 2026-07-29 Accepted 子决策：厘米尺只进入隔离评测适配器

用户确认继续执行上一轮推荐方案。厘米尺是本批 holdout 的实验参照，不是 Journey 当前
面向用户设计的拍摄入口，因此：

- 不修改 `FoodImageAnalyzeRequest`、OpenAPI、移动端参照选项或正式 v1.3 Prompt；
- 新建仅本机运行的隔离评测器，复用同一个 Qwen Provider、Pydantic 结构化输出、Token/
  延迟/费用记录和密封数据，但使用独立版本化的厘米尺试验 Prompt/Schema；
- 预先固定门禁：有尺份量误差中位数 ≤30%、相对同图无尺中位误差改善 ≥15%、60 个条件的
  参照使用判断准确率 ≥95%、Schema/强制校正 100%、p95 ≤8 秒、fallback 为 0；
- 先完成 dry-run、资产哈希和预算检查，再对密封 v1 数据执行唯一一次真实 Qwen 配对评测；
  运行后禁止根据本 holdout 的失败样本调整 Prompt 或 Schema；
- 报告只保存样本 ID、金标、结构化预测、指标、Token、费用和延迟，不保存图片、base64、
  API Key 或可恢复的来源帖子信息。

该子决策不把 ADR-030 整体转为 Accepted。隔离结果只能证明当前模型在这批厘米尺图片上的
尺度推断能力；不能直接证明 Journey 卡、盘直径或碗直径的正式产品链路已经达到质量门禁。

唯一一次真实评测随后完成。Qwen `qwen3.7-flash` 在 60 个输入中产生 53 个有效结构化结果，
仅 24/30 组两边都可评分；同图完整配对的有尺份量误差中位数为 47.82%，无尺为 48.87%，
相对改善 2.17%，远低于 15% 门槛。有尺有效结果 24/24 声称使用参照，无尺有效结果 29/29
没有声称使用参照，但把 7 次结构化失败计入后参照判断为 53/60=88.33%，仍低于 95%。
p95 3744 ms 通过，fallback 7 次失败。

首版评分用不同数量的有尺/无尺有效样本各自求中位数，错误得到 4.37% 改善；零调用复算按
24 个完整配对修正为 2.17%。首版失败分支还未保存 7 次无效响应的用量，因此
`$0.00144897` 只作为已记录费用下限。评测器已修复评分与失败用量记录并增加回归测试，但不
重跑密封集、不修改冻结 Prompt。结果未达门禁，ADR-030 继续 Proposed，正式产品继续
Mock/强制用户校正/手动记录回退。

### 2026-07-29 Accepted 子决策：实验性辅助定位，厘米尺路线 No-Go

用户要求继续后，按上一轮建议选择“接受辅助定位并收尾”，不擅自启用未经评审的更强模型。
基于真实门禁失败，当前产品边界固定为：

- 食物图片入口明确标注“实验”，直接提示模型不能通过照片准确称重；点估计明确不是称重值；
- 图片只生成可编辑候选，用户校正和显式确认前不得写入；失败、离线或关闭时回退手动记录；
- Development 可在本机显式启用；Preview、Production 和 staging 继续关闭图片入口并使用
  Mock/零外发配置，直到新的独立评测通过；
- 不把厘米尺加入公开 API，不再使用本 30 组密封集调整 Prompt，也不追加同集模型调用；
- 保留现有图片候选、参照卡和评测证据，作为受控实验与秋招展示资产，不删除已实现代码；
- 若未来比较更强视觉模型或改变交互，必须新建 Proposed ADR、使用新的独立 holdout，重新
  确认供应商、隐私、预算和门禁，不能把本次失败静默改写为已解决。

“No-Go”仅指当前厘米尺改善路线和“照片可可靠称重”的产品承诺，不表示删除图片选择、隐私
处理、结构化候选或用户校正能力。ADR-030 仍为 Proposed，真实图片 Provider 不具备
Preview/Production 启用条件。

当前执行环境访问 SNAPMe 官方 1.89 GB 归档时由托管网关返回 HTTP 403；MetaFood3D 又需要
外部申请。因此本轮只固化来源、许可和证据边界，不下载、不伪造配对数据，也不新增
`checkerboard` 请求类型。取得合法数据后，必须先密封清单、核验授权与 marker 共视，再实施
契约扩展和真实评测。

本增补仍属于 ADR-030 Proposed。只有密封尺度 cohort 上份量误差中位数 ≤30%、相对无参照
配对基线至少改善 15%、参照使用判断 ≥95%，同时原有全部门禁通过，才可转 Accepted。

实现后建立 `journey-food-image-holdout-v1`：15 张单一食物、15 张混合餐，与调参集在
sample ID、Nutrition5k source ID 和 SHA-256 上全部零重叠。Qwen v1.3 的 holdout 结果为
Schema/强制校正 100%、Top-3 76.67%、份量误差中位数 36.36%、热量覆盖 90%、p95
3473 ms、fallback/自动写入/隐私标记为 0；无参照时 30/30 没有虚构使用参照。该结果未通过
Top-3 和份量门禁，并且不包含尺度配对样本，因此不改变 Proposed 状态，也不用于继续调参。

研究依据：[Food Portion Estimation via 3D Object Scaling](https://openaccess.thecvf.com/content/CVPR2024W/MTF/html/Vinod_Food_Portion_Estimation_via_3D_Object_Scaling_CVPRW_2024_paper.html)、
[单图份量估计中的 fiducial marker](https://pmc.ncbi.nlm.nih.gov/articles/PMC6226047/)。

### 回退

将 `FOOD_IMAGE_ANALYSIS_ENABLED=false` 或 `FOOD_IMAGE_PROVIDER=mock` 即可停用真实图片外发；
无需回退数据库结构。移除图片入口后，既有文字 Agent 和饮食表单仍完整可用。若真实 Provider
质量不达标，保留已验证的选图—预览—手动校正流程，不展示模型估算。

## ADR-031：食物识别与份量确认解耦

**Status: Proposed（产品方向获用户接受，但 Qwen 唯一真实质量门禁失败；不进入正式产品）**
**Date: 2026-07-30**

### 背景

ADR-030 的真实评测已经证明：当前 Qwen `qwen3.7-flash` 可以运行完整图片候选链路，但在独立
holdout 上的食物名称 Top-3 和份量误差均未达到门槛；加入厘米尺后，完整配对的份量误差仍为
47.82%，相对改善只有 2.17%。继续要求单张照片同时完成食物识别和克重估算，会把不可观察的
三维体积、密度、可食部和烹饪含水量混成一个看似精确的数字。

当前三个选择为：

1. 继续更换模型并承诺照片估重，成本和误导风险最高，且仍需要新的称重配对集；
2. 完全删除图片入口，工程风险最低，但丢失已经验证的隐私、候选、校正和确认链路；
3. 保留图片只做“食物名称候选”，份量由用户选择常用单位或输入克重，热量由受控营养数据
   和现有业务规则计算。

### Proposed 决策

选择第 3 项作为下一轮候选方向，但在本 ADR 被用户接受、独立 holdout 建成且模型复核完成前
不修改正式 App、API、Prompt 或 Schema：

- 视觉模型只返回最多 3 个食物名称候选、是否为食物、低/中置信度和需要用户确认标记；
- 不让视觉模型输出克重、热量点估计或“已称重”表述；
- 用户必须选择候选或手动填写名称，并用克、份、个、碗等现有表单能力确认份量；
- 确认后的营养换算复用服务端受控数据和现有饮食记录契约，不由视觉模型自由生成；
- 图片分析仍不自动写库，原图仍只在请求内存处理，Feature Flag、正式环境关闭和手动回退
  保持不变；
- ADR-030 的厘米尺 No-Go 不撤销；本方案不再把尺度参照作为食物名称识别的前置条件；
- 暂不指定或启用更强视觉模型。候选模型必须在独立 Key、区域、价格、数据政策和预算复核后
  才能进入一次性密封评测。

### 2026-07-30 用户确认与数据门禁

用户确认继续第 3 项“识别候选 + 手动确认份量”方向。本确认只接受产品方向和独立数据集
建设，不等于接受任一视觉模型的真实质量，也不授权修改正式产品或直接调用 Provider。

`journey-food-image-recognition-holdout-v2` 已在任何新 Provider 调用前完成密封：

- 60 张来自 Wikimedia Commons 的全新图片，分层为中国家庭餐 20、单一食物 15、混合餐
  10、包装食品 10、非食物 5；
- 每条记录保留文件页、原图、作者、许可和许可 URL；许可覆盖 CC BY、CC BY-SA、CC0 和
  Public domain；
- 五组联系表完成全量目视 QA；不含可识别人脸、未成年人、证件、病历或个人标识；
- 与既有调试集、泛化集和厘米尺集在数据集来源、source ID 和 SHA-256 上均为 0 重叠；
- 密封清单固定 `prompt_tuning_allowed=false`，真实 Provider 调用数为 0；
- 图片二进制保持 Git ignored，不进入应用包；版本化清单不包含图片 base64 或密钥。

因此“用户接受方向”和“建立独立 holdout”两项前置条件已满足。ADR 仍保持 Proposed，是
因为候选模型、区域、价格、数据政策和独立 Key 尚待重新复核，且一次真实质量评测尚未执行。

### 转为 Accepted 的条件

必须先建立 `journey-food-image-recognition-holdout-v2`，与既有调试集、泛化集和厘米尺集在
来源、样本 ID 和 SHA-256 上全部零重叠，并满足：

- 至少 60 张：20 张中国家庭餐、15 张单一食物、10 张混合餐、10 张包装食品、5 张非食物；
- 不含人脸、未成年人、证件、病历、位置或其他无关个人信息；
- 来源许可或用户授权可追溯，且图片、标签与授权证据在密封前完成核验；
- 食物名称 Top-3 ≥85%，中国家庭餐子集 Top-3 ≥80%，非食物拒答 ≥95%；
- Schema 有效率、`needs_user_correction=true`、禁止自动写入和禁止视觉模型输出克重均为
  100%；
- p95 ≤8 秒、fallback=0；Token 和费用完整记录，单日预算继续不超过人民币 1 元；
- holdout 密封后禁止根据失败样本改 Prompt；如需调试，另建不重叠 development set。

### 2026-07-31 模型复核与唯一真实评测

评测前重新确认：

- 北京区域 `qwen3.7-flash` 当前对应快照 `qwen3.7-flash-2026-07-15`，支持图片输入；
- 小于等于 32K Token 的北京价格为输入人民币 0.2 元/百万 Token、输出人民币 0.8 元/
  百万 Token；项目继续使用人民币 1 元/日硬上限；
- 阿里云隐私声明称调用数据不用于模型训练并使用 AES-256 加密，但同时说明因法律要求会
  存储调用数据，未公布精确保留期。因此仅允许本次公开许可、无个人信息的密封集外发；
- 使用独立 Qwen Key，评测器固定关闭 thinking、重试、后备模型路由和缓存，不输出 Key、
  图片字节或原始模型文本。

官方依据：[模型与快照](https://help.aliyun.com/en/model-studio/text-generation-model/)、
[北京区域多模态支持](https://help.aliyun.com/zh/model-studio/batch-inference)、
[模型价格](https://help.aliyun.com/en/model-studio/model-pricing)、
[隐私声明](https://help.aliyun.com/zh/model-studio/privacy-notice)。

冻结评测器 `journey-food-image-recognition-eval-1.0.0` 在 Provider 调用 0 的 dry-run
通过后，对 60 张密封集只运行一次。机器报告
`evals/reports/STAGE9_QWEN_RECOGNITION_V2.json` 的 SHA-256 为
`e455f44ef12a547df509c50864926e3c1c35dd49fbf05b976ca218acab515afe`：

| 指标 | 结果 | 门槛 | 状态 |
|---|---:|---:|---|
| 总体食物名称 Top-3 | 37/55 = 67.27% | ≥85% | FAIL |
| 中国家庭餐 Top-3 | 12/20 = 60% | ≥80% | FAIL |
| 非食物拒答 | 5/5 = 100% | ≥95% | PASS |
| Schema / 强制校正 / 禁止估重 | 59/60 = 98.33% | 100% | FAIL |
| 评测降级/失败计数 | 1（无后备模型调用） | 0 | FAIL |
| p95 | 3416 ms | ≤8000 ms | PASS |
| Token/成本记录 | 60/60 | 100% | PASS |
| 总估算费用 | $0.00240432（约 ¥0.0173） | ≤$0.02 且 ≤¥1/日 | PASS |
| 未确认自动写入 | 0 | 0 | PASS |

正式分数不可重算或用来调整当前 Prompt。事后只做了不改变分数的质量审计，发现冻结别名
匹配对“水饺/饺子”“肉酱螺旋意面/肉酱意面”“牛排套餐/牛排餐”等合理同义或更具体名称
过严。这意味着 67.27% 不能被外推为模型真实准确率，但同样不能据此把失败改成通过。未来
若重启，必须在任何模型调用前用全新 development set 改进标签本体和语义评分，再建立全新
密封 holdout；不得重跑 v2。

结论：ADR-031 保持 Proposed，正式 App/API 不接入该真实识别能力，阶段 9 食物图片授权
范围以 No-Go 停止。即使未来名称识别通过，照片自动估重仍受 ADR-030 No-Go 约束。

### 回退

若用户不接受该方向，保留 ADR-030 的 Development 实验性候选与正式环境关闭状态，不修改
任何业务代码。若后续识别门禁失败，继续使用手动饮食记录；不得恢复照片自动估重承诺。

## ADR-032：当前版本不实现语音转文字

**Status: Accepted**
**Date: 2026-07-31**

### 背景

阶段 9 食物图片单项关闭后，计划要求后续多模态能力必须由用户逐项选择。语音转文字曾被
建议为候选下一步，但用户明确决定“不做语音转文字”。

### 决策

- 当前 Journey 交付范围不实现录音、语音转文字或 Realtime Voice Agent；
- 首页继续以文字作为 Agent 的统一输入，现有饮食、运动、查询和建议路由不受影响；
- 不申请麦克风权限，不采集、上传、存储或转写音频；
- 不建立语音 Provider、音频数据集、评测集或相关 CI；
- 该能力标记为 `Deferred / 当前范围外`，不是默认下一阶段。

### 影响与重新启动条件

本决策减少权限、音频隐私、模型费用和跨平台原生模块维护范围，不需要删除任何现有业务
能力。只有用户未来单独明确改变本决策时，才允许新建 Proposed ADR，先完成权限、数据保留、
供应商、预算、评测和无网回退审查；不得仅凭“按计划继续”自动恢复。

## ADR-033：当前版本收敛为文字与图片，发布验收必须使用对应真实模型

**Status: Accepted**
**Date: 2026-08-01**

### 背景

阶段 7/8 使用 Mock 完成了稳定、零成本的工程回归，但 Mock 只能证明路由、Schema、工具、
RAG、客户端流程和降级契约，不能证明 DeepSeek 或 Qwen 的真实质量。用户进一步确认当前产品
功能暂时只保留文字与图片，并要求验收改为各自对应的真实模型。

### 决策

- 当前新增能力范围收敛为文字 Agent 与食物图片候选；语音、视频、手机号、HealthKit/
  Health Connect 和通知不进入本次验收；
- 普通 CI 继续使用 Mock、空真实 Key 和零预算，避免外部波动、费用和密钥风险；
- 发布验收必须额外运行真实模型门禁：文字使用当前配置的 DeepSeek，图片使用当前配置的
  Qwen 北京区域模型；报告必须记录 Provider、精确模型名、Prompt/Schema/数据版本、Token、
  延迟、费用、fallback 和量化分数；
- Mock 通过不得替代真实模型通过；真实模型功能冒烟也不得替代独立质量集；
- 当前 DeepSeek `deepseek-v4-flash` 首轮量化门禁发现一条画像查询误路由；Router Prompt
  从 `1.0.0` 升级到 `1.0.1` 后，28/28 复验全部通过，可用于联网本机演示；
- 当前 Qwen `qwen3.7-flash` 的真实 API 冒烟通过，但 ADR-031 的 60 张独立质量门禁失败，
  所以图片仍只允许 Development 实验性使用，不能进入 Preview/Production/staging；
- 模型 alias、快照、价格或政策变化后，发布前必须重新探测并生成新报告，不得沿用旧结论。

### 影响

阶段 7 的 Mock 门禁继续承担高频工程回归；真实模型门禁是低频、显式、带预算的发布门禁，
不进入外部贡献者或普通 GitHub Actions。当前“文字 + 图片”整体发布状态仍为 Conditional，
因为图片质量未通过；这不会阻断文字 Agent 和手动饮食记录。

### 回退

将 `AGENT_PROVIDER=mock` 可回退到确定性文字演示；将 `FOOD_IMAGE_PROVIDER=mock` 或
`FOOD_IMAGE_ANALYSIS_ENABLED=false` 可停止图片外发。回退不修改数据库结构，也不影响手动
记录、Journey 或“我的”。

## ADR-034：Agent v2 采用单 Agent 的计划—执行—校验闭环

**Status: Accepted**
**Date: 2026-08-03**

### 背景

阶段 6 已实现意图路由、结构化候选、业务工具、LangGraph 工作流、受控 RAG、人工确认、
执行轨迹和模型切换，因此不是普通聊天包装。但当前工具调度主要由固定 `if/elif` 分支完成，
推荐/周总结也是固定 DAG；缺少显式任务计划、统一工具注册表、策略校验、结果验证、受限重规划
和跨模型对话线程。用户确认按“更像 Agent、但不为多 Agent 而多 Agent”的方向继续。

### 决策

- 继续使用单路由 Agent，不引入多个模型角色互相对话；
- 使用 Pydantic `AgentPlan` 表达目标、步骤、依赖、工具和是否需要人工确认；
- 建立服务端类型化工具注册表，固定工具名称、能力、风险级别、只读/写入边界、输入 Schema
  和超时；模型只能从白名单选择，不能生成任意函数名；
- 使用 LangGraph 条件边组织 Planner → Policy Guard → Executor → Verifier；最多 6 个步骤、
  最多 1 次受控重规划，超限后必须澄清或降级；
- 饮食、运动、体重只生成候选，保持现有确认 Token、所有权和幂等写入；模型和 Planner
  均无权绕过确认直接修改业务数据；
- 线程和记忆保存在 PostgreSQL，模型只接收任务所需的最小结构化摘要。画像、目标和业务记录
  仍是事实源；不把完整原始对话或个人事实默认写入向量库；
- 不依赖单一 Provider 的原生 tool-calling 协议。LangChain/LiteLLM 负责结构化计划和模型
  路由，服务端注册表负责可移植、可测试的真实工具执行；
- 首页展示精简的计划和节点状态，完整脱敏轨迹继续由 `/api/v1/agent/runs/{run_id}` 提供；
- 普通 CI 继续使用 Mock；Allure 作为 Pytest 报告增强，与既有 JUnit/Coverage 并存，不把
  `requests` 作为形式化依赖加入项目，FastAPI API 测试继续使用 HTTPX/TestClient。

### 数据与隐私边界

- `agent_threads` 仅保存用户归属、状态和有上限的结构化回合摘要；不保存原始输入正文；
- 每条摘要记录来源 run、意图、候选类型、确认状态和回答类别，不保存模型密钥或图片；
- 用户确认后的饮食、运动、体重仍写入既有业务表；线程记忆只引用事实，不成为重复事实源；
- Trace 的输入继续只保存长度/类型等脱敏摘要；Allure 附件也不得包含 Token、密钥、完整
  Authorization header 或原始敏感正文。

### 量化门禁

- Planner Schema 合法率、Policy 拦截率、Trace 完整率、未确认写入阻断率均为 100%；
- 工具选择与参数准确率 ≥95%，核心任务完成率 ≥90%，失败后正确澄清/恢复率 ≥95%；
- 不必要工具调用率 ≤5%，每次运行步骤数 ≤6、重规划次数 ≤1；
- RAG 引用支持率 ≥95%，高风险规则通过率 100%；
- Mock/CI 外部调用与费用必须为 0；真实 DeepSeek v2 门禁必须记录模型、Prompt/Schema、
  Token、延迟、费用、fallback，且不得用旧版文字报告代替；
- Pytest、migration 回环、Ruff、移动端测试/类型检查/lint 和核心 E2E 必须保持通过；Allure
  结果作为 CI artifact 生成，JUnit/Coverage 报告继续保留。

### 回退

保留 v1 路由和现有业务工具实现作为内部确定性回退。若 Planner、Policy、线程迁移或真实模型
门禁失败，通过配置关闭 v2 编排并回到 v1 固定分支；数据库 downgrade 只删除 v2 线程、计划
和验证元数据，不删除用户画像、饮食、运动、体重、Journey 或既有 Agent Run/确认数据。

### 转为 Accepted 的条件

阶段 10 全部 Checklist、数据库 upgrade/downgrade、Mock 全量回归、Agent v2 新量化门禁、
真实 DeepSeek 文字门禁和 iOS/Android/Web 最小展示全部产生可重复证据后，才能将本 ADR
标记为 Accepted。图片质量仍由 ADR-030/031 单独约束，不因 Agent v2 通过而改变。

### 验收结果

- 2026-08-03 已完成 `0004 → 0003 → 0004` migration 回环和 `alembic check`，核心业务表
  在 downgrade 后保持不变。
- Mock 全量回归为 79 条后端/评测测试通过、后端覆盖率 90.80%；342 条版本化样本和 22 项
  Agent/RAG/图片契约门禁全部通过，外部调用与费用为 0。
- 真实 DeepSeek `deepseek-v4-flash` 首轮 8 个任务、16 次调用暴露“额外读取 Journey”和依赖
  关系不合法问题，工具序列准确率为 0、Policy 合法率为 75%。Planner Prompt 从
  `journey-agent-planner-2.0.0` 升至 `2.0.1` 后，第二次固定验收的计划 Schema、工具序列、
  Policy、Provider/模型、无 fallback 和 Token 记录均为 100%，p95 3112 ms，费用
  `$0.00257824`。修正前后报告均保留，证明不是只展示成功样本。
- 移动端 31 条组件测试、5 条逻辑测试、类型检查和 lint 通过；2 条 Web E2E、Web/iOS/
  Android JS 构建通过，iOS 与 Android Release 模拟器均完成实际安装运行。Android 实际
  展示了计划、工具步骤、验证结果和受限重规划计数。
- Allure 原始结果、JUnit、Coverage、Agent JSON 报告均可由本机与 CI 生成；脱敏测试确认
  附件不包含 Token、密钥、Authorization、原始消息或完整检索片段。

上述条件已满足，因此 ADR-034 转为 Accepted。阶段 9 图片质量结论仍为 No-Go；Agent v2
通过不代表食物图片模型达到正式发布标准。

## ADR-035：Agent v3 采用人工确认检查点与 Observation 驱动的有限重规划

**Status: Accepted**
**Date: 2026-08-04**

### 背景

Agent v2 已具备结构化规划、工具白名单、策略校验和执行结果汇总，但有两个产品断点：

1. `awaiting_confirmation` 被视为可继续步骤；组合任务中的建议可能在用户确认饮食/运动前
   生成，无法保证使用最终校正后的业务数据。
2. 工具失败后的“重规划”只裁剪依赖步骤并继续独立步骤，没有把结构化 Observation 交回
   Planner 选择另一条安全路径。

用户确认继续增强 Agent，但不授权多 Agent、无限循环、后台自主写入或跨供应商自动转发健康
数据。

### Proposed 决策

- Agent Run 在遇到待确认候选时进入 `waiting_for_user`，保存不含原始输入的安全 checkpoint，
  暂停所有依赖确认结果的后续步骤；全部候选确认后才能恢复。
- Confirmation API 继续完成单条幂等写入，并返回 Run 的确认进度；显式 Resume API 负责
  所有权、状态、确认完整性和 checkpoint 校验，避免一次 confirmation 响应暗中触发不可见
  的额外模型费用。移动端在最后一条确认后明确提示并调用恢复。
- 每个工具结果转成结构化 Observation：步骤、工具、状态、错误类型、是否可恢复、输出摘要
  和允许的替代工具；不得保存原始消息、模型思维链、Authorization 或密钥。
- Verifier 返回 `done`、`wait_for_user`、`replan`、`clarify`、`fallback` 或 `stop`。只有
  `recoverable=true` 且预算未超限时才能重规划。
- Replanner 最多运行 2 次，只接收原目标摘要、剩余安全计划、脱敏 Observation 和工具目录；
  新计划仍必须通过原有 Policy Guard。非法计划回退确定性 Recovery Policy。
- 第一版替代路径只增加高价值确定性能力：知识生成失败时返回检索型安全摘要，个性化建议
  生成失败时返回规则建议；记录解析失败继续回退可编辑候选/手动表单，不增加直接写库工具。
- 同一 Run 的恢复使用当前配置供应商；Provider 失败不自动把健康数据发送到另一供应商。
- 保留单 Agent、模块化单体和现有三个一级入口；不新增后台定时任务或多 Agent 对话。
- 保留 Pytest + HTTPX/TestClient 白盒集成测试；新增 Requests + Pytest + Allure 网络黑盒
  套件，直接访问 Docker API，不替换现有测试。

### 数据与安全边界

- checkpoint 只保存安全计划、当前游标、步骤状态、候选 ID、确认进度和 Observation；计划
  `segment` 必须在持久化前清空。
- 原始输入仍只保存 hash 和长度；恢复不得依赖重新读取原文。
- 所有写工具继续不存在于 Planner 工具目录；确认 Token、所有权、过期和 Idempotency-Key
  规则保持不变。
- checkpoint 必须有过期时间；过期、状态冲突、跨用户和重复恢复均返回稳定错误码。

### 量化门禁

- 未确认写入阻断、跨用户恢复阻断、循环终止、checkpoint 脱敏和 Policy 合法率均为 100%。
- 全部候选确认后恢复成功率 ≥95%；可恢复故障的正确替代路径成功率 ≥90%。
- 工具选择准确率 ≥95%；不必要工具调用率 ≤5%；最多 6 步、2 次重规划。
- 普通 CI 使用 Mock、空真实 Key、外部调用与费用为 0；Requests 黑盒套件不得读取 `.env`
  中真实模型 Key。
- 真实 DeepSeek 门禁必须覆盖正常计划、等待确认前停止和 Observation 重规划；单次门禁预算
  不超过 `$0.02`，失败时保持 Proposed。

### 回退

- `AGENT_V3_ENABLED=false` 回退 Agent v2；checkpoint 表和字段不影响核心业务记录。
- Migration downgrade 只删除 v3 checkpoint/observation 元数据，不删除用户、记录、画像、
  Journey、既有 Run 或 Confirmation。
- Requests 黑盒套件可独立移除，不影响 TestClient/JUnit/Coverage/Allure 基线。

### 转为 Accepted 的条件

阶段 11 全部 Checklist、migration 回环、Mock 全量门禁、Requests 黑盒、移动端确认恢复、
三端构建和显式真实 DeepSeek v3 门禁产生证据后，ADR-035 才能转 Accepted。

### 验收结果

- Alembic `0005_agent_v3` 已完成 `0005 → 0004 → 0005` 回环和 `alembic check`；downgrade
  只移除 v3 checkpoint/observation 字段，不删除核心业务表。
- Mock 全量回归为 85 条测试通过、后端覆盖率 90.49%；362 条版本化样本、26 项门禁全部
  通过，外部调用与费用为 0。未确认写入、跨用户/重复恢复、循环超限和 checkpoint 原文泄露
  均由自动化测试阻断。
- Docker 隔离 API 上的 Requests + Pytest + Allure 网络黑盒覆盖注册、Run、暂停、确认、
  Resume 和 Trace，1/1 通过；它与 HTTPX/TestClient 白盒测试、JUnit、Coverage 并存。
- 移动端 31 条组件测试、5 条逻辑测试、类型检查、lint 和 2 条 Web E2E 通过；Web、iOS、
  Android JS 构建均通过。E2E 验证了“记录 + 建议”在确认后显式恢复并展示基于新数据的结果。
- 固定的真实 DeepSeek `deepseek-v4-flash` v3 门禁仅执行一次：4/4 checkpoint 计划和 2/2
  可恢复故障替代选择通过，Provider/模型匹配与 Schema 无 fallback 均为 100%，10 次调用
  总费用 `$0.00171864`，低于 `$0.02` 上限；报告未包含 Key 或原始消息。

上述条件已满足，因此 ADR-035 转为 Accepted。ADR-034 中“不引入 Requests”的测试选型说明
仅代表阶段 10 当时范围，本 ADR 以独立网络黑盒层补充而非替换 HTTPX/TestClient。图片质量
仍由 ADR-030/031 单独约束，Agent v3 通过不改变图片 No-Go。

## ADR-036：采用本地优先的数据副本与 AI 原生首页

**Status: Proposed**
**Date: 2026-08-04**

### 背景

当前移动端已经能缓存部分查询并把离线新增记录放入加密待同步队列，但画像/目标仍依赖 API，
编辑和删除受限；首页用大面积 Hero 和警告卡表达离线状态，统一输入在常见手机首屏不够突出，
角色贴图与卡片层次也未达到用户期望的年轻、智能和轻盈感。

### Proposed 决策

- PostgreSQL 保持跨设备同步事实源，移动端建立按账户隔离的本地规范化数据副本；
- 首次成功登录后同步画像、目标和全部健康记录，离线可读写，联网后通过 Outbox、幂等键和
  版本冲突检测同步；退出时清除该账户本地数据和队列；
- 首次登录、找回密码、在线 Agent、图片和 Web Research 继续要求联网；离线确定性归类和
  内置常识不得冒充 Agent；
- 首页保持“首页 / Journey / 我的”三个一级入口和薄荷绿叶子品牌，但把统一输入提升为首屏
  主操作；离线状态使用轻量状态与同步文案，不再使用占据首屏的大警告卡；
- 第一轮“温和 AI 健康伙伴”和“轻量数据智能”已被用户否决：过暗、偏灰，且重画吉祥物质量
  不符合预期；不得把这两套方向继续实现；
- 第二轮“暖白薄荷 Journey”已由用户确认并完成视觉子项：固定浅色品牌体验，复用原版叶子
  角色，以旧版明亮薄荷 Hero、暖白背景和减少卡片数量为核心；
- 详细矩阵、视觉规格和量化门禁见
  [`product/LOCAL_FIRST_AI_UI_PROPOSAL.md`](product/LOCAL_FIRST_AI_UI_PROPOSAL.md)。

### 风险与回退

- 本地健康数据增加设备丢失、串号和同步冲突风险，必须使用设备级密钥、账户隔离和显式冲突
  处理；在这些门禁未完成前保持当前部分缓存方案；
- 完整本地副本可能随数据增长，需要后续用真实容量决定保留策略；当前个人使用规模下先优先
  可用性；
- UI 方向未确认前不得修改完整页面。若新首页可用性测试失败，保留当前页面路由和 API，仅
  回退视觉层，不回退离线数据完整性目标。

### 已确认的视觉子决策（2026-08-04）

- 用户明确接受方案 C，并授权继续实现首页视觉；该子决策视为已确认，不再回到已否决的暗色
  A/B 方向；
- 移动端采用固定暖白＋明亮薄荷浅色主题，首页复用 `journey-leaf-home.png`，保留三个一级
  入口；统一输入置于 Hero 下沿，在线/离线只改变状态和能力文案，不把页面整体变暗；
- 本次没有实现完整本地副本、冲突处理、数据库/API 或 Agent 工具，因此 ADR-036 整体继续
  `Proposed`，不能据此宣称 Journey 已经 local-first。

### 转为 Accepted 的条件

视觉方向已确认；仍需用户确认本地数据范围和冲突策略。后续实现阶段完成迁移、加密/隔离、离线/同步
故障测试、双模拟器及可用性门禁后，才能转为 Accepted。

## ADR-037：生活内容采用受控 Web Research 与用户主动分享，不直接绑定小红书账号

**Status: Proposed**
**Date: 2026-08-04**

### 背景

用户希望 Agent 获取小红书等年轻、多元的生活信息。当前 Journey 工具白名单没有浏览器或
通用网页搜索工具；`knowledge.retrieve` 是受控 RAG，不是浏览器。公开可确认的小红书开放
能力集中在商家/电商、小程序和笔记发布等场景，尚未确认存在可任意检索消费者笔记或推荐流的
公共 API。

### Proposed 决策

- 不收集小红书账号、密码、Cookie、验证码，不代理自动登录，也不驱动用户登录态浏览器后台
  抓取、互动或发布；
- 近期只考虑用户逐次主动分享公开链接到 Journey，由用户确认后保存最小元数据、短摘要和
  来源链接，不批量复制正文或图片；
- 通用信息获取另建受控 `Web Research Tool`，必须使用公开页面、域名白名单、SSRF 防护、
  无 Cookie、超时/响应体上限、引用、日期、审计和 Prompt Injection 防护；
- 如果未来获得小红书正式应用、OAuth 及明确包含所需内容的 Scope，先复核最新平台协议、
  数据用途与删除义务，再通过官方 API 接入；
- 社交内容只能作为生活灵感和偏好候选。营养数值、健康风险和建议依据必须来自受控知识库或
  权威来源，并在 Schema/UI 中标明证据级别。

### 依据

- [小红书 Ark 开放平台简介](https://school.xiaohongshu.com/en/open/quick-start/introduction.html)
  当前描述的是商品、库存、价格和包裹相关第三方能力；
- [小红书小程序开放平台](https://redopen.xiaohongshu.com/)公开的是小程序载体、经营入口和
  笔记发布等能力；
- [小红书开放平台开发者协议](https://xiaohongshu.apifox.cn/doc-2811022)要求合法渠道、用户
  同意和最小必要，禁止索取平台账号密码/认证凭据或代理自动登录，并约束内容与平台数据使用。

### 风险与回退

- 平台能力、协议和可用 Scope 会变化，实施前必须重新核对官方文档；
- 公开网页也可能有版权、个人信息、错误内容和 Prompt Injection 风险，默认只返回摘要与
  链接，不进入健康事实库；
- 若不存在合规稳定的读取方式，则回退为用户手动保存链接和自写备注，不实现自动抓取。

### 转为 Accepted 的条件

用户确认近期采用“主动分享链接”还是仅保留规划；后续专项完成法律/平台复核、威胁模型、
Schema、引用与安全测试并通过量化门禁后，才能转为 Accepted。
