# Journey 文档索引

> 更新日期：2026-08-13
> 当前执行：阶段 13 秋招 Demo 封板 Completed；ADR-039 Accepted，当前没有自动启动的新阶段
> 最近完成：移动端固定暖白＋明亮薄荷浅色主题，首页复用原版叶子角色并落地首屏统一输入、
> 开放式今日指标和轻量 Agent 状态；320/390 pt 视觉核对通过
> 当前状态：Journey 是 Orchestrator + Record/Knowledge/Summary 三个有界 Specialist 的
> Multi-Agent 闭环；复用既有 Planner、Policy、Executor、Observation、Verifier、确认恢复和
> 最多 2 次重规划。Mock 全量为 100 条后端/评测测试、90.69% 覆盖率、362 条既有样本/26 项
> 门禁和 60 条 RAG Eval；Requests 黑盒 2 条、移动端 48 条 Jest + 5 条逻辑测试、2 条核心 Web
> E2E 与三端构建均通过。
> 2026-08-13 封板后修复真实 Agent 客户端 10 秒超时和过期 Resume 状态；真实 DeepSeek v4 Pro
> 周总结 smoke 20.4 秒返回 HTTP 200。Home 新增可解释静息能量估算并把旧“净结余”更名为
> “记录差值”，明确不等于完整 TDEE。
> 真实 DeepSeek v3 固定门禁 10 次调用全部通过，费用 `$0.00171864`。Allure、JUnit、
> Coverage 和 Agent JSON 报告并存。
> 真实复合 Multi-Agent 黑盒 1/1、28.02 秒；RAG v2 的 Recall@3/5 为 1.0、MRR 0.9625，真实
> Generation Groundedness/Relevance 为 0.9625、Citation Correctness 0.9083、Abstention 1.0。
> 阶段 9 食物图片的 60 张质量门禁仍失败，因此图片只允许 Development 实验性候选；
> 当前可用于本机作品集演示，但不等同于公网生产、商店签名或图片模型正式发布通过。
> 2026-08-05 已建立迁移基线分支，并按用户授权备份到 GitHub 私有仓库
> `boom080/journey_v1`；未创建 PR。单服务器 production Compose、API/PostgreSQL、Web export
> 和 Caddy HTTPS 配置已验证；四容器本机整栈仍受 Docker Hub 网络超时阻塞，尚未公网部署

## 阅读顺序

1. [`../AGENTS.md`](../AGENTS.md)：Codex 工作规则和阶段边界。
2. [`JOURNEY_REFACTOR_PLAN.md`](JOURNEY_REFACTOR_PLAN.md)：唯一可执行迁移计划。
3. [`ARCHITECTURE_DECISIONS.md`](ARCHITECTURE_DECISIONS.md)：已确认与待确认决策。
4. [`CURRENT_PROJECT_AUDIT.md`](CURRENT_PROJECT_AUDIT.md)：旧项目事实基线与逐阶段当前实现审计。
5. [`AGENT_TECH_RESEARCH.md`](AGENT_TECH_RESEARCH.md)：Agent、RAG 和评测技术选择。
6. [`EXECUTION_LOG.md`](EXECUTION_LOG.md)：实际执行与验证证据。
7. [`DEVELOPMENT.md`](DEVELOPMENT.md)：阶段 3 本地运行、地址和环境前置说明。
8. [`API.md`](API.md)：阶段 4/6 `/api/v1`、身份、核心业务、Agent/RAG 与测试账号契约。
9. [`deployment/STAGING.md`](deployment/STAGING.md)：阶段 8 staging、备份恢复和云部署门禁。
10. [`deployment/SERVER_DOCKER.md`](deployment/SERVER_DOCKER.md)：单服务器 production
    Docker Compose、HTTPS、备份、升级与回退路径。
