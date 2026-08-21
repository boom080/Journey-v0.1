# Journey

Journey 是由旧版微信小程序迁移而来的跨平台 AI 健康记录 App。当前目标是一个稳定、可解释、
可量化评测的秋招 Demo，不再无限增加产品功能。三个一级入口固定为：首页、Journey、我的。

## Implemented

- Expo SDK 57 的 iOS、Android、Web 客户端；邮箱/用户名 + 密码、Token/Refresh Token、
  SecureStore 与按账户 AES-256-GCM 本地副本；
- FastAPI 模块化单体、PostgreSQL 18、Alembic `0007`、画像/目标/饮食/运动/体重/Home/Journey
  稳定 `/api/v1` 契约；
- Home 由服务端统一给出“摄入－已记录运动”的记录差值，以及基于完整画像的 Mifflin–St Jeor
  静息能量消耗估算；资料不足时明确不估算，不把该值冒充完整 TDEE；
- Orchestrator + Record/Health Knowledge/Journey Summary 三个有界 Specialist Agent；
  Planner、Policy、工具白名单、Confirmation Gate、Observation、Verifier 和最多 2 次重规划；
- 受控 RAG、引用、`insufficient_context`、60 题固定 Eval、rag-v1/v2 比较；
- 原生端离线 CRUD Outbox、自动恢复同步、版本冲突选择与退出清理；
- Docker Compose 管理 API/PostgreSQL/RAG/Agent 依赖，移动端 Metro/Simulator 按原生开发机制
  运行在宿主机。

## Demo Ready

- 主场景：`今天中午吃了一份牛肉面，晚上跑了5公里，我这周减脂情况怎么样？`；Orchestrator
  拆分任务，生成两个记录候选，用户逐条确认后写库，再输出 7 天总结与引用；
- 真实 DeepSeek Requests 黑盒 1/1 通过，28.02 秒；启动和 `/health/ready` 明确显示 REAL/MOCK、
  Provider 与 Model；
- Docker 全量 100 条后端/评测测试、覆盖率 90.69%；48 条移动 Jest + 5 条逻辑测试；Mock
  Requests 黑盒 2/2；Web Playwright 2/2；
- 真实 DeepSeek 周总结客户端允许 120 秒工作流窗口；2026-08-13 实际 v4 Pro smoke 在 20.4 秒内
  返回 HTTP 200、3 条引用、无降级；Run 完成后客户端会清理过期“继续执行”状态；
- 60 题 RAG v2：Recall@3/5 1.0、MRR 0.9625；真实 Generation Groundedness 0.9625、
  Relevance 0.9625、Citation Correctness 0.9083、Abstention Accuracy 1.0；
- Web/iOS/Android bundle 通过；iPhone 17 Pro 与 Pixel 9 Debug 构建、安装和当前 JS 页面运行；
- `./infra/demo/demo_up.sh` 完成端口 preflight、构建、migration、health 和 REAL Provider 检查。

## Experimental

- 食物图片链路已经具备“模型 → 候选 → 用户校正 → 确认 → 保存”，但 Qwen 独立密封质量门禁
  未通过：Top-3 67.27%、中国家庭餐 60%、Schema 98.33%。只能在 Development 作为实验性
  候选，Preview/Production 默认关闭；不能宣称照片可以准确称重；
- 用户主动保存的小红书公开链接只作 `inspiration_only` 生活灵感，不进入 Agent/RAG/健康事实；
  production 自动预览默认关闭；
- 单服务器 production Compose 已有可部署配置，但没有公网域名、正式证书或生产 SLA 证据。

## Post-Demo / Future

语音输入/语音转文字、视频动作识别、微信登录、Apple/Google/第三方 OAuth、手机验证码、手机号
绑定、邮箱验证码/验证、忘记密码/邮件找回、HealthKit、Health Connect、Push、自动抓取小红书、
通用浏览器 Agent、自由网页搜索 Agent 和复杂社交功能均已暂停，不是近期计划。已有兼容字段不会
仅为封板而破坏性删除。

production id 为 `com.boom080.journey`。当前没有 Apple Developer Program、Android Play
upload key、公网上线或商店发布证据，不能把“本机 Demo Ready”描述成“生产发布完成”。

工程边界：

- `apps/mobile/`：Expo Development Build，首页、Journey、我的及 Agent 候选确认流程。
- `backend/`：FastAPI 模块化单体、核心业务 API、Agent/RAG、Provider Router、Alembic、
  HTTPX/TestClient 白盒测试、Requests 网络黑盒与 Allure/JUnit/Coverage 报告。
- `packages/`：OpenAPI/TypeScript 跨端契约和 design token。
- `compose.yaml`：本机 FastAPI API、PostgreSQL 与隔离测试服务。
- `compose.production.yaml`：单服务器 PostgreSQL、FastAPI、Expo Web 与 Caddy HTTPS 网关；
  当前配置/API/Web/Caddy 已分别验证，四容器本机整栈仍受 Docker Hub 网络超时阻塞。
- `evals/`：362 条既有 Agent/契约样本、60 条 RAG Eval、真实图片密封集、量化门禁与报告。
- `assets/brand/`：从旧项目保留的卡通人物和品牌资产。
- 生活灵感：用户主动提交白名单公开链接，受限预览/手动回退并显式确认；不绑定小红书账号，
  不使用 Cookie，不进入 Agent/RAG/健康事实层。

开发说明见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)，API 见
[docs/API.md](docs/API.md)，Multi-Agent 与 RAG 说明见
[docs/architecture/MULTI_AGENT_DATA_FLOW.md](docs/architecture/MULTI_AGENT_DATA_FLOW.md) 和
[docs/architecture/RAG_ARCHITECTURE_AND_EVAL.md](docs/architecture/RAG_ARCHITECTURE_AND_EVAL.md)，
阶段 8 运行手册见
[docs/deployment/STAGING.md](docs/deployment/STAGING.md)；服务器 Docker 上线路径见
[docs/deployment/SERVER_DOCKER.md](docs/deployment/SERVER_DOCKER.md)；演示脚本见
[docs/demo/INTERVIEW_DEMO.md](docs/demo/INTERVIEW_DEMO.md)，开发、测试开发、产品和售前
岗位的讲述材料见
[docs/demo/RESUME_AND_INTERVIEW.md](docs/demo/RESUME_AND_INTERVIEW.md)，按岗位分类、每次更新
同步维护的面试案例见 [qiuzhaomianshi.md](qiuzhaomianshi.md)；需要在另一个项目中按具体 JD
生成简历时，使用带证据路径、状态标签和诚实边界的
[秋招跨岗位项目素材知识库](docs/demo/JOURNEY_CAREER_MATERIAL_KNOWLEDGE_BASE.md)。开始后续工作前请阅读
[AGENTS.md](AGENTS.md) 和 [docs/README.md](docs/README.md)；唯一迁移计划是
[docs/JOURNEY_REFACTOR_PLAN.md](docs/JOURNEY_REFACTOR_PLAN.md)。

新对话交接请先阅读 [PROJECT_STATUS.md](PROJECT_STATUS.md) 和
[NEXT_TASK.md](NEXT_TASK.md)。两份文件是当前现场快照与最近单项任务，不替代上述路线图和 ADR。
