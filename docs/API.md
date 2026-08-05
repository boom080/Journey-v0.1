# Journey API v1

> 阶段 4 核心契约 + 阶段 6 Agent/RAG + 阶段 9 食物图片候选 + 阶段 11 Agent v3。机器可读事实源是
> [`../packages/contracts/openapi.json`](../packages/contracts/openapi.json)。

## 统一约定

- 基础前缀：`/api/v1`
- 主键：UUID 字符串。
- 时间戳：ISO 8601 且必须包含时区；服务端以 UTC 存储。
- 业务日期：按照用户 Profile 的 IANA timezone 从记录时间派生。
- 鉴权：`Authorization: Bearer <access_token>`。
- 请求追踪：可传 `X-Request-ID`，响应始终回传有效 request ID。
- 创建饮食、运动、体重时可传 `Idempotency-Key`；同 key、同 payload 返回原结果，
  同 key、不同 payload 返回 `409 idempotency_conflict`。
- 列表分页：`limit`、`offset`、`meta.total`；Journey 使用日期 `cursor`。
- Agent 候选确认必须传 `Idempotency-Key`；同一候选只能成功写入一次。

统一错误格式：

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": []
  },
  "request_id": "..."
}
```

## 身份 API

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/auth/register` | 邮箱、用户名、密码注册并返回 token pair |
| POST | `/auth/login` | 使用邮箱或用户名登录 |
| POST | `/auth/refresh` | 轮换 refresh token 并返回新 token pair |
| POST | `/auth/logout` | 撤销当前 session |
| GET | `/auth/me` | 查询当前用户与身份列表 |

access token 默认 15 分钟，refresh token 默认 30 天。手机号身份只预留数据模型，当前
没有短信接口。

## 画像和目标

| 方法 | 路径 | 用途 |
|---|---|---|
| GET/PATCH | `/profile` | 获取或更新显示名、时区、身高等画像 |
| GET/PUT | `/goals/current` | 获取或幂等更新当前目标 |

最新体重来自 WeightRecord，不在 Profile 保存第二份值。

## 核心记录和聚合

| 方法 | 路径 | 用途 |
|---|---|---|
| GET/POST | `/food-records` | 列表与创建饮食记录 |
| PATCH/DELETE | `/food-records/{id}` | 更新或删除本人饮食记录 |
| GET/POST | `/activity-records` | 列表与创建运动记录 |
| PATCH/DELETE | `/activity-records/{id}` | 更新或删除本人运动记录 |
| GET/POST | `/weight-records` | 列表与创建体重记录 |
| PATCH/DELETE | `/weight-records/{id}` | 更新或删除本人体重记录 |
| GET | `/home/today` | 指定或用户今日的确定性聚合 |
| GET | `/journey` | 日期范围与日期 cursor 聚合 |

所有记录查询和变更都按当前 User 过滤；访问他人记录统一返回 404，避免泄露存在性。

