# Journey 开发与验证说明

> 本文是运行手册，不是第二份迁移计划。阶段任务和状态只以
> [`JOURNEY_REFACTOR_PLAN.md`](JOURNEY_REFACTOR_PLAN.md) 为准。

## 已固定工具版本

- Node.js `22.23.1`、npm `10.9.8`
- Expo SDK `57`、React Native `0.86`、React `19.2.3`、TypeScript `6.0`
- Python `3.12`；lock 由 CPython `3.12.11` 解析
- PostgreSQL `18.4`、Alembic `1.18.x`
- Xcode `26.6`、iOS Simulator `26.5`、CocoaPods `1.17.0`
- Android Studio JBR `21.0.10`、Android API `36/36.1`、Pixel 9 ARM64 AVD

## 统一环境文件

```bash
cp .env.example .env
```

只在本机 `.env` 中替换开发密码；不得提交 `.env`。根 npm 脚本和 Compose 都读取
这一份文件。Expo 只会内联 `EXPO_PUBLIC_` 前缀变量，服务端和模型密钥不得使用该
前缀。

食物图片功能使用服务端与客户端两个开关，便于彻底回退入口和 API：

```dotenv
FOOD_IMAGE_ANALYSIS_ENABLED=true
FOOD_IMAGE_PROVIDER=mock
EXPO_PUBLIC_FOOD_IMAGE_ANALYSIS_ENABLED=true
```

Development、CI 和 staging 默认仍使用 Mock；Preview/Production 的 EAS profile 默认关闭
客户端入口。DeepSeek V4 Key 只供文字 Agent 使用，不得配置为 `FOOD_IMAGE_PROVIDER`。
本机 Qwen `qwen3.7-flash` 已通过独立 Key、北京端点、正数预算和无个人信息合成 Smoke；
100 张调参集和 30 张零重叠密封 holdout 的真实评测也已完成。ADR-030 仍为 Proposed：
v1.3 holdout 名称 Top-3 76.67%、单一食物份量误差中位数 36.36%，未达到 85%/≤30%；
尺度配对 cohort 尚未建立。默认/CI/staging 继续 Mock，只有全部门禁通过后才能扩大使用。

地址规则：

- iOS Simulator 与 Web：`http://127.0.0.1:8000`
- Android Emulator：未显式设置时自动使用 `http://10.0.2.2:8000`
- 真机：使用电脑局域网地址或后续 HTTPS staging；`127.0.0.1` 指向手机自身

若要使用 Android 默认值，不要在 `.env` 中设置 `EXPO_PUBLIC_API_BASE_URL`；若同一
文件需要在 iOS/Android 间切换，则在启动命令前显式覆盖该变量。

## 后端与数据库

在仓库根目录运行：

```bash
docker compose config
docker compose up --build
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
docker compose exec api alembic current
docker compose down
```

`down` 不删除命名 volume；删除 volume 需要单独授权。API 容器启动时执行
`alembic upgrade head`，随后只在显式允许时幂等创建本地测试账号；应用 import 不建表。

宿主机诊断路径使用 Python 3.12 和 `backend/requirements-dev.lock`，不要继续使用
仓库里旧的 Python 3.9 `backend/.venv`。

## API、Agent 与测试账号

API 契约见 [`API.md`](API.md)，OpenAPI JSON 位于
`packages/contracts/openapi.json`。Compose 的 local 环境默认明确启用测试账号：

- `demo@journey.local`
- `journey_demo`
- `JourneyDemo2026`

复制 `.env.example` 后应覆盖本地测试密码。production 若启用 `SEED_TEST_ACCOUNT` 会拒绝
启动。access token 默认 15 分钟，refresh token 默认 30 天并在数据库中支持轮换和撤销。

后端测试固定在独立 `journey_test` PostgreSQL 数据库运行。推荐使用 Docker test target，
避免宿主 Python 与锁定版本不一致：

```bash
docker build --target test -t journey-api-test -f backend/Dockerfile .
docker run --rm --network journey_default \
  -e PYTHONPATH=/work \
  -e APP_ENV=test \
  -e APP_SECRET_KEY=local-test-secret-at-least-32-characters \
  -e DATABASE_URL=postgresql+psycopg://journey:local-journey-db-password@db:5432/journey_test \
  -e SEED_TEST_ACCOUNT=false \
  -v "$PWD/backend:/work:ro" -w /work journey-api-test \
  pytest -q -p no:cacheprovider
```

