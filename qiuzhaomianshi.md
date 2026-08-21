# Journey 秋招面试问题与项目案例

> 初版日期：2026-08-10
>
> 使用方式：每个案例都按“当前项目中遇到什么情况 → 通过什么方式解决 → 结果与证据 →
> 不能夸大的边界”组织。面试时先讲结论，再根据追问展开技术细节。本文不替代
> `docs/EXECUTION_LOG.md`；数字变化时以最新实际测试结果同步更新。

## 一、Agent 开发岗位

### 1. 面试问题：这个项目为什么可以叫 Agent，而不只是调用一次大模型？

**日期：2026-08-03—2026-08-04**

- 当前项目中遇到的情况：阶段 6 的意图路由和推荐流程虽然能工作，但主要依赖固定 DAG，缺少
  显式计划、统一工具策略、执行结果校验，以及工具失败后的可解释恢复。
- 通过的解决方式：将架构重构为单 Agent 的 Planner → Policy Guard → Executor →
  Observation → Verifier → Replanner；工具只能来自类型化白名单，单次最多 6 步、最多 2 次
  重规划，写操作必须暂停等待用户确认，恢复时重新读取最新业务事实。
- 结果与证据：阶段 11 的 4/4 checkpoint 计划、2/2 故障恢复选择和 Provider/Schema 门禁均为
  100%；10 次真实 DeepSeek 调用费用 `$0.00171864`。Mock、网络黑盒和移动端恢复流程均通过。
- 面试边界：它是“有界、可解释、有人类检查点的单 Agent”，不是多 Agent 自由讨论，也不是
  可以无限自主循环的通用智能体。
- 证据：`backend/app/agent/execution_graph.py`、`backend/app/agent/tool_registry.py`、
  `docs/ARCHITECTURE_DECISIONS.md` 的 ADR-034/035、`docs/EXECUTION_LOG.md` 阶段 10/11。

### 2. 面试问题：模型把“查询体重”误判成“写入体重”时，你如何修复？

**日期：2026-08-01**

- 当前项目中遇到的情况：真实 DeepSeek 文字门禁首轮把“查询我的体重”误路由为写体重，路由
  准确率为 17/18（94.44%），没有达到预设门槛，而且写入类误判风险高于普通回答错误。
- 通过的解决方式：保留失败样本并定位到 Router Prompt 的读写边界表达不足；把“读取画像/历史”
  与“生成写入候选”拆成明确规则，升级 Prompt 到 `intent-router-1.0.1`，继续保持确认后写入。
- 结果与证据：修正后同一固定文字门禁 28/28 通过，查询只返回画像结果、候选数为 0，没有用
  降低阈值掩盖问题。
- 面试边界：这是固定数据集上的发布门禁结果，不代表所有自然语言表达都达到 100%。
- 证据：`evals/`、`docs/EXECUTION_LOG.md` 的 2026-08-01 记录、ADR-033/034。

### 3. 面试问题：如何在 DeepSeek、Qwen、GLM、Kimi 之间切换，又避免业务代码绑定供应商？

**日期：2026-07-22**

- 当前项目中遇到的情况：最初模型调用与 DeepSeek 配置耦合，用户希望未来新增供应商时不重写
  Agent；同时不同模型的 function calling、JSON 输出和 thinking mode 并不完全一致。
- 通过的解决方式：采用 LangChain/LangGraph 承载 Agent 流程，LiteLLM Router 管理 Provider
  Profile、模型能力映射、重试、超时、预算和成本；每个供应商使用独立 Key 变量，结构化结果
  统一经过 Pydantic Schema 校验，Mock 也作为正式 Provider Profile。
- 结果与证据：DeepSeek Flash/Pro 已完成能力分流和真实合成 smoke；Qwen、GLM、Kimi、OpenAI
  Compatible 已建立配置与契约路径，普通 CI 固定 Mock、空 Key、费用 0。
- 面试边界：建立 Provider Profile 不等于所有供应商都完成真实质量验收；当前真实文字门禁主要
  是 DeepSeek，Qwen 图片质量仍为 No-Go。
- 证据：`backend/app/agent/model_router.py`、`backend/app/agent/provider_profiles.py`、
  ADR-028/029、`docs/EXECUTION_LOG.md` 2026-07-22 记录。

### 4. 面试问题：每次可能调用不同模型，用户记忆怎么保持一致？

**日期：2026-08-03—2026-08-05**

- 当前项目中遇到的情况：如果依赖某个供应商的会话记忆，切换模型后上下文会丢失，也难以审计
  哪些内容是用户事实、哪些只是模型推测。
- 通过的解决方式：把用户画像、目标、记录和 Journey 放在 PostgreSQL 业务表作为事实源；Agent
  线程只保存脱敏、最小结构化状态和 checkpoint，不保存原始提示词、完整 RAG 片段或模型私有
  会话；执行和 resume 时通过工具重新读取最新事实。
