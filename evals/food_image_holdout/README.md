# Stage 9 食物图片密封泛化 holdout

> Dataset version: `journey-food-image-holdout-v1`
> Status: Generalization cohort ready only; scale-reference cohort Pending

该目录与 `food_image_real/manifest.jsonl` 的 100 张 Prompt 调试/评测集严格分离。当前清单固定
30 张从未用于 v1.0—v1.2 调参的 Nutrition5k 图片：15 张单一食物、15 张混合餐。它们只用于
检查 v1.3 在未见图片上是否退化，不提供物理尺度参照，不能证明 Journey 参照卡改善了份量。

## 密封与防泄漏

- `prepare_holdout.py verify` 同时检查样本 ID、Nutrition5k source ID 和图片 SHA-256，
  三者与 100 张调参集必须零重叠。
- 清单生成后只允许 `download`/`verify`；任何重新策展都必须写入执行日志并升级
  `dataset_version`，不得依据模型失败案例替换样本。
- 图片二进制位于 Git 忽略的 `assets/`，不进入普通 CI、应用包、数据库、Prompt 或文档。
- 许可沿用 Nutrition5k CC BY 4.0，归属和原始 URL 逐条固定。

```bash
python3 evals/food_image_holdout/prepare_holdout.py curate
python3 evals/food_image_holdout/prepare_holdout.py download
python3 evals/food_image_holdout/prepare_holdout.py verify
```

## 不能据此宣称的内容

当前图片都标记 `scale_reference.type=none`。尺度参照的真实收益仍需另建至少 30 张配对 cohort：
同一份称重食物分别以无参照和完整 9×5 cm Journey 卡/已知盘碗直径拍摄，许可清晰、无人物或
个人信息。只有配对 cohort 通过 ADR-030 指标后，才能宣称参照改善份量估算。

SimpleFood45 的论文/仓库说明其包含物理参照、重量和能量，但公开仓库没有清晰数据许可，
因此本项目当前不下载、不纳入 holdout。

2026-07-29 的互联网筛选还确认了两个分层候选：

- [SNAPMe](https://doi.org/10.15482/USDA.ADC/1528346)：CC BY-SA 4.0，非包装餐食含
  3.81×3.81 cm 棋盘格，适合做同图有/无尺寸提示的次级配对评测；但其金标来自 ASA24
  参与者饮食记录，不是实验室称重，不能关闭当前硬门禁。官方 1.89 GB 归档在本执行环境
  返回 HTTP 403，本轮未下载。
- [MetaFood3D](https://lorenz.ecn.purdue.edu/~food3d/)：CC BY-NC 4.0，含食物重量、营养、
  RGB-D 和 fiducial marker 资料；需要申请密码，且取得数据后仍需核验 marker 与食物是否
  在同一评测帧共视。本轮未提交外部申请、未下载。

不得为了立即运行评测而把 SNAPMe 的自报份量改称真实称重，也不得把许可不清晰的
ECUSTFD/SimpleFood45 混入清单。取得合格数据后应另建版本化配对目录，不修改本无参照
holdout。

## v1.3 首次密封结果

Qwen `qwen3.7-flash` 只运行一次，随后不再依据本 holdout 调 Prompt：

- Schema/强制校正 100%，Top-3 76.67%，单一食物份量误差中位数 36.36%。
- 热量区间覆盖 90%，p95 3473 ms，fallback/自动写入/隐私标记均为 0。
- 30/30 正确没有声称使用不存在的尺度参照。
- 总估算费用 `$0.00161268`。

机器报告：[`../reports/STAGE9_QWEN_V1_3_HOLDOUT.json`](../reports/STAGE9_QWEN_V1_3_HOLDOUT.json)。
Top-3 与份量门禁失败；尺度配对质量仍是 Pending。
