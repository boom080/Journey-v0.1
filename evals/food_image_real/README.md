# Stage 9 真实食物图片评测集

> Dataset version: `journey-food-image-real-v1`
> Scope: 只用于阶段 9“食物图片识别、份量估算和用户校正”本机评测。

本目录的 `manifest.jsonl` 是版本化事实源。图片二进制下载到 `assets/`，被 Git 忽略，不进入
普通 CI、Docker 镜像、应用包或数据库。

## 样本构成

| 分层 | 数量 | 来源 | 主要金标 |
|---|---:|---|---|
| 单一食物 | 30 | Nutrition5k | 食物名、称重克数、热量 |
| 混合餐盘 | 30 | Nutrition5k | 前三大可见食材、总称重、总热量 |
| 困难餐盘 | 10 | Nutrition5k | 多食材、无显式尺度，总称重、总热量 |
| 饮料 | 10 | Open Food Facts | 包装名、净含量、每 100 ml 热量 |
| 包装食品 | 10 | Open Food Facts | 包装名、净含量、每 100 g 热量 |
| 非食物 | 10 | Openverse 索引的 CC BY/BY-SA/CC0/Public Domain 图片 | `should_abstain=true` |

Nutrition5k 的场景来自美国加州少数食堂，主要为俯拍餐盘；Open Food Facts 是社区数据，标签
可能不完整。两者都不能代表中国用户真实分布。该偏差会保留在报告中，不用测试通过率掩盖。

## 许可与归属

- Nutrition5k：CC BY 4.0；`Nutrition5k: Towards Automatic Nutritional Understanding of
  Generic Food`, Thames et al., CVPR 2021。
- Open Food Facts：产品图片 CC BY-SA；每条清单保留产品页、图片 URL 和归属。
清单中的图片仅用于质量评测，不重新发布为 Journey 产品素材。若对外分发图片，必须继续满足
各来源的署名和 ShareAlike 条款。Openverse 是许可索引，清单同时固定原始落地页和许可 URL；
若原始来源撤回或许可信息变化，必须重新评审，不得只相信缓存字段。

## 构建与校验

首次策展会访问三个官方数据源并生成清单：

```bash
python3 evals/food_image_real/prepare_dataset.py curate
```

清单提交后，后续只按固定 URL 下载并核对 SHA-256，不重新选择样本：

```bash
python3 evals/food_image_real/prepare_dataset.py download
python3 evals/food_image_real/prepare_dataset.py verify
```

`curate` 是显式维护操作；日常复现只能使用 `download`/`verify`，避免上游数据变化导致评测集
静默漂移。

## 隐私边界

- 样本不得包含人脸、身份、身体照片、病历或用户个人健康数据。
- 原图不进入 PostgreSQL、Trace、日志或 Git。
- 真实 Provider 评测必须由本机 `.env` 显式开启，使用北京区域端点和每日预算。
- 评测输出只能保存预测结构、延迟、Token、成本、样本 ID 和聚合指标，不保存 base64。