- 结果与证据：组合“记录 + 建议”会先暂停，用户确认写入后再恢复并读取更新数据；跨供应商不
  依赖隐藏会话状态，线程与用户隔离测试通过。
- 面试边界：当前没有自动学习长期人格偏好，也没有把所有聊天全文做成向量记忆。
- 证据：`backend/app/services/agent.py`、`backend/app/models/agent.py`、ADR-034/035。

### 5. 面试问题：工具失败后 Agent 如何决定重试、换工具还是停止？

**日期：2026-08-04**

- 当前项目中遇到的情况：早期失败处理只是裁剪依赖节点，不能说明“发生了什么、是否可恢复、
  为什么选择替代工具”，容易把重试写成不可控循环。
- 通过的解决方式：Executor 将失败转为结构化 Observation，记录错误类型、可恢复性和允许的
  替代工具；Verifier 决定 done/wait/replan/clarify/fallback/stop，Replanner 只能从预注册替代
  工具中选择，并受 2 次上限和预算约束。
- 结果与证据：两类故障恢复选择 2/2 通过；不可恢复错误会澄清或停止，不跨供应商暗中转发，
  不绕过人工确认。
- 面试边界：这是业务工作流的有界恢复，不是让模型任意编写新工具或执行代码。
- 证据：`backend/app/agent/execution_graph.py`、`evals/run_agent_v3_provider_acceptance.py`、ADR-035。

### 6. 面试问题：为什么生活灵感没有直接做成 Agent 浏览器工具？

**日期：2026-08-09—2026-08-10**

- 当前项目中遇到的情况：用户希望 Agent 获取小红书的年轻生活信息，但当前工具白名单和公开
  平台能力都不足以支持稳定、合规的消费者笔记搜索；直接给 Agent 浏览器会扩大 SSRF、登录态、
  Prompt Injection、版权和健康错误引用风险。
- 通过的解决方式：把需求降维成用户主动分享的独立生活灵感收藏；后端只做白名单元数据预览，
  用户确认后保存，并固定 `inspiration_only`；不把该数据注册为 Agent Tool 或 RAG 文档。
- 结果与证据：后台自动抓取、Cookie 使用、Agent 自动调用和进入健康事实层均为 0；安全/API
  专项 6/6、移动流程 4/4，全量后端 93/93、移动 Jest 45/45。
- 面试边界：这是有意识的权限收敛，不是 Agent 技术做不到；未来通用 Web Research 需要新 ADR
  和新的安全/平台评审，不能从本能力自动升级。
- 证据：ADR-037、`backend/app/services/inspirations.py`、`backend/app/agent/tool_registry.py`。

## 二、测试开发岗位

### 1. 面试问题：为什么同时使用 HTTPX/TestClient 和 Requests + Pytest + Allure？

**日期：2026-08-04**

- 当前项目中遇到的情况：TestClient 适合快速覆盖服务内部契约，但不能完全代表 Docker 网络、
  端口、启动和真实 HTTP 行为；第一次网络黑盒还误连主 API，读取了本机真实 Provider 配置。
- 通过的解决方式：保留 TestClient 白盒集成层，新增独立 `blackbox-api + test-db` Compose；
  Requests 从容器外按真实 HTTP 完成注册、Agent Run、确认、Resume、Trace 和错误码校验，环境
  强制 Mock、空真实 Key、零预算，并输出 Allure/JUnit。
- 结果与证据：独立 Requests 网络黑盒 1/1 通过；不再访问主 API，不产生真实模型调用。
- 面试边界：1 条黑盒是核心链路门禁，不等于覆盖所有业务分支；细分异常仍由白盒测试承担。
- 证据：`backend/blackbox_tests/`、`compose.yaml`、`.github/workflows/ci.yml`、ADR-035。

### 2. 面试问题：如何让 Agent 测试不是“看起来回答不错”？

**日期：2026-07-20—2026-08-05**

- 当前项目中遇到的情况：生成式结果具有随机性，仅做人工体验无法稳定判断路由、工具、Schema、
  引用、延迟和成本是否回归。
- 通过的解决方式：版本化 Prompt、Schema、知识库与评测集；把意图准确率、工具选择、参数、
  引用、无答案、降级、Token、延迟和费用拆成量化指标；普通 CI 使用确定性 Mock。
- 结果与证据：截至 ADR-037 验收为 93 条后端/评测测试、90.72% 覆盖率、362 条样本和 26 项
  门禁全部通过，报告同时提供 JUnit、Coverage、Allure 和 Agent JSON。
- 面试边界：Mock 证明工程契约与回归稳定性，不能替代真实模型质量门禁。
- 证据：`evals/datasets/`、`evals/run_evals.py`、`reports/`、`.github/workflows/ci.yml`。

### 3. 面试问题：离线同步如何测试不重复写入、不静默覆盖？

