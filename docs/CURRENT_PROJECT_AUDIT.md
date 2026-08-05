# Journey 当前项目审计

> 审计日期：2026-07-15
> 审计对象：微信小程序退役前的 `main` 工作树
> 性质：代码事实基线；不是新架构说明

## 阶段 2 退役结果（2026-07-16）

- 旧微信/Taro 客户端、构建配置、根 Node 依赖清单和本地生成物已删除。
- 3 张叶子角色 PNG 和 1 个 SVG 已逐字节复制到 `assets/brand/`，哈希见资产清单。
- 页面结构、设计 token、业务规则和删除候选已形成文档。
- 微信开发者工具已安装；Taro 微信构建成功，14 张运行截图已完成并逐张检查。
- 用户实际点击微信登录后无法进入应用：`/wechat-login` 请求
  `http://127.0.0.1:8000` 失败。其余受保护页面通过开发者工具本地虚拟会话采集，
  不能视为登录或端到端流程通过。
- 后端 `_mini` 迁移桥按 ADR-020 `Accepted` 保留到阶段 4，不再新增功能。
- 阶段 2 完成时尚无新客户端；其后阶段 3 已按下节建立新基线。

## 阶段 3 实现基线（2026-07-17）

- 新客户端位于 `apps/mobile/`，使用 Expo SDK 57、React Native 0.86、TypeScript
  strict、Expo Router 和 Development Build；只有首页、Journey、我的三个骨架路由。
- 首页仅包含 API live health 连通性卡片，没有迁移登录、饮食、运动、Journey 数据或
  Agent 业务页面。
- `packages/contracts/` 与 `packages/design-tokens/` 分别提供最小健康契约和品牌 token。
- FastAPI 新入口默认只注册 `/health/live` 与 `/health/ready`；旧 `_mini` 路由通过
  `ENABLE_LEGACY_MINI_ROUTES=false` 隔离，等待阶段 4 替换。
- 数据库默认连接全新 PostgreSQL；应用 import 不再 `create_all` 或执行 SQLite 补列。
  Alembic 只有 `0001_empty_baseline`，没有业务表或旧数据迁移。
- `compose.yaml` 只定义 `api` 与 PostgreSQL 18.4 `db`，使用命名 volume；API 镜像为
  Python 3.12 多阶段构建、非 root 运行和就绪健康检查。
- TypeScript、Expo lint、Web 静态导出、iOS/Android JavaScript bundle、后端单测、
  Uvicorn live smoke 与 Alembic offline SQL 已通过。
- Docker Desktop 4.82.0、Compose 5.3.0 已完成镜像构建、API/PostgreSQL 健康检查、
  重启、停止与命名 volume 保留验收；Alembic 真库循环通过。
- 阶段 3 后续已完成 iOS 26.5 Simulator 与 Android API 36.1 ARM64 AVD 验收；本段只
  保留当时建立骨架时的事实，不再代表当前阶段状态。

## 阶段 4/5 当前实现（2026-07-17）

- FastAPI 已稳定提供 `/api/v1` 身份、画像、目标、饮食、运动、体重、首页与 Journey
  契约；PostgreSQL/Alembic 当前 revision 为 `0002_core_api`。
- Expo 客户端已完成登录/注册/测试账号入口、画像和目标设置，以及首页、Journey、我的
  三个一级入口；页面不依赖 Taro、微信登录或微信运行时。
- 首页保留叶子卡通品牌资产，提供统一输入、确定性 Mock 候选和快捷手动记录；没有接入
  真实模型、Agent 或 RAG。
- iOS/Android 原生会话使用 SecureStore；TanStack Query 管理服务器数据；AsyncStorage
  保存按用户隔离的离线新增队列，幂等键防止恢复联网后重复写入。队列中的健康记录仍需
  在生产发布前补充本地加密、保留期限和清除策略。
- 本地常识包版本为 `1.0.0`，只包含一般营养、补水、睡眠和安全提示；未知输入不会伪造
  Agent 结果。
- iOS 与 Android 已实际完成登录、画像/目标、三类手动记录、首页聚合、Journey 历史；
  Android 另完成飞行模式排队与恢复联网自动同步。Web 静态导出通过，仍是补充形态。

## 阶段 6 当前实现（2026-07-20）

