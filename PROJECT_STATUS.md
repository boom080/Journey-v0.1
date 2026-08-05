# Journey 项目交接状态

> 更新时间：2026-08-04
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

当前处于 **阶段 12：本地优先与 AI 原生体验，Status: In Progress**：

- 已完成：用户确认的“暖白薄荷 Journey”方案 C 首页视觉子项；
- 未完成：完整本地数据副本、编辑/删除 Outbox、同步冲突、退出清理；
- 未完成：小红书主动分享链接或受控 Web Research 的产品选择与实现；
- ADR-036、ADR-037 仍为 `Proposed`，不能宣称 Journey 已经 local-first 或已绑定小红书。

## 2. 当前 Git 与目录安全状态

| 项目 | 当前事实 |
|---|---|
| 当前分支 | `main` |
| 远程仓库 | `origin` → `https://github.com/boom080/fitness.git` |
| 当前 HEAD | `06b52f024547e76e1cd216e27f3ac41717dd3671`，旧微信版提交“FastApi改为微信云开发” |
| 工作区状态 | **171 项未提交变化**：16 Modified、87 Deleted、68 Untracked；其中 2 项是本轮新增的根目录交接文档 |
| 主要原因 | 微信/Taro 旧端退役，Expo/FastAPI/PostgreSQL/Agent 新架构尚未建立 Git 基线提交 |
| 远程状态 | 本轮未 commit、未 push、未创建 PR、未修改远端 |

这是当前最高优先级的工程风险：大量已验证代码只存在于未提交工作区。后续严禁执行
`git reset --hard`、`git clean`、强制 checkout 或任何清理命令，也不要把旧微信文件的删除误判为
可随意恢复/清理。建立本地基线提交必须先获得用户明确授权。

敏感与生成文件状态：

- 根目录 `.env` 已被 `.gitignore` 忽略，本次没有读取或打印内容；当前权限为 `0644`，建议后续
  单独执行 `chmod 600 .env`；
- `reports/`、`artifacts/`、Expo `dist*`、原生 `ios/`/`android/`、覆盖率和缓存均被忽略；
- `apps/mobile/ios/` 约 5.6 GB，`apps/mobile/android/` 约 3.5 GB，属于本机生成的原生工程/
  构建缓存。不要为省空间擅自删除；如需清理应先单独确认并保留重建路径。

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
- 离线新增记录进入按用户隔离、AES 加密、24 小时/50 条上限的待同步队列；
- 当前离线只支持部分记录和内置常识，不支持完整画像/历史本地读写。

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

### 阶段 10—11：Agent v2/v3

- 单 Agent 的 Planner → Policy Guard → Executor → Observation → Verifier → Replanner；
- 工具白名单、最多 6 步/2 次重规划、写入前人工确认；
- 组合任务在候选确认后显式 Resume，并重新读取最新业务事实；
- PostgreSQL 保存最小结构化线程记忆、脱敏 checkpoint、Observation 和执行轨迹；
- 可恢复故障只能选择白名单替代工具，不能无限循环或暗中切换供应商；
- 真实 DeepSeek v3 固定门禁通过：4 个 checkpoint 计划、2 个恢复选择、10 次调用，费用
  `$0.00171864`。

### 阶段 12 已完成的视觉子项

- 固定暖白 + 明亮薄荷浅色品牌主题，不再跟随已否决的暗灰方向；
- 首页复用原版 `journey-leaf-home.png`，统一输入位于首屏；
- 今日指标改为开放式分栏，Agent 状态改为轻量状态条；
- 在线/离线文案保持真实能力边界，未把部分离线包装为 local-first；
- 320 × 844、390 × 844 Web 手机视口人工核对通过；
- 新首页已完成 Web/iOS/Android JS export，但**尚未重新形成本轮 iOS/Android 原生安装截图**。

## 4. 主要目录及作用

