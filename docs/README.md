# Journey 文档索引

> 更新日期：2026-08-04
> 当前执行：阶段 12 In Progress；方案 C 已由用户确认并完成首页视觉子项，完整本地数据副本与
> 小红书路径仍待用户单独确认
> 最近完成：移动端固定暖白＋明亮薄荷浅色主题，首页复用原版叶子角色并落地首屏统一输入、
> 开放式今日指标和轻量 Agent 状态；320/390 pt 视觉核对通过
> 当前状态：Journey 是单 Agent 的 Planner → Policy Guard → Executor → Observation →
> Verifier → Replanner 闭环。组合“记录 + 建议”会先暂停，用户校正确认后才读取最新业务事实
> 继续执行；可恢复失败最多重规划 2 次，不能跨供应商暗中转发或绕过确认写入。Mock 全量为
> 85 条测试、90.49% 后端覆盖率、362 条版本化样本和 26 项门禁；Requests 网络黑盒 1 条、
> 移动端 33 条组件/契约测试 + 5 条逻辑测试、2 条核心 Web E2E、Web/iOS/Android JS 构建均通过。
> 真实 DeepSeek v3 固定门禁 10 次调用全部通过，费用 `$0.00171864`。Allure、JUnit、
> Coverage 和 Agent JSON 报告并存。
> 阶段 9 食物图片的 60 张质量门禁仍失败，因此图片只允许 Development 实验性候选；
> 当前可用于本机作品集演示，但不等同于公网生产、商店签名或图片模型正式发布通过。
> 2026-08-05 已建立迁移基线分支，并按用户授权备份到 GitHub 私有仓库
> `boom080/journey_v1`；未创建 PR

## 阅读顺序

1. [`../AGENTS.md`](../AGENTS.md)：Codex 工作规则和阶段边界。
2. [`JOURNEY_REFACTOR_PLAN.md`](JOURNEY_REFACTOR_PLAN.md)：唯一可执行迁移计划。
3. [`ARCHITECTURE_DECISIONS.md`](ARCHITECTURE_DECISIONS.md)：已确认与待确认决策。
4. [`CURRENT_PROJECT_AUDIT.md`](CURRENT_PROJECT_AUDIT.md)：旧项目代码事实。
5. [`AGENT_TECH_RESEARCH.md`](AGENT_TECH_RESEARCH.md)：Agent、RAG 和评测技术选择。
6. [`EXECUTION_LOG.md`](EXECUTION_LOG.md)：实际执行与验证证据。
7. [`DEVELOPMENT.md`](DEVELOPMENT.md)：阶段 3 本地运行、地址和环境前置说明。
8. [`API.md`](API.md)：阶段 4/6 `/api/v1`、身份、核心业务、Agent/RAG 与测试账号契约。
9. [`deployment/STAGING.md`](deployment/STAGING.md)：阶段 8 staging、备份恢复和云部署门禁。
10. [`deployment/BUILD_AND_RELEASE.md`](deployment/BUILD_AND_RELEASE.md)：三端构建、变体与签名路径。
11. [`demo/INTERVIEW_DEMO.md`](demo/INTERVIEW_DEMO.md)：3—5 分钟演示脚本和验收口径。
12. [`demo/RESUME_AND_INTERVIEW.md`](demo/RESUME_AND_INTERVIEW.md)：开发、测试开发、产品和
    售前岗位的简历描述、STAR 案例、问答依据与诚实边界。
13. [`product/FOOD_IMAGE_PRIVACY_AND_EVAL.md`](product/FOOD_IMAGE_PRIVACY_AND_EVAL.md)：阶段 9
    食物图片单项的隐私、评测、回退和真实 Provider 启用门禁。
14. [`../evals/reports/STAGE9_FOOD_IMAGE_EVALUATION_REPORT.md`](../evals/reports/STAGE9_FOOD_IMAGE_EVALUATION_REPORT.md)：
    Mock/工程基线、真实 Qwen 三轮指标、失败修正和未通过门禁。
15. [`../evals/food_image_real/README.md`](../evals/food_image_real/README.md)：
    100 张授权图片评测集的组成、许可、复现和隐私边界。
16. [`../evals/food_image_holdout/README.md`](../evals/food_image_holdout/README.md)：
    30 张密封泛化 holdout、防泄漏校验和尺度配对数据缺口。
17. [`../evals/food_image_scale_candidate/README.md`](../evals/food_image_scale_candidate/README.md)：
    16 张用户确认授权来源、88 个称重参考单格和 30 个尺度配对候选的加工与密封前门禁。
18. [`../evals/food_image_scale_holdout/README.md`](../evals/food_image_scale_holdout/README.md)：
    30 组内部尺度配对的密封、哈希验证、授权限制及公开契约阻塞项。
19. [`../evals/food_image_recognition_holdout/README.md`](../evals/food_image_recognition_holdout/README.md)：
    ADR-031 的 60 张密封识别型独立 holdout、许可、隐私、零重叠和复验说明。
20. [`../evals/reports/REAL_MODEL_ACCEPTANCE_2026_08_01.md`](../evals/reports/REAL_MODEL_ACCEPTANCE_2026_08_01.md)：
    文字与图片对应真实模型的发布验收矩阵、指标和当前 Conditional 结论。
21. [`../evals/reports/REAL_AGENT_V2_PROVIDER_ACCEPTANCE.json`](../evals/reports/REAL_AGENT_V2_PROVIDER_ACCEPTANCE.json)：
    Agent v2 首轮真实规划失败证据。
22. [`../evals/reports/REAL_AGENT_V2_PROVIDER_ACCEPTANCE_2.json`](../evals/reports/REAL_AGENT_V2_PROVIDER_ACCEPTANCE_2.json)：
    Planner Prompt 修正后的真实 DeepSeek 通过报告。
23. [`../evals/reports/REAL_AGENT_V3_PROVIDER_ACCEPTANCE.json`](../evals/reports/REAL_AGENT_V3_PROVIDER_ACCEPTANCE.json)：
    Agent v3 checkpoint 计划与 Observation 恢复选择的真实 DeepSeek 通过报告。
24. [`product/LOCAL_FIRST_AI_UI_PROPOSAL.md`](product/LOCAL_FIRST_AI_UI_PROPOSAL.md)：阶段 12
    离线能力矩阵、首页信息架构、视觉迭代与实现验收、浏览器/小红书边界和量化标准。

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
| 8 | staging、构建与秋招展示 | Completed / Revalidated | 本机 staging、Web E2E、三端构建、双模拟器 Release 安装和四类岗位材料完成 |
| 9 | 当前范围：文字 Agent + 食物图片候选 | 文字真实门禁 PASS；图片 API smoke PASS、质量 FAIL；整体 Conditional | 图片仅在新 ADR、新模型、新独立密封集和预注册语义评分规则后重启正式验收；其余能力不进入当前范围 |
| 10 | Agent v2 与测试报告增强 | Completed | 单 Agent 计划—策略—执行—校验闭环、Allure 和真实 DeepSeek v2 门禁通过 |
| 11 | Agent v3 确认恢复、Observation 重规划与 Requests 黑盒 | Completed | ADR-035 Accepted；无自动下一阶段 |
| 12 | 本地优先与 AI 原生体验 | In Progress（视觉子项已实现） | 方案 C 已确认并验收；等待用户确认本地数据范围和小红书主动分享路径 |

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