- FastAPI 新增 `/api/v1/agent/runs`、本人轨迹查询和候选确认接口；OpenAPI 快照同步。
- Agent 由确定性/结构化 Intent Router、Food/Activity/Profile/Journey/Knowledge 工具、
  Model Router、Context Builder、Recommendation 与 Weekly Summary LangGraph 组成。
- `AGENT_PROVIDER=mock`、空 key、预算 `$0` 是默认；OpenAI、DeepSeek 与自定义
  OpenAI-compatible 仅是未启用 adapter 配置，首个真实供应商仍未决定。
- PostgreSQL/Alembic 当前 revision 为 `0003_agent_rag`，新增脱敏 run/tool trace、一次性
  确认和公共知识 source/document/chunk 表；upgrade/downgrade/check 通过。
- 受控知识包 `journey-core-1.0.0` 含 4 个项目改写文档，记录来源 URL、许可备注、地区、
  版本、hash、metadata 与确定性向量；混合检索支持引用和 no-answer，未启用 pgvector。
- 移动端沿用三个一级入口：在线首页调用 Agent，多个候选逐项进入原记录表单编辑和确认；
  Journey 可生成带引用周总结；离线仍明确禁用 Agent，只保留手动记录和本地常识。
- iOS 已实际完成双意图、编辑后确认写入、首页更新和周总结；Android 已完成 Agent 历史
  查询与 API 连通。Web 静态导出、34 项后端测试、TypeScript 与 lint 均通过。

## 1. 仓库与工作树

- 远程项目：`boom080/fitness`。
- 当前分支：`main`，跟踪 `origin/main`。
- 本轮开始时存在用户已删除的 `docs/rebuild-status.md`、`docs/start-miniapp.md`，未恢复。
- 本轮开始时存在未跟踪的 `docs/JOURNEY_ROADMAP.md`，其有效内容将合并到唯一计划并退役。
- 阶段 2 已删除 `dist/`、根 `node_modules/` 和 `.swc/`；`backend/.venv/`
  仍是旧后端本地环境，不代表新架构的依赖策略。

## 2. 退役前目录结构（历史基线）

```text
.
├── src/                    # Taro/React 微信小程序源码
│   ├── pages/              # home、journey、profile、food、activity、auth、invite
│   ├── components/         # AI 估算面板、错误边界
│   ├── services/           # API 请求、认证、记录、画像、AI
│   ├── store/              # session 与本地缓存
│   ├── utils/              # 热量、趋势、分页、路由等逻辑
│   ├── styles/             # 主题和全局 SCSS
│   └── assets/             # 卡通人物、图片、Logo/SVG
├── config/                 # Taro dev/prod/env 配置
├── dist/                   # 微信构建产物
├── backend/
│   ├── app/
│   │   ├── api/routes/     # 全部为 *_mini 路由
│   │   ├── core/           # DB、安全、微信、配置、启动补列
│   │   ├── crud/           # 用户、饮食、运动、邀请码
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── schemas/        # Pydantic Schema
│   │   └── services/       # 首页、Journey、AI 与 fallback
│   ├── scripts/            # 邀请码脚本
│   └── requirements.txt    # 未锁定 Python 依赖
├── package.json            # Taro 4 + React 18
├── project.config.json     # 微信开发者工具配置
└── README.md               # 简短微信小程序说明
```

## 3. 退役前端技术栈与页面（历史基线）

### 技术栈

- React 18.3.1。
- Taro 4.0.x；依赖使用 caret 范围，CLI/运行时/预设存在 4.0.x 与 4.1.x 混合。
- Webpack 5、Babel、Sass。
- JavaScript/JSX，没有 TypeScript。
- 微信小程序构建脚本：`dev:weapp`、`build:weapp`。
- `build:h5` 脚本存在，但当前依赖中没有 H5 platform plugin。

### 页面清单