11. [`deployment/BUILD_AND_RELEASE.md`](deployment/BUILD_AND_RELEASE.md)：三端构建、变体与签名路径。
12. [`demo/INTERVIEW_DEMO.md`](demo/INTERVIEW_DEMO.md)：3—5 分钟演示脚本和验收口径。
13. [`demo/RESUME_AND_INTERVIEW.md`](demo/RESUME_AND_INTERVIEW.md)：开发、测试开发、产品和
    售前岗位的简历描述、STAR 案例、问答依据与诚实边界。
14. [`product/FOOD_IMAGE_PRIVACY_AND_EVAL.md`](product/FOOD_IMAGE_PRIVACY_AND_EVAL.md)：阶段 9
    食物图片单项的隐私、评测、回退和真实 Provider 启用门禁。
15. [`../evals/reports/STAGE9_FOOD_IMAGE_EVALUATION_REPORT.md`](../evals/reports/STAGE9_FOOD_IMAGE_EVALUATION_REPORT.md)：
    Mock/工程基线、真实 Qwen 三轮指标、失败修正和未通过门禁。
16. [`../evals/food_image_real/README.md`](../evals/food_image_real/README.md)：
    100 张授权图片评测集的组成、许可、复现和隐私边界。
17. [`../evals/food_image_holdout/README.md`](../evals/food_image_holdout/README.md)：
    30 张密封泛化 holdout、防泄漏校验和尺度配对数据缺口。
18. [`../evals/food_image_scale_candidate/README.md`](../evals/food_image_scale_candidate/README.md)：
    16 张用户确认授权来源、88 个称重参考单格和 30 个尺度配对候选的加工与密封前门禁。
19. [`../evals/food_image_scale_holdout/README.md`](../evals/food_image_scale_holdout/README.md)：
    30 组内部尺度配对的密封、哈希验证、授权限制及公开契约阻塞项。
20. [`../evals/food_image_recognition_holdout/README.md`](../evals/food_image_recognition_holdout/README.md)：
    ADR-031 的 60 张密封识别型独立 holdout、许可、隐私、零重叠和复验说明。
21. [`../evals/reports/REAL_MODEL_ACCEPTANCE_2026_08_01.md`](../evals/reports/REAL_MODEL_ACCEPTANCE_2026_08_01.md)：
    文字与图片对应真实模型的发布验收矩阵、指标和当前 Conditional 结论。
22. [`../evals/reports/REAL_AGENT_V2_PROVIDER_ACCEPTANCE.json`](../evals/reports/REAL_AGENT_V2_PROVIDER_ACCEPTANCE.json)：
    Agent v2 首轮真实规划失败证据。
23. [`../evals/reports/REAL_AGENT_V2_PROVIDER_ACCEPTANCE_2.json`](../evals/reports/REAL_AGENT_V2_PROVIDER_ACCEPTANCE_2.json)：
    Planner Prompt 修正后的真实 DeepSeek 通过报告。
24. [`../evals/reports/REAL_AGENT_V3_PROVIDER_ACCEPTANCE.json`](../evals/reports/REAL_AGENT_V3_PROVIDER_ACCEPTANCE.json)：
    Agent v3 checkpoint 计划与 Observation 恢复选择的真实 DeepSeek 通过报告。
25. [`product/LOCAL_FIRST_AI_UI_PROPOSAL.md`](product/LOCAL_FIRST_AI_UI_PROPOSAL.md)：阶段 12
    离线能力矩阵、首页信息架构、视觉迭代与实现验收、浏览器/小红书边界和量化标准。
26. [`../qiuzhaomianshi.md`](../qiuzhaomianshi.md)：按岗位分类、随每次项目更新同步维护的秋招
    面试问题、量化证据和诚实陈述边界。
27. [`architecture/MULTI_AGENT_DATA_FLOW.md`](architecture/MULTI_AGENT_DATA_FLOW.md)：有界
    Orchestrator/Specialist 主链路、确认门和结构化 Trace。
28. [`architecture/RAG_ARCHITECTURE_AND_EVAL.md`](architecture/RAG_ARCHITECTURE_AND_EVAL.md)：
    当前 RAG 参数、v1/v2 比较、真实生成指标与限制。
