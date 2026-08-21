# Journey 项目交接状态

> 更新时间：2026-08-13
> 用途：新对话的仓库现场快照，不替代 `AGENTS.md`、`docs/JOURNEY_REFACTOR_PLAN.md`、
> `docs/ARCHITECTURE_DECISIONS.md` 或 `docs/EXECUTION_LOG.md`。若内容冲突，以代码核查和上述
> 单一事实源为准。

## 1. 项目目标与当前阶段

Journey 是由旧版微信小程序迁移而来的跨平台 AI 健康管理应用，面向健身、饮食、运动、体重
与生活方式管理，不提供医疗诊断或治疗建议。

目标形态：

- Expo Development Build 为统一客户端，iOS Simulator 是主要本机开发/演示路径；
- Android Emulator 用于跨平台验收，Web 是补充发布形态；
- FastAPI、PostgreSQL、Agent、RAG 和自动化测试由三端共享；
- 一级入口固定为“首页 / Journey / 我的”；首页用统一自然语言输入自动识别记录、查询和建议；
- Agent 必须有结构化计划、白名单工具、人工确认、执行校验、有限重规划和可审计轨迹，不能只把
  普通模型调用改名为 Agent。

**阶段 13：秋招 Demo 封板已经 Completed**：

- ADR-039 已转为 `Accepted`：保留一个 Orchestrator，在同一 FastAPI 进程内显式划分
  Record、Health Knowledge、Journey Summary 三个 Specialist Agent；没有增加 Agent 群聊、
  新微服务或模型直连数据库；
- 首页主 Demo 已真实跑通“牛肉面 + 跑步 5km + 本周减脂情况”：Orchestrator 拆解复合输入，
  两类记录形成候选，Summary 读取 7 天结构化数据，写入仍必须经过 Confirmation Gate；
- RAG v2 使用固定 60 题数据集分层评估 Retrieval 与 Generation。真实 DeepSeek 报告达到
  Recall@3/5=1.0、MRR=0.9625、Groundedness/Answer Relevance=0.9625、Citation
  Correctness=0.9083、Abstention Accuracy=1.0；失败的第一轮报告同样保留；
- Journey 在原有多日语义上增加 7/30 天窗口、趋势、目标、AI 总结与建议；没有改成今日
  Timeline；
- Docker preflight、一键启动、真实/Mock 模式可见性、复合场景网络黑盒、离线 Outbox 恢复、
  Web E2E、三端 export 和 iOS/Android Debug 模拟器均已验收；
- Demo 封板后默认只进行 bug fix、Eval、E2E、Docker 与文档维护；语音、视频、OAuth、手机
  登录、健康平台、通知、自动小红书抓取和通用浏览器 Agent 统一为 Post-Demo / Future。

**2026-08-13 封板维护已完成（ADR-040 Accepted）**：

- 修复真实 Agent 工作流超过客户端统一 10 秒阈值后产生的假“网络不可用”、过期 Resume 和
  候选二次确认误导；Agent Run/Resume 使用 120 秒客户端窗口，并用 Run Trace 对账完成状态；
- Home/Journey 将旧 `net_kcal` 明确标为“记录差值”，新增基于完整画像的 Mifflin–St Jeor
  静息能量预测和记录口径余量，明确不等于完整 TDEE 或医疗测量；
- 当前全量证据为后端/评测 100/100、覆盖率 90.69%，移动 Jest 48/48 + 逻辑 5/5；真实
  DeepSeek v4 Pro 周总结 smoke 20.4 秒返回 HTTP 200、3 条引用、无降级。

**阶段 12：本地优先与 AI 原生体验已经 Completed**：

- 已完成：用户确认的“暖白薄荷 Journey”方案 C 首页视觉子项；
- 已完成：ADR-036 原生 local-first 第一批范围，包含画像、目标、最近 90 天记录/Journey、
  离线 CRUD Outbox、版本冲突选择和退出彻底清理；
- 已完成：ADR-037 用户主动分享公开链接、受限元数据预览、手动回退、显式确认、来源展示和
  删除；生活灵感固定为 `inspiration_only`，与 Agent/RAG/健康事实隔离；
- ADR-036、ADR-037 均已 `Accepted`。不能宣称 Journey 已绑定小红书，也不能宣称 Agent 已有
  通用浏览器或 Web Research 工具。

