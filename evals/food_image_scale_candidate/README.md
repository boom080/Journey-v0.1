# Stage 9 小红书授权称重图片候选集

> Dataset version: `journey-food-image-scale-candidate-v0`
> Status: Candidate processing complete；已升级到独立 sealed holdout

本目录整理用户在 2026-07-29 提供的 16 张小红书图片。用户再次确认作者允许 Journey 取用，
并要求继续使用；帖子已经关闭、链接无法恢复，因此授权状态记为 `user_attested_final`，
不是可对外再分发的开放许可证。二进制只用于 Journey 本机研发、评测和项目展示。

## 当前加工结果

- 16 张原图保存于 Git 忽略的 `assets/source/`，不进入应用包、Docker 镜像或普通 CI。
- 1 张长图只作份量参考；1 张 6×6 总览与已有原图重复，不拆分。
- 其余 14 张按原始拼图边界无生成式修改地拆出 88 个格子。
- 其中 5 张带尺子和秤的 2×3 拼图拆出 30 个 `scale_pair_candidate`。
- 原始叠字、作者水印和秤读数均保留；不移除水印、不生成食物、不修改份量。
- 30 个带尺候选另外生成两份确定性遮挡输入：`with_ruler` 保留尺子，
  `without_ruler` 遮挡尺子；两者均遮挡食物名/克重叠字和秤读数。

`source_manifest.jsonl` 记录原图哈希、尺寸、角色和授权边界；
`manifest.jsonl` 记录格子裁切、声明名称/克重、可见证据及进入硬门禁前的阻塞项。

## 已完成的密封前检查

图片中直接出现食物名称、声明克重或电子秤读数，原样输入模型会造成答案泄露，因此没有把
原始格子直接送入 Provider。2026-07-29 已完成：

1. 人工逐格转录并核对 30 个电子秤实际读数，写入 `gold_mass_g`。
2. 对全部 30 组有尺/无尺配对完成 contact sheet 和疑难格放大检查；未发现食物被遮挡、
   答案文字或秤显示残留。
3. 固定新版本哈希并升级为
   [`journey-food-image-scale-holdout-v1`](../food_image_scale_holdout/README.md)。

来源链接无法恢复是永久 provenance 限制：允许内部使用，但该批图片不能作为开放数据集
对外发布，也不能把授权状态描述为独立第三方已经核验。

现有公开 API 不支持 `centimeter_ruler` 参照类型，所以密封集尚未运行 Qwen；这不改变
ADR-030 的 `Status: Proposed`，也不降低至少 30 张、份量误差中位数 `≤30%`、相对无参照
改善 `≥15%`、参照判断 `≥95%` 的门禁。

## 命令

原图已放入 `assets/source/` 时：

```bash
python3 evals/food_image_scale_candidate/prepare_candidates.py prepare
python3 evals/food_image_scale_candidate/prepare_candidates.py make-pairs
python3 evals/food_image_scale_candidate/prepare_candidates.py verify
python3 evals/food_image_scale_candidate/prepare_candidates.py verify-pairs
```

`prepare` 仅调用 macOS 自带的 `sips` 按规则裁切，不使用生成式图像工具。`verify` 校验
原图/格子哈希、尺寸、数量、重复排除和候选状态。`make-pairs` 使用本目录 Swift 脚本绘制
固定遮挡区域；它不生成或补画图像内容。