| 目录/文件 | 作用 |
|---|---|
| `AGENTS.md` | 后续 Codex 的强制规则、当前阶段和边界 |
| `docs/README.md` | 文档索引与阶段状态总览 |
| `docs/JOURNEY_REFACTOR_PLAN.md` | 唯一可执行路线图和 Checklist |
| `docs/ARCHITECTURE_DECISIONS.md` | ADR；Accepted/Proposed/Superseded 状态事实源 |
| `docs/CURRENT_PROJECT_AUDIT.md` | 当前代码和迁移事实审计 |
| `docs/EXECUTION_LOG.md` | 已执行命令、结果、问题和边界证据 |
| `apps/mobile/` | Expo SDK 57 / React Native 0.86 客户端、测试、E2E、原生生成目录 |
| `backend/` | FastAPI 模块化单体、Agent/RAG、数据模型、Alembic、白盒/黑盒测试 |
| `packages/contracts/` | OpenAPI 快照与跨端 TypeScript 契约 |
| `packages/design-tokens/` | 薄荷绿品牌色、间距、圆角和排版 token |
| `compose.yaml` | 本地 API、PostgreSQL、测试和黑盒测试编排 |
| `compose.staging.yaml` | 与开发库隔离的本机 staging 覆盖配置 |
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
| `apps/mobile/src/providers/sync-provider.tsx` | 在线提交、网络失败排队、恢复联网重试和查询失效 |
| `apps/mobile/src/lib/pending-storage.ts` | 原生 AES 加密待同步队列与用户清理；Web 仅内存队列 |
| `apps/mobile/src/lib/api.ts` | `/api/v1` 客户端和刷新令牌逻辑 |
| `apps/mobile/app.config.js` | development/preview/production 标识和原生权限 |
| `backend/app/main.py` | FastAPI 应用、中间件、CORS 和路由装配 |
| `backend/app/core/settings.py` | PostgreSQL、供应商、预算、图片和环境安全校验 |
| `backend/app/api/v1/router.py` | `/api/v1` 稳定路由总入口 |
| `backend/app/services/agent.py` | Agent v1/v2/v3 run、确认、resume、trace 与持久化编排 |
| `backend/app/agent/tool_registry.py` | 受控工具定义、风险、确认要求和确定性替代工具 |
| `backend/app/agent/execution_graph.py` | 有界执行、Observation、Verifier、Replanner 和暂停逻辑 |
| `backend/app/agent/model_router.py` | LangChain/LiteLLM 结构化输出、供应商路由、重试、预算和降级 |
| `backend/app/knowledge/` | 内置知识、摄取、嵌入与检索 |
| `backend/alembic/versions/0005_agent_v3.py` | 当前数据库 head 的 checkpoint/Observation schema |

## 6. 已确认技术方案与重要决策

- **跨平台**：Expo Development Build + React Native；iOS Simulator 主演示，Android 验收，
  Web 补充。当前 Expo `~57.0.6`、React Native `0.86.0`。
- **后端**：FastAPI 模块化单体，不拆复杂微服务。
- **数据库**：PostgreSQL 18 + SQLAlchemy + Alembic；不迁移旧 SQLite 数据。
- **身份**：邮箱或用户名 + 密码，手机号后置；测试账号由服务端可控播种。
- **Agent**：LangChain/LangGraph + 嵌入式 LiteLLM Provider Router；单 Agent、有界计划和工具
  闭环，不为展示强造多 Agent。
- **状态/记忆**：用户画像和业务表是事实源，模型无关的最小结构化线程记忆存在 PostgreSQL；
  不依赖供应商会话记忆。
- **安全写入**：饮食、运动、体重候选必须用户确认，组合任务确认后显式 resume。
- **RAG**：项目受控知识库和引用；无浏览器、通用网页或小红书工具。
- **模型切换**：DeepSeek/Qwen/GLM/Kimi/OpenAI-compatible 由服务端环境配置；Mock 是合法 Provider
  且为普通 CI 默认值；客户端不持有模型 Key。
- **图片**：ADR-030/031 仍 Proposed/No-Go；实验性候选不能表述为正式质量通过。
- **语音**：ADR-032 Accepted，当前版本不实现语音转文字。
- **阶段 12**：方案 C 视觉子决策已确认；ADR-036 的完整 local-first 和 ADR-037 的生活内容
  接入仍 Proposed。

## 7. 本轮及近期修改过的代码

最近的实际代码变化集中在：

- 新增 `apps/mobile/src/components/home-overview.tsx`；
- 修改首页装配 `apps/mobile/src/app/(tabs)/index.tsx`；
- `ScreenShell` 支持自定义 Hero；
- `theme-provider.tsx` 固定暖白薄荷浅色应用主题；
- 更新首页 Jest、布局契约、覆盖率采集和 Playwright E2E 断言；
- 阶段 11 新增/修改 Agent v3 checkpoint、resume、Observation、Replanner、迁移 `0005_agent_v3`、
  Requests 黑盒和真实 Provider 门禁；