阶段 8 于 2026-08-05 完成一次服务器 Docker production 复验：独立 Compose、API/PostgreSQL
production 运行、Web HTTPS export 和 Caddy 配置均已验证；Docker Hub 网络超时仍阻塞四容器
本机整栈。当前是“可部署配置”，不是“已经公网部署”。

## 2. 当前 Git 与目录安全状态

| 项目 | 当前事实 |
|---|---|
| 当前分支 | `codex/journey-migration-baseline` |
| 远程仓库 | `journey-v1` → private `boom080/journey_v1`；旧 `origin` 仍为 `boom080/fitness` |
| 当前 HEAD | `2654c4308279a95f9fd8d45109807373b518202d`，迁移基线提交 |
| 工作区状态 | 2026-08-13 本轮收口检查时共 120 项变化：90 项已跟踪修改、30 项未跟踪；均尚未提交 |
| 主要原因 | 阶段 8 production、阶段 12 local-first/生活灵感及阶段 13 Demo 封板实现与证据 |
| 远程状态 | 迁移基线已推送；本轮变更未 commit、未 push、未创建 PR |

迁移基线风险已解除；当前 production、local-first 与生活灵感改动仍属于用户工作区，后续严禁执行
`git reset --hard`、`git clean`、强制 checkout 或任何未授权清理。commit/push 仍需用户单独授权。

敏感与生成文件状态：

- 根目录 `.env` 已被 `.gitignore` 忽略，本次没有读取或打印 Key；当前权限为 `0600`；
- `reports/`、`artifacts/`、Expo `dist*`、原生 `ios/`/`android/`、覆盖率和缓存均被忽略；
- `apps/mobile/ios/` 约 5.6 GB，`apps/mobile/android/` 约 3.5 GB，属于本机生成的原生工程/
  构建缓存。不要为省空间擅自删除；如需清理应先单独确认并保留重建路径。

### 阶段 8 production Docker 复验

- `compose.production.yaml` 一次编排 PostgreSQL、FastAPI、Expo Web 和 Caddy；只有网关发布
  80/443，PostgreSQL/API 只在 Docker 网络中可达；
- 当前代码的 production API 镜像已重新构建；隔离 API/PostgreSQL project 自动迁移到
  `0007_life_inspirations (head)`，live/ready 均为 200，并确认 production、Mock、禁测试账号、
  禁真实图片识别和默认禁生活灵感自动预览；四容器与真实 HTTPS 仍保留到服务器验收；
- Web 使用 HTTPS Origin 导出 14 路由；Caddy 2.11.4 官方二进制验证 Caddyfile 有效并启用
  自动 HTTPS；
- Docker Hub anonymous token 连接超时阻塞 Node/Nginx/Caddy 镜像拉取，因此没有四容器本机
  整栈或真实域名证书证据；上线服务器必须补跑 `up -d --build --wait` 与 HTTPS smoke；
- iOS/Android 不由 Docker 分发，仍需签名构建并注入同一 HTTPS API Origin。

## 3. 已完成工作

### 阶段 1—3：迁移基线与跨平台骨架

- 审计旧仓库、提取品牌角色/UI/业务规则，建立唯一迁移计划和 ADR；
- 按清单退役微信/Taro 客户端，旧代码的删除仍保留在 Git 工作区中；
- 建立 npm workspace、Expo SDK 57 客户端、FastAPI 与 PostgreSQL 18 Docker 基线；
- Web、iOS、Android 路径均已建立，生产 application id 确认为 `com.boom080.journey`。

### 阶段 4—5：身份、业务 API 与移动端核心流程

- 邮箱或用户名 + 密码的注册、登录、刷新、退出和测试账号；
- 用户画像、目标、饮食、运动、体重、首页聚合和 Journey 历史 API；
- 登录、画像/目标、首页、Journey、我的、手动饮食/运动/体重页面；
- 阶段 5 当时的离线新增记录进入按用户隔离、AES 加密、24 小时/50 条上限的待同步队列；
- 该旧队列现只作为升级迁移兼容，当前 local-first 能力见阶段 12 小节。

### 阶段 6—7：Agent、RAG、自动化测试与 CI

- LangChain + LangGraph + 嵌入式 LiteLLM Router；
- DeepSeek、Qwen、GLM、Kimi、OpenAI 和 OpenAI-compatible Provider Profile；
- 受控知识库、检索、引用、无答案处理、Prompt/Schema/Knowledge 版本；
- Pytest + HTTPX/TestClient 白盒、Requests + Pytest + Allure 网络黑盒、Jest、Playwright E2E；
- GitHub Actions 的 backend、mobile、web-e2e 三个 job，普通 CI 固定 Mock、空 Key、零预算。

