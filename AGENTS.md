# Journey Codex 工作规则

本文件是后续 Codex 任务的第一入口。开始任何工作前，必须先阅读本文件和
[`docs/README.md`](docs/README.md)。

## 当前目标

Journey 将从旧版微信小程序升级为 Agent 增强的跨平台健康管理应用：

- 三个一级入口：首页、Journey、我的。
- 首页直接提供统一自然语言输入，自动识别饮食、运动、查询、建议等意图。
- Expo Development Build + iOS Simulator 是主要开发和演示路径。
- Android Emulator 用于跨平台验收，Web 是补充发布形态。
- FastAPI、PostgreSQL、Agent、RAG 与测试能力由各客户端共享。
- 产品属于健身、营养和生活方式管理，不提供医疗诊断或治疗建议。

## 单一事实源

- 唯一迁移计划：[`docs/JOURNEY_REFACTOR_PLAN.md`](docs/JOURNEY_REFACTOR_PLAN.md)
- 已确认架构决策：[`docs/ARCHITECTURE_DECISIONS.md`](docs/ARCHITECTURE_DECISIONS.md)
- 旧项目事实基线：[`docs/CURRENT_PROJECT_AUDIT.md`](docs/CURRENT_PROJECT_AUDIT.md)
- Agent 技术调研：[`docs/AGENT_TECH_RESEARCH.md`](docs/AGENT_TECH_RESEARCH.md)
- 实际执行证据：[`docs/EXECUTION_LOG.md`](docs/EXECUTION_LOG.md)
- 秋招面试案例：[`qiuzhaomianshi.md`](qiuzhaomianshi.md)

不得创建第二份平行路线图。新决策应写入 ADR；被替代的决策标记为
`Superseded`，不得静默覆盖。

## 求职面试材料维护

每次项目更新（代码、配置、数据库、测试、架构决策或交付状态发生变化）都必须同步填写
[`qiuzhaomianshi.md`](qiuzhaomianshi.md)：

- 使用实际日期，并归入 Agent 开发、测试开发、AI 产品、售前/解决方案、客户端/全栈等岗位；
- 采用“当前项目中遇到的情况 → 通过的解决方式 → 量化结果与证据 → 面试陈述边界”格式；
- 只记录仓库中可验证的事实，不把 Mock 结果当真实模型质量，不把可部署当已上线；
- 如果本次没有形成新的面试问题，也必须在该文件“更新记录”中写明本次变更、验证结果和
  “无新增问题”，以证明已完成同步检查；
- 面试材料不替代 `docs/EXECUTION_LOG.md`，两者的日期、指标和完成状态必须一致。

## 当前阶段

- 阶段 13 已于 2026-08-10 Completed，ADR-039 Accepted：在既有 Agent v3 状态机上明确为一个
  Orchestrator + Record/Health Knowledge/Journey Summary 三个职责受限 Specialist；不做 Agent
  群聊、独立微服务或无限循环，写记录仍必须经过 Confirmation Gate。精确复合输入的真实
  DeepSeek 网络黑盒 1/1（28.02 秒），Mock 黑盒 2/2，Web E2E 2/2；60 题 RAG v2
  Recall@3/5=1.0、MRR=0.9625，真实 Generation Groundedness/Relevance=0.9625、Citation
  Correctness=0.9083、Abstention=1.0。阶段 13 后默认只做 bug fix、E2E、Eval、Docker 与文档，
  不自动启动新产品能力。
- 阶段 8 于 2026-08-05 增加服务器 Docker production 复验：独立 Compose 已编排 PostgreSQL、
  FastAPI、Expo Web 与 Caddy HTTPS 网关，数据库/API 不发布宿主端口，production 默认 Mock、
  禁止测试账号和真实图片识别。Compose、API/PostgreSQL、Web export 与 Caddyfile 已分别验证；
  本机 Docker Hub token 网络超时仍阻塞 Node/Nginx/Caddy 镜像拉取，因此尚未形成四容器整栈或
  真实公网证书证据。不得把“可部署配置”表述成“已上线”。
- 阶段 12 已于 2026-08-10 Completed。ADR-036 于 2026-08-05 转 Accepted：原生端按账户使用
  SecureStore 密钥 + AES-256-GCM 密文保存画像、目标、最近 90 天记录/Journey，支持离线
  create/update/delete Outbox、服务端 version/`If-Match-Version`、字段级冲突选择和退出彻底
  清理；Web 只保留进程内副本。ADR-037 于 2026-08-10 转 Accepted：仅允许用户主动分享
  小红书公开链接，受限预览标题/摘要并显式确认，固定为 `inspiration_only`，不进入 Agent、
  RAG 或健康事实层；production 默认关闭自动预览。未实现账号绑定、Cookie、后台/批量抓取、
  通用浏览器或 Agent Web Research，后续任何扩展必须新建 Proposed ADR。
- 阶段 11 Agent v3 已于 2026-08-04 完成，ADR-035 Accepted：人工确认 checkpoint/显式恢复、
  Observation 驱动的最多 2 次重规划、两条确定性替代工具、移动端恢复状态，以及 Requests +
  Pytest + Allure 网络黑盒均已验收。ADR-039 只替代了当时“不扩展 Multi-Agent”的阶段边界，
  并严格限制为三个有界 Specialist；长期偏好、语音、视频或新图片能力仍不得自动扩展。
- 当前没有自动推进的新阶段。阶段 10 Agent v2 与测试报告增强已于 2026-08-03 完成，
  ADR-034 已转 Accepted。系统采用单 Agent 的 Planner → Policy Guard → Executor → Verifier
  闭环、类型化工具白名单、结构化计划、最多 6 步/1 次重规划、人工确认和 PostgreSQL 最小
  结构化线程记忆；关闭 `AGENT_V2_ENABLED` 可回退既有 v1 固定工作流。