## Agent 与受控知识

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/agent/runs` | 路由单/多意图，执行查询或返回可编辑候选、引用和有序事件 |
| GET | `/agent/runs/{run_id}` | 仅本人查询脱敏工具轨迹、版本、Token、延迟、重试与成本 |
| POST | `/agent/runs/{run_id}/resume` | 全部候选确认后，显式恢复 checkpoint 并读取最新业务数据 |
| POST | `/agent/confirmations/{candidate_id}` | 验证签名令牌和幂等键后写入一条 food/activity/weight 记录 |

默认 `AGENT_PROVIDER=mock` 且 API key 为空；响应明确返回 `fallback_used=true`、provider、
model 和 `$0` 成本。写意图不会在 `/agent/runs` 阶段产生业务记录。候选确认令牌有效期
15 分钟，绑定当前 user、run、candidate 和 kind；payload 可以由用户修改字段，但不能
改变候选类型。RAG 只从受控公共知识返回真实 chunk/document/source/version 引用；无相关
知识时返回 no-answer，不进行自由网络搜索。

阶段 11 默认以 `AGENT_V3_ENABLED=true` 启用带人工检查点和失败恢复的单 Agent 闭环；关闭后
回退 `AGENT_V2_ENABLED` 所控制的阶段 10 路径。请求可选传入本人已有的
`thread_id`；省略时创建新线程。跨用户或不存在的线程返回 404。响应在原有兼容字段外增加：

- `thread_id`：PostgreSQL 线程标识；线程只保留最近 8 条结构化摘要，不保存原始消息正文。
- `plan`：Schema v3 计划，最多 6 步；每步只有白名单 `tool`、`depends_on`、
  `requires_confirmation` 和脱敏任务片段。
- `step_results`：每步的 `completed`、`failed`、`skipped` 或 `awaiting_confirmation` 状态。
- `observations`：步骤、工具、状态、错误类型、是否可恢复、脱敏摘要和允许的替代工具。
- `verification`：`done`、`wait_for_user`、`replan`、`clarify`、`fallback` 或 `stop` 决策，
  以及最多 2 次的 `replan_count`。
- `confirmation_progress` 与 `resumable`：候选总数、已确认/待确认数量和是否允许显式恢复。

组合“记录 + 建议”会在候选生成后返回 `status=waiting_for_user`，不会提前读取未确认数据或
生成建议。Confirmation 响应只报告进度，不隐藏触发新的模型费用；全部候选确认后客户端调用
Resume。Resume 校验本人归属、状态、确认完整性和过期时间，只能成功一次；候选型单步任务在
最后一次确认后直接完成，无需 Resume。

Planner 不能创建任意函数名，Executor 只执行服务端类型化注册表中的工具。饮食、运动和体重
工具仍只生成候选；即使计划和验证均通过，也必须调用 confirmation API 才会写业务表。
`GET /agent/runs/{run_id}` 返回同一计划、验证、Prompt/Schema/Knowledge 版本、Token、延迟、
费用、checkpoint 状态、恢复次数和脱敏工具轨迹。模型 Replanner 只能从 Observation 声明的
白名单替代工具中选择，结果还要重新通过 Policy Guard；知识生成失败可用
`knowledge.safe_summary`，建议生成失败可用 `recommendation.rules_fallback`。将
`AGENT_V3_ENABLED=false` 回退 v2，再关闭 `AGENT_V2_ENABLED` 才回退阶段 6 的 v1 固定分支；
两种回退均不改变公开请求契约和既有业务数据。

## 食物图片候选（阶段 9 单项）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/food-images/analyses` | 校验一张 JPEG/PNG/WebP，在内存中生成可编辑饮食候选 |

请求必须由已登录用户发送，并显式包含 `confirm_upload=true`；解码后不超过 5 MiB，声明尺寸
不超过 4096×4096。响应只可能是 `candidate` 或 `manual_required`，图片永不直接写饮食记录。
用户修改候选后仍通过 `/agent/confirmations/{candidate_id}` 确认，最终来源为 `image`。

v1.3 可选请求字段：

- `scale_reference_type`：`none`（默认）、`journey_card`、`plate_diameter` 或
  `bowl_diameter`。
- `scale_reference_size_cm`：只有盘/碗直径模式必填，范围 8—60；Journey 卡固定 9×5 cm，
  不接受自定义尺寸。
- 响应 `estimate.scale_reference_used` 只表示模型是否声明使用了完整可信的参照；它不是精度
  证明，结果仍必须校正。参照类型/尺寸只进入请求和脱敏 Trace，不写入饮食记录。

默认、CI、staging 仍使用 `FOOD_IMAGE_PROVIDER=mock` 并显著声明“未真实识别图片”；
DeepSeek V4 不用于图片。本机 Qwen `qwen3.7-flash` 已在 100 张授权图片集完成真实评测，
v1.3 还在 30 张零重叠 holdout 得到 Top-3 76.67%、份量误差 36.36%，仍未通过门禁；
尺度配对质量未评测。响应食物项可附带可选
`canonical_name_en` 供评测和跨语言归一化；显示名称仍使用 `name`。当前 Prompt 为
`journey-food-image-1.3.0`，Schema 为 `journey-food-image-schema-3`。原图、base64、
文件名和 EXIF 不写入数据库、日志、Trace、RAG 或备份；Trace 只保留 MIME、字节数、宽高、
参照类型/尺寸、Provider、模型、Token、费用和延迟。启用边界见
[`product/FOOD_IMAGE_PRIVACY_AND_EVAL.md`](product/FOOD_IMAGE_PRIVACY_AND_EVAL.md)。

## 本地测试账号

Compose 默认明确启用：

- 邮箱：`demo@journey.local`
- 用户名：`journey_demo`
- 密码：`JourneyDemo2026`

这只是本机开发账号，不得复用于 staging/production。复制 `.env.example` 后应覆盖本地
测试密码。production 环境若配置 `SEED_TEST_ACCOUNT=true` 会拒绝启动。

## 契约更新

修改 Pydantic API schema 后执行：

```bash
cd backend
PYTHONPATH=. python scripts/export_openapi.py
```

随后必须运行 OpenAPI snapshot test。不得只更新 JSON 以绕过失败；先确认变化是否兼容。