| 页面 | 源码 | 主要职责 | 迁移价值 |
|---|---|---|---|
| 首页 | `src/pages/home/main.jsx` | 今日摘要、AI 首页建议、入口 | 保留产品语义和聚合逻辑，UI 重建 |
| Journey | `src/pages/journey/main.jsx` | 多日记录、分页/加载更多 | 保留时间线语义和分页逻辑候选 |
| 我的 | `src/pages/profile/main.jsx` | 画像、目标、能量/体重相关信息 | 保留字段与产品逻辑，UI 重建 |
| 饮食 | `src/pages/food/main.jsx` | 手动记录、AI 估算、保存/删除 | 保留确认流程思想和领域规则 |
| 运动 | `src/pages/activity/main.jsx` | 手动记录、AI 估算、保存/删除 | 保留确认流程思想和领域规则 |
| 登录 | `src/pages/auth/index.jsx` | `Taro.login()` 微信登录 | 淘汰 |
| 邀请码 | `src/pages/invite/index.jsx` | 激活流程 | 是否保留产品需求尚未提出，默认淘汰 |

### 微信/Taro 强耦合

- UI 组件来自 `@tarojs/components`。
- 生命周期使用 `useDidShow`。
- 网络使用 `Taro.request`。
- 缓存使用 `Taro.getStorageSync`、`setStorageSync`、`removeStorageSync`。
- 导航使用 `switchTab`、`navigateTo`、`redirectTo`、`reLaunch`。
- 登录使用 `Taro.login()` 和微信临时代码。
- Toast、Picker、页面配置与 `project.config.json` 均属于小程序运行环境。

这些组件不能直接复制到 React Native；其业务意图可以作为重建参考。

## 4. 可复用资产与业务逻辑

### 可原样保留候选

- 已从 `src/assets/` 提取到 `assets/brand/` 的卡通人物、Logo 和插画；
  分辨率、哈希、旧引用和待确认版权状态见资产清单。
- 部分产品文案与 Journey 命名。

### 需要适配后复用

- `src/utils/daily-energy.js`：能量相关纯计算候选。
- `src/utils/weight-trend.js`：体重趋势候选。
- `src/utils/profile.js`：画像格式化/规则候选。
- `src/utils/record-display.js`、`estimate-display.js`：展示转换候选。
- `src/utils/journey-pagination.js`：分页状态候选。
- `src/utils/food-name.js`、`day.js`：纯函数候选。
- `src/styles/theme.scss`：只能作为 design token 提取来源，不能直接用于 React Native。

### 需要重构

- API client、身份状态、本地缓存和导航抽象。
- 首页/Journey 聚合与错误状态。
- 饮食和运动的 AI 候选确认流程。
- 用户画像与目标模型。

### 已在阶段 2 淘汰

- Taro 页面、组件、配置和构建产物。
- 微信登录、OpenID/UnionID、邀请码激活流程。
- 小程序专属服务与路由辅助代码。
- 旧 SQLite 数据和启动补列逻辑。

上述客户端内容已在资产、截图和规则提取完成后按清单删除。

## 5. 后端现状

### 技术栈

- FastAPI + Uvicorn。
- SQLAlchemy 同步 ORM。
- Pydantic。
- `python-jose` JWT 与 Passlib/bcrypt。
- `python-dotenv`。
- `requirements.txt` 没有任何版本约束或 lock。
- 本地 `.venv` 路径显示曾使用 Python 3.9；这不是新环境的最终版本决定。

### API 路由

`backend/app/main.py` 注册以下 `_mini` 路由：

- `auth_mini.py`
- `profile_mini.py`
- `home_mini.py`
- `food_records_mini.py`
- `activity_records_mini.py`
- `journey_mini.py`
- `ai_mini.py`

新 API 需要版本化契约和跨平台身份，不应继续沿用 `_mini` 名称。

### 服务与 CRUD

- `home_mini.py`、`journey_mini.py` 包含聚合逻辑，适合提取到应用服务。
- `food_record.py`、`activity_record.py` CRUD 可提供领域行为参考。
- `user_mini.py`、`deps_mini.py` 与微信用户和当前令牌结构耦合。

## 6. 当前数据模型

| 模型 | 关键字段 | 问题 |
|---|---|---|
| `User` | openid、unionid、nickname、goal、gender、height、weight、body_fat_rate | `openid` 必填；与微信身份强耦合；画像字段与 Profile 重复 |
| `Profile` | account、goal、reminder、unit、gender、age、height、weight、target_weight | 与 User 存在双份画像事实源 |
| `FoodRecord` | 日期、餐次、详情、地点、kcal、source_type、ai_type | 缺少更完整营养项、份量与幂等字段 |
| `ActivityRecord` | 日期、名称、地点、kcal、source_type、ai_type | 缺少时长、强度等结构化字段 |
| `InviteCode` | code、状态、使用次数、openid | 新身份方案默认不需要 |

