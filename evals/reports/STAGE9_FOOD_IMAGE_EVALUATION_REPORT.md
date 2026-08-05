# 阶段 9 食物图片单项评测报告

> Date: 2026-07-31
> Providers: Mock + Qwen `qwen3.7-flash`
> Dataset: 100 张调参集 + 30 张无参照 holdout + 30 组内部尺度配对 + 60 张识别 holdout
> Real-vision acceptance: **FAIL — ADR-030/ADR-031 remain Proposed**

## 结论

Mock/工程基线、真实 Provider 政策复核、授权数据集和三轮 Qwen 评测均已完成。v1.2 已通过
Schema、强制校正、热量区间、非食物拒答、延迟、费用、无自动写入、隐私和零 fallback
门禁；名称 Top-3 为 84.44%（门槛 85%），单一食物份量相对误差中位数为 37.48%
（门槛 ≤30%），因此整体 `gate_passed=false`。

这不是“功能不可用”：它可作为低/中置信度、必须由用户修改确认的辅助候选，Mock 与手动
记录始终可回退。但它还不能被描述为准确的图片营养测量，也不能把 ADR-030 转为 Accepted。

## 数据与政策边界

真实集固定 100 张：Nutrition5k 单一食物 30、混合餐 30、困难餐盘 10；Open Food Facts
饮料 10、包装食品 10；Openverse 索引的开放许可非食物 10。清单逐条保存来源、作者、许可、
原始 URL、SHA-256、尺寸和金标，二进制被 Git 忽略。数据不含用户照片、人脸、身份或健康
记录。Nutrition5k 主要来自加州食堂，中文菜和家庭拍摄不足；包装标签可能缺失，非食物仅
10 张，结果不能外推为完整用户分布。

阿里云百炼服务协议要求按用户指示处理，不得未经授权把内容用于训练；隐私声明未公布模型
调用内容的精确保留天数，因此残余隐私风险仍写入 Proposed ADR。评测只在本机、北京端点、
独立 Key、每日人民币 1 元预算下运行；报告不保存图片、base64 或 Key。

## Mock/契约基线

`food_image_contract.json` 共 22 条：12 条食物候选、6 条非食物拒答、4 条非法输出。最终
全量评测为 318 条、17 项 Agent/RAG/图片契约门禁全部 PASS，`failure_count=0`、外部费用
`$0`。机器可读结果见 [`latest.json`](latest.json)。

## 真实 Qwen 三轮结果

| 指标 | Baseline v1.0 | v1.1 | v1.2 | 门槛 | 最终 |
|---|---:|---:|---:|---:|---|
| Schema 有效率 | 53/100 | 40/100 | 100/100 | 100% | PASS |
| `needs_user_correction=true` | 42.22%* | 27.78%* | 100/100 | 100% | PASS |
| 食物名称 Top-3 | 26/90（28.89%） | 20/90（22.22%） | 76/90（84.44%） | ≥85% | **FAIL** |
| 单一食物份量误差中位数 | 100% | 100% | 37.48% | ≤30% | **FAIL** |
| 热量真实值落入区间 | 10/90（11.11%） | 23/90（25.56%） | 76/90（84.44%） | ≥80% | PASS |
| 非食物拒答 | 10/10 | 10/10 | 10/10 | ≥95% | PASS |
| API p95 | 3273 ms | 12207 ms | 2945 ms | ≤8000 ms | PASS |
| 单次最高估算费用 | `$0.000077` | `$0.000086` | `$0.000068` | ≤`$0.01` | PASS |
| Provider fallback | 47 | 60 | 0 | 0 | PASS |
| 未确认自动写入 / 隐私标记 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | PASS |

\* baseline/v1.1 的该指标使用了旧分母，只用于历史比较；v1.2 起按所有有效结果计算。v1.2
报告对这一指标做了机械口径修正，没有追加 Provider 调用。

三轮机器报告：

- [`STAGE9_QWEN_REAL_BASELINE.json`](STAGE9_QWEN_REAL_BASELINE.json)
- [`STAGE9_QWEN_REAL_AFTER_V1_1.json`](STAGE9_QWEN_REAL_AFTER_V1_1.json)
- [`STAGE9_QWEN_REAL_AFTER_V1_2.json`](STAGE9_QWEN_REAL_AFTER_V1_2.json)

v1.2 共 54,407 input / 27,391 output Token，估算总费用 `$0.00455481`，中位延迟
2163.5 ms；100 个 AgentRun 与 100 个 ToolTrace 均只保留允许的非内容元数据。

## ADR-031 识别优先唯一评测

