# Journey 量化评测

阶段 7 和普通 CI 的确定性评测只使用合成数据、受控知识和 Mock Model，不读取真实用户健康
数据、不发送外部请求。运行时 Prompt 不会加载金标答案。

```bash
python3 evals/datasets/build_datasets.py
PYTHONPATH=backend python3 evals/run_evals.py --enforce
```

CI 使用 PostgreSQL service 和锁定的后端测试镜像执行同一评测器。报告记录 Prompt、
Schema、知识版本、数据集数量、逐项指标、失败案例、耗时和零外部成本证明。

## 真实文字 Provider 发布门禁

普通 CI 的 Mock 门禁不能替代真实模型质量。2026-08-01 起，文字发布验收使用当前配置的
真实 Provider 单独运行；该命令会产生费用且不会进入 GitHub Actions。先执行零调用 dry-run：

```bash
docker run --rm --env-file .env -e PYTHONPATH=/app \
  --entrypoint python journey-test:latest \
  evals/run_text_provider_acceptance.py --max-cost-usd 0.02
```

确认 Provider、模型、28 次调用和预算后，显式增加 `--execute` 并指定新的报告文件。评测固定
覆盖 18 条分层意图、5 条饮食解析和 5 条运动解析；报告不保存 Key。2026-08-01 的
DeepSeek `deepseek-v4-flash` 首轮结果为路由 94.44%，发现“我的体重是多少”被误判为记录
weight；Router Prompt 从 `1.0.0` 升到 `1.0.1` 后复验为路由/饮食/运动 100%、0 fallback、
p95 1768 ms，门禁通过。修正前后报告分别为
`reports/REAL_TEXT_DEEPSEEK_V4_FLASH_2026_08_01.json` 与
`reports/REAL_TEXT_DEEPSEEK_V4_FLASH_2026_08_01_AFTER_ROUTER_FIX.json`。

真实图片仍使用下方独立密封质量门禁。单张 API 冒烟通过不能覆盖 60 张图片质量失败；完整
文字/图片验收矩阵见 `reports/REAL_MODEL_ACCEPTANCE_2026_08_01.md`。

## Agent v2 计划与执行门禁

`datasets/agent_v2_plans.json` 固定 24 条计划样本，覆盖单意图、组合饮食/运动、画像、
Journey、知识问答、个性化建议、周总结、线程跟进和非法计划。`run_evals.py --enforce`
在原有 318 条基线上纳入该数据集，当前总计 342 条样本和 22 项门禁，新增指标为：

- 计划 Schema 合法率；
- 工具序列准确率；
- 工具参数准确率；
- 人工确认与写入 Policy 合法率；
- 最多 6 步、最多 1 次重规划的边界合规率。

真实 Agent v2 只在显式发布验收时运行，固定 8 个任务、Router + Planner 共 16 次调用，
不访问业务数据库、不写用户记录。先执行不调用 Provider 的 dry-run：

```bash
docker compose run --rm --no-deps --entrypoint python \
  -e PYTHONPATH=/app -v ./evals:/app/evals api \
  evals/run_agent_v2_provider_acceptance.py --max-cost-usd 0.02
```

确认 Provider、模型、16 次调用和预算后才增加 `--execute`。报告会保存模型、Prompt/Schema、
工具序列、Policy、Token、延迟、费用和 fallback，不保存 Key、原始任务正文或完整计划片段。

2026-08-03 首轮 `journey-agent-planner-2.0.0` 结果保存在
[`reports/REAL_AGENT_V2_PROVIDER_ACCEPTANCE.json`](reports/REAL_AGENT_V2_PROVIDER_ACCEPTANCE.json)：
模型过度加入 `context.load`/`journey.read` 且部分依赖非法，工具序列准确率 0、Policy 75%，
门禁失败。冻结最小工具配方并升级到 `2.0.1` 后，第二份报告
[`reports/REAL_AGENT_V2_PROVIDER_ACCEPTANCE_2.json`](reports/REAL_AGENT_V2_PROVIDER_ACCEPTANCE_2.json)
的意图、Schema、工具序列、Policy、Provider/模型、无 fallback 和 Token 记录均为 100%，
p95 3112 ms、费用 `$0.00257824`，门禁通过。两份报告都必须保留，用于展示量化反馈闭环。

## RAG Eval v1：Retrieval / Generation 分层评测

`datasets/rag_eval_v1.json` 固定 60 题（40 有答案、20 应拒答），覆盖单文档、多文档、相似干扰、
模糊问题、知识缺失和高风险拒答。普通 CI 比较同一 Dataset/知识 bundle 的两套配置：