29. [`../evals/reports/RAG_EVAL_V1_2026_08_10.md`](../evals/reports/RAG_EVAL_V1_2026_08_10.md)：
    60 题 RAG Eval 的版本化人类可读报告。
30. [`demo/JOURNEY_CAREER_MATERIAL_KNOWLEDGE_BASE.md`](demo/JOURNEY_CAREER_MATERIAL_KNOWLEDGE_BASE.md)：
    面向 Agent 开发、测试开发、运维、售前、产品和 AI 产品岗位的事实素材库；包含技术、问题
    案例、量化证据、状态边界和供其他 Codex 按 JD 取材的使用规则。

## 当前进度

| 阶段 | 名称 | 状态 | 启动条件 |
|---|---|---|---|
| 1 | 决策与基线固化 | Completed | 2026-07-15 验收通过 |
| 2 | 旧资产提取与微信端退役 | Completed | 2026-07-16 验收通过 |
| 3 | 新工程骨架与最小 Docker 基线 | Completed | 2026-07-17 双模拟器与 API 验收通过 |
| 4 | 身份、画像与核心业务 API | Completed | 2026-07-17 API/数据库/契约验收通过 |
| 5 | 移动端核心页面 | Completed | 2026-07-17 双模拟器核心闭环与离线同步验收通过 |
| 6 | Agent 与 RAG | Completed | Mock 零外部调用、受控 RAG、确认写入与双模拟器验收通过 |
| 7 | 量化评测、自动化测试与 CI | Completed | 318 条评测、17 项 Agent/RAG 门禁和全栈测试通过 |
| 8 | staging、构建、服务器 Docker 与秋招展示 | Completed / Revalidated | 本机 staging、Web E2E、三端构建、双模拟器 Release；production Compose 为 Conditional，本机整栈仍受 Docker Hub 网络阻塞 |
| 9 | 当前范围：文字 Agent + 食物图片候选 | 文字真实门禁 PASS；图片 API smoke PASS、质量 FAIL；整体 Conditional | 图片仅在新 ADR、新模型、新独立密封集和预注册语义评分规则后重启正式验收；其余能力不进入当前范围 |
| 10 | Agent v2 与测试报告增强 | Completed | 单 Agent 计划—策略—执行—校验闭环、Allure 和真实 DeepSeek v2 门禁通过 |
| 11 | Agent v3 确认恢复、Observation 重规划与 Requests 黑盒 | Completed | ADR-035 Accepted；无自动下一阶段 |
| 12 | 本地优先与 AI 原生体验 | Completed | ADR-036 local-first 与 ADR-037 用户主动分享生活灵感均已验收；账号绑定、后台抓取和通用 Web Research 不在范围 |
| 13 | 秋招 Demo 封板 | Completed | ADR-039；真实 LLM、有限 Multi-Agent、RAG Eval、7/30 Journey、E2E 与 Docker 一键启动均已验收 |

## 维护规则

- 本页只记录导航和当前状态，不重复完整任务清单。
- `JOURNEY_REFACTOR_PLAN.md` 是唯一计划，不再维护平行 Roadmap。
- 阶段状态只在验收证据写入 `EXECUTION_LOG.md` 后更新。
- 代码与文档冲突时，以代码核查结果为准，并在同一任务内修正文档。

## 阶段 2 提取产物

- [`product/LEGACY_ASSET_INVENTORY.md`](product/LEGACY_ASSET_INVENTORY.md)：品牌资产、哈希与来源状态。
- [`product/LEGACY_UI_REFERENCE.md`](product/LEGACY_UI_REFERENCE.md)：页面语义、设计 token、状态矩阵和截图门禁。
- [`product/LEGACY_LOGIC_MIGRATION_MATRIX.md`](product/LEGACY_LOGIC_MIGRATION_MATRIX.md)：前后端业务规则迁移分类。
- [`product/WECHAT_RETIREMENT_CHECKLIST.md`](product/WECHAT_RETIREMENT_CHECKLIST.md)：已执行的微信端退役范围与验证证据。