**日期：2026-08-05**

- 当前项目中遇到的情况：离线新增容易因重试产生重复记录，多设备编辑可能后写覆盖先写，退出
  后的异步任务还可能把旧账户数据重新写回缓存。
- 通过的解决方式：客户端使用 Outbox、幂等键和连续动作合并；服务端为五类资源增加 `version`
  与 `If-Match-Version`，过期写入返回 409 和服务端快照；移动端让用户逐字段选择本机或云端；
  退出/切号使用 epoch 使在途任务失效并清除副本、密钥和缓存。
- 结果与证据：新增账户隔离、离线 CRUD、幂等重试、404 收敛和 409 冲突测试；最终移动端
  41/41 + 逻辑 5/5，后端 87/87，通过双模拟器 Debug 运行。
- 面试边界：1000 条故障注入、公网多设备和真实设备密钥取证仍是生产加固项。
- 证据：`apps/mobile/src/providers/sync-provider.tsx`、`apps/mobile/src/lib/local-replica.ts`、
  `backend/tests/test_sync_conflicts.py`、ADR-036。

### 4. 面试问题：E2E 失败时如何判断是产品回归还是测试脚本过期？

**日期：2026-08-03—2026-08-04**

- 当前项目中遇到的情况：首页组件拆分和 Agent 状态文案升级后，Playwright/Jest 仍匹配旧文件
  与旧“校验通过”文案，导致实现正确但测试失败；同时不能简单删除断言让流水线变绿。
- 通过的解决方式：先用失败截图和 DOM 确认真实页面状态，再把断言迁移到实际组件和新的用户
  可见状态，保持候选确认、结果更新和首屏布局标准，不降低覆盖率门槛。
- 结果与证据：Web 核心 E2E 恢复 2/2；首页 Jest 纳入新组件后 33/33，随后 local-first 扩展至
  41/41。
- 面试边界：只修改与已确认产品行为不一致的测试，不把真实回归归因于“脚本问题”。
- 证据：`apps/mobile/e2e/core-flow.spec.ts`、`apps/mobile/tests/`、执行日志阶段 10/12。

### 5. 面试问题：模型评测失败后为什么不能反复跑到通过？

**日期：2026-07-29—2026-07-31**

- 当前项目中遇到的情况：食物图片 Demo 可以返回结果，但照片估重和中国家庭餐识别是否可靠
  没有证据；如果看完结果再改规则或反复重跑，会污染密封集并产生选择性汇报。
- 通过的解决方式：先固定隐私边界、指标、唯一运行次数和 No-Go 条件，再建立授权、哈希密封、
  零重叠 holdout；失败后只分析，不在同一集合上调参重跑。
- 结果与证据：识别型门禁总体 Top-3 37/55（67.27%）、中国家庭餐 12/20（60%）、Schema
  59/60，低于阈值，因此正式图片能力保持 Closed / No-Go。
- 面试边界：No-Go 是质量决策，不表示 API 不可调用，也不表示未来新模型永远不能重启新评测。
- 证据：`evals/food_image_recognition_holdout/`、ADR-030/031、阶段 9 评测报告。

## 三、AI 产品经理岗位

### 1. 面试问题：用户说 UI 太暗、太复古时，你如何把主观反馈变成可验收需求？

**日期：2026-08-04**

- 当前项目中遇到的情况：第一轮 A/B 稿偏暗偏灰，重画叶子吉祥物也不符合原项目气质；仅说
  “再好看一点”无法指导开发和验收。
- 通过的解决方式：明确否决原因并保留决策记录，复用原版角色，确定“暖白 + 明亮薄荷”方案 C；
  把首屏输入位置、320/390 pt 不截断、点击目标、卡片层级和在线/离线文案写成量化标准。
- 结果与证据：320 × 844 和 390 × 844 视觉核对通过；标题孤行、指标截断都通过真实截图迭代
  修复，Web/iOS/Android export 通过。
- 面试边界：完成的是首页与主题基线，不等于整套产品已做 5 人可用性盲测。
- 证据：`docs/product/LOCAL_FIRST_AI_UI_PROPOSAL.md`、`home-overview.tsx`、ADR-036。

### 2. 面试问题：为什么把“离线时 Agent 全不可用”改成 local-first？

**日期：2026-08-04—2026-08-05**

- 当前项目中遇到的情况：离线状态一刀切会让用户连画像和历史都看不到，与健康记录产品的连续
  使用预期不符；但把模型下放本机又超出当前成本和工程范围。
- 通过的解决方式：把能力拆成“个人数据本地可读写、Agent 联网可用、内置常识离线可用”；
  原生端按账户加密保存 90 天副本，Outbox 联网同步，Web 明确只做进程内副本。
- 结果与证据：ADR-036 Accepted，离线画像/目标/记录 CRUD、冲突选择和退出清理通过自动化与
  双模拟器验收。