在照片估重与厘米尺路线 No-Go 后，ADR-031 把视觉模型职责收窄为“最多 3 个食物名称候选，
份量必须由用户确认”。60 张 Wikimedia Commons 全新数据在许可、隐私、视觉 QA 和三重
零重叠检查后，以 Provider 调用 0 密封。评测前重新确认 Qwen
`qwen3.7-flash-2026-07-15`、北京区域、数据政策、独立 Key、价格和人民币 1 元/日预算。

冻结 Prompt/Schema/评分器的 dry-run 为 0 调用；正式运行每图一次，无重试、后备模型
路由、缓存、thinking 或数据库写入：

| 指标 | 结果 | 门槛 | 状态 |
|---|---:|---:|---|
| 总体食物名称 Top-3 | 37/55 = 67.27% | ≥85% | **FAIL** |
| 中国家庭餐 Top-3 | 12/20 = 60% | ≥80% | **FAIL** |
| 单一食物 / 混合餐 / 包装食品 | 86.67% / 40% / 80% | 诊断 | — |
| 非食物拒答 | 5/5 = 100% | ≥95% | PASS |
| Schema / 强制校正 / 禁止估重 | 59/60 = 98.33% | 100% | **FAIL** |
| 评测降级/失败 / p95 | 1（无后备模型调用）/ 3416 ms | 0 / ≤8000 ms | **FAIL / PASS** |
| Token/费用记录 | 60/60 | 100% | PASS |
| 总估算费用 | $0.00240432（约 ¥0.0173） | ≤$0.02 且 ≤¥1/日 | PASS |
| 未确认自动写入 | 0 | 0 | PASS |

共记录 57,876 input / 7,170 output Token，中位延迟 2265 ms。唯一结构化失败为
`recognition-mixed-meal-008` 的 `ValidationError`，未重试。机器报告
[`STAGE9_QWEN_RECOGNITION_V2.json`](STAGE9_QWEN_RECOGNITION_V2.json) 的 SHA-256 为
`e455f44ef12a547df509c50864926e3c1c35dd49fbf05b976ca218acab515afe`，运行收据与本机
检查点均验证 60/60 完成。

事后不改分的审计发现冻结别名匹配会漏判“水饺/饺子”“肉酱螺旋意面/肉酱意面”等合理
同义或更具体名称，所以 67.27% 不应外推为模型真实准确率；但预注册门禁已失败，也不能
事后放宽评分接受。ADR-031 保持 Proposed，正式 App/API 不接入该真实能力。若未来重启，
先用全新 development set 改进标签本体和语义评分，再建立全新密封 holdout；不得重跑 v2。

## 失败—修正—回归

1. Baseline 大量输出不满足 Schema，份量也经常不可评分。没有降低门槛或修改金标。
2. v1.1 加入更长、更具体的 Prompt 和 Schema v2 后反而退化：32 次 Provider 不可用/超时、
   28 次结构化失败，Schema 40%，p95 12.207 秒。结论是长 Prompt 不适合当前 Flash 模型。
3. 对失败原始输出做最小诊断后发现，部分包装食品能给出热量上下界但缺少点估计，或返回
   不允许的枚举；这些是可确定修复的契约兼容问题，不应伪装成识别失败。
4. v1.2 改用精简 JSON-mode Prompt，增加中英文规范名，并只做有限归一化：非法 high 降为
   medium、非法餐别改 other、强制校正、从已有上下界取中点、把过窄区间扩为有界宽区间。
   不合成缺失食物名、食物项或完全缺失的热量。
5. v1.2 把 Schema 从 40% 修到 100%、fallback 从 60 降到 0、p95 从 12.207 秒降到
   2.945 秒，Top-3 和热量覆盖显著提升；但份量视觉估计仍超门槛，Top-3 也差 1 个有效
   样本才达到 85%。为避免围绕固定测试集继续调参导致过拟合，本轮停止追加真实调用。

## 回退与后续启动条件

当前默认/CI/staging 继续 `FOOD_IMAGE_PROVIDER=mock`；关闭
`FOOD_IMAGE_ANALYSIS_ENABLED` 后，文字 Agent、手动饮食、首页和 Journey 不受影响。下一次
仅在用户明确授权时选择其一：

1. 用同一锁定数据集比较更强的视觉模型，并保持相同 Prompt/Schema/预算门禁；或
2. 先给拍照流程增加餐具/手掌等尺度参照引导，建立独立 holdout 后再评估份量。

任何路线都必须先处理数据集偏差与过拟合风险，全部硬门禁通过后才能转 Accepted。

## 2026-07-29 v1.3 尺度参照与密封泛化结果