`backend/app/main.py` 在导入时执行 `Base.metadata.create_all()`；`bootstrap.py` 直接检查 SQLite 并运行 `ALTER TABLE` 补列。当前没有 Alembic 或正式迁移历史。

## 7. AI 能力现状

### 已实现

- 食物文本热量估算。
- 运动文本消耗估算。
- 首页建议生成。
- 通过环境变量配置 qwen、deepseek、openai 和 self-hosted 候选。
- 基于能力维护模型候选列表。
- OpenAI-compatible HTTP 调用与超时处理。
- 本地关键词/规则 fallback。

### 仅为预留或未完成

- 图片分析、OCR、PDF、RAG 能力开关存在，但默认关闭。
- 没有真实向量数据库、文档摄取、Chunk、检索或引用链路。
- 没有 Intent Router、业务工具层、LangGraph 工作流或 Context Builder。
- 没有对话状态、长期记忆、工具确认、Agent 轨迹和评测集。
- 当前 AI API 仍是三类固定 LLM 功能，不属于完整 Agent 架构。

## 8. 安全、环境变量与密钥

### 已发现问题

- `backend/app/core/security.py` 硬编码开发 JWT secret。
- CORS 使用 `allow_origins=["*"]` 且允许 credentials，配置需要按环境收紧。
- `.env.example` 和 `backend/.env.example` 仅适合作为参考，需在新架构统一。
- 当前微信配置读取 App ID/Secret；退役后应移除。
- 模型候选和 API Key 读取机制存在，但缺少启动时完整校验、密钥轮换和日志脱敏测试。

未在本审计文档记录或展示任何真实密钥值。

## 9. 测试与 CI

- 仓库没有项目级前端、后端、API、Agent、RAG 或 E2E 测试。
- 检索到的测试文件均来自本地虚拟环境依赖，不是本项目测试。
- 没有 GitHub Actions。
- 没有 lint、格式化、类型检查、覆盖率或构建门禁。
- 没有 Mock 模型、隔离测试数据库或评测数据版本管理。

## 10. Docker 与部署

- 没有 `Dockerfile`、`compose.yaml`、`.dockerignore`、容器入口或健康检查。
- 当前后端以本地 Uvicorn/venv 方式运行。
- 当前数据库默认位于 `backend/journey_miniapp.db`。
- 微信端由宿主机 Taro 构建到 `dist/` 并交给微信开发者工具。
- 没有 staging/production 部署配置、备份恢复或发布流水线。

## 11. 当前可运行性

当前验证结果：

- 2026-07-16 执行 `npm run build:weapp` 成功，Taro CLI 为 `4.1.11`，仅有已有资源体积警告。
- 构建产物已在微信开发者工具 Stable `2.01.2510290`、基础库 `3.15.2`、
  iPhone 12/13 (Pro) `390×844` 模拟器中打开。
- 14 张页面、数据态、AI 候选态和网络错误态截图已保存到
  `docs/assets/legacy-ui/`。
- **不能直接运行完整业务流程**：真实微信登录请求无法连接旧 FastAPI 地址，
  因而登录、邀请码、真实数据读写和 AI 调用均未形成端到端闭环。
- 登录后的页面截图使用虚拟本地会话和缓存进入，仅用于 UI/资产退役取证。
- FastAPI 曾完成本机 smoke 启动。
- H5 构建因缺少 Taro H5 platform plugin 失败。

本次只为退役前证据重新构建和采集截图，没有为旧端修复依赖、业务或后端问题。

## 12. 迁移分类结论

### 可以原样保留

- 经版权和质量检查通过的卡通人物、Logo、插画。
- 项目名称、Journey 时间线语义和部分产品文案。

### 需要适配

- 纯计算、分页、格式化和趋势逻辑。
- 后端饮食、运动、首页与 Journey 的业务规则。
- AI fallback 的确定性降级思路。

### 需要重构

- 身份、用户画像、API 契约、数据库迁移、模型抽象和错误处理。
- Agent 输入、确认与执行轨迹。
- 移动端状态、缓存、离线和请求层。

