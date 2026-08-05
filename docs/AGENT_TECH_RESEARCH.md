# Journey Agent 技术调研

> 首次调研：2026-07-15；阶段 6 复核：2026-07-20；Provider Router 复核：2026-07-22
> 范围：Python/FastAPI 生态中的模型适配、Agent 编排、RAG、可观测性与评测
> 注意：维护状态是调研日快照，正式安装前必须再次核对版本、许可证和兼容矩阵。

## 1. 选型原则

- 支持 FastAPI/Pydantic 和异步调用。
- 支持工具调用、结构化输出和流式事件。
- 支持状态工作流、人工确认、超时、重试和恢复。
- 能替换模型供应商，但不为“多模型”引入无法测试的动态行为。
- 能记录 Agent 轨迹、Token、延迟、成本和版本。
- 支持 Mock、回归数据集和确定性业务测试。
- 不以 Star 数作为唯一标准；优先官方仓库、近期维护、文档和许可证。
- 不为了简历关键词制造多 Agent、微服务或独立向量数据库。

## 阶段 6 实施前复核（2026-07-20）

### 框架与许可证

| 能力 | 锁定版本 | 复核结果 |
|---|---:|---|
| LangChain | 1.3.14 | PyPI 2026-07-16 发布；官方仓库 MIT；只用于模型与结构化输出适配 |
| langchain-litellm | 0.7.0 | LangChain 官方集成；提供 `ChatLiteLLMRouter`、结构化输出和工具调用边界 |
| LiteLLM | 1.86.2 | 嵌入式 Python Router；精确版本与哈希锁定，不部署 Proxy |
| LangGraph | 1.2.9 | PyPI 2026-07-10 发布；官方仓库 MIT；只用于两个多节点工作流 |
| Pydantic | 2.13.4 | 与 FastAPI 0.128.8、Python 3.12 锁文件组合安装和测试通过 |
| OpenTelemetry API | 1.43.0 | Apache-2.0；当前只发本地 spans，不配置外部 exporter |
| OpenAI Python（传递依赖） | 2.46.0 | 由 LiteLLM 锁定；用于兼容异常与 OpenAI-compatible HTTP 边界 |

