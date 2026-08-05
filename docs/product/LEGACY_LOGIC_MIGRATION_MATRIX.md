# 旧版业务规则迁移矩阵

> 基线 commit：`06b52f024547e76e1cd216e27f3ac41717dd3671`
> 目的：保留规则与产品语义，不保留微信/Taro 表现层
> 分类：原样思想保留 / 适配后复用 / 重构 / 淘汰

## 1. 核心产品流程

| 旧流程 | 当前实现 | 有价值的规则 | 新架构去向 | 分类 |
|---|---|---|---|---|
| 微信登录→邀请码→首页 | `auth`、`invite`、`use-page-guard` | 登录态保护页面这一思想 | 邮箱/用户名密码、refresh token、测试账号 | 淘汰旧实现，重构身份 |
| 首页今日摘要 | `home/main.jsx` + `home_mini.py` | 饮食/运动/日常消耗聚合、记录数、近期更新 | `HomeService` + 首页 Query API | 适配后复用 |
| 自然语言饮食估算 | `ai_mini.py` + `ai_service.py` + Food 页面 | 先解析候选、再由用户确认写入 | Intent Router + Food Tool + Confirmed Write | 保留思想，重构 |
| 自然语言运动估算 | 同上 + Activity 页面 | 先解析候选、再确认 | Activity Tool + Confirmed Write | 保留思想，重构 |
| 精确手动记录 | Food/Activity 表单和 CRUD | AI 不可用仍可记录 | 新移动端手动表单 + 业务 API | 保留思想，重构 UI/API |
| 写入后刷新 | `refreshHomeCache`、`syncAfterMutation` | 首页和 Journey 与记录一致 | Query invalidation/同步事件 | 适配后复用 |
| Journey 多日回看 | `journey/main.jsx` + `journey_mini.py` | 日期范围、倒序、分页、多日聚合 | `JourneyService` + cursor API | 适配后复用 |
| 首页建议/贴纸 | `generateHomeSuggestion` + `home-panel.js` | 建议失败时使用柔和固定提醒 | Recommendation Workflow + 明确 fallback | 适配后复用 |

## 2. 前端 `src/utils/` 逐项评审

| 文件 | 规则 | 判断 | 迁移任务/风险 |
|---|---|---|---|
| `ai.js` | AI Result 默认值、候选转 Food/Activity 写入参数 | 重构 | Pydantic/共享契约替代自由对象；写入必须含确认令牌和幂等键 |
| `daily-energy.js` | Katch-McArdle、Hume 瘦体重、活动系数 1.35、日常消耗 | 适配后复用 | 迁到后端确定性领域服务；补公式来源、年龄/人群边界和金标测试；不能当医疗结论 |
| `day.js` | 本地日期、时间、日期偏移、安全数组、错误文案 | 适配后复用 | 明确用户时区；不要依赖设备与服务器隐式本地时间 |
| `estimate-display.js` | 餐次识别、活动标题清洗、候选展示名 | 保留思想 | 作为输入规范化/展示层测试样本；模型输出仍需 Schema 校验 |
| `food-name.js` | 中文食物别名、装饰词清洗、展示名选择 | 适配后复用 | 移到有测试的 normalization 模块；当前别名仅 4 类，不能作为完整知识库 |
| `home-copy.js` | 按热量/记录阈值生成固定首页摘要 | 适配后复用 | 作为确定性 fallback；阈值需产品/安全评审，避免夸大健康意义 |
| `home-panel.js` | 3 条/页、贴纸文案清洗、30–55 字柔化 | 适配后复用 | 保留短建议风格；不得把模型风险内容仅靠“柔化”变安全 |
| `home-updates.js` | 饮食/活动类型推断和标题规范化 | 重构 | 新 API 返回显式 record type，不再靠 kcal/字段猜测类型 |
| `journey-pagination.js` | 5 天一页、cursor 追加、按日期定位/就近页 | 可移植纯逻辑候选 | 转 TypeScript 并补分页边界、重复 cursor、时区测试 |
| `profile.js` | 性别别名、正数校验、画像 payload | 重构 | 新 Profile schema 支持用户目标和未来身份；避免 `0` 代表未知 |
| `record-display.js` | 优先 `time_text`，否则从时间戳提取 HH:mm | 适配后复用 | 统一 ISO 时间、用户时区和 locale 格式化 |
| `router.js` | 三 Tab 与 Taro 导航去重 | 淘汰实现 | 三入口语义保留，使用 Expo Router/React Navigation |
| `use-page-guard.js` | guest/invite/activated 页面守卫 | 淘汰实现 | 新认证守卫只区分会话和资料完成状态，不保留邀请码 |
| `weight-trend.js` | 7700 kcal/kg 理论换算、解析昨日状态文案 | 高风险重构 | 不能从展示文本反向解析事实；如保留，只标“理论估算”并以结构化结余计算 |

## 3. 需要保留的确定性计算

### 当前热量关系

```text
total_burn = activity_kcal + daily_energy_kcal
net_kcal = intake_kcal - total_burn
```

新后端必须成为唯一计算源，客户端只展示，不再同时保留服务器 `net_kcal` 和客户端重算的两个真相。

### 日常消耗

当前优先级：

1. 有体脂：Katch-McArdle。
2. 有身高：Hume 估算瘦体重，再使用 Katch-McArdle。
3. 只有体重：按性别使用固定瘦体重比例。
4. 乘以默认活动系数 1.35。