### 阶段 8：本机 staging、构建与求职材料

- 本机隔离 staging、备份/恢复、健康检查和故障回退文档；
- iOS/Android Release 曾在模拟器完成安装运行，Web 可静态导出；
- 3—5 分钟演示脚本、架构图、测试报告、四类岗位讲述材料；
- 未租服务器、未公网部署、未完成 Apple/Google Play 商店签名或上架。

### 阶段 9：食物图片候选（Closed / No-Go）

- 完成隐私边界、授权数据、尺度实验、密封集、真实 Qwen 调用和用户校正流程；
- Qwen API 功能冒烟成功，但独立质量门禁失败：Top-3 67.27%、中国家庭餐 60%、Schema
  98.33%；
- 图片只允许 Development 实验性候选，Preview/Production/staging 不启用真实图片识别；
- 当前不做语音转文字；视频、手机号、HealthKit/Health Connect、通知均未获单项授权。

### 阶段 10—11：Agent v2/v3 基线

- 单 Agent 的 Planner → Policy Guard → Executor → Observation → Verifier → Replanner；
- 工具白名单、最多 6 步/2 次重规划、写入前人工确认；
- 组合任务在候选确认后显式 Resume，并重新读取最新业务事实；
- PostgreSQL 保存最小结构化线程记忆、脱敏 checkpoint、Observation 和执行轨迹；
- 可恢复故障只能选择白名单替代工具，不能无限循环或暗中切换供应商；
- 真实 DeepSeek v3 固定门禁通过：4 个 checkpoint 计划、2 个恢复选择、10 次调用，费用
  `$0.00171864`。

### 阶段 13：有限 Multi-Agent 与 Demo 封板

- 复用 v3 的状态机、Policy Guard、Observation、Verifier、Replanner、checkpoint 和恢复机制；
- Orchestrator 负责拆解、路由、共享 Run State 与汇总，Record/Knowledge/Summary Specialist
  只执行各自工具白名单；Specialist 不是独立服务，也不互相自由对话；
- Execution Trace 只显示意图、已选 Agent、工具、状态、候选数、检索文档/分数、数据范围和
  耗时，不展示隐藏思维过程；
- RAG v1/v2 固定数据集比较同时记录 Recall@K、Precision@K、MRR、nDCG、生成质量、延迟、
  Token、费用、Provider、模型与配置；没有把 Mock 分数冒充真实模型质量；
- 真实 DeepSeek 复合黑盒 1/1 通过；后端全量 100/100、移动 Jest 46/46 + 逻辑 5/5、Web
  E2E 2/2，后端覆盖率 90.60%；
- 食物图片仍沿用用户校正与确认链路，但真实质量门禁保持 No-Go，不因 Demo 封板伪装成已上线。

### 阶段 12 已完成的 ADR-036

- 固定暖白 + 明亮薄荷浅色品牌主题，不再跟随已否决的暗灰方向；
- 首页复用原版 `journey-leaf-home.png`，统一输入位于首屏；
- 今日指标改为开放式分栏，Agent 状态改为轻量状态条；
- 在线/离线文案保持真实能力边界；原生端现已实现第一批 local-first，Web 明确仅进程内副本；
- 320 × 844、390 × 844 Web 手机视口人工核对通过；
- 原生端每账户 AES-256-GCM 密文 + SecureStore 密钥，保存画像、目标和最近 90 天记录/Journey；
- 离线支持记录新增/编辑/删除、画像/目标变更；联网后用 Outbox、幂等键和资源版本同步；
- `0006_local_first` 为五类资源增加版本控制，过期更新返回字段级可解释冲突，不静默覆盖；
- 退出、账户切换和会话失效清除密文、副本、Outbox、冲突、密钥和查询缓存；
- Web/iOS/Android export 通过，Android 16 Pixel_9 与 iOS 26.5 iPhone 17 Pro 已完成当前
  Debug 原生构建、安装和 JS bundle 运行。

### 阶段 12 已完成的 ADR-037