### 已淘汰或计划淘汰

- 整个微信/Taro 表现层和构建链已淘汰。
- OpenID/UnionID、邀请码和 `_mini` API 按 ADR-020 在阶段 4 替换后淘汰。
- 当前没有 SQLite 数据文件；SQLite 配置、启动补列和硬编码安全配置仍待阶段 3/4 替换。

### 当前缺失能力

- iOS/Android/Web 新客户端。
- PostgreSQL/Alembic。
- Docker/CI/测试。
- 邮箱/用户名身份。
- Agent Router、Tools、Workflow、Context Builder、受控 RAG。
- 可观测性、评测、staging 和发布路径。

## 13. 高风险问题

1. 资产未提取便删除旧端，导致卡通形象、风格和业务规则丢失。
2. FastAPI 中保留 `_mini` 和微信身份，污染新 API。
3. User/Profile 双份画像造成 Agent 上下文矛盾。
4. 未锁定依赖与旧 Python 环境导致 Docker 和 Agent SDK 兼容问题。
5. 启动时自动改 schema，无法可靠升级和回退。
6. 模型输出直接写记录，造成错误或重复数据；新架构必须确认和幂等。
7. 把预留的 RAG 开关误认为真实 RAG 能力。
8. 图片/视频默认上传或长期保存造成隐私风险。
9. 最后才容器化，集中暴露环境差异；应先做最小基线、后做生产打包。

## 14. 阶段 7 迁移后现状补充（2026-07-20）

本文件前述章节保留旧项目审计基线；以下记录当前新架构的实际状态，避免把历史缺失项
误读为现状：

- 微信/Taro、OpenID/UnionID、邀请码、SQLite 和 `_mini` 迁移桥已按阶段 2/4 退役。
- FastAPI/PostgreSQL/Alembic、邮箱或用户名密码身份、画像/目标、核心记录 API、Expo
  三端页面和阶段 6 Agent/RAG 均已落地。
- 后端/评测现有 69 项自动化测试，后端覆盖率 91.07%；包含认证/权限、参数/错误、幂等并发、
  Agent 确认所有权、迁移、RAG ingestion 和完整公共 HTTP 闭环。
- 移动端有 5 项确定性逻辑测试和 31 项 Jest 测试，statements 覆盖率 81.46%；另有 2 条
  Playwright 核心 Web E2E 与 Web/iOS/Android JS bundle 构建检查。
- 量化评测包含 318 条合成数据，17 项门禁最终全部通过；普通 CI 固定 Mock、空 key、
  零预算和零外部成本。
- `.github/workflows/ci.yml` 已建立 backend、mobile、web-e2e 三个 job；本机 staging、
  iOS Release Simulator 和 Android Release APK 已验收。公网部署、商店签名、正式发布包
  和真实主 Agent 质量仍未完成，属于独立发布任务或 Proposed 决策。

## 15. 阶段 9 食物图片单项现状补充（更新于 2026-07-29）

- Expo 新增 `/food-image`：相机/相册、本地预览、明示上传、餐别/说明、宽区间估算、Mock
  标识、用户校正与手动记录回退；三个一级入口没有改变。
- FastAPI 新增 `/api/v1/food-images/analyses` 与独立 `backend/app/media/`。图片只在请求内存
  中处理，数据库只记录脱敏运行元数据和用户最终确认的结构化饮食记录；没有新增媒体表、
  对象存储或 migration。
- 图片与文字 Provider 分离。仓库/CI/staging 默认 Mock；Qwen `qwen3.7-flash` 只在本机、
  北京端点和独立预算下执行真实评测，DeepSeek V4 继续只用于文字 Agent。
- 评测包含 318 条合成样本、17 项 Mock 门禁、100 张调参集和 30 张密封 holdout。后端最终
  54 tests / 91.07% coverage，移动端 7 suites / 31 tests 通过。
- v1.3 增加 Journey 9×5 cm 参照卡、已知盘/碗直径、`scale_reference_used`、拍摄引导和
  30 张密封泛化 holdout。holdout 与调参集三层零重叠，得到 Top-3 76.67%、份量误差
  36.36%、热量覆盖 90%、p95 3473 ms；尺度配对 cohort 尚未建立。