迁移前必须补来源、适用范围、单位和边界测试；用户输入不足时明确“估算不可用”，不能伪装为精确消耗。

### 理论体重变化

当前使用 `热量结余 / 7700`。新产品若展示，必须写“理论换算，不代表短期体重实际变化”，并从结构化数值计算，禁止解析 `status_text`。

## 4. 前端服务/API 契约映射

| 旧端点 | 当前用途 | 新端点/服务方向 | 处理 |
|---|---|---|---|
| `POST /auth/wechat-login` | 微信 code 换 JWT | `POST /api/v1/auth/register`、`login`、`refresh` | 删除旧端点 |
| `POST /auth/verify-invite` | 邀请码激活 | 无 | 删除 |
| `GET /auth/me` | 微信用户状态 | `GET /api/v1/users/me` | 重建 |
| `GET/PUT /profile/me` | 画像读写 | `/api/v1/profile` | 重建统一 Profile |
| `GET /home/summary` | 今日聚合 | `/api/v1/home/today` | 提取聚合逻辑 |
| `GET /journey-days` | cursor 多日记录 | `/api/v1/journey` | 保留 cursor 语义，重建 schema |
| `/food-records` CRUD | 饮食记录 | `/api/v1/food-records` | 重建字段、权限和幂等 |
| `/activity-records` CRUD | 运动记录 | `/api/v1/activity-records` | 增加时长/强度/距离等字段 |
| `POST /ai/food-text-estimate` | 固定 LLM 食物解析 | 统一 Agent run + Food candidate event | 被 Agent 工具替代 |
| `POST /ai/activity-text-estimate` | 固定 LLM 运动解析 | 统一 Agent run + Activity candidate event | 被 Agent 工具替代 |
| `POST /ai/home-suggestion` | 首页建议 | Recommendation Workflow | 重建并加入引用/安全/轨迹 |

具体新 URL 仍需阶段 4 API ADR 确认；表中只表示能力映射。

## 5. FastAPI 模块迁移判断

### 适配后保留

- `app/services/home_mini.py`：饮食/运动聚合和近期更新的业务思想。
- `app/services/journey_mini.py`：多日聚合、时间排序和 cursor 返回思想。
- `app/services/ai_service.py`：能力候选、失败原因、有限 fallback 的思想。
- `app/services/ai_client.py`：OpenAI-compatible 调用和错误分类的参考。
- Food/Activity CRUD 的“按 user_id 限定记录”规则。
- Pydantic response model 的契约意识。

### 必须重构

- 所有 `_mini` 路由、Schema、依赖与命名。
- `User`/`Profile` 双份画像事实源。
- Food/Activity 每次 CRUD 内部直接 commit，缺少应用服务事务。
- AI 返回自由 JSON 后再手工读取字段的流程。
- 模型候选与业务能力配置应迁入 LangChain Adapter + 自研 Router。
- CORS、JWT secret、日志脱敏、错误码、request/trace ID。

### 淘汰

- `core/wechat.py`。
- `auth_mini.py` 的微信 code2session 和邀请码激活。
- `deps_mini.py` 的 activated user 语义。
- `crud/user_mini.py` 的 OpenID 用户创建。
- InviteCode 模型、CRUD 和管理脚本。
- `bootstrap.py` 的 SQLite 运行时补列。

## 6. 当前实现中必须避免照搬的问题

1. **客户端与服务端重复计算**：客户端重算 `net_kcal` 并把服务器值放入 `extra.server_net_kcal`，容易出现不一致。
2. **画像双事实源**：`users` 和 `profiles` 同时保存 goal/height/weight 等字段。
3. **展示文本反向解析**：体重趋势从 `status_text` 抽取 kcal，不可靠且不利于本地化。
4. **弱类型 AI 结果**：手工默认值可能掩盖模型遗漏字段。
5. **类型猜测**：首页更新用字段与 kcal 猜 Food/Activity，新契约应显式返回类型。
6. **安全硬编码**：开发 JWT secret 固定在源码。
7. **schema 不可回滚**：启动时 `create_all` 和 SQLite `ALTER TABLE` 补列。
8. **依赖未锁定**：Python requirement 无版本；Taro 包版本区间混合。
9. **无项目测试**：任何复用逻辑都必须先补 characterization test，不能直接复制并假定正确。

## 7. 新共享模块候选

以下是阶段 3/4 的候选目录，不在阶段 2 创建空实现：

```text
backend/app/domain/energy.py          # 确定性热量与日常消耗
backend/app/domain/records.py         # Food/Activity 规则
backend/app/services/home.py          # 今日聚合
backend/app/services/journey.py       # 多日聚合
packages/contracts/                   # 客户端 API/Event 类型
packages/design-tokens/               # 从旧 SCSS 选择性转化
apps/mobile/src/lib/formatters/       # 日期、标题、单位展示
```

## 8. 提取验收

- [x] 已评审 `src/utils/` 全部 14 个文件。
- [x] 已记录热量、日常消耗、体重趋势、日期、分页和 AI 候选确认规则。
- [x] 已记录旧 API 到新能力的映射。
- [x] 已记录 FastAPI 可复用逻辑、必须重构与淘汰模块。
- [x] 已列出禁止直接照搬的高风险实现。
- [ ] 阶段 3/4 实际迁移时为每条复用规则补测试和来源说明。
