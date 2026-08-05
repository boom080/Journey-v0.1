# Stage 9 内部尺度配对 holdout

> Dataset version: `journey-food-image-scale-holdout-v1`
> Status: Sealed and evaluated once；真实 Provider 门禁未通过

本目录把用户确认获作者许可的 30 组小红书称重图片密封为内部配对评测集。来源帖子已经
关闭，无法恢复逐条 URL 或第三方授权记录，因此只允许 Journey 本机研发、评测和项目展示，
不得作为开放数据集再分发。

每组含两张相同尺寸的确定性遮挡图：

- `with_ruler`：遮挡食物名、克重叠字和电子秤显示，保留厘米尺；
- `without_ruler`：在同一图片上额外遮挡厘米尺；
- `gold_mass_g`：人工逐格核对原图电子秤显示得到的实际读数；
- 两版均未生成、补画或修改食物内容。

60 张二进制位于 Git 忽略的 `assets/`，清单固定 SHA-256、尺寸、授权边界、金标和视觉
QA 状态。密封后禁止用本数据调整 Prompt、Schema 或模型参数。

## 隔离评测方式

当前 `/api/v1/food-images/analyses` 只接受 `none`、`journey_card`、
`plate_diameter` 和 `bowl_diameter`。它不能声明“图中是厘米尺”，现有真实评测器也严格复用
该公开契约。把有尺图以 `none` 发送会让 Provider 被明确告知不得假设未声明物体尺寸，无法
形成公平的有参照/无参照对照。

因此本数据集密封时标记为 `hard_gate_eligible=false`。用户于
2026-07-29 确认采用不影响正式产品接口的隔离试验适配器，不把 `centimeter_ruler` 加入
公开契约。隔离 Prompt/Schema、门禁和预算检查固定后，只允许执行一次真实 Provider 配对
评测；不得为了得到数字绕过现有契约或根据密封集继续调参。

## 唯一一次 Qwen 结果

`qwen3.7-flash` 共执行 60 次：30 张有尺、30 张同图无尺。只有 24 组两边都得到有效结构化
结果，因此份量改善按这 24 个完整配对计算。

| 指标 | 结果 | 门槛 | 状态 |
|---|---:|---:|---|
| Schema / 强制校正 | 53/60 = 88.33% | 100% | **FAIL** |
| 完整可评分配对 | 24/30 = 80% | 100% | **FAIL** |
| 有尺份量误差中位数 | 47.82% | ≤30% | **FAIL** |
| 同图无尺份量误差中位数 | 48.87% | 诊断基线 | — |
| 有尺相对改善 | 2.17% | ≥15% | **FAIL** |
| 参照使用判断 | 53/60 = 88.33% | ≥95% | **FAIL** |
| Provider fallback | 7 | 0 | **FAIL** |
| p95 延迟 | 3744 ms | ≤8000 ms | PASS |

53 个有效输出中，有尺 24/24 声称使用参照，无尺 29/29 没有声称使用参照；总准确率按全部
60 次计算并把 7 次结构化失败计为错误。报告记录到 24,035 input / 7,032 output Token 和
`$0.00144897`，但 7 次失败响应的用量未被首版评测器保存，因此该金额只是下限，不能作为
完整费用证明。评测器已修复该记录缺陷，但不会重跑密封集。

- 原始一次运行报告：
  [`../reports/STAGE9_QWEN_SCALE_RULER_PAIRED_V1.json`](../reports/STAGE9_QWEN_SCALE_RULER_PAIRED_V1.json)
- 零 Provider 调用的配对口径修正版：
  [`../reports/STAGE9_QWEN_SCALE_RULER_PAIRED_V1_RESCORED.json`](../reports/STAGE9_QWEN_SCALE_RULER_PAIRED_V1_RESCORED.json)

该结果说明当前 Flash 模型即使看见厘米尺，也没有达到 Journey 的份量质量门禁。不得根据
这些失败样本修改冻结 Prompt，也不得外推为 Journey 卡、盘/碗直径链路已经通过或完全无效。

## 数据校验

```bash
python3 evals/food_image_scale_candidate/prepare_candidates.py verify-pairs
python3 evals/food_image_scale_holdout/seal_holdout.py verify
```

不再提供第二次真实运行命令；`verify` 只校验已密封哈希，不调用模型、联网或修改业务代码。