- 面试边界：没有离线大模型；Agent 无网仍不可用，Web 刷新后也不承诺本地持久化。
- 证据：ADR-036、`local-replica.ts`、`sync-provider.tsx`。

### 3. 面试问题：如何用失败结果做 Go/No-Go 产品决策？

**日期：2026-07-31**

- 当前项目中遇到的情况：食物拍照估算很适合演示，但真实指标未达到可向用户承诺的准确性，
  继续包装为正式功能会制造错误热量和信任风险。
- 通过的解决方式：把“技术可调用”“识别候选”“自动估重”“正式发布”拆成不同门槛；保留
  Development 实验入口和用户校正回退，但 Preview/Production/staging 关闭真实图片识别。
- 结果与证据：根据预注册阈值作出 Closed / No-Go，并记录重启条件：新 ADR、新模型、全新密封
  集和预先修正的评分规则。
- 面试边界：不能把 Schema 98.33% 说成识别准确率 98.33%；核心 Top-3 只有 67.27%。
- 证据：ADR-031、`STAGE9_FOOD_IMAGE_EVALUATION_REPORT.md`。

### 4. 面试问题：年轻生活内容为什么不直接绑定小红书账号？

**日期：2026-08-09—2026-08-10**

- 当前项目中遇到的情况：用户希望获得更年轻、多元的生活信息，但公开平台能力没有证明存在
  可任意搜索消费者笔记的 API；账号绑定、Cookie 或后台抓取会引入隐私、版权和平台风险。
- 通过的解决方式：选择“用户逐次主动分享公开链接”最小闭环；只允许官方域名 HTTPS，逐跳
  做 DNS/重定向/SSRF 校验，无 Cookie、超时和 256 KB 上限，只提取标题与 500 字短摘要；无法
  读取就手动填写，保存前显式确认，固定标记 `inspiration_only`。
- 结果与证据：新增 6 条后端安全/API 测试和 4 条移动流程测试；生活灵感与 Agent/RAG、健康
  事实完全隔离，后台自动抓取次数为 0。
- 面试边界：这不是“小红书账号绑定”，也不是通用 Web Research 或推荐流抓取；production
  默认关闭自动预览，可回退为手动标题/摘要。
- 证据：ADR-037、`backend/app/services/inspirations.py`、`apps/mobile/src/app/inspirations.tsx`。

## 四、售前 / 解决方案岗位

### 1. 面试问题：如何向客户说明“可部署”与“已上线”的区别？

**日期：2026-08-05**

- 当前项目中遇到的情况：已完成单服务器 production Compose，但本机 Docker Hub token 网络
  超时阻塞 Node/Nginx/Caddy 镜像拉取，也没有真实服务器、域名和证书。
- 通过的解决方式：分别验证 API/PostgreSQL、Web export 和 Caddyfile，保留服务器上线清单与
  回退方案；文档统一写“可部署配置 / Conditional”，不把局部验证说成四容器公网整栈成功。
- 结果与证据：PostgreSQL/API 不暴露宿主端口，Caddy 是唯一 80/443 入口；真实公网 HTTPS、
  外部备份恢复仍列为待验收。
- 面试边界：源码已备份到私有仓库不等于公网发布，模拟器安装也不等于 App Store 上架。
- 证据：`compose.production.yaml`、`docs/deployment/SERVER_DOCKER.md`、ADR-038。

### 2. 面试问题：为什么没有为了“先进”拆成微服务？

**日期：2026-07-15—2026-07-20**

- 当前项目中遇到的情况：项目要同时展示客户端、Agent、RAG、测试和交付，如果过早拆微服务，
  会增加部署、链路追踪、事务和面试解释成本，却没有相应业务规模收益。
- 通过的解决方式：采用 FastAPI 模块化单体，按身份、记录、Agent、知识库和服务层划分边界；
  PostgreSQL、API、Web、网关通过 Compose 编排，未来有明确瓶颈再拆。
- 结果与证据：同一后端支撑三端、Agent 与 RAG，自动化门禁可在单条 CI 链路完成，适合个人
  项目和单服务器部署。
- 面试边界：模块化单体不是没有架构；当前结论服务于本项目规模，不主张所有企业系统都不应
  使用微服务。
- 证据：ADR-004、项目目录、`compose*.yaml`。

### 3. 面试问题：如何给不同客户或岗位演示同一个项目？

**日期：2026-07-31—2026-08-05**

- 当前项目中遇到的情况：开发岗关心架构和代码，测试开发关心门禁，产品岗关心指标决策，售前
  关心部署边界；只演示页面不能证明交付能力。
- 通过的解决方式：建立 3—5 分钟主流程和分岗位讲述：模拟器演示记录—确认—Journey—建议；
  同时准备架构图、Allure/JUnit/Coverage、Agent 轨迹、No-Go 报告、Docker 部署与故障预案。
