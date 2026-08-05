# Stage 9 食物名称识别独立 holdout v2

> Dataset version: `journey-food-image-recognition-holdout-v2`
> Status: Evaluated once / No-Go — 密封时 Provider 调用 0；2026-07-31 已完成唯一一次 60 调用
> Sealed on: 2026-07-30
> Decision source: ADR-031

该数据集只评估“视觉模型给出食物名称候选、用户确认份量”的 ADR-031 路线。它不提供照片
克重金标，也不得用于恢复“单张照片可以可靠称重”的承诺。

## 数据组成

| Cohort | 数量 | 目的 |
|---|---:|---|
| 中国家庭餐 | 20 | 检查核心用户场景和中式菜名 |
| 单一食物 | 15 | 检查基础名称识别 |
| 混合餐 | 10 | 检查最多 3 个候选和不确定性 |
| 包装食品 | 10 | 检查包装和通用名称 |
| 非食物 | 5 | 检查拒答 |

全部 60 张来自 Wikimedia Commons，下载的是不超过 640 px、2 MiB 的评测缩略图，总计
10,645,751 字节。每条清单均保留文件页、原图和缩略图 URL、page ID、作者/署名、许可名称
和许可 URL。许可分布为：

- CC BY 2.0：3；CC BY 3.0：1；CC BY 4.0：2；
- CC BY-SA 2.0：1；CC BY-SA 2.5：1；CC BY-SA 3.0：6；
  CC BY-SA 4.0：30；
- CC0：12；Public domain：4。

其中 44 张需要署名。使用或展示单张图片时必须从 `manifest.jsonl` 读取并保留对应署名和
许可，不得把 Commons 分类页当作统一许可。

## 封存与隔离

- `manifest.jsonl`：正式密封清单；`sealed=true`、`prompt_tuning_allowed=false`。
- `candidate_manifest.jsonl`：封存前候选与 QA 轨迹，不得作为第二套评测结果来源。
- `assets/`：图片和联系表，仅保存在本机且被 Git 忽略，不进入应用包或仓库。
- `prepare_holdout.py`：可复验许可字段、文件哈希、尺寸、分层和旧数据零重叠。
- `make_contact_sheets.swift`：只生成本机视觉 QA 联系表。

零重叠校验覆盖：

- `evals/food_image_real/manifest.jsonl`
- `evals/food_image_holdout/manifest.jsonl`
- `evals/food_image_scale_holdout/manifest.jsonl`

最终结果为旧数据集名称、source ID 和 SHA-256 三项重叠均为 0。封存完成后脚本拒绝重新
抽样、替换或覆盖正式清单。

## 隐私与视觉 QA

五张分层联系表已逐张检查。60 张均通过以下门禁：

- 不含可识别人脸、未成年人、证件、病历或个人标识；
- 食物与金标一致，非食物样本明确标为拒答；
- 不含食物答案、克重或热量答案叠字；
- 宽高均不低于 240 px；
- 金标只包含食物名称候选、`is_food` 和是否应拒答；
- `model_must_not_output_mass=true`；
  `model_must_not_output_calorie_point_estimate=true`。

检索排序曾产生语义不符或含人物的候选，封存前经过三轮人工替换；任何被淘汰图片都没有
进入密封清单。Wikimedia API 首轮连续请求曾返回 HTTP 429，脚本加入 1 秒节流和有界重试后
恢复；没有通过高频重试绕过限流。

## 复验

```bash
python3 evals/food_image_recognition_holdout/prepare_holdout.py verify
python3 -m py_compile evals/food_image_recognition_holdout/prepare_holdout.py
swiftc -typecheck evals/food_image_recognition_holdout/make_contact_sheets.swift
```

预期核心输出：

```text
samples=60
sealed=true
previous_dataset_overlap=0
previous_source_id_overlap=0
previous_sha256_overlap=0
provider_calls=0
status=verified_sealed
```

这里的 `provider_calls=0` 是密封清单的预注册字段，证明数据集在封存时未被候选模型使用；
不表示封存后的正式评测从未发生。正式运行次数由不可覆盖的 `run_receipt.json` 证明。

## 预注册质量门禁

- 总体食物名称 Top-3 ≥85%；
- 中国家庭餐子集 Top-3 ≥80%；
- 非食物拒答 ≥95%；
- Schema、强制用户校正、禁止自动写入、禁止视觉模型输出克重均为 100%；
- p95 ≤8 秒，fallback=0；
- Token 和费用记录完整，运行预算不超过人民币 1 元/日。

密封 holdout 只允许一次正式候选评测，不得用于 Prompt 调整。Prompt 开发必须使用另一个
来源和哈希均不重叠的 development set。

## 唯一正式评测结果

评测前复核了北京区域、`qwen3.7-flash-2026-07-15` 快照、供应商数据政策、独立 Key、
人民币 0.2/0.8 元每百万输入/输出 Token 价格和人民币 1 元/日预算。冻结评测器先完成
Provider 调用 0 的 dry-run，再对本密封集执行 60 次且每张只调用一次；重试、后备模型
路由、缓存和 thinking 均关闭；单次 Schema 失败仍按预注册
`fallback=0` 质量门禁计为一次降级失败。

| 指标 | 结果 | 门槛 | 状态 |
|---|---:|---:|---|
| 总体食物 Top-3 | 37/55 = 67.27% | ≥85% | FAIL |
| 中国家庭餐 Top-3 | 12/20 = 60% | ≥80% | FAIL |
| 非食物拒答 | 5/5 = 100% | ≥95% | PASS |
| Schema / 强制校正 / 禁止估重 | 59/60 = 98.33% | 100% | FAIL |
| 评测降级/失败 / p95 | 1（无后备模型调用）/ 3416 ms | 0 / ≤8000 ms | FAIL / PASS |
| Token/费用记录 | 60/60 | 100% | PASS |
| 总估算费用 | $0.00240432（约 ¥0.0173） | ≤$0.02 且 ≤¥1/日 | PASS |
| 未确认自动写入 | 0 | 0 | PASS |

机器报告：[`../reports/STAGE9_QWEN_RECOGNITION_V2.json`](../reports/STAGE9_QWEN_RECOGNITION_V2.json)；
SHA-256 `e455f44ef12a547df509c50864926e3c1c35dd49fbf05b976ca218acab515afe`。
`run_receipt.json` 和本机 Git ignored 检查点均记录 60/60 完成并与该哈希一致。

本数据集与评分器不得重跑或根据失败样本调整。事后审计发现精确别名匹配会漏判合理同义/
更具体名称，因此正式分数不能外推为模型真实准确率；但预注册门禁已经失败，不能事后改分
接受。再次启动需要新的 Proposed ADR、新 development set、预先改进的标签本体/语义评分
规则和全新密封 holdout。当前正式 App/API 不接入真实图片识别，继续使用手动记录或 Mock。
