# Journey 3—5 分钟秋招演示脚本

> 演示版本：0.1.0 / Real text + experimental image。主设备为 iOS Simulator；Android 与
> Web 是兼容性证据，Mock 是断网和确定性回归的备用路径。

## 开场前准备

运行测试账号 reset，确认 `/health/ready`、DeepSeek/Qwen 模型可用性和本次预算；预先打开
首页、真实模型验收报告、架构图和测试报告，但不要展示密钥或预填一条会被误认为已写入的
数据。无网或 Provider 异常时切换 Mock/备用录屏，并明确它只是回退。

## 0:00—0:30：一句话价值与边界

“Journey 是一个 Agent 增强的健身、营养与生活方式管理应用。用户从首页说一句话，系统识别
意图、调用确定性工具、给出结构化候选，只有用户确认后才写入；它不是医疗诊断产品。”

展示三个一级入口：首页、Journey、我的，以及从旧微信端保留的品牌角色。

## 0:30—1:10：身份与画像

使用 `demo@journey.local` 登录，进入“我的”展示目标、身高、体重与活动水平。说明邮箱或用户名
登录、测试账号隔离、Token 安全存储；不要在屏幕或讲稿展示密码。

## 1:10—2:20：统一输入、人工检查点与恢复

在首页输入：“今天中午吃了一份牛肉面，晚上跑了5公里，我这周减脂情况怎么样？”。讲解：

1. Orchestrator 识别复合意图并选择 Record、Journey Summary、Health Knowledge Specialist；
2. Planner 生成饮食/运动候选、7 天上下文、知识和周总结计划，Policy Guard 校验每个
   Specialist 的工具 allowlist 与依赖；
3. Record Agent 只生成两个候选，Run 进入 `waiting_for_user`；此时 Summary 未执行，数据库未变化；
4. 用户逐条校正并确认后幂等写入，客户端显式 Resume；Summary Agent 重新读取最新记录、目标和
   体重趋势，必要时调用 Knowledge Agent/RAG；
5. 展示 `selected_agents`、候选数、检索文档、范围、Observation、Verifier 和 `0/2` 重规划。
   可选用失败演示展示模型超时后选择规则建议，
   不可恢复错误则停止，不会无限循环或自动改投另一供应商。

主演示使用 DeepSeek `deepseek-v4-flash`；候选卡的 usage/trace 应显示真实 Provider、模型、
Token、延迟和估算费用。普通 CI 仍使用确定性 Mock，不能把 Mock 指标冒充在线模型质量。

## 2:20—2:55：首页与 Journey 联动

回到首页展示摄入、消耗、热量差和最近记录自动更新；进入 Journey 展示按日期聚合和体重趋势。
强调所有客户端共用 `/api/v1` 和 PostgreSQL，不在客户端复制业务真相。

## 2:55—3:30：建议、周报与 RAG 证据

展示自动生成的 7 天总结，再切换 Journey 的 30 天视图；打开引用和 trace：展示画像、目标、
摄入/运动/体重趋势、受控营养知识库、Prompt/
Schema/Knowledge 版本、执行节点、耗时、Token 与真实估算成本。解释无相关知识时拒绝伪造
引用；切换 Mock 回退时成本才为 0。

## 3:30—4:15：量化质量闭环

打开测试报告：362 条既有版本化样本和 26 项门禁覆盖意图、计划 Schema、工具序列、参数、确认
Policy、checkpoint、Observation 恢复、RAG、图片契约、降级、安全和时延；同时展示 100 条
后端/评测测试（覆盖率 90.60%）、Requests + Pytest + Allure Mock 黑盒 2 条、
真实复合黑盒 1 条、46 条移动组件测试、5 条逻辑测试、2 条核心 Web E2E，以及
Allure/JUnit/Coverage 并存。另展示固定 60 题 RAG Eval：v2 Recall@3/5 1.0、MRR 0.9625，
真实 Groundedness/Relevance 0.9625、Citation 0.9083、Abstention 1.0。说明阈值失败
会阻断 CI，Prompt/Schema/知识库改动必须更新版本并对比基线。随后展示 Agent v2 的失败修正
报告和 Agent v3 真实报告：DeepSeek 对 4 个 checkpoint 计划、2 个恢复选择共 10 次调用全部
通过，费用 `$0.00171864`。这是“评测发现问题 → 修改 Prompt/状态机 → 全量回归”的证据。旧文字门禁
也曾发现画像查询误路由并通过 Prompt 修正；Qwen 单张真实 API
冒烟通过，但 60 张图片质量门禁失败。强调“根据量化反馈改进”是产品工程闭环，不只是一段
LLM 调用。

## 4:15—4:45：交付与回退

展示 iOS Simulator 主路径、Android 可安装 APK、Web production build、Docker staging IaC。
可选展示一张已授权测试图片：Qwen 只生成实验性候选，保存前必须校正；不能宣称照片准确
称重。关闭网络或切换失败用例，展示 Agent 不可用但手动记录/历史不被阻断。最后打开架构图，总结：
模块化单体控制复杂度，Agent 的计划、策略、工具、人工检查点、Observation、验证、有限恢复
和线程记忆均可解释，测试与交付证据可复现。

如果面试官追问真实模型质量，主动展示食物图片 No-Go：真实密封评测未达到预注册 Top-3 和
份量误差门槛，因此正式环境关闭图片能力。这是量化决策证据，不把实验结果包装成上线能力。

## 演练验收

- 每次 3—5 分钟，不跳过“确认后写入”“真实文字模型”和“图片质量仍 No-Go”的说明。
- reset 后主演示连续成功 2 次；失败演示成功 1 次。
- 页面数据与 API/数据库一致；引用能追溯到版本化知识条目。
- 任何网络故障在 30 秒内切本地或备用录屏。