- 结果与证据：iOS/Android Debug 当前可运行，Web 有 2 条核心 E2E 和 14 条静态路由；四类岗位
  材料已进入仓库。
- 面试边界：演示环境主要是本机，不声称商店发布或生产 SLA。
- 证据：`docs/demo/INTERVIEW_DEMO.md`、`docs/demo/RESUME_AND_INTERVIEW.md`。

### 4. 面试问题：怎样控制 AI 项目的费用和数据风险？

**日期：2026-07-20—2026-08-04**

- 当前项目中遇到的情况：真实模型便于展示，但 CI、开发误调用和多供应商切换可能产生费用，
  健康画像也不应无边界转发。
- 通过的解决方式：普通 CI 强制 Mock、空 Key、零预算；真实 Provider 只有明确执行开关、固定
  小数据集、正预算和价格配置才能运行；客户端从不保存模型 Key，Agent 日志脱敏并统计 Token、
  延迟和费用。
- 结果与证据：普通 CI 外部调用和费用为 0；真实 Agent v3 门禁 10 次调用总费用
  `$0.00171864`，报告不包含 Key 或原始用户消息。
- 面试边界：当前是工程预算门禁，不是成熟企业 FinOps 平台；供应商数据政策仍需上线前复核。
- 证据：`backend/app/core/settings.py`、Provider acceptance 报告、ADR-029/035。

## 五、客户端 / 全栈开发岗位

### 1. 面试问题：如何从微信小程序迁移到 iOS、Android 和 Web，又不维护三套前端？

**日期：2026-07-15—2026-07-17**

- 当前项目中遇到的情况：旧端严重依赖 Taro/微信登录和小程序 API，但页面结构、品牌资产和业务
  流程仍有价值；直接套 WebView 或一次性重写都存在维护和 UI 丢失风险。
- 通过的解决方式：保留原版角色与业务规则，退役微信专属代码，在同仓库建立 Expo Development
  Build + React Native Web；用共享 contracts/design tokens 连接 FastAPI `/api/v1`。
- 结果与证据：首页、Journey、我的三入口在 iOS/Android 模拟器运行，Web 作为补充构建；业务
  API 与 Agent/RAG 三端共享。
- 面试边界：React/Taro 的业务思想和资产得到复用，不是原组件零成本直接运行在 React Native。
- 证据：阶段 1—5 计划与日志、`apps/mobile/`、`packages/`。

### 2. 面试问题：本地健康数据怎样做到按账户隔离和退出清理？

**日期：2026-08-05**

- 当前项目中遇到的情况：只用 AsyncStorage 明文保存画像和记录不满足隐私边界；切换账号或
  退出时，还要防止网络请求完成后把旧数据重新写回。
- 通过的解决方式：原生端用 SecureStore 保存每账户密钥，AES-256-GCM 保存副本、Outbox 和
  冲突；Key、AAD 和存储 namespace 都绑定用户；退出增加 epoch 失效机制并清除密文、旧队列、
  查询缓存和密钥。Web 只保留内存副本。
- 结果与证据：双账户不可互读、退出清理和在途任务失效测试通过，iOS/Android Debug 实际链接
  `expo-crypto` 与 `expo-secure-store`。
- 面试边界：尚未完成真实设备取证、越狱/Root 威胁验证和硬件级合规认证。
- 证据：`local-replica.ts`、`auth-provider.tsx`、`sync-provider.test.tsx`、ADR-036。

### 3. 面试问题：如何保证前后端契约和数据库迁移一致？

**日期：2026-07-17—2026-08-10**

- 当前项目中遇到的情况：移动端、FastAPI Schema 和 PostgreSQL 字段分别修改时容易漂移，离线
  同步又增加 `version`、冲突快照和新资源。
- 通过的解决方式：FastAPI OpenAPI 作为接口事实源，导出到后端快照和 `packages/contracts`；
  客户端使用 TypeScript 契约；数据库变更只通过可逆 Alembic migration，并执行
  upgrade → downgrade → upgrade 和 `alembic check`。
- 结果与证据：当前迁移从 `0001` 演进至 `0007_life_inspirations`；类型检查、OpenAPI 快照和
  API 测试共同阻止契约静默漂移。
- 面试边界：当前 TypeScript 类型仍由仓库维护并与 OpenAPI 对照，不是完整自动代码生成平台。
- 证据：`backend/scripts/export_openapi.py`、`packages/contracts/`、`backend/alembic/versions/`。

## 六、2026-08-10 Demo 封板新增案例

### Agent 开发岗位：如何证明 Multi-Agent 不是简单改名？

**日期：2026-08-10**

- 当前项目中遇到的情况：既有 Agent v3 有计划、工具和恢复闭环，但所有能力都以一个 Agent
  名义出现；如果只把工具文件改成多个 Agent 名称，无法证明职责隔离或协作价值。
