# Journey

Journey 正在从旧版微信小程序升级为 Agent 增强的跨平台健康管理应用。

当前进度：阶段 1—8、10、11 已完成，阶段 9 获授权的食物图片单项已按真实质量门禁
**Closed / No-Go**；阶段 12 为 **In Progress**，已完成用户确认的“暖白薄荷 Journey”首页
视觉子项，完整本地数据副本与生活内容接入仍未实现。统一身份与核心业务 API、Expo 三端页面、受控 RAG、确认后写入、
单 Agent 的 Planner → Policy Guard → Executor → Verifier 闭环，以及全栈自动化门禁均已
落地。2026-08-04 当前复验结果为：85 条后端/评测测试、90.49% 后端覆盖率、362 条版本化
Agent/RAG/图片契约样本、26 项量化门禁、33 条移动组件测试、5 条逻辑测试和 2 条核心 Web
E2E；iOS 与 Android Release 均已在模拟器真实安装运行，Web production export 生成 13 条
静态路由。

仓库和普通 CI 默认 Mock、空模型 Key、外部调用与成本均为 0。LangChain/LangGraph + 嵌入式
LiteLLM Router 支持 DeepSeek，并为 Qwen、GLM、Kimi 建立 Provider Profile。Agent v3
使用服务端类型化工具注册表、结构化计划、人工确认 checkpoint、最多 6 步/2 次重规划和
PostgreSQL 最小结构化线程记忆，不依赖某个模型厂商的会话状态。组合任务在用户确认后显式
恢复，可恢复故障通过 Observation/Verifier 选择白名单替代工具。2026-08-01
新增真实模型发布门禁：DeepSeek `deepseek-v4-flash` 首轮发现一条画像查询误路由，升级
Router Prompt 后 28/28 文字量化验收通过；Qwen
`qwen3.7-flash` 真实 API 冒烟通过，但独立图片质量门禁仍失败。因此联网本机演示可使用真实
文字模型和实验性图片候选，整体“文字 + 图片”尚不能表述为正式发布验收通过。本机工程演示
已验收，production id 为
`com.boom080.journey`；公网服务器、Apple 商店签名与 Android Play 签名均未执行，不能把
当前状态表述为已生产发布。

当前新增功能范围暂时收敛为文字与食物图片，不启动语音、视频等能力。食物图片方向完成了
授权数据、独立密封集和真实 Qwen 评测，但自动估重与“识别候选”两条
路线都没有达到预注册门槛：ADR-031 的总体 Top-3 为 67.27%、中国家庭餐为 60%、Schema
为 98.33%。Preview/Production/staging 不启用真实图片识别，Development 仅可实验性生成
候选，并继续使用手动记录与用户确认回退。
这一 No-Go 是项目的量化产品决策案例，不是已上线功能。用户也已明确当前不做语音转文字；
其余阶段 9 能力未启动。

工程边界：

- `apps/mobile/`：Expo Development Build，首页、Journey、我的及 Agent 候选确认流程。
- `backend/`：FastAPI 模块化单体、核心业务 API、Agent/RAG、Provider Router、Alembic、
  HTTPX/TestClient 白盒测试、Requests 网络黑盒与 Allure/JUnit/Coverage 报告。
- `packages/`：OpenAPI/TypeScript 跨端契约和 design token。
- `compose.yaml`：仅包含 FastAPI API 与 PostgreSQL。
- `evals/`：362 条版本化样本、真实图片调试集、无参照/尺度/识别密封集、量化门禁与报告。
- `assets/brand/`：从旧项目保留的卡通人物和品牌资产。

开发说明见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)，API 见
[docs/API.md](docs/API.md)，阶段 8 运行手册见
[docs/deployment/STAGING.md](docs/deployment/STAGING.md)，演示脚本见
[docs/demo/INTERVIEW_DEMO.md](docs/demo/INTERVIEW_DEMO.md)，开发、测试开发、产品和售前
岗位的讲述材料见
[docs/demo/RESUME_AND_INTERVIEW.md](docs/demo/RESUME_AND_INTERVIEW.md)。开始后续工作前请阅读
[AGENTS.md](AGENTS.md) 和 [docs/README.md](docs/README.md)；唯一迁移计划是
[docs/JOURNEY_REFACTOR_PLAN.md](docs/JOURNEY_REFACTOR_PLAN.md)。

新对话交接请先阅读 [PROJECT_STATUS.md](PROJECT_STATUS.md) 和
[NEXT_TASK.md](NEXT_TASK.md)。两份文件是当前现场快照与最近单项任务，不替代上述路线图和 ADR。
