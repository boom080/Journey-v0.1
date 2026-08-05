# Journey 真实模型验收报告

> 日期：2026-08-01
> 当前功能范围：文字 Agent + 食物图片候选
> 总体状态：**Conditional / 未达到正式发布验收**

## 验收分层

Journey 不再把 Mock 结果表述为真实模型质量。验收固定为两层：

1. Mock 工程回归：继续进入普通 CI，验证 API、Schema、工具、RAG、失败降级和客户端流程，
   保证结果稳定且不使用真实密钥；
2. 真实模型发布门禁：分别调用文字与图片所配置的 Provider，验证模型身份、结构化输出、
   fallback、Token、延迟、成本和专项质量指标。

Mock 门禁通过不等于真实模型门禁通过。任一正式能力的真实质量门禁失败时，该能力必须关闭、
降级或保持实验状态。

## 当前模型映射

| 能力 | Provider | 模型 | 当前结论 |
|---|---|---|---|
| 文字意图路由与饮食/运动解析 | DeepSeek | `deepseek-v4-flash` | 修正后真实量化门禁通过，可用于联网本机演示 |
| 食物图片候选 | Qwen 北京区域 | `qwen3.7-flash` | 真实 API 链路通过；独立质量门禁失败，只能实验性使用 |
| 普通 CI 与离线回归 | 本地 Mock | 版本化确定性模型 | 仅证明工程契约，不证明供应商质量 |

2026-08-01 通过两端 `/models` 只读探测确认所选 alias 当前可用；探测没有消耗推理 Token，
也没有输出或保存 API Key。

## 文字真实模型门禁

新增 `evals/run_text_provider_acceptance.py`，使用版本化合成数据执行 28 次真实调用：

- 意图路由：9 个意图组，每组固定选择 2 条，共 18 条；
- 饮食解析：5 条；
- 运动解析：5 条；
- 预注册门槛：路由准确率 ≥90%，饮食/运动解析 ≥80%，Provider/模型、Schema、无 fallback
  和 Token 记录均为 100%，p95 ≤8 秒，总费用 ≤`$0.02`。

结果：

| 指标 | 结果 | 门槛 | 状态 |
|---|---:|---:|---|
| 意图路由 exact accuracy | 18/18 = 100% | ≥90% | PASS |
| 饮食解析 | 5/5 = 100% | ≥80% | PASS |
| 运动解析 | 5/5 = 100% | ≥80% | PASS |
| Provider/模型匹配 | 28/28 = 100% | 100% | PASS |
| Schema 且无 fallback | 28/28 = 100% | 100% | PASS |
| Token 记录 | 28/28 = 100% | 100% | PASS |
| p95 | 1768 ms | ≤8000 ms | PASS |
| 重试 / fallback | 0 / 0 | 0 / 0 | PASS |
| 费用 | `$0.00246372` | ≤`$0.02` | PASS |

首轮 `intent-router-1.0.0` 报告虽然以 94.44% 达到 90% 门槛，但暴露了真实业务缺陷：
“我的体重是多少”被判为记录 `weight`，而不是读取 `profile`。项目没有因为总分及格而忽略
失败样本；Router Prompt 升级到 `intent-router-1.0.1`，明确“查询已有体重属于 profile，
只有提供明确体重数值并表达记录/称重才属于 weight”，随后对相同版本化集完整复验。

修正后机器报告：`REAL_TEXT_DEEPSEEK_V4_FLASH_2026_08_01_AFTER_ROUTER_FIX.json`，SHA-256：
`bffd0e625924d26552c3122fa265c297f44992d0b2c8dbd17eebbd55b24d0e32`。修正前报告继续保留，
SHA-256 为 `421f1ec717dbc34602fec46e27ee7a9259bb7f54a5686da4c2341e253f04e801`。

更新本机 API 镜像后，又通过公开 `/api/v1/agent/runs` 回归“我的体重是多少”：真实 DeepSeek
返回 `profile`、0 候选、存在画像回答、`fallback=false`，证明修正不只在离线评测器中生效。

评测器新增 3 条零外部调用测试、Router Prompt 新增 1 条回归后，完整 Compose 回归为 69/69；
后端覆盖率 91.07%，既有
318 条 Mock 样本与 17 项门禁继续全部通过。

## 真实 API 端到端冒烟

本机 Compose API 使用测试账号完成两条联网链路：

- 文字输入“午餐……然后慢跑 30 分钟”：DeepSeek 返回 `food`、`activity` 两个意图和两个
  可编辑候选，`fallback=false`；1344 input / 436 output Token，4819 ms，估算费用
  `$0.00031024`；
- 修正后画像查询“我的体重是多少”：DeepSeek 返回 `profile`、0 候选并读取画像回答，
  `fallback=false`，1401 ms，估算费用 `$0.00008918`；
- 一张 Nutrition5k CC BY 4.0 苹果测试图：Qwen 返回“苹果”候选，`is_food=true`、
  `needs_user_correction=true`、`image_retained=false`、`fallback=false`；665 input / 210 output
  Token，2259 ms，估算费用 `$0.00004181`。

该图片仅来自已授权、无个人信息的非密封测试集。单张冒烟只证明真实 API、图片外发、结构化
候选和隐私契约可运行，不替代图片质量评测。

## 图片真实质量门禁

仍以已经封存的 `STAGE9_QWEN_RECOGNITION_V2.json` 为事实源：60 张真实 Qwen 评测的总体
Top-3 为 67.27%、中国家庭餐为 60%、Schema/强制校正为 98.33%，均未达到 85%、80% 和
100% 的预注册门槛。因此：

- 不重跑、重算或改写该密封结果；
- 不因单张苹果冒烟成功就宣称图片能力验收通过；
- 图片只允许本机 Development 实验性生成候选，必须用户校正和确认；
- Preview、Production 与 staging 继续关闭真实图片能力；失败时回退手动饮食记录。

## 最终结论

- **文字真实模型：PASS。**
- **图片真实 API 功能链路：PASS。**
- **图片真实质量：FAIL。**
- **“文字 + 图片”整体正式发布验收：FAIL / Conditional。**

当前版本适合联网本机演示“真实文字模型 + 实验性图片候选”，也保留 Mock 作为 CI 和离线
回退。只有图片在新的 Proposed ADR、全新独立密封集和预注册评分规则下通过真实门禁后，
才能把“文字 + 图片”整体状态改为正式验收通过。