- “我的”新增生活灵感入口；用户逐次主动粘贴小红书公开链接，预览失败时可手动填写；
- 只保存 URL、来源、标题、短摘要、抓取日期、用户确认标签和 `inspiration_only`，支持两步删除；
- 后端只允许 HTTPS 白名单，逐跳做 DNS/重定向 SSRF 校验，无 Cookie、8 秒超时、256 KB 上限，
  Prompt Injection 或访问失败直接手动回退；
- `0007_life_inspirations`、API 与共享契约已建立；production 默认关闭自动预览；
- 没有账号绑定、登录态、Cookie、后台/批量抓取、通用浏览器、Agent Tool 或 RAG 摄取。

## 4. 主要目录及作用

| 目录/文件 | 作用 |
|---|---|
| `AGENTS.md` | 后续 Codex 的强制规则、当前阶段和边界 |
| `docs/README.md` | 文档索引与阶段状态总览 |
| `docs/JOURNEY_REFACTOR_PLAN.md` | 唯一可执行路线图和 Checklist |
| `docs/ARCHITECTURE_DECISIONS.md` | ADR；Accepted/Proposed/Superseded 状态事实源 |
| `docs/CURRENT_PROJECT_AUDIT.md` | 当前代码和迁移事实审计 |
| `docs/EXECUTION_LOG.md` | 已执行命令、结果、问题和边界证据 |
| `qiuzhaomianshi.md` | 每次项目更新同步维护的分岗位面试案例、日期、量化证据和陈述边界 |
| `apps/mobile/` | Expo SDK 57 / React Native 0.86 客户端、测试、E2E、原生生成目录 |
| `backend/` | FastAPI 模块化单体、Agent/RAG、数据模型、Alembic、白盒/黑盒测试 |
| `packages/contracts/` | OpenAPI 快照与跨端 TypeScript 契约 |
| `packages/design-tokens/` | 薄荷绿品牌色、间距、圆角和排版 token |
| `compose.yaml` | 本地 API、PostgreSQL、测试和黑盒测试编排 |
| `compose.staging.yaml` | 与开发库隔离的本机 staging 覆盖配置 |
| `compose.production.yaml` | 单服务器 PostgreSQL/API/Web/Caddy production 编排 |
| `.github/workflows/ci.yml` | backend、mobile、web-e2e 三个 CI job |
| `evals/datasets/` | 362 条版本化 Agent/RAG/图片契约评测样本 |
| `evals/reports/` | Mock 与真实 DeepSeek/Qwen 的版本化评测报告 |
| `assets/brand/` | 从旧项目保留的原版卡通人物和品牌资产 |
| `infra/` | API entrypoint、Web 镜像、staging、演示重置和构建变体验证 |
| `docs/demo/` | 架构、演示脚本、交付报告、简历与面试材料 |
| `docs/deployment/` | staging、构建发布、隐私安全和故障处理 |
| `reports/` | 被忽略的最新 JUnit、Coverage、Allure、E2E 和评测输出 |
| `artifacts/` | 被忽略的模拟器截图、发布演练和图片评测证据 |

## 5. 关键代码文件

| 文件 | 作用 |
|---|---|
| `apps/mobile/src/app/_layout.tsx` | 主题、Query、Auth、Sync Provider 和登录保护路由 |
| `apps/mobile/src/app/(tabs)/index.tsx` | 首页 Agent run/resume、候选确认与业务数据装配 |
| `apps/mobile/src/components/home-overview.tsx` | 阶段 12 暖白薄荷首页视觉、输入、指标和状态条 |
| `apps/mobile/src/providers/sync-provider.tsx` | 本地查询/写入、90 天同步、Outbox 合并、冲突与恢复 |
| `apps/mobile/src/lib/local-replica.ts` | 原生账户隔离 AES 副本、Outbox、冲突和退出清理；Web 仅内存 |
| `apps/mobile/src/lib/pending-storage.ts` | 旧离线新增队列，只用于迁移兼容并在退出时清理 |
| `apps/mobile/src/lib/api.ts` | `/api/v1` 客户端和刷新令牌逻辑 |
| `apps/mobile/src/app/inspirations.tsx` | 生活灵感主动分享、手动回退、确认、来源与删除流程 |
| `apps/mobile/app.config.js` | development/preview/production 标识和原生权限 |
| `backend/app/main.py` | FastAPI 应用、中间件、CORS 和路由装配 |
| `backend/app/core/settings.py` | PostgreSQL、供应商、预算、图片和环境安全校验 |
| `backend/app/api/v1/router.py` | `/api/v1` 稳定路由总入口 |
| `backend/app/services/agent.py` | Agent v1/v2/v3 run、确认、resume、trace 与持久化编排 |
| `backend/app/agent/tool_registry.py` | 受控工具定义、风险、确认要求和确定性替代工具 |
| `backend/app/agent/execution_graph.py` | 有界执行、Observation、Verifier、Replanner 和暂停逻辑 |
| `backend/app/agent/model_router.py` | LangChain/LiteLLM 结构化输出、供应商路由、重试、预算和降级 |
| `backend/app/knowledge/` | 内置知识、摄取、嵌入与检索 |
| `backend/alembic/versions/0006_local_first_versions.py` | 业务资源并发版本 schema 基线 |
| `backend/app/services/inspirations.py` | 白名单预览、SSRF/重定向/大小/超时/恶意元数据门禁与 CRUD |
| `backend/alembic/versions/0007_life_inspirations.py` | 当前数据库 head 的生活灵感 schema |