版本依据：[LangChain releases](https://github.com/langchain-ai/langchain/releases)、
[LangGraph releases](https://github.com/langchain-ai/langgraph/releases)、
[PyPI LangChain](https://pypi.org/project/langchain/)、
[PyPI LangGraph](https://pypi.org/project/langgraph/)、
[LangChain LiteLLM integration](https://docs.langchain.com/oss/python/integrations/chat/litellm)、
[LiteLLM docs](https://docs.litellm.ai/)。生产和测试锁文件已在 Linux ARM64 镜像中使用
hash 校验安装。

### 供应商、预算和数据政策

| 候选 | 复核结果 | 当前决定 |
|---|---|---|
| OpenAI API | 官方说明 API 数据默认不用于训练；普通 abuse monitoring logs 最长可保留 30 天，获批控制另议；价格按具体模型分别计费 | **Proposed**；adapter 已具备，用户确认前不启用 |
| DeepSeek API | 官方 OpenAI-compatible Base URL 为 `https://api.deepseek.com`；V4-Flash/Pro 支持 JSON 与 Tool Calls；价格和模型可用性会变化，数据政策尚未完成项目级验收 | **合成 Smoke 已通过**；Flash/Pro 双模型 Profile 已建立，仓库/CI 默认 Mock，个人健康数据待授权 |
| Qwen / GLM / Kimi | 三家均提供 OpenAI-compatible 接口；Qwen 已做政策复核与真实图片评测，GLM/Kimi 仍只有占位；当前模型和价格会变化 | **Qwen Proposed**：真实链路可用但 Top-3/份量未达门槛；GLM/Kimi 启用前仍须补价格、政策和同一契约评测 |
| Anthropic API | 官方文档说明商业 API 默认 30 天后端删除，部分安全或法律场景例外；当前没有安装 native adapter | **备选**；不为“可切换”提前增加依赖 |

政策和价格复核入口：[OpenAI API data controls](https://platform.openai.com/docs/guides/your-data)、
[OpenAI API pricing](https://openai.com/api/pricing/)、
[DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing/)、
[Anthropic data retention](https://privacy.anthropic.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data)、
[Anthropic pricing](https://docs.anthropic.com/en/docs/about-claude/pricing)。

本阶段确定的预算是：外部调用 `0` 次、外部 Token 成本 `$0`、`AGENT_API_KEY` 留空。
启用外部模型前必须由用户确认 provider、模型映射、每天美元上限、单价快照和数据政策；
配置不完整时 Settings fail-fast，不能静默使用默认供应商。

### DeepSeek V4 配置复核（2026-07-22）

- 官方模型 ID 已确认是 `deepseek-v4-flash` 与 `deepseek-v4-pro`；旧
  `deepseek-chat`/`deepseek-reasoner` 将于 2026-07-24 23:59（北京时间）停止使用，因此
  Journey 不采用旧别名。
- 两个 V4 模型均支持 JSON Output、Tool Calls 和思考/非思考模式。用户随后明确确认同一
  API 可调用 Flash 与 Pro；Journey 通过 LangChain + LiteLLM Router 统一调用，不增加
  DeepSeek 专属 SDK。
- 当前映射：高频路由、文本解析和知识回答使用 `deepseek-v4-flash`；仅
  `recommendation` 与 `weekly_summary` 使用 `deepseek-v4-pro`。Flash 关闭思考，Pro
  开启思考并使用 `high` effort。实测发现 LangChain function calling 的
  `tool_choice=required` 与 Pro thinking 冲突，因此 Pro 结构化生成使用官方 JSON Output
  并注入 Pydantic JSON Schema；Flash 保留 function calling。
- 2026-07-22 官方美元 cache-miss 价格：Flash 输入 `$0.14`/百万 Token、输出 `$0.28`；
  Pro 输入 `$0.435`、输出 `$0.87`。项目按模型分别记录价格；启用或切换模型前必须重新
  核价，并以 `AGENT_MAX_OUTPUT_TOKENS=2048` 限制单次生成规模。
- 技术配置准备不等于数据政策通过。已使用两条明确标记为合成的饮食/运动文本完成真实
  Flash Smoke，并以虚构生活方式数据完成一次 Pro 结构化 Smoke（208 input / 115 output
  Token、2812 ms、估算 `$0.00019053`）；真实健康文本可能包含饮食、运动、体重和画像，
  用户尚未明确同意发送范围与保存政策，因此不发送个人记录。

复核来源：[DeepSeek 首次 API 调用](https://api-docs.deepseek.com/)、
[模型与价格](https://api-docs.deepseek.com/quick_start/pricing/)、
[Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/)、
[JSON Output](https://api-docs.deepseek.com/guides/json_mode/)、
[Chat Completion API](https://api-docs.deepseek.com/api/create-chat-completion/)。

## 2. GitHub 候选快照

以下仓库在 2026-07-15 查询时均未归档，并有近期提交。许可证以 GitHub API 返回和仓库文件为准；标记“需复核”的项目不得在未检查具体版本许可证前加入依赖。

| 项目 | 官方仓库 | 主要用途 | 维护快照 | 许可证快照 | 引入成本 | Journey 兼容性 | 建议 |
|---|---|---|---|---|---|---|---|
| LangChain | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 模型、消息、工具、Retriever 与集成适配 | 活跃，2026-07-14 有提交 | MIT | 中 | Python/FastAPI 兼容，供应商生态广 | **采用有限能力**：模型/工具适配，不让业务层依赖任意 Chain |
| LangGraph | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 有状态工作流、持久化、HITL、恢复 | 活跃，2026-07-14 有提交 | MIT | 中 | 适合确认、周报、建议工作流 | **按需采用**，不用于简单单步解析 |
| Pydantic AI | [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | 类型安全 Agent、供应商适配、结构化输出、评测 | 活跃，2026-07-15 有提交 | MIT | 低到中 | 与 FastAPI/Pydantic 非常契合 | **备选**；当前不与 LangChain 双重封装，保留评测思路 |
| OpenAI Agents SDK | [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | Tools、handoff、guardrail、session、tracing | 活跃，2026-07-15 有提交 | MIT | 低到中 | 能支持多供应商适配，但 OpenAI 体验最完整 | **备选**；若未来以 OpenAI 为主或需要 Realtime，再做 Spike |
| LlamaIndex | [run-llama/llama_index](https://github.com/run-llama/llama_index) | 文档摄取、索引、Retriever、RAG | 活跃，2026-07-13 有提交 | MIT | 中 | RAG 功能丰富，但第一版受控知识库规模不大 | **暂不采用全框架**；先自研清晰 ingestion/retriever 接口 |
| LiteLLM | [BerriAI/litellm](https://github.com/BerriAI/litellm) | 多模型统一调用、路由、重试与成本 | 活跃；1.86.2 已锁定 | OSS 主体 MIT；Enterprise 目录另议 | 中 | 与现有 LangChain 边界兼容 | **采用嵌入式 Router**；不部署 Proxy，供应链版本必须精确锁定 |
| Langfuse | [langfuse/langfuse](https://github.com/langfuse/langfuse) | Trace、Prompt、Dataset、Eval、成本 | 活跃，2026-07-14 有提交 | GitHub API 未明确，需复核 | 中到高 | 功能完整，可自托管或托管 | **后置评估**；先用 OTel + 自有记录，避免早期多服务 |
| Phoenix | [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) | OpenTelemetry AI 可观测性与评测 | 活跃，2026-07-15 有提交 | GitHub API 未明确，需复核 | 中 | 适合本地 trace/RAG 调试 | **可观测性 Spike 候选**，不立即常驻部署 |
| DeepEval | [confident-ai/deepeval](https://github.com/confident-ai/deepeval) | LLM/Agent 自动评测 | 活跃，2026-07-14 有提交 | Apache-2.0 | 中 | pytest 风格，适合回归 | **候选**；先用确定性 pytest，主观指标再引入 |
| Ragas | [vibrantlabsai/ragas](https://github.com/vibrantlabsai/ragas) | RAG 与 LLM 评测 | 近期维护，2026-02-24 有提交 | Apache-2.0 | 中 | 适合 RAG 指标，但常含 judge 模型 | **RAG 阶段候选**，不能代替人工金标与引用检查 |

## 3. 最终建议组合

### 第一层：业务服务（自研，确定性）

FastAPI 应用服务是唯一写入入口：

- `ProfileService`
- `FoodRecordService`
- `ActivityRecordService`
- `JourneyService`
- `RecommendationService`
- `KnowledgeService`

权限、事务、幂等、确认令牌和审计属于业务层，不交给框架或模型决定。

### 第二层：工具与结构化契约

使用 Pydantic 定义：

- `IntentResult`
- `FoodCandidate` / `FoodWriteRequest`
- `ActivityCandidate` / `ActivityWriteRequest`
- `ProfilePatchCandidate`
- `JourneyQuery`
- `KnowledgeQuery` / `Citation`
- `RecommendationResult`
- `WeeklySummaryResult`
- `ClarificationRequest`
- `AgentError` / `FallbackResult`

模型只能生成候选参数；写工具必须验证用户、确认令牌、幂等键和权限。

### 第三层：LangChain 适配

只使用以下能力：

- 不同模型供应商的 Chat Model adapter。
- 工具声明与结构化输出。
- 消息和流式事件的统一接口。
- Retriever 接口。
- 测试中的 Fake/Mock Chat Model。

不采用难以审计的长 Chain，不在领域对象中传播 LangChain 类型。

外部模型统一经过 `langchain-litellm` 的 `ChatLiteLLMRouter`。LiteLLM 只作为嵌入 FastAPI
进程的 Provider Router，不增加独立 Proxy、虚拟 Key 服务或新容器。Mock 仍是独立确定性
Adapter，CI 不经过 LiteLLM 发起网络调用。

### 第四层：LangGraph 工作流

只在存在多步骤、状态或人工确认时使用：

```text
Recommendation
读取画像 -> 读取今日/近期数据 -> 检索知识 -> 生成建议 -> 校验引用 -> 安全检查 -> 输出

Weekly Summary
读取周数据 -> 计算确定性指标 -> 检索必要知识 -> 生成总结 -> 校验结构/安全 -> 输出

Confirmed Write
识别/拆分 -> 生成候选 -> 暂停等待用户确认 -> 调用业务服务 -> 刷新聚合 -> 返回结果
```

简单意图分类或一次工具查询使用普通 Python 控制流，不强制建立 Graph。

### 第五层：Model Router（LangChain/LiteLLM + 轻量业务封装）

Router 依据显式配置路由，不让模型自行选择任意供应商：

- `intent_classification`：低延迟、低成本、结构化能力。
- `food_text_parse`：中文理解、结构化输出。
- `activity_text_parse`：中文理解、结构化输出。
- `knowledge_answer`：长上下文与引用遵循。
- `recommendation` / `weekly_summary`：综合推理与结构化输出。
- 后续 `food_vision`、`body_progress`、`activity_video`：多模态能力。

配置必须记录 provider、model、capability、Prompt 版本、超时、重试上限和成本单价快照。第一版只完整接入一个真实供应商；第二供应商需要通过同一契约测试后才能启用。

`AGENT_PROVIDER` 是服务端 Profile 开关。DeepSeek、Qwen、GLM、Kimi 使用相互独立的 Key、
Base URL、模型映射和定价配置；缺 Key、正预算或当前模型价格时 fail-fast，禁止把一个
供应商的 Key/价格复用给另一个供应商。移动端不得选择任意 Provider 或持有 Key。

Mock 是测试 Adapter，不是生产模型。生产模型不可用时走确定性 fallback。

### LiteLLM 供应链门禁

2026 年 3 月，LiteLLM 官方披露 PyPI `1.82.7`、`1.82.8` 曾被注入凭据窃取代码，随后已
删除受影响包并恢复干净发布。Journey 明确避开这两个版本，固定 `litellm==1.86.2` 与
`langchain-litellm==0.7.0`，生产/开发锁文件保存所有 wheel/sdist 哈希，Docker 使用
`pip install --require-hashes` 验证。升级必须重新审计官方安全公告、生成锁并跑完整 Mock
门禁，不能使用无上限的 `latest`。来源：[LiteLLM official security issue](https://github.com/BerriAI/litellm/issues/24518)。

## 4. 业务 Agent 设计

不采用多个相互聊天的 Agent。建议使用一个入口 Router 加显式工具和工作流：

| 能力 | 输入 | 行为 | 写入规则 |
|---|---|---|---|
| Intent Router | 首页文本 | 分类、置信度、多意图拆分、澄清 | 不写入 |
| Food Tool | 食物描述 | 解析名称、份量、餐次、营养候选 | 用户确认后写入 |
| Activity Tool | 运动描述 | 解析类型、时长、强度、消耗候选 | 用户确认后写入 |
| Profile Tool | 用户/任务 | 读取画像或生成变更候选 | 读取直接；变更确认 |
| Journey Tool | 日期范围 | 读取记录、趋势和确定性指标 | 不写入 |
| Nutrition Knowledge Tool | 问题 | 受控检索、引用、无答案 | 不写入 |
| Recommendation Workflow | 画像 + 近期数据 + 知识 | 个性化建议与依据 | 保存结果需确认或明确策略 |
| Weekly Summary Workflow | 周数据 | 指标、总结、建议、引用 | 生成记录可重新计算 |
| Fallback | 失败上下文 | 表单、固定计算、缓存或明确错误 | 禁止静默写入 |

## 5. Context Builder 与长期状态

### 事实来源优先级

1. PostgreSQL 结构化用户与业务数据。
2. 由确定性代码计算的近期聚合和趋势。
3. 用户确认的偏好与摘要。
4. 按任务检索的少量个人记忆。
5. 当前会话必要消息。

系统 Prompt 只保存稳定规则，不保存用户动态状态。每次调用记录 Context 组成、数据版本和 Token 预算；敏感字段按最小必要原则传递。

### 长期状态

- 用户画像和健康记录由业务表管理。
- 对话按会话保存并支持保留期与删除。
- 模型推断不得直接变成画像事实。
- 用户个人记忆与公共 RAG 索引严格隔离。
- 不依赖任何供应商的服务端会话作为唯一状态。

## 6. RAG 方案

### 第一版

- 受控知识源，记录来源 URL/出版物、发布日期、地区、许可和版本。
- ingestion、清洗、Chunk、metadata、embedding 和索引各自可测试。
- PostgreSQL 已稳定且确有语义检索需求后启用 pgvector。
- Retrieval 返回文档 ID、Chunk ID、分数和原文证据。
- 生成回答必须引用实际返回证据；没有相关资料时返回 no-answer。
- 公共知识库与个人数据采用不同 collection/namespace 和权限路径。

### 暂不做

- 大规模抓取未知网站。
- 运行时自由网络搜索作为健康依据。
- 独立向量数据库集群。
- 让模型自行编造或修复引用。

## 7. 超时、重试与降级

- 每个能力独立设置超时，不使用无限重试。
- 只对明确可重试错误进行有限次数指数退避。
- 写工具使用幂等键；模型重试不能导致重复写入。
- Provider 失败由 Router 返回标准错误，再选择显式配置的备用模型或确定性 fallback。
- 离线时客户端不调用 Agent，显示本地知识、固定计算和手动表单。
- 所有降级响应明确标记来源，不能伪装成在线模型回答。

## 8. 可观测性、Prompt 和成本

第一版先定义自有事件和 OpenTelemetry span，避免锁定平台：

- `request_id`、`trace_id`、`user_id_hash`、session/run ID。
- intent、workflow、node、tool、确认状态、错误类型。
- provider、model、Prompt 版本、Schema 版本、知识库版本。
- 输入/输出 Token、首 Token 延迟、总延迟、重试、估算成本。
- 检索文档/Chunk ID 与引用验证结果。

不得在日志中记录密码、Token、完整身体照片/视频或不必要的健康原文。Phoenix、Langfuse 或托管平台只能在阶段 6/7 Spike 后按许可证、隐私和维护成本决定。

## 9. 自动化评测方案

### 初始数据集

- 至少 100 条意图路由样本。
- 至少 50 条食物解析样本。
- 至少 50 条运动解析样本。
- 至少 20 条混合意图样本。
- 至少 20 条高风险健康输入。
- 至少 20 条超时、格式错误、工具失败和降级场景。
- 一组版本化 RAG 问题、相关文档和 no-answer 样本。

### 初始门槛

| 指标 | MVP 门槛 |
|---|---:|
| 意图路由准确率 | ≥ 90% |
| 写工具选择正确率 | ≥ 95% |
| 工具参数 Schema 合法率 | 100% |
| 未经确认的写入 | 0 |
| 高风险安全规则通过率 | 100% |
| CI 中真实模型调用 | 0 |

RAG 的 Recall@k、引用支持率、no-answer 准确率以及延迟/成本门槛在建立首批金标数据后由基线结果确定，不能先写虚假数字。

### 展示闭环

每次 Prompt、模型映射、路由或检索策略变更，保存：

1. 变更前数据集与指标。
2. 失败案例分类。
3. 变更内容和版本。
4. 变更后完整回归结果。
5. 准确率、延迟和成本的权衡。

## 10. 明确不建议采用

- 为 Food、Activity、Profile 各建一个会相互聊天的独立 Agent。
- 让模型直接访问数据库或生成 SQL 写入。
- 同时接入大量真实模型供应商以制造“可切换”表象。
- 第一版同时部署 LangSmith/Langfuse/Phoenix/LiteLLM Proxy 等全部平台。
- 把 Mock 当作生产模型或向用户返回伪 AI 结果。
- 把全部对话和用户数据全量塞入 Prompt。
- 没有来源和许可记录的大规模健康知识抓取。

## 11. 实施前必须再次确认

- Python、LangChain、LangGraph、Pydantic 和模型 SDK 的兼容版本。
- 各候选仓库目标版本的许可证。
- 主供应商在目标地区的可用性、数据政策、工具调用与结构化输出能力。
- 模型价格和 Token 计算方式。
- pgvector、Embedding 模型和知识源的版本策略。
- OpenTelemetry exporter 与 staging 的隐私边界。

## 12. 阶段 7 评测组合结论（2026-07-20）

阶段 7 没有再引入额外 Agent 平台，而是复用阶段 6 的 LangChain/LangGraph/Pydantic 边界，
增加轻量自研确定性评测器、版本化 JSON 数据集、pytest/pytest-cov、Jest/RNTL、Playwright
和 GitHub Actions。这样能直接检查业务路由、工具参数、结构化 Schema、RAG 引用和确认
写入，而不把框架自身测试误当产品质量。

- Agent/RAG：阶段 7 基线最初为 296 条合成样本、13 项门禁；当前已扩展到 318 条、
  17 项门禁，首轮 39 个失败与当前 0 失败均保留。
- 评测：当前不采用 LLM judge，避免外部成本、随机性和同源偏差；真实模型评测仍为
  `Status: Proposed`。
- 可观测性：沿用自有 run/tool trace 和版本字段，CI 报告 Token、延迟、预算与成本；
  没有为了阶段 7 同时部署 LangSmith、Langfuse 或 Phoenix。
- RAG：继续使用小型受控知识库与确定性检索；本阶段数据不足以支持引入独立向量数据库。

详细数据与限制见 [`../evals/reports/STAGE7_EVALUATION_REPORT.md`](../evals/reports/STAGE7_EVALUATION_REPORT.md)。

## 13. 阶段 9 食物图片技术复核（更新于 2026-07-28）

- Expo 官方 ImagePicker 支持 iOS/Android/Web 的系统相册与相机，配置插件可以设置权限文案并
  通过 `microphonePermission=false` 移除 Android `RECORD_AUDIO`。本项目解析到
  `expo-image-picker 57.0.5`，iOS/Android 冷构建和安装均通过。
- DeepSeek V4 官方 API 发布资料只给出 OpenAI ChatCompletions/Anthropic 文本消息接口，没有
  图片输入契约。Journey 据此把 V4 视为 text-only；已有 DeepSeek Key 不参与图片分析。
- 初始调研选择 `qwen3.7-plus`；2026-07-28 北京区域模型 API 已列出更新的
  `qwen3.7-flash`/`qwen3.7-flash-2026-07-15`。独立 Key 的图片输入、非思考 JSON、
  LangChain/LiteLLM/Pydantic 适配和 `/api/v1` 均完成无个人信息合成 Smoke，因此将
  `qwen3.7-flash` 作为当前 Proposed 真实视觉候选；合成 Smoke 不替代真实图片质量评测。
- 实现继续复用 LangChain 消息/Pydantic 结构化输出与嵌入式 LiteLLM Router，但使用独立
  `FOOD_IMAGE_PROVIDER`，避免切换文字 Agent。真实 Provider 失败不会自动把同一照片转发给
  另一供应商。
- 阿里云百炼当前服务协议要求按指示处理输入、不得用于自身目的或未经授权披露，且未获授权
  不得训练；隐私声明没有公开模型调用内容的精确保留天数。该不确定性仍是 Proposed ADR 的
  残余风险，不能用“北京端点”替代逐次同意和数据最小化。
- Qwen 结构化输出官方指南支持 `response_format={"type":"json_object"}`，同时要求 Prompt
  明确包含 JSON、调用方继续校验输出。真实调试证明当前 Flash 模型对过长 Prompt 更易超时/
  结构化失败，因此 v1.2 使用精简 JSON Prompt + Pydantic 后验校验，只归一化可确定修复的
  字段，不编造缺失识别内容。
- 100 张开放许可图片集和三轮真实评测已完成。v1.2 达到 Schema 100%、热量覆盖 84.44%、
  非食物拒答 100%、p95 2945 ms、零 fallback；Top-3 84.44% 与份量误差中位数 37.48%
  仍未达到 85%/≤30% 门槛，因此不建议把 `qwen3.7-flash` 标为已验收视觉模型。
- 份量估计研究指出单张 2D 图片丢失物理尺度，常用已知尺寸 fiducial marker 做校正。
  v1.3 因此先增加 Journey 9×5 cm 参照卡/已知盘碗直径，而不是立即换更贵模型。30 张
  零重叠无参照 holdout 得到 Top-3 76.67%、份量误差 36.36%，说明原调参集结果不能直接
  外推。SimpleFood45 缺少清晰公开数据许可，未纳入；尺度收益继续等待合法配对 cohort。

官方来源：[Expo ImagePicker](https://docs.expo.dev/versions/latest/sdk/imagepicker/)、
[DeepSeek V4 API 发布](https://api-docs.deepseek.com/news/news260424/)、
[Qwen 视觉理解](https://help.aliyun.com/en/model-studio/vision-model/)、
[Qwen 模型清单](https://www.alibabacloud.com/help/en/model-studio/models)、
[Qwen 结构化输出](https://help.aliyun.com/zh/model-studio/qwen-structured-output)、
[阿里云百炼服务协议](https://terms.alicdn.com/legal-agreement/terms/common_platform_service/20230728213935489/20230728213935489.html)、
[模型服务灵积隐私声明](https://help.aliyun.com/en/model-studio/privacy-notice)、
[Food Portion Estimation via 3D Object Scaling](https://openaccess.thecvf.com/content/CVPR2024W/MTF/html/Vinod_Food_Portion_Estimation_via_3D_Object_Scaling_CVPRW_2024_paper.html)、
[单图份量估计 fiducial marker 研究](https://pmc.ncbi.nlm.nih.gov/articles/PMC6226047/)。

## 14. 阶段 10 Agent v2 与测试报告结论（2026-08-03）

阶段 10 没有引入互相对话的多 Agent，也没有增加独立编排服务。最终组合是：

- LangGraph：承载 Planner → Policy Guard → Executor → Verifier 条件图和受限重规划；
- LangChain + 嵌入式 LiteLLM Router：完成供应商无关的结构化规划与模型调用；
- Pydantic + 自研类型化工具注册表：控制工具白名单、参数、依赖、风险和人工确认；
- PostgreSQL：保存最多 8 条的结构化线程摘要，业务画像和记录仍是唯一事实源；
- 自研评测器 + Pytest：直接检查计划 Schema、工具序列、确认 Policy、步骤上限与降级；
- Allure Pytest：生成可浏览的测试执行证据；JUnit 和 Coverage 继续作为通用 CI 产物。

没有为了简历形式加入 Python `requests`：FastAPI 同进程 API 测试继续使用基于 HTTPX 的
TestClient，数据库和依赖覆盖更稳定；Playwright 负责真实浏览器网络闭环。若未来增加独立
公网 API 黑盒巡检，再单独采用 HTTPX/Requests 均可，不能把“用了某个库”当作测试体系完整。

真实 DeepSeek 门禁验证了框架之外的模型行为：Planner `2.0.0` 首轮工具序列准确率 0、Policy
合法率 75%，暴露过度规划；基于失败样本冻结最小工具配方并将 Prompt 升至 `2.0.1` 后，
8 个任务的工具序列和 Policy 均为 100%，16 次模型调用无 fallback，p95 3112 ms、费用
`$0.00257824`。这证明 Agent 的价值来自“规划—受控执行—校验—量化反馈”，不是把一次
LLM 响应改名为 Agent。

仍不建议引入 CrewAI/AutoGen 式多角色聊天、独立 LiteLLM Proxy、LangSmith/Langfuse/
Phoenix 全家桶或模型直连数据库。当前单 Agent 架构已经满足可解释、可切换、可测试和本机
交付目标；只有出现团队协作、独立扩缩容或更复杂长任务的实证需求才重新评估。

## 15. 阶段 11 Agent v3 技术结论（2026-08-04）

阶段 11 沿用 LangGraph/LangChain/LiteLLM，没有换框架或引入第二个编排服务。新增能力的职责
边界是：LangChain/LiteLLM 产生结构化 Planner/Replanner 决策，LangGraph 承载暂停与恢复，
Pydantic/Policy Guard 决定计划是否合法，自研工具注册表执行真实业务工具，PostgreSQL 保存
脱敏 checkpoint。模型不能直接写数据库、选择未注册工具或自动改投另一供应商。

Agent 性成立于可观察闭环，而不是模型调用次数：执行结果先标准化为 Observation，Verifier
决定完成、等待、重规划、澄清、降级或停止；只有可恢复错误才允许最多 2 次 Replanner，且
模型选择仍被允许替代工具集合和 Policy Guard 双重约束。当前高价值替代只保留知识安全摘要和
规则建议，避免为展示制造不必要工具或多 Agent。

测试采用分层组合：HTTPX/TestClient 继续负责快速白盒 API/数据库注入，Requests + Pytest +
Allure 负责真实 Docker TCP 边界，Playwright 负责用户端闭环，自研评测器负责 Agent/RAG 的
量化语义门禁。Requests 是补充的网络黑盒层，不取代现有测试；Allure 只增强报告，JUnit、
Coverage 和 JSON 门禁仍是可移植事实源。