- 通过的解决方式：保留同一 Run State，以 Orchestrator 负责路由/拆分/汇总，Record、Health
  Knowledge、Journey Summary 三个 Specialist 各有明确工具 allowlist；Policy 拒绝角色/工具
  不匹配，记录只生成候选，确认后才写库。前端展示结构化角色、工具、候选数、检索文档、范围和
  时延，不展示思维链。
- 量化结果与证据：精确复合输入的真实 DeepSeek Requests 黑盒 1/1、28.02 秒；Mock 黑盒 2/2、
  Web E2E 2/2；数据库同时出现食物和运动记录，周总结只在两个候选确认后执行。
- 面试陈述边界：这是有界 Orchestrator + Specialist 协作，不是多个自治模型群聊，也没有无限
  自主循环或未经确认写库。
- 证据：`backend/app/agent/specialists.py`、`docs/architecture/MULTI_AGENT_DATA_FLOW.md`、ADR-039。

### Agent / RAG 开发岗位：如何用实验回答“你的 RAG 好不好”？

**日期：2026-08-10**

- 当前项目中遇到的情况：旧评测主要看 Recall@3 和引用支持，无法判断正确文档排第几、无答案时
  是否拒答，也不能比较不同 top-k/rerank 配置。
- 通过的解决方式：冻结 60 题 Dataset 和知识 bundle hash，分 Retrieval/Generation 两层评估
  Recall@1/3/5、MRR、nDCG、Groundedness、Relevance、Citation、Abstention、时延、Token 和
  成本；同一数据比较 rag-v1 与 rag-v2，Mock Generation 强制标记 `SKIPPED_REAL_MODEL`。
- 量化结果与证据：v2 Recall@3/5 1.0、MRR 0.9625；真实 DeepSeek Groundedness/Relevance
  0.9625、Citation 0.9083、Abstention 1.0，41 次模型调用、费用 `$0.00624232`。
- 面试陈述边界：知识库只有四份项目文档，scorer 是固定 reference-point 规则，不是医学专家
  认证；Citation 0.9083 仍有改进空间。
- 证据：`evals/datasets/rag_eval_v1.json`、`evals/run_rag_eval.py`、RAG Eval 报告。

### 测试开发岗位：真实模型不稳定时怎样区分产品失败和测试失败？

**日期：2026-08-10**

- 当前项目中遇到的情况：真实 E2E 首次业务已完成，但 Requests 客户端 15 秒先超时；另一轮因
  “过去的7天”与“过去7天”文案差异失败；又一轮确实发生 Provider `model_timeout` 降级。
- 通过的解决方式：分别检查数据库 Run/Tool Trace，不放宽业务核心断言；把客户端 timeout
  配置化，Mock/CI 保持 15 秒、真实验收 75 秒；文案改为语义等价断言；根据真实成功工具耗时
  24.3 秒把模型超时调到 30 秒，仍保留一次重试和降级。
- 量化结果与证据：最终真实复合黑盒 1/1、28.02 秒，Mock 2/2、0.50 秒；全量 100 测试、
  覆盖率 90.60%。失败尝试和降级 Run 未删除。
- 面试陈述边界：30 秒是当前 Demo 观测后的配置，不是生产 SLA；外部 Provider 仍可能波动。
- 证据：`backend/blackbox_tests/test_agent_blackbox.py`、Agent Tool Trace、`EXECUTION_LOG.md`。

### AI 产品岗位：评测失败后怎样做产品决策，而不是只调 Prompt？

**日期：2026-08-10**

- 当前项目中遇到的情况：第一份真实 RAG 报告 Retrieval 很高，但 Abstention Accuracy 只有
  0.6833；知识库无答案时继续调用模型既增加幻觉风险，也浪费成本。
- 通过的解决方式：把“不足 Context”提升为工作流控制状态，在 Retrieval 层直接返回
  `insufficient_context`，不把问题交给模型硬答；同时修正版本化拒答 scorer，并生成新报告而不
  覆盖失败报告。
- 量化结果与证据：Abstention 从 0.6833 提升到 1.0，真实调用从 60 降到 41，19 次由确定性
  控制流拒答；最终费用 `$0.00624232`。
- 面试陈述边界：这是固定 60 题上的改善，不能外推成所有健康问题都安全；高风险医疗仍不回答。
- 证据：`backend/app/agent/workflows.py`、两份真实 RAG 报告、ADR-039。

### 售前 / 解决方案岗位：如何让 Demo 与客户现有 Docker 项目共存？

**日期：2026-08-10**

- 当前项目中遇到的情况：本机另一个 `mall` Compose Project 已占用 PostgreSQL Host Port 5432，
  直接启动 Journey 会冲突，停止对方项目又不符合交付边界。
- 通过的解决方式：容器内部仍使用标准 `db:5432`，Journey Host Port 改为可配置 55432；preflight
  在启动前报告端口归属、Compose Project、REAL/MOCK、环境文件、迁移和健康状态，只操作
  Journey namespace，不执行全局 prune。