- 阶段 2 的旧微信/Taro 文件删除仍是当前 Git 变化的一部分。

注意：`apps/mobile/app.config.js` 仍设置 `userInterfaceStyle: 'automatic'`，而 React Navigation/
Journey Theme 已固定浅色。应用主体保持浅色，但原生系统弹窗或边缘区域仍可能跟随系统主题；
后续若要求全链路固定浅色，需要单独修正并做双平台视觉验收。

## 8. 本次交接实际运行的命令与结果

| 命令/检查 | 结果 |
|---|---|
| `pwd`、`git status --short`、`ls -la` | 当前为 Journey 工作区；初始 169 项，本轮新增 2 份交接文档后最终为 171 项；无目录切换风险 |
| `git branch --show-current`、`git log -1`、`git remote -v` | `main`；HEAD 为旧微信版提交；origin 正确 |
| `docker compose ps` | `api`、`db`、`test-db` 均运行；api/db healthy |
| `GET /health/live`、`GET /health/ready` | 均返回 `status=ok`，ready 的 database=`ok` |
| `docker compose exec -T api alembic current` | `0005_agent_v3 (head)` |
| `docker compose --profile test run --rm --build test` | **85 passed**；覆盖率 **90.49%**；362 样本、26 门禁全部 PASS；Mock、成本 0 |
| `docker compose --profile blackbox run --rm --build blackbox` | Requests + Pytest + Allure 黑盒 **1 passed**，0.24 s |
| `npm run mobile:typecheck` | PASS |
| `npm run mobile:lint` | PASS |
| `npm run mobile:test:ci` | Jest **33/33 PASS**；覆盖率 75.56/65.16/72.09/77.77 |
| `npm run test:logic --workspace @journey/mobile` | Node 逻辑测试 **5/5 PASS** |
| 最近一次 `npm run mobile:e2e:web` | Mock API 下核心 Web E2E **2/2 PASS** |
| 最近一次 Web/iOS/Android Expo export | Web 13 条静态路由、iOS/Android Hermes bundle 均成功 |
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
| Docker Hub 曾拉取 Web Nginx 基础镜像超时 | 保留静态 export 与本机运行证据；未伪报 Web 镜像复验成功 |
| npm 存在 Expo/Jest/ESLint 传递依赖告警 | 保持锁定兼容基线，禁止 `npm audit fix --force` |

## 10. 尚未完成的任务与风险

1. **Git 基线已建立**：迁移成果已在 `codex/journey-migration-baseline` 形成单次提交，并按
   用户授权推送到 GitHub 私有仓库 `boom080/journey_v1`；未创建 PR。
2. **完整 local-first 未实现**：画像/目标/历史仍主要依赖 API；离线编辑/删除、完整本地副本、
   版本冲突和退出彻底清理未完成。
3. **小红书/Web Research 未实现**：当前 Agent 没有浏览器能力；不得使用账号密码、Cookie、
   自动登录或批量抓取。
4. **新首页没有新的原生安装证据**：三端 JS export 通过，但阶段 12 UI 之后没有重新生成
   iOS/Android Release 安装截图。
5. **图片真实质量 No-Go**：功能存在不等于质量通过；不能进入 Preview/Production。
6. **公网与商店发布未完成**：无服务器、域名、HTTPS、Apple Developer Program、iOS
   Distribution、Android upload key 或商店材料提交。
7. **本机 `.env` 权限**：当前 `0644`，建议收紧到 `0600`；不得把任何 Key 写入客户端/仓库。
8. **主题配置细节**：`app.config.js` 的 `userInterfaceStyle` 仍为 automatic，与固定浅色产品决策
   不完全一致。
9. **本机磁盘占用**：原生生成目录约 9.1 GB；只能在明确授权和可重建验证后清理。
10. **远端发布边界**：当前只有私有源码备份，不等于公网部署、商店发布或生产验收。

## 11. 下一步最合理的工作

迁移 Git 基线已完成。下一项产品工作仍需用户单独授权：把 ADR-036 的完整本地数据范围拆成
单一阶段，先确认本地副本范围、账户隔离、退出清理、版本冲突和 migration/测试方案。
小红书/Web Research 应晚于本地数据可靠性，且不得与该阶段同时启动。