测试命令不包含真实密钥，也不调用模型。首次使用前需在本地 PostgreSQL 创建
`journey_test` 并执行 Alembic；执行证据见 `EXECUTION_LOG.md`。

仓库与 CI 默认使用以下安全基线，复制 `.env.example` 后也不得把 key 提交到 Git：

```dotenv
AGENT_PROVIDER=mock
AGENT_API_KEY=
AGENT_API_BASE_URL=
AGENT_DAILY_BUDGET_USD=0
```

Mock 会返回结构化路由、候选、引用、轨迹和确定性降级，不发出外部模型请求。以后接入
真实供应商前，必须先确认供应商、模型映射、数据政策、地区可用性、每日预算及每个模型
的实际输入/输出单价；应用会拒绝缺少这些门禁的非 Mock 配置。外部模型统一经过
LangChain/LangGraph 与嵌入式 LiteLLM Router，不部署额外 Proxy 服务。Agent API 与确认协议见
[`API.md`](API.md)。

### Provider Profile 切换

`AGENT_PROVIDER` 是服务端开关，不是移动端设置。各供应商 Key 独立保存；只需提前完成一次
配置，之后切换 Provider 不需要修改 Agent、工具、Prompt 或 API 业务代码：

```dotenv
AGENT_PROVIDER=mock
DEEPSEEK_API_KEY=
QWEN_API_KEY=
GLM_API_KEY=
KIMI_API_KEY=
```

当前已实现 `mock`、`deepseek`、`qwen`、`glm`、`kimi`、`openai` 和通用
`openai_compatible` Profile。Qwen、GLM、Kimi 只有无密钥配置占位，未执行真实调用；启用
任一新 Profile 前必须填写其独立 Key、启用当日模型价格、正数每日预算，确认数据政策并
重跑同一套结构化输出/工具选择/降级评测。缺任一条件，API 启动会 fail-fast。

### DeepSeek V4 本机配置

官方 OpenAI-compatible 地址是 `https://api.deepseek.com`，当前模型 ID 是
`deepseek-v4-flash` 和 `deepseek-v4-pro`。用户已确认同一 API 支持二者；高频解析与查询
使用 Flash，个性化建议与周总结使用 Pro：

```dotenv
AGENT_PROVIDER=deepseek
DEEPSEEK_API_KEY=仅在本机.env填写新密钥
DEEPSEEK_API_BASE_URL=https://api.deepseek.com
DEEPSEEK_DEFAULT_MODEL=deepseek-v4-flash
DEEPSEEK_MODEL_MAP_JSON={"recommendation":"deepseek-v4-pro","weekly_summary":"deepseek-v4-pro"}
DEEPSEEK_MODEL_PRICING_JSON={"deepseek-v4-flash":{"input":0.14,"output":0.28},"deepseek-v4-pro":{"input":0.435,"output":0.87}}
AGENT_MAX_OUTPUT_TOKENS=2048
AGENT_DAILY_BUDGET_USD=0.10
```

上述价格使用 2026-07-22 官方 V4 cache-miss 美元单价；启用当天必须重新核价。Flash
默认关闭思考模式并通过 function calling 生成结构化结果；Pro 默认开启思考模式并使用
`high` effort，其结构化生成改走官方 JSON Output + Pydantic Schema，避免 thinking 与
`tool_choice=required` 冲突。单次输出默认最多 2048 Token。旧
`AGENT_API_KEY` 仅为现有本机配置提供兼容，建议后续把值迁移到 `DEEPSEEK_API_KEY`。
当前本机已创建被 Git 忽略的 `.env`，完成两次 Flash 与一次 Pro 合成数据 Smoke；Key 值
未被打印或写入仓库。
真实个人健康数据仍未获准发送。用户仍须确认已经在 DeepSeek 控制台撤销聊天中暴露的旧
Key，并明确接受健康数据发送范围后，才能把本机合成验证扩大到实际个人使用。

## 阶段 7 自动化门禁

完整的无密钥回归从仓库根目录执行：

```bash
docker compose --profile test run --rm --build test
npm run test:logic --workspace @journey/mobile
npm run test:ci --workspace @journey/mobile
npm run mobile:typecheck
npm run mobile:lint
npm run mobile:web:build
npm run mobile:e2e:web
```