## 6. 已确认技术方案与重要决策

- **跨平台**：Expo Development Build + React Native；iOS Simulator 主演示，Android 验收，
  Web 补充。当前 Expo `~57.0.6`、React Native `0.86.0`。
- **后端**：FastAPI 模块化单体，不拆复杂微服务。
- **数据库**：PostgreSQL 18 + SQLAlchemy + Alembic；不迁移旧 SQLite 数据。
- **身份**：邮箱或用户名 + 密码，手机号后置；测试账号由服务端可控播种。
- **Agent**：LangChain/LangGraph + 嵌入式 LiteLLM Provider Router；一个 Orchestrator + 三个
  职责受限的 Specialist，共享同一有界执行闭环，不做 Agent 群聊。
- **状态/记忆**：用户画像和业务表是事实源，模型无关的最小结构化线程记忆存在 PostgreSQL；
  不依赖供应商会话记忆。
- **安全写入**：饮食、运动、体重候选必须用户确认，组合任务确认后显式 resume。
- **RAG**：项目受控知识库和引用；生活灵感不进入 RAG。Agent 无浏览器、通用网页或小红书工具。
- **模型切换**：DeepSeek/Qwen/GLM/Kimi/OpenAI-compatible 由服务端环境配置；Mock 是合法 Provider
  且为普通 CI 默认值；客户端不持有模型 Key。
- **图片**：ADR-030/031 仍 Proposed/No-Go；实验性候选不能表述为正式质量通过。
- **语音**：ADR-032 Accepted，当前版本不实现语音转文字。
- **阶段 12**：方案 C、ADR-036 和 ADR-037 均已确认并验收；ADR-037 只接受用户主动分享，
  不是账号绑定或 Web Research。
- **阶段 13**：ADR-039 Accepted；真实 LLM、有限 Multi-Agent、RAG v1/v2 Eval、Journey 7/30、
  Docker preflight 和 Demo 主链路已封板。

## 7. 本轮及近期修改过的代码

最近的实际代码变化集中在：

- 新增 `apps/mobile/src/components/home-overview.tsx`；
- 新增 `apps/mobile/src/lib/local-replica.ts` 与 Sync Provider 本地优先实现；
- 修改首页、Journey、我的、画像/目标和记录页以统一使用本地副本；
- 新增 Alembic `0006_local_first`、API 资源 `version`、`If-Match-Version` 和 409 冲突快照；
- 新增 Alembic `0007_life_inspirations`、生活灵感模型/Schema/API/受限预览服务与共享契约；
- 新增移动端生活灵感页面、Profile 入口及 6 条后端/4 条移动专项测试；
- 新增 `qiuzhaomianshi.md`，并在 `AGENTS.md` 固化每次更新必须同步面试材料；
- 新增后端同步冲突测试与移动副本/Outbox/冲突组件测试；
- `ScreenShell` 支持自定义 Hero；
- `theme-provider.tsx` 固定暖白薄荷浅色应用主题；
- 更新首页 Jest、布局契约、覆盖率采集和 Playwright E2E 断言；
- 阶段 11 新增/修改 Agent v3 checkpoint、resume、Observation、Replanner、迁移 `0005_agent_v3`、
  Requests 黑盒和真实 Provider 门禁；
- 阶段 13 新增 Specialist allowlist、可观察 Multi-Agent Trace、复合输入拆解、Journey 7/30
  汇总、RAG v2 hybrid rerank、60 题分层 Eval、Docker preflight 和离线重连 E2E；