- ADR-030 因此保持 Proposed，不得描述为完整视觉质量验收或参照改善已通过。

## 16. 真实模型验收现状补充（2026-08-01）

本节更新第 14 节“真实主 Agent 质量仍未完成”的历史状态：

- 当前新增能力范围收敛为文字 Agent 与食物图片候选；普通 CI 仍以 Mock、空真实 Key 和
  零预算运行，避免外部波动影响工程回归。
- 本机 `.env` 当前把文字映射到 DeepSeek `deepseek-v4-flash`，图片映射到北京区域 Qwen
  `qwen3.7-flash`；两个 `/models` 端点均确认所选 alias 可用，Key 未进入客户端或报告。
- 新增真实文字量化门禁：18 条分层意图、5 条饮食解析、5 条运动解析共 28 次调用；首轮发现
  “我的体重是多少”被误判为 weight。Router Prompt 从 `1.0.0` 升至 `1.0.1` 后复验为路由、
  饮食、运动均 100%，Provider/模型、Schema、无 fallback 和 Token 记录均 100%，p95
  1768 ms，费用 `$0.00246372`，文字门禁通过。
- 新增 3 条真实文字评测器测试与 1 条 Prompt 回归后，完整 Compose 测试为 69/69；后端覆盖率
  仍为 91.07%，318 条 Mock 样本和 17 项确定性门禁继续全绿。
- 真实公共 API 冒烟中，DeepSeek 成功生成 food/activity 两个候选；Qwen 成功把已授权苹果图
  识别为苹果候选，强制用户校正且 `image_retained=false`。该结果只证明功能链路。
- 图片质量仍以 60 张密封报告为准：总体 Top-3 67.27%、中国家庭餐 60%、Schema 98.33%，
  未达门槛。因此 Development 仅可实验性演示图片候选，Preview/Production/staging 关闭；
  当前“文字 + 图片”整体真实发布验收为 Conditional，而非全部通过。

## 17. 阶段 10 Agent v2 现状补充（2026-08-03）

- `/api/v1/agent/runs` 已从固定 `if/elif` 调度升级为单 Agent 的 Planner → Policy Guard →
  Executor → Verifier 条件图；旧 v1 分支仍可通过 `AGENT_V2_ENABLED=false` 回退。
- 服务端工具注册表固定 10 个工具及其风险/确认属性；模型计划必须通过 Pydantic Schema、
  白名单、依赖和确认 Policy，不允许动态 SQL、任意函数名、无限循环或后台自主任务。
- `AgentRunResponse` 新增 `thread_id`、结构化 `plan`、`step_results` 和 `verification`；每次
  最多 6 步、最多 1 次重规划。饮食、运动、体重仍只生成候选，必须用户确认后幂等写入。
- Alembic `0004_agent_v2` 新增 `agent_threads` 和 Agent Run 计划/验证字段；线程只保留最近
  8 条结构化摘要，不保存原始消息、图片或模型密钥，画像与业务表仍是事实源。
- 当前自动化基线为 79 条后端/评测测试、后端覆盖率 90.80%、342 条版本化样本和 22 项
  量化门禁；移动端为 31 条组件测试 + 5 条逻辑测试，另有 2 条 Web E2E。Allure、JUnit、
  Coverage 和 Agent JSON 报告由同一 CI 生成，API 测试使用 FastAPI HTTPX/TestClient。
- 真实 DeepSeek v2 门禁首轮识别出过度调用和依赖错误；Planner Prompt `2.0.1` 修正后，
  8 个任务、16 次调用的意图、Schema、工具序列、Policy、Provider/模型、无 fallback 和
  Token 记录均为 100%，p95 3112 ms、费用 `$0.00257824`。修正前后报告都保留。
- Web/iOS/Android JS 构建、2 条核心 Web E2E 和双平台 Release 模拟器安装运行通过。当前
  可表述为“Agent 增强本机作品集应用”，不得表述为公网生产、商店发布或图片质量通过。

## 18. 阶段 11 Agent v3 现状补充（2026-08-04）

- `AgentRun` 已持久化脱敏 checkpoint、Observation、恢复次数和过期时间；迁移版本为
  `0005_agent_v3`。checkpoint 不含原始消息，计划 `segment` 持久化前清空。