根据 v1.2 的份量短板，v1.3 没有直接更换视觉模型，而是增加可选 9×5 cm Journey 参照卡、
已知盘/碗直径、`scale_reference_used`、完整边缘/俯拍引导和脱敏 Trace。Prompt/Schema
更新为 `journey-food-image-1.3.0` / `journey-food-image-schema-3`。

新建 `journey-food-image-holdout-v1` 30 张：单一食物 15、混合餐 15；与原 100 张集在样本
ID、Nutrition5k source ID 和图片 SHA-256 上全部零重叠。该集不含尺度参照，只用于检测未见
图片上的泛化，运行后不再调 Prompt。

| 指标 | v1.3 密封 holdout | 门槛 | 状态 |
|---|---:|---:|---|
| Schema / 强制校正 | 100% / 100% | 100% / 100% | PASS |
| 食物名称 Top-3 | 23/30 = 76.67% | ≥85% | **FAIL** |
| 单一食物份量误差中位数 | 36.36% | ≤30% | **FAIL** |
| 热量区间覆盖 | 27/30 = 90% | ≥80% | PASS |
| 无参照不虚构使用参照 | 30/30 = 100% | ≥95% | PASS |
| API p95 / fallback | 3473 ms / 0 | ≤8000 ms / 0 | PASS |
| 自动写入 / 隐私标记 | 0 / 0 | 0 / 0 | PASS |

19,620 input / 9,609 output Token，总估算费用 `$0.00161268`。机器报告见
[`STAGE9_QWEN_V1_3_HOLDOUT.json`](STAGE9_QWEN_V1_3_HOLDOUT.json)。该轮结束时尺度参照收益
仍为 `Not evaluated`；随后建立的内部厘米尺配对结果见下一节。

## 2026-07-29 内部厘米尺配对结果

用户确认作者授权的 16 张图片经拆分、答案遮挡、实际秤读数逐格核对和全量视觉 QA 后，
密封为 `journey-food-image-scale-holdout-v1`：30 组、60 张有尺/同图无尺输入。二进制
Git ignored，来源帖子关闭且链接不可恢复，因此只允许内部研发、评测和展示。

用户确认厘米尺只进入隔离评测器，不修改正式 App/API。Prompt/Schema
`journey-food-image-scale-ruler-eval-1.0.0` /
`journey-food-image-scale-ruler-schema-1` 在运行前固定，并对 Qwen 执行唯一一次 60 调用。

| 指标 | 修正后结果 | 门槛 | 状态 |
|---|---:|---:|---|
| Schema / 强制校正 | 53/60 = 88.33% | 100% | **FAIL** |
| 完整可评分配对 | 24/30 = 80% | 100% | **FAIL** |
| 有尺份量误差中位数 | 47.82% | ≤30% | **FAIL** |
| 同图无尺份量误差中位数 | 48.87% | 诊断基线 | — |
| 相对改善 | 2.17% | ≥15% | **FAIL** |
| 参照使用判断 | 53/60 = 88.33% | ≥95% | **FAIL** |
| fallback / p95 | 7 / 3744 ms | 0 / ≤8000 ms | **FAIL / PASS** |

首版机器报告错误地用 24 个有尺有效值和 29 个无尺有效值各自求中位数，得到 4.37% 改善；
只读复算改为 24 个同图完整配对后为 2.17%。原报告保留，修正版不调用 Provider。另有
7 次 `ValidationError` 的 Token/费用没有被首版失败分支保存；已记录
24,035 input / 7,032 output Token 和 `$0.00144897` 只能作为下限。评测器随后修复用量
保留并增加回归测试，但禁止重跑密封集。

机器报告：

- [`STAGE9_QWEN_SCALE_RULER_PAIRED_V1.json`](STAGE9_QWEN_SCALE_RULER_PAIRED_V1.json)
- [`STAGE9_QWEN_SCALE_RULER_PAIRED_V1_RESCORED.json`](STAGE9_QWEN_SCALE_RULER_PAIRED_V1_RESCORED.json)

结论：厘米尺参照在当前模型和数据上只带来 2.17% 的份量误差改善，且绝对误差仍为
47.82%，不能通过门禁。ADR-030 继续 Proposed；Mock、强制用户校正和手动记录回退不变。

## 产品收尾决策

本轮不再围绕密封集调参，也不启用未经评审的更强模型。图片能力保留为 Development 实验性
辅助候选：页面直接提示模型不能通过照片准确称重，点估计不是称重值；Preview、Production
和 staging 继续关闭。厘米尺路线标记 No-Go，但隐私处理、结构化候选、用户校正和手动回退
继续保留。未来重新启动真实质量工作必须使用新 ADR、新独立 holdout 和重新复核的视觉模型。