- 新增 `docs/architecture/MULTI_AGENT_DATA_FLOW.md`、
  `docs/architecture/RAG_ARCHITECTURE_AND_EVAL.md` 与版本化 RAG Eval 报告；
- 阶段 2 的旧微信/Taro 文件删除仍是当前 Git 变化的一部分。

注意：`apps/mobile/app.config.js` 仍设置 `userInterfaceStyle: 'automatic'`，而 React Navigation/
Journey Theme 已固定浅色。应用主体保持浅色，但原生系统弹窗或边缘区域仍可能跟随系统主题；
后续若要求全链路固定浅色，需要单独修正并做双平台视觉验收。

## 8. 本次交接实际运行的命令与结果

| 命令/检查 | 结果 |
|---|---|
| `pwd`、`git status --short`、`ls -la` | 当前为 Journey 根目录；最终 115 项未提交变化，无目录切换或清理 |
| `git branch --show-current`、`git log -1`、`git remote -v` | `codex/journey-migration-baseline`；HEAD `2654c43`；迁移基线远端不变 |
| `docker compose ps` | 本机 API/db 已用临时宿主 PostgreSQL 端口 55432 恢复；API healthy |
| `GET /health/live`、`GET /health/ready` | 均正常；ready 的 database/rag=`ok`，明确显示 REAL DeepSeek |
| Alembic `downgrade 0006` → `upgrade 0007` + `check` | PASS；当前 `0007_life_inspirations (head)`，无待生成操作 |
| `docker compose --profile test run --rm --build test` | **100 passed**；覆盖率 **90.60%**；362 个既有样本/26 门禁与 RAG v1/v2 比较均 PASS |
| Mock / REAL Requests + Pytest + Allure 黑盒 | Mock **2/2**；真实 DeepSeek 复合 Multi-Agent **1/1**，28.02 s |
| RAG v2 真实 60 题评测 | 最终全部门禁 PASS；失败的第一轮报告也保留，不用 Mock 冒充真实质量 |
| `npm run mobile:typecheck` | PASS |
| `npm run mobile:lint` | PASS |
| `npm run mobile:test` | Jest **46/46 PASS** + 逻辑测试 **5/5 PASS** |
| `npm run test:logic --workspace @journey/mobile` | Node 逻辑测试 **5/5 PASS** |
| `npm run mobile:e2e:web` | 强制 Mock API 下核心 Web E2E **2/2 PASS** |
| Web/iOS/Android Expo export | Web 14 条静态路由、iOS/Android Hermes bundle 均成功 |
| `docker compose config --quiet` + production config | PASS；production 生活灵感自动预览为 `false` |
| Android/iOS Development Build | Pixel_9 与 iPhone 17 Pro 构建、安装并加载当前 JS bundle；无业务 fatal |
| 敏感信息检查 | `.env` 被忽略；交接文档不含真实 Key；未读取或输出 `.env` 内容 |

最新机器报告：`reports/backend/junit.xml`、`reports/backend/coverage.xml`、
`reports/backend/blackbox-junit.xml`、`reports/evals/latest.json`、
`apps/mobile/reports/junit.xml`、`apps/mobile/reports/e2e-junit.xml`。这些目录被 Git 忽略。

## 9. 遇到的问题与解决方法