- 量化结果与证据：`docker compose down → demo_up.sh` 后 API/DB healthy，live/ready 200，RAG
  ok、REAL DeepSeek、Alembic `0007`；`mall` 未被停止或修改。
- 面试陈述边界：当前是一台开发机的可复现 Demo，不代表公网高可用、灾备或生产 SLA。
- 证据：`infra/demo/preflight.py`、`infra/demo/demo_up.sh`、`compose.yaml`。

## Agent 开发岗位：真实 Run 已完成，为什么 App 仍提示继续执行失败？

**日期：2026-08-13**

- 当前项目中遇到的情况：真实复合 Agent 的两个候选已写入、Summary/RAG 已完成，但移动端先提示
  网络不可用，随后残留“继续执行”；再次确认又触发 Idempotency-Key 不同 Payload 冲突。
- 通过的解决方式：用 PostgreSQL Run/Confirmation 与结构化 Trace 对账，确认问题是移动端统一
  10 秒超时，而真实工具链约 20—25 秒；普通 API 继续 10 秒，Agent Run/Resume 改为 120 秒，
  不降低服务端 30 秒/次、1 次重试和降级。确认/Resume 响应不确定时读取本人 Run Trace，完成则
  清理过期状态；幂等保护继续阻止重复写入。
- 量化结果与证据：问题 Run completed/consumed、确认 2/2；修复后真实 DeepSeek v4 Pro 周总结
  HTTP 200，端到端 20,434 ms，3 条引用，fallback=false；iOS Simulator 内再次点击“生成”，
  约 27 秒出现总结和 3 条依据，无“网络不可用”。
- 面试陈述边界：120 秒是客户端等待窗口，不是生产 SLA；没有实现后台任务队列或任意无限等待。

## AI 产品岗位：为什么“摄入减运动”不能直接叫净热量结余？

**日期：2026-08-13**

- 当前项目中遇到的情况：旧 `net_kcal` 只等于摄入减已记录运动，却在 Home/Journey 显示“净结余”，
  用户正确指出没有基础代谢，指标会让人误以为是全天真实能量平衡。
- 通过的解决方式：保留兼容字段但产品文案改成“记录差值”；基于完整画像增加 Mifflin–St Jeor
  静息能量预测，并单独返回记录口径估算余量。资料不完整、性别系数不适用或超出原始样本年龄时
  明确不估算；UI/Agent 明示不含全部日常活动与食物热效应、不等于 TDEE。
- 量化结果与证据：测试账号返回摄入 600、运动 300、记录差值 300、静息估算 1,591.5 kcal/天、
  记录口径余量 −1,291.5；Docker 全量 100/100，移动 48/48+5。
- 面试陈述边界：这是健康成人预测公式，不是间接测热或医疗建议；漏记会造成估算偏差。

## 测试开发岗位：怎样证明是客户端超时，而不是模型或 RAG 坏了？

**日期：2026-08-13**

- 当前项目中遇到的情况：UI 报“网络不可用”，单看截图会误判外部模型、Docker 网络或 RAG 故障。
- 通过的解决方式：分层检查 HTTP 客户端阈值、数据库 Run 状态、Confirmation 幂等记录、工具
  latency 与 `/health/ready`；新增 Run Trace confirmation progress、客户端状态恢复测试和静息
  估算服务端/离线双口径测试；保留失败测试证据后修正。
- 量化结果与证据：定向后端 17/17；全量 100/100、覆盖率 90.69%；移动 Jest 48/48、逻辑 5/5；
  REAL 周总结 20.4 秒，而旧客户端阈值仅 10 秒。
- 面试陈述边界：本轮没有重跑完整真机 E2E 自动化或宣称公网 SLA；实际 Docker API 与真实模型
  smoke 已通过。

## 售前 / AI 产品 / 测试开发岗位：如何让不同岗位复用同一项目素材又不夸大？

**日期：2026-08-13**

- 当前项目中遇到的情况：Journey 已积累 Agent、RAG、测试、Docker、产品决策和真实失败报告，
  但既有材料分散在代码、ADR、执行日志与多份报告中；直接让简历工具自由总结，容易把 Mock 写成
  真实质量、把 production Compose 写成已上线，或把图片 No-Go 写成正式能力。
- 通过的解决方式：基于当前代码和报告建立跨岗位素材知识库，使用 `IMPLEMENTED`、
  `REAL-VALIDATED`、`MOCK-VALIDATED`、`EXPERIMENTAL/NO-GO`、`CONDITIONAL`、`FUTURE`
  状态标签；为技术、指标和问题案例配置素材编号与相对证据路径，并按 Agent 开发、测试开发、
  运维、售前、产品和 AI 产品给出不同取材主线与禁用陈述。