- 2026-08-13 完成阶段 13 后封板维护：修复真实 Agent 客户端 10 秒超时、已完成 Run 的过期
  Resume 状态与幂等冲突误导；真实 DeepSeek v4 Pro 周总结 smoke 20.4 秒返回 HTTP 200、3 条
  引用、无降级。Home 新增 Mifflin–St Jeor 静息能量估算，旧 `net_kcal` 仅标为“记录差值”，
  明确不等于 TDEE；ADR-040 Accepted。
- 当前全量证据为 100 条后端/评测测试与 90.69% 后端覆盖率、362 条既有版本化样本、26 项
  门禁与 60 条 RAG Eval、48 条移动组件/契约测试 + 5 条逻辑测试、2 条核心 Web E2E、Web
  14 路由及 iOS/Android JS 构建，以及
  阶段 12 的 iOS/Android Debug 模拟器安装运行。Requests 网络黑盒 1/1 通过；Allure、
  JUnit、Coverage 与 Agent JSON 报告并存。真实 DeepSeek Agent v3 的 4 个 checkpoint 计划、
  2 个恢复选择、Provider/Schema 门禁均为 100%，10 次调用费用 `$0.00171864`。当前状态为
  “可用于本机求职演示”，不是公网生产或商店发布完成。
- 最近完成：阶段 9 食物图片单项的 ADR-031 唯一一次识别质量评测（2026-07-31）；质量
  门禁失败，执行范围已停止，正式产品不启用真实图片识别。
- 当前状态：阶段 9 仅食物图片单项；Mock/工程基线、供应商政策复核、100 张授权评测集与
  Qwen `qwen3.7-flash` 三轮真实评测已完成。v1.3 又完成可选尺度参照、30 张零重叠密封
  泛化 holdout 和 30 组内部厘米尺配对唯一一次评测；有尺份量误差 47.82%、相对改善
  2.17%，Schema/参照判断 53/60，真实质量门禁未通过，ADR-030 保持 Proposed
  。厘米尺路线已 No-Go，图片仅保留为 Development 实验性
  辅助候选。用户已接受 ADR-031 的“识别候选 + 用户确认份量”方向；60 张全新
  `journey-food-image-recognition-holdout-v2` 已完成逐文件许可、隐私/视觉 QA、三重
  零重叠校验，并已对 Qwen `qwen3.7-flash-2026-07-15` 运行唯一一次 60 调用评测：
  总体 Top-3 37/55（67.27%）、中式 12/20（60%）、Schema 59/60，门禁失败；ADR-031
  保持 Proposed，不修改正式 App/API。再次启动必须使用新的 Proposed ADR、全新密封集和
  预先修正的语义评分规则，不得重跑或据此调整现有 holdout。
- 用户于 2026-07-31 明确决定当前 Journey 不做语音转文字；该能力与 Realtime Agent
  Spike 记为 Deferred / 当前范围外，后续不得作为默认下一步。视频、手机号、
  HealthKit/Health Connect 和通知仍需逐项单独授权。
- 语音、视频、微信登录、第三方 OAuth、手机/邮箱验证码、找回密码、HealthKit/Health Connect、
  Push、自动小红书、通用浏览器、自由网页搜索和复杂社交统一归为 Post-Demo / Future；已有
  兼容字段不得仅为封板而破坏性删除。
- 当前边界：本机演示是已接受的阶段 8 验收口径。未经单独确认不得租用或创建公网资源、
  执行商店签名、上传真实个人照片或启用未经评审的视觉模型。
- 已知交付限制：Android 只使用 debug certificate，用户没有 Apple Developer Program；
  Web 容器基础镜像拉取仍受 Docker Hub 网络超时影响；npm 当前存在 Expo/Jest/ESLint
  工具链传递依赖告警，禁止用 `npm audit fix --force` 破坏当前兼容基线。后续动作必须由
  用户明确选择，例如本地 Git 提交、服务器部署或上游依赖升级，不得自动开始新功能。
- 当前下一步不是新产品功能：阶段 8/12 的大量工作区变更尚未提交。只有用户单独授权后才能
  做最终敏感信息/差异复核并创建本地提交；不得自动 push 或创建 PR。

## 强制执行规则

1. 每次只执行一个阶段，完成验收后停止并汇报。
2. 操作前执行并展示 `pwd`、`git status`、`ls -la`；只能在当前工作目录内操作。
3. 不使用写死的项目绝对路径，不搜索或修改其他项目。
4. 不执行 `rm -rf`、强制重置、清理未提交代码或其他破坏性命令。
5. 不覆盖用户已有改动；先核对 Git 状态和差异。
6. 不提交、push、创建 PR 或修改远程仓库，除非用户单独明确授权。
7. 微信/Taro 客户端已按阶段 2 清单退役；不得无计划恢复旧端或继续增加微信功能。
8. 不迁移旧 SQLite 数据；PostgreSQL/Alembic 阶段 4 schema 已建立，后续变更必须新增
   migration 并保持 upgrade/downgrade 验收。
9. 不在客户端存储模型密钥，不在仓库或测试中使用真实密钥。
10. 未决定事项使用 `Status: Proposed`，不得将推测写成事实。

## 完成任务的证据要求

每个 Checklist 项只有满足以下条件才能勾选：

- 修改内容与阶段范围一致。
- 运行了计划中规定的验证命令或测试。
- 结果和已知问题写入 `docs/EXECUTION_LOG.md`。
- 必要时更新审计、ADR 和文档索引。
- 同步更新 `qiuzhaomianshi.md` 的对应岗位案例与更新记录。
- 明确给出下一阶段的启动条件，但不自动开始下一阶段。