Compose `test-db` 使用 tmpfs 隔离测试数据，`test` target 依次执行 migration、85 条后端/
评测测试、覆盖率门禁和 Agent/RAG 量化门禁。当前确定性基线为 362 条样本、26 项门禁、
后端覆盖率 90.49%。机器可读报告写入被 Git 忽略的 `reports/`；
版本化改进证据位于 [`../evals/reports/STAGE7_EVALUATION_REPORT.md`](../evals/reports/STAGE7_EVALUATION_REPORT.md)。

GitHub Actions 的 backend、mobile、web-e2e 三个 job 使用相同命令，上传 JUnit、覆盖率、
评测、Allure 原始结果、Web 构建和 E2E 报告。Allure 附件在写入前递归脱敏；JUnit 与
Coverage 继续保留，避免报告插件故障遮蔽基础结果。普通 CI 固定 Mock、空 key 和零预算。

本机查看 Allure 需要另行安装 Allure CLI，然后执行：

```bash
allure serve reports/backend/allure-results
```

API 白盒自动化使用 Pytest + FastAPI HTTPX/TestClient；阶段 11 另增 Requests + Pytest +
Allure 网络黑盒，访问隔离 Compose API，覆盖注册、Run、暂停、确认、Resume 和 Trace。运行：

```bash
docker compose --profile blackbox run --rm --build blackbox
```

独立浏览器闭环由 Playwright 覆盖。iOS/Android 原生 Release 安装路径已在阶段 8/10 验收。

当前 `npm audit --audit-level=high` 可通过，但报告 Expo/Jest 工具链中的 12 个 moderate
告警；不得使用 `npm audit fix --force` 跨主要版本修复。`expo install --check` 还提示 SDK
57 四个包有一个 patch 版本差异，应在阶段 8 单独验证后升级，不能与发布改动混在一起。

## Expo Development Build

```bash
npm install
npm run mobile:typecheck
npm run mobile:lint
npm run mobile:ios
npm run mobile:android
npm run mobile:web
```

首次 `mobile:ios`/`mobile:android` 会生成并编译本地 Development Build；原生生成
目录不作为业务源码维护。iOS 需要完整 Xcode 与可用 Simulator runtime，Android
需要 Android Studio/SDK、ADB 和 Emulator。Metro 与模拟器运行在宿主机，不进入
Docker。

Android Studio 已自带 JBR，但终端可能没有全局 Java。出现 `Unable to locate a Java
Runtime` 时，在当前终端设置：

```bash
export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
```

### Xcode 26.6 与 File Provider 已知问题

仓库位于 macOS `Documents` 的 File Provider 管理目录时，Expo SDK 57 的
`ExpoModulesJSI` 嵌套 SwiftPM 产物会被自动附加 Finder 扩展属性，首次构建可能报：

```text
resource fork, Finder information, or similar detritus not allowed
```

本机验收在被 Git 忽略的
`node_modules/expo-modules-jsi/apple/scripts/build-xcframework.sh` 中，为嵌套
`xcodebuild` 增加 `CODE_SIGNING_ALLOWED=NO` 后通过；最终 Journey App 仍由外层 Xcode
正常构建和签名。该改动不属于项目源码，重新安装 `node_modules` 后可能需要重新核对；
后续应优先采用 Expo 官方修复版本，不应无审查地永久维护上游补丁。

## 阶段 3 本机验收结果（历史基线）

截至 2026-07-17，Docker Desktop 4.82.0、Docker Engine 29.6.1 和 Compose 5.3.0
已经通过阶段 3 验收：镜像构建、API/PostgreSQL health、容器重启、非 root 用户、
Alembic `upgrade/downgrade/upgrade` 和 `down` 均成功；命名 volume 保留。

- iPhone 17 Pro / iOS 26.5：Development Build 安装成功；首页、Journey、我的均可切换；
  首页显示 `http://127.0.0.1:8000` 与“已连接 · local”。
- Pixel 9 / Android 16、API 36.1 ARM64：Debug APK 构建安装成功；首页、Journey、我的
  均可切换；首页显示 `http://10.0.2.2:8000` 与“已连接 · local”。
- TypeScript 与 Expo lint 通过；后端 health 测试在本阶段较早一次执行为 `4 passed`。
- 阶段 3 已结束；当前阶段状态以文档索引和迁移计划为准。