- 组合记录任务遇到候选后进入 `waiting_for_user`。Confirmation 只负责幂等写入并返回确认
  进度；新增 `POST /api/v1/agent/runs/{run_id}/resume` 在全部确认后显式恢复，重新读取最新
  画像、目标和记录。跨用户、未确认、过期和重复恢复均使用稳定错误响应。
- 执行闭环扩展为 Planner → Policy Guard → Executor → Observation → Verifier → Replanner；
  最多 6 步、2 次恢复，重规划仍须通过 Policy Guard。知识生成和个性化建议分别有
  `knowledge.safe_summary`、`recommendation.rules_fallback` 两条确定性替代路径。
- `AGENT_V3_ENABLED=false` 可回退 v2；候选确认与核心业务表不受影响。系统仍是单 Agent
  模块化单体，不是后台长任务、多 Agent 对话或医疗决策系统。
- 当前全量基线为 85 条测试、90.49% 后端覆盖率、362 条样本和 26 项门禁；Requests +
  Pytest + Allure 隔离网络黑盒 1/1、移动端 31+5、Web E2E 2/2 和三端 JS 构建通过。
- 真实 DeepSeek v3 固定门禁验证 4 个 checkpoint 计划和 2 个恢复选择，10 次调用总费用
  `$0.00171864`，全部门禁通过。图片质量 No-Go、公网/商店未发布等既有边界不变。

## 19. 浏览器权限与离线现状补充（2026-08-04）

- Journey App 的 Agent 工具注册表当前只包含饮食、运动、体重、画像、Journey、知识检索、
  建议和周总结等受控业务工具；共享契约中也没有 `browser`、`web.search` 或小红书工具。
- `knowledge.retrieve` 只检索项目受控知识库，模型 Provider 只负责模型调用；当前 Agent 不能
  打开通用浏览器、使用登录态、搜索小红书或把网页自动写入 RAG。
- 当前移动端使用 SecureStore 保存会话和加密密钥，用 AsyncStorage 保存加密待同步队列；
  离线可以排队新增饮食、运动、体重，也能使用确定性本地意图和内置常识。
- 画像/目标当前仍以在线 API 查询为主，离线编辑被禁用；Journey 只能读取已有 React Query
  缓存。编辑/删除的离线排队、完整本地数据副本、版本冲突和退出账号彻底清理尚未实现。
- 因此当前产品只能称为“部分离线可记录”，不能称为 local-first。目标矩阵与 UI 改造提案见
  `docs/product/LOCAL_FIRST_AI_UI_PROPOSAL.md`。其中方案 C 视觉子项已经实现，但本地数据目标仍
  为 Proposed，不能据此宣称代码已经 local-first。

## 20. 阶段 12 暖白薄荷首页现状补充（2026-08-04）

- 首页新增 `components/home-overview.tsx`，承载暖白薄荷 Hero、原版行走叶子、首屏统一输入、
  快捷提示、开放式今日指标和轻量 Agent 状态；原有 Agent 结果、候选确认、手动饮食/运动/
  体重入口及三个一级路由保持不变。
- `ScreenShell` 增加自定义 Hero 插槽但保留其他页面原有 Hero；主题固定使用浅色品牌 palette，
  不再根据系统深色模式切成暗灰方案。本次没有新增依赖。
- 在线文案明确 Agent 会归类、调用工具并在写入前确认；离线文案只承诺当前已有的手动记录、
  待同步和内置常识，不承诺离线 Agent、图片或完整画像/历史编辑。
- 320 × 844 和 390 × 844 本地 Web 手机视口视觉核对通过；修正了首轮实现中标题末字孤行、
  320 pt 标题省略和指标数字截断问题。
- 移动端当前为 33 条 Jest 组件/契约测试与 5 条逻辑测试；新增首页组件进入覆盖率统计后，全局
  statements 75.56%、branches 65.16%、functions 72.09%、lines 77.77%。核心 Web E2E 2/2、
  Web/iOS/Android Expo export 均通过。
- E2E 临时强制 API 为 Mock、空模型 Key和零预算；测试后已恢复 `.env` 选择的 DeepSeek
  Provider并确认 API healthy。没有产生真实模型调用、修改数据库 schema 或改动 Agent/RAG。