```bash
PYTHONPATH=backend python3 evals/run_rag_eval.py \
  --mode mock --config rag-v1 --output reports/evals/rag-v1.json --enforce
PYTHONPATH=backend python3 evals/run_rag_eval.py \
  --mode mock --config rag-v2-candidate \
  --baseline reports/evals/rag-v1.json \
  --output reports/evals/rag-v2-candidate.json --enforce
```

Mock 只评 Recall@1/3/5、Precision、MRR、nDCG、检索拒答和时延；Generation 必须显示
`SKIPPED_REAL_MODEL`。当前 v1 → v2 的 Recall@3 为 0.9625 → 1.0、Recall@5 为 0.9625 → 1.0、
MRR 为 0.9500 → 0.9625。

真实模式必须使用非 Mock Provider、正预算、显式 `--execute` 和全新报告文件；Runner 拒绝覆盖
已有报告，并拒绝 Dataset/bundle hash 不同的基线。2026-08-10 DeepSeek 最终报告为
`reports/evals/rag-v2-real-2026-08-10-r2.json`：Groundedness/Relevance 0.9625、Citation
Correctness 0.9083、Abstention 1.0、41 次调用、19 次确定性 `insufficient_context`、费用
`$0.00624232`。首次拒答 0.6833 的失败报告继续保留。人类可读报告见
[`reports/RAG_EVAL_V1_2026_08_10.md`](reports/RAG_EVAL_V1_2026_08_10.md)。

`food_image_contract.json` 只验证结构化输出、份量/热量区间、非食物拒答和强制用户校正
契约，不含照片。真实质量集 `food_image_real/manifest.jsonl` 固定 100 张公开许可图片；
二进制下载到被 Git 忽略的 `assets/`，不进入普通 CI。

```bash
python3 evals/food_image_real/prepare_dataset.py download
python3 evals/food_image_real/prepare_dataset.py verify
python3 evals/food_image_holdout/prepare_holdout.py verify
python3 evals/food_image_scale_holdout/seal_holdout.py verify
```

真实 Provider 评测是本机显式操作，要求隔离的 `journey_test` PostgreSQL、根 `.env` 中独立
Qwen 配置、外发确认和正预算；不得放进 GitHub Actions：

```bash
PYTHONPATH=backend python3 evals/run_food_image_real.py \
  --manifest evals/food_image_real/manifest.jsonl \
  --report evals/reports/STAGE9_QWEN_REAL_AFTER_V1_2.json \
  --run-label stage9-qwen-real-after-v1.2
```

评测器只保存结构化预测、指标、Token、费用、延迟和样本 ID，不保存图片、base64、Key 或
个人数据。`--manifest` 可选择 100 张调参集或 30 张密封 holdout；`--report` 与 `--output`
是同一参数。当前 v1.3 holdout 的 Top-3 和份量误差未达门槛，且不包含尺度配对样本，
不能视为上线通过或参照改善证据。

内部尺度配对集使用独立版本化评测器，不改变正式 API。30 组只执行过一次真实 Qwen 评测；
正确配对口径为 24 个完整结果，有尺误差 47.82%、无尺 48.87%、改善 2.17%，门禁失败。
原始报告和零调用修正版分别为
[`STAGE9_QWEN_SCALE_RULER_PAIRED_V1.json`](reports/STAGE9_QWEN_SCALE_RULER_PAIRED_V1.json)
与
[`STAGE9_QWEN_SCALE_RULER_PAIRED_V1_RESCORED.json`](reports/STAGE9_QWEN_SCALE_RULER_PAIRED_V1_RESCORED.json)；
不得重跑或据此调参。

ADR-031 Proposed 的路线将食物名称识别与份量确认解耦。
[`food_image_recognition_holdout/README.md`](food_image_recognition_holdout/README.md)
记录 60 张独立 Wikimedia Commons 图片的授权、隐私、零重叠与唯一真实评测。冻结的
`run_food_image_recognition.py` 已对 Qwen `qwen3.7-flash-2026-07-15` 运行一次：
总体 Top-3 67.27%、中式 60%、Schema 98.33%，门禁失败；不可重跑或用该 holdout 调参。
机器报告为
[`reports/STAGE9_QWEN_RECOGNITION_V2.json`](reports/STAGE9_QWEN_RECOGNITION_V2.json)。

阶段 7 的首轮失败、修正分类、最终指标与已知边界见
[`reports/STAGE7_EVALUATION_REPORT.md`](reports/STAGE7_EVALUATION_REPORT.md)。
阶段 9 的 Mock/真实评测、失败—修正和当前回退见
[`reports/STAGE9_FOOD_IMAGE_EVALUATION_REPORT.md`](reports/STAGE9_FOOD_IMAGE_EVALUATION_REPORT.md)。