| 问题 | 解决方法/当前结论 |
|---|---|
| 第一轮首页 A/B 过暗、偏灰、重画吉祥物质量差 | 两套方案明确否决；方案 C 使用暖白、明亮薄荷和原版角色 |
| 390 pt 新首页标题末字孤行 | 拆分稳定标题行并缩小角色占位 |
| 320 pt 标题省略、指标数字截断 | 再压缩 Hero，单位移动到指标标签行；320/390 复验通过 |
| 首页输入抽为新组件后布局测试仍读取旧文件 | 把断言改到真实 `home-overview.tsx`，未降低测试标准 |
| DeepSeek 首轮把“查询我的体重”误路由为写体重 | Router Prompt 升至 `1.0.1`，真实 28/28 文字门禁通过 |
| Qwen 图片 API 可调用但识别质量不达标 | 按预注册门禁 No-Go，不反复重跑密封集，不启用正式图片能力 |
| 黑盒测试早期误连主 API、存在真实 Provider 风险 | 改为独立 `blackbox-api` + `test-db`，强制 Mock/空 Key/零预算 |
| 本轮 E2E 启动时宿主 `5432` 已被占用 | 不停止现有 PostgreSQL，改用临时宿主端口 `55432`；容器内部连接与迁移不变 |
| zsh 中误用只读变量名 `status` | 改名为 `health_state` 后完成健康轮询；失败命令未改变数据或配置 |
| 生活灵感预览可能遇到登录墙、反爬或恶意元数据 | 不绕过访问控制；无 Cookie、强制上限并回退用户手动标题/摘要，内容不进入 Agent/RAG |
| Docker Hub 曾拉取 Web Nginx 基础镜像超时 | 保留静态 export 与本机运行证据；未伪报 Web 镜像复验成功 |
| 当前 Android Release 补充构建停在 Gradle `lintVitalRelease` | 中止重复等待；当前 Debug 构建、安装和 JS 运行已通过，既有阶段 10 Release 证据保留，但本轮不宣称新的 Release 通过 |
| npm 存在 Expo/Jest/ESLint 传递依赖告警 | 保持锁定兼容基线，禁止 `npm audit fix --force` |
| 真实复合黑盒最初被 15 秒客户端超时中断 | 把真实黑盒超时显式设为 75 秒；普通 Mock/CI 仍保持 15 秒快速失败 |
| 周总结工具在 12 秒预算下完成后仍被判超时 | 依据真实 24.5 秒证据把 Agent 默认超时调整为 30 秒，仍只允许一次有限重试 |
| 第一轮真实 RAG 拒答准确率仅 0.6833 | 零检索结果改为确定性 `insufficient_context` 且不调用模型；第二轮为 1.0，失败报告保留 |
| Web E2E 的 Plan/Trace 文本造成 strict locator 重复 | 使用精确 Plan 文本定位，不删除 Trace 展示，最终 2/2 通过 |

## 10. 尚未完成的任务与风险

1. **当前阶段尚未形成新 Git 基线**：历史迁移基线已在 `codex/journey-migration-baseline`
   提交；阶段 8/12/13 的当前 115 项变化仍未提交、未 push、未创建 PR。
2. **local-first 发布加固未完成**：第一批范围已经实现，但 1000 条长离线故障注入、5 人盲测、
   真实设备密钥取证和公网多设备同步仍未执行；Web 只提供进程内副本，刷新后不保证保留。
3. **小红书账号绑定/Web Research 未实现**：ADR-037 的主动分享收藏已完成，但当前 Agent 仍
   没有浏览器能力；不得使用账号密码、Cookie、自动登录、批量抓取或把生活灵感当健康证据。
4. **当前原生证据是 Debug Development Build**：iOS/Android 已重新构建、安装并加载当前
   JS；Android 的额外 Release 构建停在 Gradle `lintVitalRelease` 后被中止，因此本轮不新增
   Release 结论，也不影响既有阶段 10 Release 模拟器证据。
5. **图片真实质量 No-Go**：功能存在不等于质量通过；不能进入 Preview/Production。
6. **公网与商店发布未完成**：production Docker 配置已形成，但仍无服务器、域名、真实证书、
   外部备份恢复、Apple Developer Program、iOS Distribution、Android upload key 或商店材料。
7. **本机 `.env` 权限**：当前 `0644`，建议收紧到 `0600`；不得把任何 Key 写入客户端/仓库。
8. **主题发布复核**：代码主题已固定为浅色；正式商店包仍需在真实设备复核系统外观、加密密钥、
   锁屏恢复和卸载/重装行为。
9. **本机磁盘占用**：原生生成目录约 9.1 GB；只能在明确授权和可重建验证后清理。
10. **远端发布边界**：当前只有私有源码备份，不等于公网部署、商店发布或生产验收。
11. **未提交工作区**：阶段 8 production、ADR-036/037、ADR-039、Eval 与文档合计 115 项
    变化尚未形成新 Git 基线；不得在未审查时 reset/clean，也不得自动 push。

## 11. 下一步最合理的工作

阶段 13 已完成。下一步最合理的工作不是继续加功能，而是在用户单独授权后，对当前 115 项阶段
8/12/13 变更做最终差异、敏感信息、生成文件、迁移和测试证据复核，然后创建一个本地 Git 提交。
默认不 push、不创建 PR；若用户不授权提交，则保持工作区现状并停止。