- 量化结果与证据：知识库统一引用当前 25 个 OpenAPI Path/34 个 Operation、后端 100/100 与
  90.69% 覆盖率、362 条 Agent 样本/26 门禁、60 题 RAG Eval、真实复合黑盒 1/1 和图片
  Top-3 67.27% No-Go 等可核验事实；并提供 14 个“情况—解决—结果—边界”案例。
- 面试陈述边界：知识库是 2026-08-13 快照，不代替实时仓库审计；另一个 Codex 必须结合 JD
  选择素材，不能自行生成用户量、商业收益、生产 SLA 或未实现功能。
- 证据：`docs/demo/JOURNEY_CAREER_MATERIAL_KNOWLEDGE_BASE.md`、`docs/README.md`、当前代码与
  `reports/`/`evals/reports/`。

## 运维 / 测试开发 / 售前岗位：如何把含真实 Provider 配置和旧历史的 AI 项目安全公开为作品集？

**日期：2026-08-21**

- 当前项目中遇到的情况：Journey 本机 `.env` 配置过真实模型，旧迁移历史还包含非公开邮箱元数据，
  而公开仓库既要展示完整工程能力，又不能泄露密钥、原始评测图片、报告生成物或把“可部署”包装成
  “已上线”。首次云端 CI 还连续暴露了 Ruff、Python 模块路径和测试依赖本机环境三类问题。
- 通过的解决方式：发布前分别扫描工作树和完整 Git blob，确认 `.env`/报告/构建产物均被忽略；
  使用已审计树创建无旧提交元数据的公开干净快照，同时保留私有迁移备份。云端 CI 固定 Mock、空
  API Key、零预算；保留失败 run，逐项修复格式、`PYTHONPATH` 和测试环境隔离，不绕过门禁。
- 量化结果与证据：高置信密钥/Token/私钥命中 0，最大待发布文件约 799 KB；本地 Docker 后端
  100/100、覆盖率 90.69%，Requests + Pytest + Allure 2/2，移动 48/48+5，Web E2E 2/2；
  GitHub Actions run `32452754248` 的 backend/mobile/web-e2e 三个 job 全绿。
- 面试陈述边界：公开的是 `boom080/Journey-v0.1` 源码作品集，不是公网 Web 服务、App Store
  上架、生产高可用或真实模型质量证明；Mock CI 分数不能冒充真实 Provider Eval。
- 证据：`.gitignore`、`.github/workflows/ci.yml`、`docs/EXECUTION_LOG.md`、公开 GitHub Actions。

## 七、更新记录

| 日期 | 本次项目更新 | 面试材料变化 |
|---|---|---|
| 2026-08-21 | 将已审计 Journey 封板树以干净快照发布为 public `boom080/Journey-v0.1`；完成密钥/体积扫描并修复云端 CI 环境差异，最终三个 job 全绿 | 新增运维/测试开发/售前共用案例；可说明公开作品集的密钥防泄漏、历史隔离、Mock CI、失败留痕和环境一致性治理 |
| 2026-08-13 | 新增跨岗位 Journey 秋招素材知识库，按实际代码整理技术架构、量化指标、14 个问题解决案例、六类岗位取材和诚实边界；未修改业务代码 | 新增售前/AI 产品/测试开发共用案例；以后可按 JD 选择素材，同时阻止把 Mock、No-Go 或可部署配置包装成真实上线成果 |
| 2026-08-13 | 修复真实 Agent 客户端 10 秒超时、过期 Resume 和候选重复确认提示；新增可解释静息能量估算与记录差值口径；后端 100/100、覆盖率 90.69%，移动 48/48+5，真实周总结 20.4 秒 | 新增 Agent 开发、AI 产品、测试开发三类案例；强调用 Run/Confirmation/Trace 分层定位，以及“不把记录差值或预测 REE 冒充完整 TDEE/医学测量”的产品边界 |
| 2026-08-10 | 完成 ADR-037 用户主动分享生活灵感最小闭环；新增 URL 安全、确认保存、删除与移动端入口；全量后端 93/93、移动 45/45+5、黑盒 1/1、Mock Web E2E 2/2、Web 14 路由与三端 export 通过 | 新增并收口 Agent、测试开发、AI 产品、售前、客户端/全栈五类真实案例；重点补充生活内容合规、权限收敛与 SSRF/Prompt Injection 边界 |
| 2026-08-10 | 完成阶段 13 Demo 封板：有界 Multi-Agent、60 题 RAG Eval、真实复合 E2E、7/30 Journey、离线恢复、Docker preflight 与双模拟器运行；后端 100/100、移动 46/46+5、黑盒 Mock 2/2 + Real 1/1、Web E2E 2/2 | 新增 Agent/RAG、测试开发、AI 产品和售前五个量化案例；保留首次拒答失败、真实超时和端口冲突的解决证据，不把 Mock/本机 Demo 冒充生产质量 |
