# Journey 阶段执行日志

> 本文件记录实际执行证据，不替代迁移计划或 ADR。
> 日志按时间追加；不得为了让状态好看而删除失败记录。

## 日志模板

```markdown
## YYYY-MM-DD 阶段 N：名称

- 状态：In Progress / Completed / Blocked
- 授权范围：
- 开始 Git 状态：
- 修改文件：
- 执行命令及结果：
- 验收结果：
- 已知问题：
- 回退说明：
- 下一条建议指令：
```

## 2026-07-15 阶段 1：决策与基线固化

- 状态：Completed
- 授权范围：只更新规划和决策文档；不删除微信小程序、不改业务代码、不开始 Docker/Expo/数据库迁移。
- 开始分支：`main`，跟踪 `origin/main`。
- 开始工作树：用户此前删除 `docs/rebuild-status.md`、`docs/start-miniapp.md`；存在未跟踪 `docs/JOURNEY_ROADMAP.md`；没有业务代码改动。

### 已完成工作

- 执行 `pwd`、`git status --short --branch`、`ls -la`，确认当前目录和工作树。
- 基于实际代码核查 Taro 页面、FastAPI 路由、SQLAlchemy 模型、AI 配置、微信耦合、SQLite 启动补列、安全配置、测试/CI 和 Docker 缺失状态。
- 使用 GitHub API 核对 LangChain、LangGraph、Pydantic AI、OpenAI Agents SDK、LlamaIndex、LiteLLM、Langfuse、Phoenix、DeepEval 和 Ragas 官方仓库的维护快照。
- 建立根目录 Codex 规则、文档索引、唯一迁移计划、ADR、项目审计和 Agent 技术调研。
- 将平行的 `docs/JOURNEY_ROADMAP.md` 内容合并到唯一计划后退役。

### 本阶段明确未执行

- 未修改 `src/`、`backend/`、`config/`、依赖、数据库或环境变量。
- 未删除微信/Taro 代码或旧 SQLite 数据。
- 未创建 Docker、Expo、PostgreSQL 或 Agent 实现。
- 未 commit、push 或创建 PR。

### 验收结果

- 本地 Markdown 链接检查通过，所有相对链接目标存在。
- 阶段 1—9 均包含目标、前置、目录、任务、验收、测试、风险、回退、文件、禁止事项和下一阶段入口。
- ADR 统计：19 项 `Accepted`，7 项实现阶段再确定的 `Proposed`。
- Git 状态与 diff 复核通过：没有业务代码变化；改动只涉及文档体系，以及用户此前要求删除的两份旧文档。
- 阶段 1 验收完成，未自动开始阶段 2。

### 回退说明

本阶段新内容均为文档，可逐文件回退；用户此前删除的旧文档不属于本阶段应恢复内容。

### 下一条建议指令

阶段 1 验收后使用：

> 执行阶段 2：旧资产提取与微信端退役。严格先完成资产、截图、业务规则和删除清单，向我汇报并等待确认后再删除旧代码。

## 2026-07-16 阶段 2：旧资产提取与微信端退役

- 状态：Completed
- 授权范围：先完成卡通人物、品牌资产、参考截图、业务规则和删除清单；用户审阅后以“请按计划推进”授权实际退役。
- 基线 commit：`06b52f024547e76e1cd216e27f3ac41717dd3671`

### 已完成工作

- 执行 `pwd`、完整 `git status`、`ls -la` 并读取阶段规则。
- 清点 3 张 PNG、1 个 SVG 和导出文件，记录尺寸、格式、大小、SHA-256、引用位置和 Git 引入点。
- 将 4 个视觉文件复制到 `assets/brand/`，使用 `cmp` 和 SHA-256 验证与源文件字节一致。
- 通过原始图片检查确认叶子角色的日常、饮食和运动三个状态。
- 提取旧 SCSS 色彩、渐变、圆角、阴影、间距、字体和动效 token。
- 记录首页、Journey、我的、饮食、运动、登录和邀请码页面结构、关键文案和状态矩阵。
- 逐项评审 14 个前端 utility，记录确定性热量、日期、分页、标题清洗和确认写入规则。
- 记录旧 API 到新应用服务/Agent 能力的迁移映射。
- 区分 FastAPI 可复用、必须重构和淘汰的模块。
- 生成微信/Taro 前端、生成物、旧数据库和后端耦合模块的分批删除清单。
- 使用 Git 验证 `src/` 49 个、`config/` 4 个、根构建文件 4 个和 `backend/` 45 个文件可从基线恢复；当前源码目录没有未跟踪文件。
- 确认当前没有旧 SQLite 数据文件。

### 参考截图检查

- 初次检查时本机没有微信开发者工具；用户随后完成安装并在屏幕录制权限变更后重启 Codex。
- 重启后再次执行 `pwd`、`git status --short --branch`、`ls -la`，确认仍在项目根目录且没有业务代码变化。
- 执行 `npm run build:weapp`：Taro `4.1.11` 构建成功，仅保留已有资源体积警告。
- 使用微信开发者工具 Stable `2.01.2510290`、基础库 `3.15.2`、iPhone 12/13 (Pro) `390×844` 浅色模拟器。
- 使用微信小程序官方自动化 SDK切换路由、设置虚拟本地缓存和滚动页面；SDK 仅临时安装在被忽略的 `node_modules/.journey-automator/`，未修改根依赖清单或 lock。
- 使用仅监听 `127.0.0.1:8000` 的临时内存响应服务呈现 Food/Activity AI 候选；未写数据库、未调用真实模型，采集后已停止服务。
- 共生成并逐张目视检查 `docs/assets/legacy-ui/01` 至 `14` 的 PNG 截图。
- 删除了采集过程中的两张全桌面临时图片，避免把其他应用或个人桌面内容留在仓库。
- 未使用 AI 生成图或手工重绘冒充旧版运行截图。
- 用户补充了实际点击微信登录后的失败截图。经检查，页面显示
  `/wechat-login` 无法连接 `http://127.0.0.1:8000`，旧版不能完成真实登录。
- 已用用户提供的原始截图替换 `01-auth-default.png`，并校验复制前后
  SHA-256 均为
  `1a675cd8b2b2d6b2968a865520acaafa6e722683c4e238a020cfdd04f2f146db`。
- 更正证据口径：其他受保护页面由虚拟本地会话进入，只证明 UI 可渲染，
  不表示微信认证、邀请码或端到端业务可用。

### 实际退役

- 删除 `src/` 49 个和 `config/` 4 个已跟踪客户端文件。
- 删除 `package.json`、`package-lock.json`、`babel.config.js`、
  `project.config.json` 和仅含 `TARO_APP_API_BASE_URL` 的根 `.env.example`。
- 删除可重建的 `dist/`（39 个文件、约 1.9 MB）、`.swc/`（约 2.4 MB）
  和 `node_modules/`（40,623 个文件、约 440 MB）。
- 删除操作使用精确路径和 `find -depth -delete`/`unlink`，未使用 `rm -rf`。
- 保留 `backend/`、`assets/brand/`、`docs/`、`AGENTS.md` 和 `.git/`。
- 没有旧 SQLite 数据文件需要删除。
- 接受 ADR-020：后端微信身份与业务 `_mini` 暂作阶段 4 前迁移桥，不再新增功能。
- 重写根 README，并更新审计、计划、清单、ADR、文档索引和 Codex 阶段规则。

### 本阶段明确未执行

- 未修改 FastAPI 业务代码、模型、数据库结构或依赖。
- 未创建 Expo、Docker、PostgreSQL、Agent 或新身份实现。
- 未 commit、push、创建 PR 或修改远程仓库。

### 回退说明

- 已跟踪旧客户端可从基线 commit
  `06b52f024547e76e1cd216e27f3ac41717dd3671` 恢复。
- 品牌资产和截图保存在活动工作树；旧完整源码只通过 Git 历史回退，不建立平行 legacy 副本。

### 下一条建议指令

> 执行阶段 3：建立 Expo 骨架和最小 Docker/PostgreSQL 基线。严格只完成新工程骨架、iOS/Android/Web 最小运行、统一环境配置和后端最小容器基线，不迁移完整业务页面。

## 2026-07-17 阶段 3：新工程骨架与最小 Docker 基线

- 状态：In Progress（工程与静态构建完成；原生模拟器和 Compose 环境验收待完成）
- 授权范围：Expo 新工程骨架、iOS/Android/Web 最小运行、统一环境配置、FastAPI +
  PostgreSQL 最小容器基线；禁止迁移完整业务页面。
- 开始目录：当前 `pwd` 为 Journey 仓库根目录。
- 开始工作树：包含阶段 2 已确认的微信/Taro 删除、文档和保留资产；未覆盖、恢复、
  清理或提交这些改动。

### 环境与版本核查

- Node `22.23.1`、npm `10.9.8`、Corepack `0.34.6`。
- 系统和旧 `backend/.venv` 均为 Python `3.9.6`，不满足新基线；在 `/tmp` 下载隔离的
  CPython `3.12.11` 解析并验证 lock，没有改动系统 Python。
- Expo 官方 SDK 57 版本矩阵为 React Native 0.86、React 19.2.3、React Native Web
  0.21，最低 Node 22.13.x；本阶段据此形成 ADR-021。
- 当前只有 `/Library/Developer/CommandLineTools`，`xcrun simctl` 不可用；未发现
  Android SDK、`adb` 或 `emulator`；未发现 Docker CLI/daemon。
- 遵守阶段边界，没有安装 Xcode、Android Studio、Docker Desktop 或 Agent 框架。

### 已完成工程工作

- 创建 npm workspace 根工程、唯一 `package-lock.json`、`.node-version` 与
  `.python-version`。
- 创建 `apps/mobile/` Expo SDK 57 + Expo Router + `expo-dev-client` + TypeScript strict
  骨架；建立首页、Journey、我的三个空路由和明暗主题 Provider。
- 逐字节复制阶段 2 保留的叶子品牌图和 SVG 到客户端资产目录；复用初版颜色、间距和
  圆角 token，没有迁移完整旧页面。
- 创建 `packages/contracts/` 最小 health 契约和 `packages/design-tokens/`。
- 创建按平台选择的 API base URL：iOS/Web 默认 `127.0.0.1`、Android Emulator 默认
  `10.0.2.2`，并支持 `EXPO_PUBLIC_API_BASE_URL` 覆盖；首页加入 live health 卡片。
- 根 `.env.example` 是 Compose 与 npm 脚本共用模板；Expo 只暴露 `EXPO_PUBLIC_`
  变量，不含真实密钥。
- FastAPI 改为 `create_app()`；默认只启用 live/ready health，旧 `_mini` 路由由默认
  false 的迁移开关隔离。应用 import 不建表、不补列、不连接数据库。
- 固定 Python 3.12 依赖范围，并生成 production/dev 两份带哈希 lock。
- 创建 PostgreSQL 连接、Alembic `0001_empty_baseline`、Python 多阶段非 root
  Dockerfile、容器入口、`.dockerignore` 与只含 `api`/`db` 的 Compose。
- Compose 使用 PostgreSQL `18.4-alpine`、`/var/lib/postgresql` 命名 volume、数据库
  健康依赖和 API readiness 健康检查；没有 Redis、Celery、pgvector 或业务表。
- 创建 `docs/DEVELOPMENT.md`，记录统一环境、宿主/模拟器地址和待补验收命令。

### 执行命令及结果

- `npx create-expo-app@latest apps/mobile --template default@sdk-57 --yes`：成功。
- `npx expo install expo-dev-client` 与 `npx expo install --check`：成功，依赖匹配。
- `npm run mobile:typecheck`：首次发现无效 accessibility role、模板残留依赖和主题
  类型问题；精确移除未使用模板组件并修正后通过。
- `npm run mobile:lint`：首次由 Expo 建立 ESLint 9 配置，并发现 effect 内同步 loading
  更新；改为带取消标志的异步 health 请求后通过。
- `npm run mobile:web:build`：成功，导出 8 条静态路由。
- 临时本地静态服务器 smoke：`/`、`/journey.html`、`/profile.html` 均返回 `200`，
  验证后已停止服务器。
- `expo export --platform ios`：成功，生成 iOS Hermes bundle；这不是 Simulator 运行证据。
- `expo export --platform android`：成功，生成 Android Hermes bundle；这不是 Emulator
  运行证据。
- Python `3.12.11` 环境按 `requirements-dev.lock` 同步 42 个包：成功。
- `pytest`：`4 passed`；验证 `/health/live` 不需要数据库、数据库不可用时 readiness
  降级、secret 必填和 SQLite URL 被拒绝。
- 对阶段 3 新增/修改 Python 文件执行 Ruff check/format：通过。
- `alembic upgrade head --sql`：成功生成 PostgreSQL offline SQL，只创建并写入
  `alembic_version`。
- 宿主 Uvicorn smoke：`/health/live` 返回 `200`；在数据库未启动时
  `/health/ready` 正确返回 `503 database=unavailable`；服务已正常停止。
- 使用 PyYAML 解析 `compose.yaml`：只含 `api`/`db` 且命名 volume 路径正确；
  `sh -n` 验证容器入口成功。由于无 Docker，这不是 Compose build/up 证据。
- `npm audit --omit=dev`：报告 Expo CLI/config-plugin 依赖链中 `uuid <11.1.1` 的
  11 项 moderate；自动建议会把 `expo-splash-screen` 降到 SDK 55，属于破坏性修复，
  因此未执行 `audit fix --force`，待 Expo 上游兼容更新。

### 未完成验收与原因

- 未运行 `docker compose config/up --build/health/down`，原因是当前无 Docker。
- 未在真实 PostgreSQL 执行 Alembic `upgrade/downgrade/upgrade`，原因同上。
- 未运行 iOS Simulator，原因是只有 Command Line Tools、没有完整 Xcode/`simctl`。
- 未运行 Android Emulator，原因是没有 Android SDK/ADB/Emulator。
- 因而尚未取得 iOS/Android 调用容器 `/health/live` 的手工证据；不得把 bundle 导出
  冒充运行验收。

### 本阶段明确未执行

- 未迁移登录、画像、饮食、运动、Journey 数据页或 Agent 输入业务。
- 未创建业务数据库表、旧 SQLite 数据迁移、Agent/RAG、真实模型或真实密钥。
- 未制作 APK、iOS 发布包、生产镜像或 staging。
- 未 commit、push、创建 PR 或修改远程仓库。

### 回退说明

- Expo 骨架集中在 `apps/mobile/`，共享最小包集中在 `packages/`，可按目录精确回退。
- Alembic 是空基线，没有业务数据；Compose `down` 默认保留 volume。
- 旧微信源码仍只由 Git 历史恢复，不恢复到活动工作树。

### 下一条建议指令

> 继续阶段 3 环境验收：我已安装 Docker Desktop、完整 Xcode Simulator 和 Android
> Studio/SDK。请只运行 Compose、Alembic 空库循环、iOS/Android 三路由及 API 健康
> 连通性验收，更新执行证据；通过后结束阶段 3，不要开始阶段 4。

## 2026-07-17 阶段 3：环境验收续跑

- 状态：In Progress（Compose 与 Alembic 真库已通过；双模拟器缺少运行设备）
- 授权范围：只运行 Compose、Alembic 空库循环、iOS/Android 三路由及 API 健康
  连通性验收；通过后结束阶段 3，不进入阶段 4。
- 开始检查：再次执行 `pwd`、完整 `git status`、`ls -la`，确认仍在 Journey 根目录；
  工作树是阶段 2/3 的已知未提交改动，没有覆盖、清理、提交或恢复。

### 新环境核查

- Docker Desktop `4.82.0`、Docker Engine `29.6.1`、Compose `5.3.0` 正常可用。
- Xcode `26.6` 已激活，iOS/iOS Simulator SDK 为 `26.5`；但
  `xcrun simctl list runtimes` 为空，没有可启动 device。
- 通过 Xcode Settings → Components 只读检查确认：
  `iOS 26.5.1 + iOS 26.5 Simulator` 仍显示 `Get`，下载量约 `8.52 GB`。
- Android Studio Quail 2 `2026.1.2`、Android 36.1 platform、ADB 与 Emulator 存在；
  `emulator -list-avds` 为空，SDK 中没有 `system-images/`，也没有 AVD。
- 未擅自点击 Xcode 的大体积 Runtime 下载，也未安装 Android system image；阶段规则
  不授权在验收任务中自动安装大型组件。

### Compose 构建问题与修复

- 第一次 `docker compose up --build --detach` 成功解析配置并下载 PostgreSQL 18.4，
  但拉取 Python 镜像的 Docker Hub OAuth 请求超时；单独重试官方镜像后成功。
- 第二次构建在 `pip --require-hashes` 处失败：旧 lock 在 macOS 解析，漏掉 SQLAlchemy
  在 Linux ARM64 必需的 `greenlet`。这证明原 lock 不是容器可复现 lock。
- 使用 CPython 3.12 和 uv `--universal --generate-hashes` 重新生成 production/dev lock；
  `greenlet 3.5.3` 及跨平台 marker/hashes 已进入两份 lock。
- 一次从仓库根目录直接运行 `pytest backend/tests` 因 Python import path 不含
  `backend/` 而收集失败；切换到 `backend/` 按项目配置运行后 `4 passed`，Ruff 通过。

### Compose 与 API 验收证据

- `docker compose config`：通过；只包含 `api` 与 `db`，数据库命名 volume 挂载到
  PostgreSQL 18 的 `/var/lib/postgresql`。
- `docker compose up --build --detach`：修复 universal lock 后成功。
- API 与数据库容器均为 `healthy`；`/health/live` 和 `/health/ready` 均返回 `200`，
  ready 响应包含 `database=ok`。
- API 容器内 `id` 为 `uid=999(journey) gid=999(journey)`，验证非 root 运行。
- 真库版本为 PostgreSQL `18.4`、Linux ARM64；Alembic 当前版本为
  `0001_empty_baseline (head)`。
- 容器 restart 后 ready 仍为 `200`，Alembic revision 保持 head。
- `docker compose down` 成功，容器和网络已移除；没有使用 `-v`，命名 volume
  `journey_journey_postgres_data` 仍保留。

### Alembic 真库循环

- 显式执行 `alembic upgrade head`：成功。
- 执行 `alembic downgrade base`：成功；版本查询返回 `base`。
- 再次执行 `alembic upgrade head`：成功；容器和 SQL 查询均返回
  `0001_empty_baseline`。
- 本阶段仍只有空基线，没有创建阶段 4 业务表或迁移旧数据。

### 未完成门禁

- iOS：没有 Simulator Runtime/device，无法安装 Development Build、展示三个路由或
  验证 `127.0.0.1:8000/health/live`。
- Android：没有 system image/AVD，无法启动 Emulator、展示三个路由或验证
  `10.0.2.2:8000/health/live`。
- 已有 iOS/Android Hermes bundle 只能证明 JS bundle 成功，不能替代运行证据。
- 因两项模拟器门禁未通过，阶段 3不得标记 `Completed`，阶段 4不得开始。

### 下一条建议指令

> 继续阶段 3 双模拟器验收：我已在 Xcode Components 下载 iOS Simulator Runtime，
> 并在 Android Studio Device Manager 安装 system image、创建并启动 AVD。请只验证
> iOS/Android 的首页、Journey、我的三个路由及容器 API 健康连通性；通过后结束阶段
> 3，不要开始阶段 4。

## 2026-07-17 阶段 3：双模拟器最终验收

- 状态：Completed。
- 授权范围：只完成 Compose/Alembic、iOS/Android 三路由和 API 健康连通性验收，
  更新执行证据；没有开始阶段 4。
- 开始检查：执行 `pwd`、`git status`、`ls -la`，确认位于 Journey 根目录；既有阶段
  2/3 未提交改动保持不变，没有覆盖、清理、提交或 push。

### 环境与后端复核

- Xcode `26.6` 已识别 iOS `26.5` Runtime，iPhone 17 Pro 成功 Booted。
- Android `Pixel_9` AVD 使用 Android 16/API 36.1 ARM64，ADB 状态为 `device`。
- `docker compose up --build --detach` 成功，API 与 PostgreSQL 容器均为 `healthy`。
- `/health/live` 返回 `200 status=ok`；`/health/ready` 返回 `200 database=ok`。
- API 容器为 `uid=999(journey)` 非 root；数据库为 PostgreSQL `18.4` ARM64。
- 再次执行 Alembic `upgrade head → downgrade base → upgrade head` 成功，最终 revision
  为 `0001_empty_baseline (head)`；没有创建阶段 4 业务表。

### Android Emulator 证据

- 第一次构建发现终端无 Java；改用 Android Studio 自带 JBR `21.0.10` 后通过，无需
  安装第二套 JDK。
- Gradle `9.3.1` 首次构建成功，耗时约 `10m 12s`，生成并安装 Debug APK；构建使用
  `compileSdk/targetSdk 36` 和 `arm64-v8a`。
- ADB 界面树与截图确认首页、Journey、我的三个一级路由均实际显示并可切换。
- 首页显示 `http://10.0.2.2:8000` 和“已连接 · local”，证明客户端实际请求容器
  `/health/live` 成功。

### iOS Simulator 证据

- Expo 首次安装 Homebrew 官方 CocoaPods `1.17.0`，随后 `pod install` 成功。
- 首次 Xcode 构建遇到 `ExpoModulesJSI.framework: resource fork, Finder information,
  or similar detritus not allowed`。原因是 `Documents` 目录的 File Provider 自动给嵌套
  SwiftPM 产物附加 Finder 扩展属性。
- 在被 Git 忽略的 ExpoModulesJSI 构建脚本中仅为嵌套框架构建增加
  `CODE_SIGNING_ALLOWED=NO` 后，XCFramework 与 Journey App 构建成功；最终 App 仍由
  外层 Xcode 正常构建。此为本机构建 workaround，不是业务源码或依赖升级。
- Development Build 已安装到 iPhone 17 Pro。可视化验收确认首页、Journey、我的均
  实际显示并可切换。
- 首页显示 `http://127.0.0.1:8000` 和“已连接 · local”，证明客户端实际请求容器
  `/health/live` 成功。

### 最终检查与边界

- `npm run mobile:typecheck`：通过。
- `npm run mobile:lint`：通过。
- 本次末尾直接运行系统 `python3.12 -m pytest` 因系统解释器未安装 pytest 而未启动；
  本阶段代码测试此前已按锁定开发环境完成 `4 passed`，本次没有修改后端源码。
- 没有迁移业务页面、实现身份/画像/业务 API、创建业务表、接入 Agent/RAG、制作发布
  包、使用真实密钥、提交、push 或创建 PR。
- 阶段 3 全部门禁通过并结束；阶段 4 保持 Not Started。

### 下一条建议指令

> 执行阶段 4：身份、画像与核心业务 API。开始前先读取 AGENTS.md、文档索引、阶段 4
> 清单和相关 ADR；严格只实现新身份、用户画像、核心业务数据模型与稳定 API 契约，
> 不迁移完整移动端页面，不接入 Agent/RAG。完成阶段 4 验收后停止，不开始阶段 5。

## 2026-07-17 阶段 4：身份、画像与核心业务 API

- 状态：Completed。
- 授权范围：只实现邮箱/用户名密码身份、测试账号、画像、目标、核心业务数据模型与
  `/api/v1`；不迁移移动端完整页面，不接 Agent/RAG，不开始阶段 5。
- 开始检查：执行 `pwd`、完整 `git status`、`ls -la`；确认位于 Journey 根目录，
  阶段 2/3 的既有未提交改动保持不变，没有覆盖、清理、提交或 push。

### 架构与实现

- 接受 ADR-022：UUID 主键、UTC 时间戳、IANA 用户时区派生业务日期、统一错误 envelope、
  request ID、分页与 OpenAPI `1.0.0` 契约。
- 建立 User、Identity、PasswordCredential、Profile、Goal 单一事实源；邮箱和用户名映射
  到同一 User，`phone` 仅为未来身份扩展点，没有短信接口。
- 密码使用 bcrypt cost 12；access/refresh 默认 15 分钟/30 天。refresh 绑定数据库
  session、每次轮换，重放旧 token 会撤销 session；注销立即撤销。
- 已知账号连续 5 次失败锁定 5 分钟；登录错误不暴露账号是否存在。IP/设备级限流留给
  后续 staging 网关，不引入 Redis。
- 建立 FoodRecord、ActivityRecord、WeightRecord、Goal、AuthSession、IdempotencyKey、
  AuditEvent schema；Food 包含份量、单位、热量、宏量营养与来源，Activity 包含时长、
  强度、热量与来源。
- 建立 Profile、Goal、Food、Activity、Weight、Home、Journey 应用服务与仓储边界；
  首页/Journey 为确定性查询聚合，不保存第二份汇总。
- 饮食、运动、体重创建支持 Idempotency-Key；同 key 不同 payload 返回 409，并通过
  数据库唯一约束处理并发竞争。写入、幂等结果和审计事件同事务提交。
- local Compose 显式启用幂等测试账号；production 若启用测试账号会拒绝启动。
- 新增 `0002_core_api` migration、OpenAPI snapshot、共享 TypeScript 契约和 API 文档。
- ADR-020 标记 Superseded；删除旧 `_mini` 路由/Schema/服务、微信身份、邀请码、
  SQLite 补列、旧 AI 客户端/fallback 和邀请码管理脚本。没有接入新的 Agent 实现。
- 移除不再直接需要的 passlib/python-multipart 顶层依赖，以 uv `0.8.22` 在临时 Docker
  环境重新生成 universal hash lock；uv 工具本身没有加入项目依赖。

### 数据库、测试与契约证据

- 创建独立 `journey_test` PostgreSQL 数据库；测试前后 TRUNCATE 业务表，和 local
  `journey` 数据库隔离。
- `journey_test` 执行 `upgrade head → downgrade base → upgrade head` 成功，最终 revision
  为 `0002_core_api`；`alembic check` 返回 `No new upgrade operations detected`。
- 新锁重新构建 Docker test target 成功；pytest `19 passed`。覆盖邮箱/用户名登录、重复
  身份、密码锁定、token 轮换/重放/注销、测试账号环境门禁、画像/目标、三类记录、
  所有权、参数异常、顺序与并发幂等、CORS 契约头、首页/Journey 聚合和 OpenAPI
  snapshot。
- Ruff check/format：60 个活动 Python 文件通过。
- `npm run mobile:typecheck` 与 `npm run mobile:lint`：通过；阶段 4 没有修改移动页面。
- 后端与共享目录的 OpenAPI JSON 字节一致，API 只包含 health 和 `/api/v1`；没有
  `_mini`、wechat、AI 或 RAG 路由。
- `git diff --check`：通过。

### Compose 实际验收

- `docker compose up --build --detach` 使用新 production lock 构建成功；API/PostgreSQL
  均为 healthy，API 仍以 `uid=999(journey)` 非 root 运行。
- local 主库由 `0001_empty_baseline` 自动升级到 `0002_core_api`；测试账号只生成一次，
  identities 为 `demo@journey.local` 与 `journey_demo`。
- `/health/ready` 返回 `200 database=ok`；使用测试账号实际调用 `/auth/login` 与
  `/auth/me` 均返回 200，且 request ID 正确透传。响应 token 未写入日志或文档。
- Compose 当前保持运行，便于用户检查 API；没有创建 staging、发布镜像或云资源。

### 已知边界与回退

- Compose 默认测试密码只用于本机演示，复制 `.env.example` 后应覆盖；不得用于
  staging/production。
- 本阶段没有客户端安全存储和登录页面；它们属于阶段 5。
- 本阶段没有 Agent、RAG、模型密钥、图片、语音、视频或手机号登录。
- 可执行 Alembic downgrade 回到阶段 3 空基线；当前数据只有无价值开发测试账号。
  旧微信后端只从 Git 历史回退，不恢复到活动工作树。
- 未 commit、push、创建 PR 或修改远程仓库。

### 下一条建议指令

> 执行阶段 5：移动端核心页面。严格基于已稳定的 `/api/v1` 和共享契约，实现登录、
> 画像/目标、首页、Journey、我的以及手动饮食/运动/体重流程；保持 UI 品牌气质，
> 不接入 Agent/RAG，不修改后端范围。完成 iOS/Android 核心流程验收后停止，不开始阶段 6。

## 2026-07-17 阶段 5：移动端核心页面

- 状态：Completed。
- 授权范围：只实现基于既有 `/api/v1` 的登录、画像/目标、首页、Journey、我的和手动
  饮食/运动/体重流程；没有修改后端范围，没有接入 Agent/RAG，没有开始阶段 6。
- 开始检查：执行并展示 `pwd`、完整 `git status`、`ls -la`，确认位于 Journey 根目录；
  阶段 2—4 的既有未提交改动保持不变，没有清理、强制重置、提交、push 或创建 PR。

### 架构与实现

- 接受 ADR-023：Expo Router protected routes；Auth Context 只管理会话；TanStack Query
  管理服务器状态；表单保持局部状态，不引入 Redux/Zustand 或复杂表单框架。
- 原生 access/refresh token 使用 Expo SecureStore，Web 补充形态使用当前标签页
  `sessionStorage`；401 会执行单次 refresh 轮换并重试，失败后清除会话回到登录页。
- 登录页支持邮箱或用户名登录、注册和一键本地测试账号。测试账号为
  `demo@journey.local` / `journey_demo`，密码只来自既有 local 开发配置。
- 首页、Journey、我的保持三个一级入口并复用叶子卡通资产；提供画像、目标、三类记录
  新增/编辑/删除确认、7/30 天历史、趋势、确定性周总结、loading/empty/error/retry 状态。
- 首页统一输入只运行本地确定性 Mock 规则，生成饮食、运动、体重或知识候选；写入前必须
  打开表单由用户确认。未知输入返回无法识别，不伪造 Agent 结果。
- 新增本地常识包 `1.0.0` 和安全边界；共享契约预留 transport-neutral
  `AgentUiEvent` v1，但没有绑定模型 SDK 或新增 Agent API。
- AsyncStorage v2 离线队列按用户 ID 隔离，保留稳定 `Idempotency-Key`；不保存密码或
  令牌，编辑、删除、画像和目标修改离线禁用。队列 payload 含健康记录，生产前仍需补充
  本地加密、保留期限和清除策略。
- Android AVD 能访问局域网 API 但公共互联网 validation 不稳定，因此 NetInfo 使用
  `isConnected` 控制离线 UI，实际 API 网络失败仍进入队列，避免把公共互联网探测结果
  错当成局域网 API 不可达。
- 使用系统深浅模式与共享语义 token；SafeAreaView、ScrollView、键盘处理、动态字体上限
  和可访问性标签覆盖核心页面。

### 自动化与构建证据

- `npm run test --workspace @journey/mobile`：5/5 通过，覆盖饮食、运动、体重、版本化本地
  知识和未知意图；首次发现知识问题被运动关键词抢占，修正优先级后通过。
- `npm run mobile:typecheck`：通过；曾误运行不存在的根 `typecheck` script，改用仓库声明的
  `mobile:typecheck` 后通过。
- `npm run mobile:lint`：通过；`npx expo install --check` 返回依赖已匹配 Expo SDK。
- `npm run mobile:web:build`：通过，静态导出 12 个路由；Web 令牌仅当前标签页有效，未将
  Web 作为主演示路径。
- `docker compose ps`：API/PostgreSQL 均 healthy；`/health/ready` 返回
  `status=ok, database=ok`。本阶段没有改动后端源码、迁移或 OpenAPI。

### iOS Simulator 验收

- iPhone 17 Pro / iOS 26.5 Development Build 构建、安装和运行成功；原生
  SecureStore、NetInfo、AsyncStorage 均完成 CocoaPods 链接。
- 使用一键测试账号登录，实际设置女性、2000-01-01、170 cm、公制、减脂、目标体重
  62 kg、每日能量 1800 kcal。
- Mock 饮食候选打开预填表单后经用户确认，实际新增 520 kcal 饮食；实际新增 30 分钟
  运动并将消耗从 180 编辑为 200 kcal；实际新增 65.5 kg 体重。
- 首页更新为摄入 520、运动 200、净值 320 kcal；Journey 7 天时间线、趋势、三类详情与
  编辑入口通过；删除确认弹窗通过并选择取消，未误删验收数据。
- 视觉基线：`docs/assets/stage5-ui/ios-journey.png`。

### Android Emulator 验收

- Pixel 9 / Android 16 API 36.1 ARM64 Development Build 构建安装成功；第一次因终端没有
  `ANDROID_HOME` 失败，显式使用 Android Studio SDK/JBR 后 Gradle 构建成功。
- AVD 快照启动曾出现 goldfish pipe 错误，改为不加载/保存损坏快照的 cold boot 后恢复；
  未 wipe 用户数据。Dev Client 强制 reload 后曾丢失开发服务器，恢复 `adb reverse` 并
  重新选择当前 Metro 地址后正常。
- 一键测试账号登录后，首页读取既有 520/200/320 kcal；Journey 显示饮食、运动、体重
  时间线；我的显示账号、女性、170 cm、减脂目标与 1800 kcal。
- Android 实际新增 `Android_salad` 350 kcal、`Android_walk` 20 分钟/100 kcal 和
  66 kg 体重；首页最终更新为摄入 870、运动 300、净值 570 kcal。
- 仅在 AVD 内启用飞行模式，界面明确显示 Agent 不可用；离线新增 66.1 kg 进入队列。
  恢复网络后自动同步，最新体重变为 66.1 kg，待同步为 0 条；随后保持网络在线。
- 视觉基线：`docs/assets/stage5-ui/android-home-final.png`、
  `docs/assets/stage5-ui/android-journey.png`、`docs/assets/stage5-ui/android-profile.png`。

### 已知边界、回退与下一阶段

- Node 原生测试会提示 package 未声明 ESM 的性能 warning；不影响 5 项通过。Web export
  会提示根 `.env` 不存在并按默认 local 配置继续，这是当前预期开发行为。
- 阶段 7 才引入完整组件测试、API Mock、E2E 与视觉回归自动化；本阶段证据为纯函数单测、
  TypeScript/lint/Web 构建和双模拟器实际流程矩阵。
- 当前只有确定性 Mock 与本地常识，没有真实 Agent、RAG、模型调用、流式执行、图片、
  语音、视频、手机号或 HealthKit/Health Connect。
- 离线队列 payload 属于敏感健康数据；当前仅用于本机开发验收。阶段 8 生产发布门禁必须
  决定并验证本地加密、保留期限、注销清除与设备备份策略。
- 回退可按 `apps/mobile/src/`、共享契约/design token 和新增 Expo 依赖精确撤销；后端
  `/api/v1`、PostgreSQL schema 与数据不需要回退。
- 阶段 5 全部门禁通过并结束。阶段 6 保持 Not Started；只有用户明确授权，并重新核对
  Agent 框架版本、预算、供应商和数据政策后才可开始。

## 2026-07-20 阶段 6：Agent 与 RAG

- 状态：Completed。
- 授权范围：复用阶段 4 `/api/v1`、应用服务与数据所有权规则，以及阶段 5 已确认的三个
  一级入口和 UI；实现可测试、可解释的意图路由、工具调用、结构化输出、受控 RAG、轨迹
  与失败降级。模型 API key 按用户要求保持为空；没有开始阶段 7。
- 开始检查：执行并展示 `pwd`、完整 `git status`、`ls -la`；确认位于 Journey 根目录，
  阶段 2—5 的既有未提交改动保持不变，没有清理、强制重置、提交、push 或创建 PR。

### 开始前技术、预算与数据政策复核

- 实施日重新核对官方发布与文档后，锁定 LangChain `1.3.14`、
  `langchain-openai 1.3.5`、LangGraph `1.2.9`、Pydantic `2.13.4` 和
  OpenTelemetry API `1.43.0`；LangChain/LangGraph 为 MIT，OpenTelemetry 为
  Apache-2.0。版本与来源记录在 `AGENT_TECH_RESEARCH.md`。
- 核对 OpenAI、DeepSeek 与 Anthropic 的官方价格/数据政策。OpenAI API 默认不用于训练，
  但默认滥用监控日志最长保留 30 天；Anthropic 默认保留期、DeepSeek 地区和政策仍需用户
  在真实接入前确认。首个真实供应商和能力到模型的映射保持 `Status: Proposed`。
- 默认配置为 `AGENT_PROVIDER=mock`、空 `AGENT_API_KEY`、空 base URL、每日预算 `$0`、
  输入/输出单价 `$0`。非 Mock 配置缺少 key、模型、正预算或实际价格时会在启动时拒绝；
  OpenAI-compatible 供应商还必须提供 base URL。
- 本阶段真实外部模型请求为 `0`，外部 Token 为 `0`，外部成本为 `$0`；没有在客户端、
  仓库、测试或执行日志中写入真实密钥。

### Agent、工具与写入安全

- 新增确定性多意图 Router，支持 food、activity、weight、profile、history、knowledge、
  recommendation、weekly summary 与 clarify；医学诊断/治疗类高风险输入只能进入知识安全
  回答，不生成记录候选。
- Food、Activity、Weight 工具只解析并返回结构化候选；Profile 与 Journey 工具复用阶段 4
  service 做只读查询。Agent 不直接写业务表，也不绕过所有权与参数校验。
- 候选使用 15 分钟签名确认令牌；用户可在阶段 5 表单中编辑，确认端点再校验 user、run、
  candidate、kind、token hash、过期、单次使用和 `Idempotency-Key`，随后复用阶段 4 service
  与审计事务写入。未确认候选不会产生业务记录。
- Recommendation 和 Weekly Summary 使用 LangGraph 的 context → retrieve → generate 节点；
  直接知识问答使用同一检索与引用校验边界。响应包含有序事件、意图、候选、引用、provider、
  model、耗时、Token、成本和降级状态；当前采用单响应事件序列，不提前引入 SSE。
- 模型适配器支持 Mock、OpenAI、DeepSeek 和通用 OpenAI-compatible 入口，并按能力映射模型；
  包含超时、有限重试、每日数据库预算门禁、Pydantic 结构化校验和确定性 fallback。
- run 表只保存原始输入 SHA-256 与字符数，不保存原始 prompt；工具轨迹保存净化后的摘要，
  不保存候选名称、确认 JWT 或原始健康文本。轨迹查询仅限 run 所有者。
- Prompt、Schema、知识库均有独立版本：`journey-agent-1.0.0`、
  `journey-agent-schema-1`、`journey-core-1.0.0`；模型调用和工作流节点均建立 OTel span。

### RAG 与数据边界

- 新增 4 份 Journey 自编中文摘要知识，分别记录来源 URL、地区、许可说明、文档版本、内容
  hash、chunk 元数据和激活状态；主题覆盖饮食、运动恢复、睡眠和安全边界。
- ingestion 支持幂等、稳定 chunk ID、文档版本替换、来源停用和级联清除。第一版只处理
  仓库内受控公共知识，不抓取网络，不将个人画像、历史或对话写入向量索引。
- 检索使用 PostgreSQL JSON 中的确定性 96 维字符/双字向量加主题词权重，返回可验证引用；
  当前规模不启用 pgvector 或独立向量服务。无相关知识时返回明确 no-answer/fallback。
- 用户画像、当日数据和近期趋势由结构化最小上下文即时读取，设置约 1800 Token 上限；
  跨模型长期记忆仍以数据库事实和经用户确认的摘要为准，不依赖供应商私有会话状态。

### 数据库、API 与自动化证据

- 新增 `0003_agent_rag`，创建 agent run、tool trace、confirmation、knowledge source、document、
  chunk 六类表。独立测试库执行 `upgrade head → downgrade 0002_core_api → upgrade head` 成功，
  最终 revision 为 `0003_agent_rag`；`alembic check` 返回
  `No new upgrade operations detected`。
- 新增 `POST /api/v1/agent/runs`、`GET /api/v1/agent/runs/{run_id}` 与
  `POST /api/v1/agent/confirmations/{candidate_id}`；重新导出后端和共享 OpenAPI snapshot，
  两份契约一致。
- 最终 `pytest -q -p no:cacheprovider` 为 `34 passed`。覆盖意图、工具选择/参数、结构化
  输出、LangGraph 节点、确认所有权/单次使用/幂等、局部失败、模型超时与非法 JSON 降级、
  引用、无答案、安全边界、轨迹隐私和 OpenAPI 回归。
- 意图基线数据集 12/12 命中，准确率 100%，超过当前 90% 门禁；RAG 基线 4/4 的
  Recall@3 为 100%，超过当前 75% 门禁。这里只是阶段 6 小型回归基线，阶段 7 必须扩充
  数据集、困难负例、分组指标、延迟/成本阈值和持续报告。
- Ruff check/format：78 个活动 Python 文件通过；`npm run mobile:typecheck`、
  `npm run mobile:lint` 通过；Web 静态导出 12 个路由成功。
- 依赖锁首次尝试使用不合适的 uv 镜像/命令失败，改为 Python 3.12 bookworm uv 环境和
  `uv pip compile --universal --generate-hashes` 后成功。一次将 Ruff 命令误交给 API
  entrypoint，临时容器启动后已停止；未计为测试证据。
- 第一轮新增测试出现 7 个失败，暴露事件 kind 重复、Router 关键词误判、中文短查询召回和
  OpenAPI 快照过期；逐项修正后才取得上述 34 项通过，失败记录未被隐藏。
- 最终 Compose 重建后立即请求 health，第一次因 Uvicorn 尚在启动而得到 `curl 52`；等待
  容器标记 healthy 后 live/ready 均通过。第一次轮询脚本误用 zsh 只读变量 `status`，改用
  `health_state` 后成功，不影响容器或代码。
- 最终 Ruff 回归首次在只读源码挂载中因无法创建 `.ruff_cache` 退出；使用
  `ruff --no-cache` 重跑 check/format 后 78 个文件全部通过。一次配置取证使用了错误的
  price 属性名，按 Settings 中实际的 `agent_input_usd_per_million` / output 字段更正后，
  验证 Mock、空 key、预算与两项单价均为 0。

### Compose、真实 API 与双模拟器证据

- production/test 镜像重建成功；Compose 将 local 主库从 `0002_core_api` 升级到
  `0003_agent_rag`，API/PostgreSQL 均 healthy，`/health/live` 与 `/health/ready` 返回
  `status=ok`、`database=ok`。
- 使用测试账号实际调用 Agent：饮食输入返回候选，确认后写入一条 `source=agent`、
  321 kcal 记录；owner-only trace 返回版本、Token、耗时、成本和工具摘要。整个过程使用
  Mock，成本 `$0`。
- iPhone 17 Pro / iOS 26.5：输入“晚餐吃了苹果 88 千卡，然后散步 20 分钟”返回饮食和
  运动两个候选；把饮食改为 90 kcal 并显式确认后首页摄入从 321 更新到 411 kcal，运动
  仍为 0，证明未确认候选没有写入。Journey 周总结返回两个受控知识引用。
- Pixel 9 / Android 16 API 36.1 ARM64：通过 `adb reverse` 连接 Metro/API，输入
  “Journey”后路由到 history，返回最近两个有记录日期；界面显示 Mock、延迟与 `$0` 成本。
- 视觉证据：`docs/assets/stage6-ui/ios-home-initial.png`、
  `ios-weekly-summary.png`、`android-home-initial.png`、`android-agent-history.png`。
- Android Dev Client 初次需要重新选择当前 Metro 地址；恢复后完成验收。视觉证据完成后
  Mac 曾进入锁屏，自动化工具按安全规则停止；不影响已取得的双端证据。

### 已知边界、回退与下一阶段

- 真实供应商、模型映射、外部数据传输、每日预算和单价尚未获用户确认；不得仅填 key 就
  绕过这些门禁。图片、语音、视频、体脂娱乐估算和动作纠正仍属于阶段 9 Backlog。
- 阶段 6 未实施完整评测平台、CI、E2E、性能压测或真实模型质量基线；这些属于阶段 7。
- 可关闭 Agent 路由继续使用阶段 5 手动表单和本地常识；数据库可将
  `0003_agent_rag` downgrade 到 `0002_core_api`，不影响阶段 4 核心业务 schema。不得通过
  手工删表回退。
- 阶段 6 全部门禁通过并结束。阶段 7 保持 Not Started，只有用户明确授权后才可开始。

### 下一条建议指令

> 执行阶段 7：量化评测、自动化测试与 CI。严格基于阶段 6 已版本化的 Prompt、Schema、
> 知识库和小型基线数据集，扩充 Agent/RAG 评测、后端与移动端自动化、核心 E2E 和
> GitHub Actions；继续使用 Mock，不配置真实模型密钥。完成验收后停止，不开始阶段 8。

---

## 2026-07-20：阶段 7——量化评测、自动化测试与 CI

### 范围与安全基线

- 开始前执行 `pwd`、`git status`、`ls -la`；目录为当前 Journey 仓库，已有未提交内容均为
  阶段 2—6 连续迁移资产，没有强制覆盖、清理、提交、push 或 PR。
- 全程固定 `AGENT_PROVIDER=mock`、`AGENT_API_KEY=`、预算与单价为 0；凭据模式扫描未发现
  provider token。未读取或写入真实用户健康数据。
- 只实施阶段 7；未部署 staging、未制作签名包、未接入真实模型，也未开始阶段 8。

### 量化数据与失败—改进—回归

- 新增确定性数据生成器和评测器，共 296 条：路由 100、食物 50、运动 50、混合 20、
  高风险 20、失败降级 20、RAG 36（其中 no-answer 12）。
- 首轮 `baseline-before.json` 记录 39 个失败：意图 7、运动参数 2、引用检查 24、召回 3、
  no-answer 3。意图 94%、高风险 95%、Recall@3 87.5%、no-answer 75% 未全部达门槛。
- 按失败分布收紧写意图/风险路由、补充运动词、增加检索域门禁和主题别名；同时修复
  UUID/string 引用比较造成的 24 个评测器假失败，并纠正 2 条与既定规则冲突的金标。
- 最终 13 项全部通过：意图、混合意图、工具选择、食物/运动 Schema 与参数、高风险、
  降级、Recall@3、引用支持率和 no-answer 均为 100%；P95 0 ms（本地小知识库、毫秒取整），
  失败 0，外部成本 `$0`。完整限制和对比见
  `evals/reports/STAGE7_EVALUATION_REPORT.md`。

### 后端、数据库与 Compose

- 新增核心公共 HTTP E2E：画像 → 目标 → Agent 饮食/运动候选 → 确认写入 → 体重 →
  首页/Journey → 建议 → 周总结 → 轨迹，并再次验证未确认候选不写库。
- Compose 新增 tmpfs `test-db` 和 test target，报告写入 `reports/`。首次运行暴露容器
  `PYTHONPATH` 缺失；修正后又发现关闭内置受控知识导致 10 个 fixture 错误，最终明确
  `SEED_BUILTIN_KNOWLEDGE=true`，它不等同于外部模型调用。
- 最终 `docker compose --profile test run --rm --build test`：35 passed，7—12 秒量级，
  后端覆盖率 90.96%（门槛 70%），13 项 Agent/RAG 门禁通过。
- 独立 Alembic `0003 → 0002 → 0003` 与 `alembic check` 通过，无待生成 schema 操作。
- Ruff check/format 覆盖 `backend` 与 `evals`，81 个 Python 文件通过；生产与 test Docker
  target 均构建通过，Compose 普通/test 配置解析通过，API ready 为 database `ok`。

### 移动端与核心 E2E

- 使用 Expo SDK 57 对应的 Jest 29、jest-expo 57、React Native Testing Library 14 和
  Playwright 1.61；新增登录、首页 Agent、UI 状态、API/网络和布局契约测试。
- `test:logic`：5 passed；Jest：5 suites / 20 tests passed。覆盖率为 statements 81.18%、
  branches 70%、functions 73.13%、lines 84.02%，高于 65/55/60/65 门槛。
- TypeScript、Expo lint、Web 12 路由静态导出、iOS bundle 和 Android bundle 全部通过。
- Playwright 首轮发现保存画像后直接路由缺少浏览器 history 的等待假设；后续两轮分别
  暴露“跑步”文本选择器歧义与测试账号历史记录重复。改为显式返回目标路由、可访问角色
  选择器和允许重复的幂等断言，没有清库。最终核心 E2E `1 passed (4.0s)`。

### GitHub Actions 与供应链检查

- 新增 `.github/workflows/ci.yml` 的 backend、mobile、web-e2e 三个 job；包含锁文件安装、
  PostgreSQL service、Ruff、Alembic、pytest/coverage、量化评测、Docker build、Jest、类型、
  lint、Web/iOS/Android bundle、Playwright 和报告上传。
- Actions 固定只读权限、并发取消、Mock/空 key/零预算。使用当日官方稳定 major：
  checkout v7、setup-node v7、setup-python v6、upload-artifact v7。
- Node YAML 解析确认三个 job 语法结构存在；所有等价命令已在本机与隔离容器通过。因任务
  明确禁止 push，本轮没有触发 GitHub 远端 runner，首次远端运行留待以后获授权提交。
- `npm audit --audit-level=high` 退出 0；仍有 Expo/Jest 工具链 12 个 moderate 告警，不能用
  `--force` 跨 major 修复。`expo install --check` 提示四个 SDK 57 包差一个 patch，阶段 7
  不混入依赖升级，留待阶段 8 单独验证。

### 阶段结论与回退

- 阶段 7 全部门禁通过并结束；ADR-025 接受确定性零密钥 CI、Web 核心 E2E 与原生 bundle
  边界。关闭新增 CI 不影响运行时；Agent 可继续回退到 Mock/手动表单，数据库仍通过
  migration 回退，禁止手工删表。
- 阶段 8 保持 Not Started。开始条件是用户明确授权 staging、构建与展示交付，并先确认
  发布标识、签名/账号、隐私和部署预算；真实模型供应商仍不能仅靠填 key 绕过 Proposed
  决策。

### 下一条建议指令

> 执行阶段 8：staging、构建与秋招展示。先确认部署平台、应用标识、Apple/Android
> 签名条件、隐私与预算；复用阶段 7 门禁，完成低成本 staging、原生构建路径、演示脚本、
> 架构/测试文档和故障预案。不要接入未经确认的真实模型，不开始阶段 9。

---

## 2026-07-20：阶段 8——本地 staging、构建与秋招展示（In Progress）

### 范围、安全与待确认条件

- 开始前重新执行并展示 `pwd`、完整 `git status`、`ls -la`；当前目录仍为 Journey，已有
  阶段 2—7 未提交资产，无新的冲突性用户改动。未执行 commit、push、PR、强制重置或清理。
- 用户授权阶段 8，但未回复三项外部条件：是否接受 Render Singapore Free 临时 staging、
  是否确认 production id `com.boom080.journey`、是否拥有付费 Apple Developer Program。
  因此没有创建云资源、费用、Distribution/upload key、AAB/IPA 或商店记录。
- 全程保持 `AGENT_PROVIDER=mock`、API Key 空、预算/单价 0；未向外部模型发送健康数据，
  未开始阶段 9。

### staging、恢复与隐私

- 新增 `compose.staging.yaml` 和 `render.yaml`。本机以独立 project、API `18000`、数据库
  `55432` 和独立 volume 验证 staging 等价环境；migration、live/ready、非生产测试账号、
  内置受控知识和 Mock/零成本均通过。Render Blueprint 仅形成 IaC，状态仍为 Proposed。
- `infra/demo/reset_demo.py` 只通过公开 `/api/v1` 重置配置账号；连续执行会先删除该账号记录
  再回到 2 条饮食、1 条运动、3 条体重，首页为 intake 668、activity 260、latest 65.4。
- `infra/staging/smoke.py` 验证登录、Journey、Agent run/trace、Prompt/Schema/Knowledge 版本、
  provider mock、cost 0；修正了 Prompt 版本应从 trace endpoint 读取的契约假设。
- PostgreSQL 18 custom dump、SHA-256、显式恢复确认和恢复后 smoke 实际通过；Free 数据库
  无托管备份的风险已写入运行手册。
- 安装 Expo 57 兼容 `expo-crypto 57.0.1`；原生离线队列改为 AES-256-GCM，密钥存
  SecureStore，24 小时/50 条/按用户清除；Web 只保留内存。新增 3 条测试覆盖密文、过期与
  注销/全清除策略。

### 三端构建证据

- 动态 `app.config.js` 固化 development/preview/production 三变体与独立标识；候选 production
  id 保持 Proposed。新增 `eas.json`。`infra/verify_app_variants.mjs` 验证三套 name/id/scheme
  以及只有 development Android 允许 cleartext；Preview/Production 为 false。
- Android 自动生成目录因 macOS 同步出现 `PackageList 2.class`；用 Expo 官方
  `prebuild --clean --platform android` 重建后 Debug 与 Release 均成功。最终 ARM64 Release
  APK 约 42 MB，SHA-256
  `e5a73e6233d82b7a9375535f5f411798604718bdd12aed19c38dbd9cd68c413e`。
- Release APK 安装到 Pixel 9，进程无 Journey crash；测试账号登录返回 200，随后
  `/api/v1/home/today` 返回 200。证书是 `CN=Android Debug`，只用于模拟器，不冒充发布签名。
- `npx pod-install` 加入 ExpoCrypto；`expo run:ios --configuration Release` 在 iPhone 17 Pro
  完成 `Build Succeeded`、安装和启动，截图显示已登录首页。本机 code-signing identity 为 0，
  所以 archive/TestFlight 仍是账号门禁。
- Web production export：12 条静态路由、2.1 MB、34 文件 SHA-256 清单。发现 Metro 会复用
  旧 API 环境值后，将 `web:build` 固化为 `--clear`，重建 bundle 明确包含目标地址。
- Web runtime Dockerfile/nginx 已完成；三次构建均在 Docker Hub OAuth token HTTPS timeout
  失败，发生在拉取 Node/nginx metadata 前，不是 Dockerfile 或 Web 源码失败。保留静态
  export 为回退，并在 CI 网络环境继续构建镜像。

### 展示交付与 CI

- 新增 staging、构建/签名、隐私/预算和故障预案文档；新增 3—5 分钟演示脚本、系统架构、
  Agent 工作流、测试金字塔、简历描述与面试问答。
- Playwright 支持 `DEMO_RECORDING=1`；核心闭环录屏最终 `1 passed (22.2s)`，文件
  `docs/demo/assets/journey-fallback-demo-0.1.0.webm` 为 535 KB，SHA-256
  `8ab0dd3b43edb1ca2906f4d14f573b0b53511ca223d6d153d6fb9808a89e401d`。修正一个文本选择器
  同时匹配输入框与候选名称的 strict-mode 歧义；录制后将测试账号幂等 reset 回稳定数据。
- CI 新增应用变体/网络策略检查、staging Compose contract 和 Web runtime image build；不含
  云部署、签名或真实模型 job。

### 阶段 7 门禁复跑

- 后端：35 passed，覆盖率 90.96%；296 条评测的 13 项门禁全部通过，failures 0、Mock
  cost `$0`；Alembic `0003 → 0002 → 0003` 和 `alembic check` 通过。
- Ruff 按 GitHub Actions 原命令和仓库配置通过：`All checks passed`、81 files formatted。
  一次测试镜像内缺少 pyproject 上下文造成默认 88 列误报，核对后未产生 49 文件改动。
- 移动端：5 条逻辑测试、6 suites / 23 Jest tests 通过；覆盖率 statements 81.18%、
  branches 70%、functions 73.13%、lines 84.02%；TypeScript、Expo lint 和应用变体通过。
- iOS/Android JS bundle 分别 3.1/4.4 MB；Web E2E 通过。`git diff --check` 通过。
- `npm audit --omit=dev --audit-level=high` 退出 0，无 high/critical；仍有 11 个 Expo 工具链
  传递的 moderate `uuid` 告警。自动 `--force` 会引入 breaking Expo 版本，未执行。

### 当前结论

- 阶段 8 保持 **In Progress**，不是 Failed：本地 staging、备份恢复、三端构建、APK 安装、
  展示资产和全部确定性门禁均已完成；唯一未满足项均需用户的外部账号/预算决策。
- 下一次只需确认 Render/预算、production id、Apple 账号与“是否接受自动化录屏作为本轮演练
  证据”。确认后可执行 HTTPS/跨网络 smoke 或接受本地 staging 回退，并据实将阶段 8 标记
  Completed。不得自动开始阶段 9。

---

## 2026-07-21：阶段 8——用户决策收口（Completed）

### 用户确认

- 暂时只做本机演示；未来可能自租一年期服务器供个人使用。阶段 8 因此接受本机隔离
  staging，不创建 Render、其他云资源或费用。未来服务器发布必须作为单独任务重新确认
  供应商、地区、域名、HTTPS、备份、监控、预算和隐私政策。
- production application id 确认为 `com.boom080.journey`。
- 用户当前没有付费 Apple Developer Program。阶段 8 的 iOS 验收以 Release Simulator 为准，
  不制作 archive、TestFlight 或 App Store 包。
- Android 当前只要求本机可安装 APK。APK 已由自动生成的 debug certificate 签名；该签名是
  Android 对安装包来源和更新连续性的数字证明，但不是 Google Play 的长期 upload key。
  本阶段不创建 upload key、不制作发布 AAB，未来上架时再单独生成并安全备份。
- 接受 `$0`、Mock、临时演示数据与自动化录屏作为本阶段证据。Mock 是与真实 provider 共用
  模型路由接口的零外部调用实现；未来可经 LangChain/LangGraph 适配层切换真实 provider，
  但不能只填 API key 就绕过安全门禁，仍须配置 provider/model/base URL（如需）、服务端
  secret、价格与预算、数据政策，并重新运行阶段 7 量化评测。

### 状态与验证

- ADR-027 转为 Accepted；阶段 8 状态更新为 Completed。阶段 8 既有 staging、备份恢复、
  iOS/Android/Web 构建、全量自动化、演示脚本和备用录屏证据保持有效。
- 本次只收口决策和文档状态，没有修改业务代码、重新执行耗时全量测试、创建外部资源、
  接入真实模型、提交或 push。
- `infra/verify_app_variants.mjs` 再次验证三个变体与 production id；`git diff --check` 通过。
- 阶段 9 保持 Backlog；必须等待用户单独选择一个明确能力并下达新指令，不自动开始。

---

## 2026-07-22：DeepSeek V4 无密钥接入准备

### 范围与安全

- 重新执行并展示 `pwd`、完整 `git status`、`ls -la`，确认只在 Journey 当前目录工作；阅读
  `AGENTS.md` 和文档索引。保留阶段 2—8 全部既有未提交改动，未执行清理、提交或 push。
- 用户要求继续下一步，但尚未确认健康数据发送政策和每日预算。本次只完善 DeepSeek V4
  配置、路由、测试与文档，不创建 `.env`、不保存聊天中暴露的 Key、不发起真实模型请求，
  不开始阶段 9。

### 官方复核与实现

- 2026-07-22 复核 DeepSeek 官方文档：OpenAI-compatible Base URL 为
  `https://api.deepseek.com`；当前模型 ID 为 `deepseek-v4-flash`、`deepseek-v4-pro`，二者
  支持 JSON Output、Tool Calls 与思考模式。
- 建立配置建议：Flash 处理高频路由、文本解析和知识回答；Pro 只处理 Recommendation 与
  Weekly Summary。适配器对 Flash 关闭思考，对 Pro 开启思考并设置 `high` effort。
- `.env.example` 只增加注释形式的无密钥模板，仓库默认仍是 Mock/空 Key/零预算。Settings
  的 API Key 字段从对象 `repr` 中排除，降低误打日志风险。
- ADR-028 保持 Proposed；只有撤销旧 Key、在本机 `.env` 填新 Key、确认健康数据发送政策和
  每日预算后，才允许进行小额真实 smoke。

### 验证证据

- Docker Desktop 初始未运行，第一次测试在连接 Docker socket 前失败；启动 Docker Desktop
  后按原命令重试，没有改变测试范围。
- `docker compose --profile test run --rm --build test`：37 passed，覆盖率 91.52%；296 条
  Agent/RAG 样本的 13 项门禁全部通过，provider `mock`、cost `$0`、failures `0`。
- 新增测试验证：DeepSeek V4 使用官方 Base URL、Flash/Pro 思考模式分流、Recommendation/
  Weekly Summary 模型映射，以及 API Key 不出现在 Settings `repr`。
- 首次容器内 Ruff 格式检查未读取 `backend/pyproject.toml`，产生默认格式建议；按仓库配置、
  只读挂载和 `--no-cache` 复跑后 `ruff check` 与 `ruff format --check` 均通过。只格式化本次
  新增的 `tests/test_agent_unit.py`，未批量改写既有文件。
- `git diff --check` 通过；仓库内长格式 `sk-` 密钥扫描无结果；根目录 `.env` 仍不存在。
- 本任务到此停止：真实调用仍未启用，ADR-028 仍为 Proposed，阶段 9 仍为 Backlog。

### Flash-only 真实合成 Smoke（后续授权）

- 用户在被 Git 忽略的根目录 `.env` 填写了 Key，并说明当前只有
  `deepseek-v4-flash`。安全摘要只确认 Key 存在及长度，不输出值；将
  `AGENT_MODEL_MAP_JSON` 改为 `{}`，所有 capability 统一使用 Flash。Compose 补充显式传递
  模型映射，测试服务继续强制 Mock。
- 首次 API 启动在任何模型调用前失败：新 `.env` 的占位数据库密码与既有 PostgreSQL volume
  密码不一致。把本机 `.env` 恢复为既有 local-only 数据库密码后复用原 volume，未删除或
  重建用户数据。
- 合成饮食文本 Smoke：HTTP 200，2.872 秒，识别 `food` 并返回 Food 候选；provider
  `deepseek`、model `deepseek-v4-flash`、fallback false、retries 0、error null。记录 948
  input / 277 output Token，按当时 Pro 费率上界估算 `$0.00065337`。
- 供应商不可达模拟首次暴露真实缺陷：`openai.APIConnectionError` 未被 Router 捕获，会冒泡
  异常。增加 OpenAI-compatible 连接、超时、鉴权、限流和 HTTP 状态的安全错误分类；修复后
  不可达地址返回 `provider_unavailable`、确定性候选、1 次重试、费用 0。
- 新增回归后 `docker compose --profile test run --rm --build test`：38 passed，覆盖率
  91.41%；296 条 Mock Agent/RAG 样本 13 项门禁全部通过，cost `$0`、failures 0；Ruff 与
  format check 通过。
- 因账号只使用 Flash，将成本配置改为 2026-07-22 Flash cache-miss 美元单价：输入
  `$0.14`/百万 Token、输出 `$0.28`。第二次合成运动 Smoke：HTTP 200，2.294 秒，识别
  `activity` 并返回 Activity 候选；fallback false、retries 0、error null，估算
  `$0.00017038`。
- 数据库共记录 2 个 DeepSeek AgentRun，累计估算 `$0.00082375`。两条输入均为明确的合成
  测试数据，没有发送用户真实健康记录。Key 未写入仓库、测试、日志或文档。
- ADR-028 仍为 Proposed：用户必须确认旧 Key 已轮换并明确个人健康数据发送政策，才能用于
  实际个人记录。验收后停止 API、开发数据库与测试数据库容器，不删除 volume，避免误触发
  真实调用；阶段 9 未开始。

---

## 2026-07-22：LangChain/LiteLLM 多供应商模型路由（Completed）

### 授权范围与目录安全

- 用户明确授权按建议采用先进模型切换框架。本任务是阶段 8 后的 Provider Router 增量，
  不是阶段 9；未迁移新页面、未增加多模态、未创建公网资源、未提交或 push。
- 开始前展示 `pwd`、完整 `git status`、`ls -la`，阅读 `AGENTS.md` 与文档索引；只在当前
  Journey 工作目录操作，保留阶段 2—8 全部既有未提交改动。
- 没有读取、打印、移动或提交 `.env` 中的 Key；所有测试固定 Mock。最终只解析本机配置并
  输出 `key_configured=True`，没有发起模型请求或发送健康数据。

### 技术复核与决策

- 保留 LangChain `1.3.14` 与 LangGraph `1.2.9`；将直接 `ChatOpenAI` 外部适配器替换为
  `langchain-litellm==0.7.0` + `litellm==1.86.2` 的嵌入式 Router，不部署 LiteLLM Proxy、
  不增加容器或控制面。ADR-029 记录为 Accepted。
- 官方文档复核当前占位模型与端点：Qwen `qwen3.6-flash`/`qwen3.7-plus`、GLM
  `glm-5.2`、Kimi `kimi-k2.6`；Qwen/GLM/Kimi 只有无 Key Profile，不做真实调用。
- 复核 LiteLLM 官方供应链通告，明确避开受影响的 PyPI `1.82.7`/`1.82.8`。生产和开发
  requirements 锁定安全版本及哈希，Docker `pip install --require-hashes` 安装成功。

### 实现结果

- 新增版本化 Provider Profile：`mock`、`deepseek`、`qwen`、`glm`、`kimi`、`openai`、
  `openai_compatible`。`AGENT_PROVIDER` 是服务端单一切换开关，移动端不持有 Key。
- 各供应商使用独立 Key 变量。旧 `AGENT_API_KEY` 只为 DeepSeek/OpenAI/通用兼容配置保留
  迁移兼容；Qwen/GLM/Kimi 明确禁止读取它，避免把一个供应商的凭据发往另一端点。
- DeepSeek 默认 Flash；Recommendation 和 Weekly Summary 使用 Pro。Flash 关闭思考，
  Pro 开启思考并使用 `high` effort。真实本机配置解析确认两个模型均注册。
- 增加按模型价格映射：Flash `$0.14/$0.28`、Pro `$0.435/$0.87`（2026-07-22 每百万输入/
  输出 Token 快照）。未配置正数价格的新 Provider 会 fail-fast，不再错误记录为 `$0`。
- LiteLLM 内层重试关闭，继续由既有 Journey Router 执行有限重试、每日预算、标准错误分类
  和确定性 fallback，避免双层重试导致重复调用。

### 失败记录与修正

- 锁文件工具 `uv` 不在 PATH；只在被忽略的旧 `backend/.venv` 安装 `uv 0.8.24`。该 venv
  仍是 Python 3.9，首次开发锁解析因此拒绝 Python 3.10+ 依赖；改用显式
  `--python-version 3.12` 后两份锁生成成功，没有放宽项目 Python 版本。
- 只读挂载执行 Ruff/compileall 时，工具尝试写缓存而失败；改用 `ruff --no-cache` 与只读
  AST 检查通过。仅格式化本次改动的 3 个 Python 文件。
- 第一次全栈为 40 passed / 1 failed：测试夹具未声明 Pro；补齐测试模型映射。第二次仍为
  40 / 1：直接构造 Settings 时适配器未回退官方 Base URL；补上 Profile 端点回退。两项
  修正后全量通过，失败证据未删除。

### 最终验证证据

- `docker compose config --quiet`：通过；未输出展开后的 secret。
- `ruff check --no-cache app tests`：All checks passed；`ruff format --check`：75 files。
- `docker compose --profile test run --rm --build test`：43 passed，覆盖率 91.39%。
- 296 条版本化 Agent/RAG 数据集的 13 项量化门禁全部 PASS，`provider=mock`、`cost=$0`、
  `failures=0`。
- 使用占位 Key、无网络调用实例化真实 LiteLLM Router：DeepSeek 2 个 deployment、Qwen
  2 个、GLM 1 个、Kimi 1 个。
- 本机 `.env` 只读配置检查：provider DeepSeek、默认 Flash、Recommendation/Weekly
  Summary 映射 Pro、Flash/Pro 均有价格、Key 已配置；未打印 Key、未调用 API。
- 验收后执行 `docker compose --profile test down`，API、开发数据库和测试数据库容器均已
  停止并移除；命名 volume 保留，没有删除数据。

### 已知边界、回退与下一步

- Qwen/GLM/Kimi 尚未配置 Key、价格、数据政策或执行契约测试，不能仅切换名称后用于真实
  健康数据。LiteLLM Proxy、跨供应商自动 fallback 和客户端 Provider 选择均未实现。
- ADR-028 继续保持 Proposed：用户仍需确认聊天中暴露的旧 Key 已轮换，并明确接受个人
  健康数据发送范围，才允许将 DeepSeek 从合成 smoke 扩大到实际个人使用。
- 如 LiteLLM 出现安全或兼容问题，可回退 `LangChainLiteLLMAdapter` 为单供应商兼容适配器；
  Mock、业务工作流、Prompt、Schema、RAG、确认写入和 `/api/v1` 契约无需变化。
- 本任务完成后停止；阶段 9 仍为 Backlog，不自动开始。下一次应由用户单独选择“个人数据
  政策/Key 轮换验收”或某个新 Provider 的 Key、价格和小额合成契约测试。

---

## 2026-07-22：DeepSeek V4 Pro 结构化输出真实合成 Smoke（Completed）

### 授权与数据边界

- 用户在 Provider Router 完成后明确要求继续，授权一次 Pro 合成验证；本任务不属于阶段 9。
- 直接调用 `LangChainLiteLLMAdapter`，输入只包含明确声明为虚构的成年测试用户、步行和
  午餐信息；未读取数据库、用户画像或真实健康记录，也未输出 `.env` Key。
- 调用前校验 provider 为 DeepSeek、Recommendation 映射为 `deepseek-v4-pro`、Key 已配置、
  每日预算为 `$0.10`，并将单次最大输出限制为 2048 Token。

### 首次失败与兼容性修正

- 第一次请求返回 HTTP 400：DeepSeek thinking mode 不接受 LangChain 结构化函数调用发送的
  `tool_choice=required`。请求未产生可记录的 Token usage，也未返回业务输出。
- 按 DeepSeek 官方 Thinking Mode、JSON Output 与 Chat Completion 文档复核：Pro 保留
  thinking/high；模型结构化生成改用 `response_format=json_object`，系统消息注入 Pydantic
  JSON Schema。Flash 非思考路径继续使用 function calling，实际业务工具仍由 Journey
  LangGraph/Tool 层编排。
- 新增 `AGENT_MAX_OUTPUT_TOKENS`，默认 2048，并传给 LiteLLM deployment，避免单次生成在
  每日预算检查之前产生无界输出。

### 验收证据

- 定向 Ruff check 与仓库配置下的 format check 通过。
- `docker compose --profile test run --rm --build test`：43 passed，覆盖率 91.42%；296 条
  Agent/RAG 样本、13 项量化门禁全部 PASS，`provider=mock`、`cost=$0`、`failures=0`。
- V4 Pro 第二次合成请求成功：Pydantic Schema 校验通过，`summary` 62 字符、引用 0；208
  input / 115 output Token，延迟 2812 ms，按 Pro cache-miss 单价估算 `$0.00019053`；未使用
  fallback。
- 验收只证明 Pro 的合成结构化输出技术路径可用。ADR-028 继续保持 Proposed：Key 轮换与
  个人健康数据发送政策未确认前，不得把真实个人记录发送给供应商。
- 完成后关闭临时测试容器，保留 PostgreSQL volume；未提交、push、创建 PR 或开始阶段 9。

---

## 2026-07-22：阶段 9 单项——食物图片、份量估算与用户校正

### 状态与边界

- 用户只授权食物图片单项，要求先完成 Proposed ADR、隐私边界、评测标准和回退方案；语音、
  视频、身体照片/体脂、手机号、HealthKit/Health Connect 和通知均未启动。
- 开始前执行并展示 `pwd`、完整 `git status`、`ls -la`，阅读 `AGENTS.md` 与文档索引；只在
  Journey 当前目录操作，保留阶段 2—8 和 Provider Router 的既有未提交改动。
- 未读取或打印根 `.env`、DeepSeek Key 或任何其他凭据；未使用真实个人照片，未发起外部
  图片请求，未修改数据库 schema，未创建媒体存储、云资源、提交、push 或 PR。
- ADR-030 与 `FOOD_IMAGE_PRIVACY_AND_EVAL.md` 先于业务实现建立。DeepSeek V4 官方发布资料
  只给出 ChatCompletions/Anthropic 文本消息接口，没有图片输入契约，因此本机 DeepSeek Key
  只继续供文字 Agent 使用。真实视觉首选 Qwen `qwen3.7-plus` 保持 Proposed。

### 实现结果

- Expo SDK 57 增加 `expo-image-picker 57.0.5`、`/food-image` modal 与首页入口：单图相机/
  相册、0.65 压缩、不读取 EXIF、本地预览、餐别/说明、逐次明示上传、JPEG/PNG/WebP 类型
  判断、宽热量区间、低/中置信度、假设、Mock 警告和手动记录回退。
- 图片候选进入既有饮食表单，用户可以修改名称、餐别、份量、单位、热量和备注；只有再次
  点击确认才写入，最终 `source=image`。离开分析页前释放客户端图片引用。
- 增加双 Feature Flag：服务端 `FOOD_IMAGE_ANALYSIS_ENABLED` 与客户端
  `EXPO_PUBLIC_FOOD_IMAGE_ANALYSIS_ENABLED`。Development 默认 Mock 开启，EAS Preview/
  Production 和本地 staging 默认关闭；直达关闭页面只提供手动饮食入口。
- iOS 权限仅声明相机/相册中文用途；Android 最终 merged APK 包含 `CAMERA`，并通过
  `microphonePermission=false` 明确移除 `RECORD_AUDIO`。
- FastAPI 新增 `POST /api/v1/food-images/analyses`、Pydantic 图片/结构化估算契约和独立
  `backend/app/media/`。API 校验鉴权、逐次同意、base64、magic bytes、MIME、5 MiB、4096
  维度；图片仅在请求内存存在。
- 图片 Provider 与文字 `AGENT_PROVIDER` 分离。Mock 明示没有识别图片；Qwen/OpenAI Adapter
  复用 LangChain 消息、Pydantic JSON 与嵌入式 LiteLLM，不部署新服务、不自动跨供应商转发。
  Qwen 还必须显式配置获确认的区域 Workspace Base URL，避免使用过时或错误地区端点。
- AgentRun 只保存随机请求派生 hash、字节数、MIME、宽高、Provider、模型、Token、费用、
  延迟和降级状态；不保存 base64、原始字节、文件名、EXIF 或可比对原图 hash。未增加数据库
  migration 或对象存储。
- 增加 22 条合成图片契约：12 食物、6 非食物、4 非法输出。总评测增至 318 条和 17 项门禁；
  真实 Provider 的 Top-3、份量误差、热量区间覆盖率、拒答率、p95 与费用均据实标记
  `Not evaluated`。

### 失败—修正证据

- 容器定向测试最初使用宿主路径 `backend/tests/...`，测试镜像工作目录实际是 `/app`，返回
  `file not found`；改为 `tests/...`。随后旧测试镜像没有新文件，再执行 `docker compose
  build test` 后 19 项定向测试通过。这是命令/镜像证据问题，不是隐藏测试失败。
- 代码审查发现 Web ImagePicker 保留 PNG/WebP 原始 MIME，而初版请求固定 `image/jpeg`；增加
  magic-prefix/MIME 判断和 PNG 组件/E2E 回归，避免服务端正确拒绝合法 Web 图片。
- 首次 Web E2E 两项登录均失败：静态站点源 `127.0.0.1:4173` 不在本次本机 API CORS，
  preflight 返回 400。只在验收启动变量中显式加入该源并重启 Mock API，未放宽生产配置。
- 图片 E2E 的图片语义最初用通用 label 选择器不稳定；改为 `role=img` + accessible name 后
  专项 `1 passed`、全量 `2 passed`。
- 回退审查发现初版只有服务端 Feature Flag，客户端入口仍显示；补齐客户端开关、EAS 变体
  验证和直达路由回退。相册取消初版静默返回，补充“没有读取或上传”提示和测试。
- 首次 iOS npm workspace 参数被解释为子目录，报缺少 `iPhone 17 Pro/package.json`；改为在
  mobile 目录直接调用 Expo CLI。Android 首次传设备 serial 未匹配 Expo device name；改用
  `Pixel_9`。两项均按原范围重试并成功。

### 最终自动化与构建证据

- 后端：`docker compose --profile test run --rm --build test` 最终 **53 passed**，覆盖率
  **91.65%**。图片 API 覆盖：未确认不写入、校正后一次写入、来源、所有权、同意、鉴权、
  MIME/base64/尺寸、非食物、Provider 失败、Feature Flag 和元数据不含图片内容。
- 评测：318 条合成样本、17 项门禁全部 PASS，`failure_count=0`、provider Mock、外部费用
  `$0`。图片 Schema、强制校正、份量/区间、非食物拒答契约均 100%。机器报告和阶段报告已
  版本化到 `evals/reports/`。
- 移动端：TypeScript 与 Expo lint 通过；**7 suites / 29 tests** 通过，statements 81.46%、
  branches 70.34%、functions 73.91%、lines 84.3%。覆盖 PNG MIME、权限拒绝、取消、离线、
  Feature Flag、Mock 候选、校正路由、API wrapper 和首页入口。
- Web：production export **13 routes**，包含 `/food-image`；Playwright 旧核心流程和图片
  选择—Mock—校正—确认—Journey 闭环最终 **2 passed (5.7s)**。
- iOS：CocoaPods 安装、`expo-image-picker` 编译、Debug `Build Succeeded`，安装并打开于
  iPhone 17 Pro / iOS 26.5 Simulator；原生模块 0 error，只有既有 Expo Dev Launcher build
  phase warning。
- Android：Pixel 9 / API 36.1 ARM64 冷构建 `BUILD SUCCESSFUL in 2m 14s`，495 tasks，Debug
  APK 安装打开；最终 manifest 有 `CAMERA`、无 `RECORD_AUDIO`。SDK XML 与上游弃用信息为
  非阻断警告。
- iOS/Android JS bundle 与 Web export 全部通过；iOS HBC 约 2.7 MB，Android HBC 约 3 MB。
- `ruff check`、`ruff format --check`、两套 Compose config、应用变体验证、
  `git diff --check` 通过；仓库扫描未发现长格式 `sk-` 密钥。未执行 `npm audit fix --force`。

### 当前结论与启动条件

- 食物图片的 Mock/工程基线完成：可演示上传、份量/热量候选、用户校正、确认写入、降级与
  隐私契约，但 Mock 不识别真实图片，不能冒充真实视觉 AI。
- 阶段 9 该父项保持 **In Progress**，ADR-030 保持 **Proposed**。只有用户另行提供独立视觉
  Key，并确认供应商地区/Workspace Base URL、保留与训练政策、删除机制、启用当日价格、
  每日预算及至少 100 张有授权标注图片后，才能执行真实视觉小额评测；所有硬门禁通过后才
  能转 Accepted/Completed。
- 阶段 9 其他能力继续 Backlog，不自动开始。最终执行 `docker compose --profile test down`、
  关闭 iOS Simulator 与 Pixel 9 Emulator；容器和网络已移除，命名 PostgreSQL volume 保留。

---

## 2026-07-28：阶段 9 Qwen 配置与模型可用性探测（Technical Smoke Completed）

### 配置核对

- 开始前再次执行并展示 `pwd`、`git status --short`、`ls -la`，阅读 `AGENTS.md` 与文档
  索引；只在 Journey 当前目录操作，保留全部既有未提交改动。
- 以脱敏方式确认根 `.env` 已设置独立 `QWEN_API_KEY`，未读取到终端输出、文档或日志；
  `FOOD_IMAGE_PROVIDER=qwen`、`FOOD_IMAGE_MODEL=qwen3.7-flash` 与北京区域共享 OpenAI
  兼容 Base URL 均已配置。
- 调用北京区域 OpenAI 兼容 `GET /models` 返回 HTTP 200，证明 Key 可完成鉴权，且服务端
  当前实际列出 `qwen3.7-flash` 与 `qwen3.7-flash-2026-07-15`。这修正了只依据滞后视觉
  文档推断“模型不存在”的结论，但模型列表存在本身不证明图片输入质量或契约兼容性。

### 最小视觉探测与阻塞项

- 用户确认当前为单人本地使用、功能优先，不要求按个人使用量优化费用；工程仍保留每日
  预算保护，防止密钥泄漏、重试循环或异常请求造成无界费用。
- 使用程序内置的 1×1 PNG 发起一次最小图片输入探测；该图片不含食物、人物、EXIF、位置或
  任何用户数据，未上传真实个人照片。
- Provider 在推理前返回 HTTP 400、错误码 `Arrearage`：账号当前欠费或余额状态异常，未
  返回模型输出，也无法证明 `qwen3.7-flash` 接受图片输入。问题发生在阿里云账户计费状态，
  不是 Journey Schema、API Key 格式或 Base URL 路由。
- 用户随后提供 2026-07-28 百炼控制台价格截图并确认单人本地使用、每日上限人民币 1 元：
  普通实时调用且输入不超过 32K 时，输入 ¥0.20/百万 Token、输出 ¥0.80/百万 Token；不采用
  Batch、Batch Chat 或缓存折扣口径。根 `.env` 已补齐价格、正数每日预算和外发确认。
- 现有成本字段以 USD 命名，为避免本阶段扩大数据库/API 改造，三项同时采用固定预算换算
  `USD 1 = CNY 7.20`：输入 `0.027778`、输出 `0.111111`、每日 `0.138889`。三者同比换算，
  因而 Token 预算比例对应约人民币 1 元；这只是本地预算门禁与估算展示，不是供应商美元
  账单。后续若改为长期公开服务，应把币种建模独立重构并以账单核对。
- `docker compose config --quiet` 通过。用户授权后由 Codex 启动 Docker Desktop，Docker
  客户端/服务端 29.6.1 就绪；首次容器校验因默认 entrypoint 先执行 Alembic、但 `--no-deps`
  未启动 `db` 而失败，改用 `--entrypoint python` 隔离数据库后完成 Python 3.12 动态检查。
- 容器内 `get_settings()` 最终通过，脱敏确认 Qwen Provider、模型、北京 Base URL、独立
  Key、价格、每日预算和外发确认全部进入实际运行配置。宿主 `python3` 3.9.6 的类型语法
  失败和测试脚本误用 `load_settings` 函数名均已纠正，不属于应用配置缺陷。
- 用户说明 `qwen3.7-flash` 有免费额度后再次执行相同的 1×1 合成图片请求，仍在推理前返回
  HTTP 400 `Arrearage`。阿里云官方错误码说明：免费额度不会绕过账户状态检查；账号欠费、
  余额不足或充值状态未同步时仍会拒绝访问，需在“费用与成本”中恢复账号正常状态并等待
  数分钟。

### 欠费恢复后的真实合成 Smoke

- 用户支付欠费后，Docker 29.6.1 保持就绪。使用程序生成的 16×16 PNG（满足供应商最小
  图片边长）重试兼容接口，HTTP 200；`qwen3.7-flash` 返回 `IMAGE_INPUT_ACCEPTED`，92
  input / 5 output Token。该图片无人物、食物、EXIF、位置或外部素材。
- 直接调用 Journey `LangChainLiteLLMFoodImageAnalyzer` 成功解析 Pydantic Schema；纯色图
  正确返回 `is_food=false`、`needs_user_correction=true`，880 input / 83 output Token，
  延迟 1548 ms，按本地换算估算 `$0.00003367`。
- 启动 PostgreSQL/API 后健康检查通过。既有演示账号密码与持久化数据库不一致，返回
  `invalid_credentials`；没有重置该账号，而是注册随机本地 Smoke 用户。第一次注册遗漏
  契约必填 `display_name` 返回 422，补齐后注册 201。
- 登录态调用 `POST /api/v1/food-images/analyses` 的非食物 Smoke 返回 HTTP 200、
  `manual_required`、`fallback_used=false`、`image_retained=false`，未创建候选；880
  input / 65 output Token，延迟 1105 ms。
- 程序生成的 256×256 煎蛋插画 Smoke 返回 HTTP 200、`candidate`，名称为“煎蛋配吐司
  （插画）”，点估计 169 kcal、宽区间 130—220 kcal、置信度 low，并保持
  `needs_user_correction=true`；885 input / 295 output Token，延迟 2615 ms，
  `fallback_used=false`、`image_retained=false`。
- 数据库审计确认最新 Qwen Run 只保存字节数、MIME、宽高、Provider、模型、Token、费用、
  延迟、候选/置信度/不留存标记；没有 base64、`data:image`、EXIF 或文件名。一次性审计
  查询最初对 PostgreSQL `JSON` 使用 `.contains()` 导致不支持的 `LIKE`，改为读取最近记录
  后在进程内筛选；业务 API 和 schema 未受影响。
- Qwen Provider 默认视觉模型、单元测试与阶段 9 文档更新为 `qwen3.7-flash`；
  `qwen3.7-plus` 保留为质量回退基线。未把任何 Key 写入仓库或输出。
- 第一次定向 pytest 命令覆盖了 test service 自带的“先 Alembic 再 pytest”命令，测试库尚
  无表，20 项均在 fixture `TRUNCATE` 阶段报 `UndefinedTable`，没有进入测试逻辑。改回仓库
  标准命令 `docker compose --profile test run --rm --build test` 后 Alembic 0001→0003
  完整升级，最终 **53 passed**、覆盖率 **91.65%**；318 条 Mock 评测、17 项门禁全部 PASS，
  `failures=0`、测试外部费用 `$0`。
- Ruff lint 通过。首次容器 format check 因测试镜像未复制 `backend/pyproject.toml` 而按
  Ruff 默认规则报告 53 个既有文件会被格式化；没有执行批量格式化。挂载真实项目配置后，
  本次修改的 `provider_profiles.py` 与 `test_food_image_unit.py` 均 lint PASS、format PASS。
- `docker compose config --quiet`、`git diff --check` 通过；测试数据库已停止，本地 API 与
  PostgreSQL 保持 healthy，未运行后台 Agent 请求。

### 回退与下一步

- Mock 继续作为 CI/staging 和真实 Provider 失败时的可解释回退；本机 `.env` 已选择 Qwen
  并满足配置与技术链路门禁。实际照片仍必须逐次由用户确认上传。
- 阶段 9 保持 **In Progress / Real-image quality evaluation Pending**：下一步只应确认阿里云
  保留/训练/删除政策并建立至少 100 张授权标注图片集，再运行 Top-3、份量误差、热量区间
  覆盖、拒答率、p95 和成本门禁。
- 不启动语音、视频、身体照片或其他阶段 9 能力，不提交、push 或创建 PR。

---

## 2026-07-28：阶段 9 食物图片真实评测与量化修正（In Progress）

### 安全、授权与政策

- 继续前执行并展示 `pwd`、`git status --short`、`ls -la`；当前目录为 Journey 仓库。完整
  保留阶段 2—9 的既有未提交改动，不执行删除、reset、清理、提交、push 或 PR。
- 只执行用户已授权的食物图片单项；语音、视频、身体/体脂图片、手机号、HealthKit/
  Health Connect 和通知仍为 Backlog。真实调用只使用独立 Qwen Key、北京端点和人民币
  1 元/日预算；Key 未写入 Git、报告、日志或终端输出。
- 复核 2026-07-19 生效的阿里云百炼服务协议：供应商应按用户指示处理，不得用于自身目的、
  未经授权披露或训练；终止服务缓冲期后应删除副本。隐私声明说明调用数据按法律要求保留并
  加密，但未公开模型调用内容的精确保留天数。该不确定性被保留为 ADR-030 残余风险。
- 用户必须对上传媒体有合法权利。评测未使用用户照片、个人健康数据、人脸或身份数据，
  只使用逐条固定许可、来源和哈希的公开图片；所有真实上传均限本机评测，不进入 CI/staging。

### 100 张授权评测集

- 建立 `journey-food-image-real-v1`：Nutrition5k 30 张单一食物、30 张混合餐、10 张困难
  餐盘；Open Food Facts 10 张饮料、10 张包装食品；Openverse 索引的开放许可非食物 10 张。
- `manifest.jsonl` 共 100 个唯一 ID，包含来源、作者、许可/许可 URL、原始页/图片 URL、
  SHA-256、尺寸和金标。图片二进制共 28,635,329 bytes，保存在 Git 忽略的 `assets/`，
  不进入 Docker 镜像、应用包、数据库或普通 CI。
- `python3 evals/food_image_real/prepare_dataset.py verify` 最终返回
  `samples=100`、六个分层数量正确、`status=verified`。Nutrition5k 的加州食堂分布、
  Open Food Facts 标签完整性和 10 张非食物的小样本偏差已写入报告。

### Baseline、失败与两轮修正

- Baseline `journey-food-image-1.0.0`：Schema 53%、Top-3 28.89%、单一食物份量误差中位数
  100%、热量区间覆盖 11.11%、非食物拒答 100%、p95 3273 ms、fallback 47；估算总费用
  `$0.00305615`。多数输出因结构化不兼容而不可评分。
- v1.1 使用更长的视觉说明与 Schema v2 后反而退化：Schema 40%、Top-3 22.22%、份量误差
  100%、热量覆盖 25.56%、p95 12207 ms、fallback 60，其中 32 次不可用/超时、28 次无效
  结构化输出。按量化结果拒绝该 Prompt，不用降低门槛掩盖回归。
- 原始响应诊断显示部分模型输出已有热量上下界但缺点估计，或给出不允许枚举。v1.2 改用
  Qwen 官方 JSON mode 的精简 Prompt，加入可选双语规范名，并只归一化可确定修复项：
  high→medium、非法餐别→other、强制校正、从已有上下界求中点、把过窄区间扩为有界宽区间；
  不合成缺失食物名、食物项或完全缺失的热量。
- v1.2 `journey-food-image-1.2.0` / `journey-food-image-schema-2`：Schema 100%、
  强制校正 100%、Top-3 76/90=84.44%、份量误差中位数 37.48%、热量覆盖
  76/90=84.44%、非食物拒答 10/10=100%、p95 2945 ms、单次最高估算费用
  `$0.000068`、fallback/自动写入/隐私标记均 0。54,407 input / 27,391 output Token，
  总估算费用 `$0.00455481`。
- v1.2 的强制校正指标改为以全部 100 个有效结果为分母；最终 JSON 的
  `report_corrections` 记录了机械口径修正，没有追加 Provider 调用。为防止围绕固定测试集
  继续调参造成过拟合，本轮不执行第四轮。

### 代码、契约与自动化

- `FoodImageItem`/`FoodImageEstimate` 增加可选 `canonical_name_en`；OpenAPI 和 TypeScript
  共享契约同步。Provider 无效结构化输出现在保留实际 Token、费用与错误 Trace，不再误记
  为零成本。
- 新增 `prepare_dataset.py` 的 curate/download/verify、版本化清单与
  `run_food_image_real.py`。评测器只允许 `APP_ENV=test` + `journey_test` 数据库，运行前
  清空隔离测试数据；报告不保存图片/base64/Key。
- 后端最终全量：**54 passed**，JUnit 0 failures / 0 errors，覆盖率 **91.20%**；318 条
  Mock Agent/RAG/图片样本、17 项门禁全部 PASS，`failure_count=0`、外部成本 `$0`。
- 移动端 Expo lint、TypeScript 通过；逻辑 5/5，组件 **7 suites / 29 tests** 全部通过。
- `docker compose config --quiet`、带无密钥占位值的 staging Compose config、
  数据集 verify、Ruff lint、按仓库 `pyproject.toml` 对本次 3 个 Python 文件的 format
  check、`git diff --check` 和 330 个 tracked/unignored 文件的脱敏密钥模式扫描均通过。
  首次 staging config 未提供其强制密码而按设计 fail-fast；
  首次容器 format check 缺少 `pyproject.toml` 而套用 Ruff 默认规则，均修正验证口径且未
  批量改动既有代码。

### 当前结论与回退

- 真实质量已经评测，不再标记 `Not evaluated`；但 Top-3 差 0.56 个百分点，份量误差高
  7.48 个百分点，两项硬门禁失败，所以 `gate_passed=false`、ADR-030 保持 Proposed、
  阶段 9 父项保持 In Progress。
- 默认/CI/staging 继续 Mock。设置 `FOOD_IMAGE_PROVIDER=mock` 或关闭
  `FOOD_IMAGE_ANALYSIS_ENABLED` 可停止图片外发；手动饮食、文字 Agent、首页与 Journey
  不受影响。
- 收尾时停止隔离 `test-db`；用户此前已运行的本地 `api` 与 `db` 保持 healthy，未继续发起
  后台模型请求。
- 下一次只应在单独授权后，用同一锁定数据集比较更强视觉模型，或先建立带尺度参照的拍照
  指引与独立 holdout；不得自动启动其他阶段 9 能力。

---

## 2026-07-29：阶段 9 食物图片 v1.3 尺度参照与密封泛化 holdout（In Progress）

### 范围、安全与决策

- 用户接受上一轮建议后，选择“先改善尺度参照并建立独立 holdout”，而不是立即启用未经
  评审的更强/更贵视觉模型。任务仍只属于食物图片单项；其他阶段 9 能力未启动。
- 开始前执行并展示 `pwd`、完整 `git status`、`ls -la`，重新阅读 `AGENTS.md` 和文档索引。
  当前目录正确；保留全部既有未提交改动，不删除、reset、提交、push 或创建 PR。
- 研究复核确认：单张 2D 图片缺少三维和物理尺度是份量估计的根本歧义，已有工作使用已知
  尺寸 fiducial marker 校正。SimpleFood45 虽提供物理参照/重量/能量，但公开仓库没有清晰
  数据许可，因此没有下载或纳入 Journey。
- ADR-030 在实现前增加 Proposed 尺度策略：Journey 自制 9×5 cm 参照卡、已知餐盘/碗口
  直径 8—60 cm、完整边缘/同平面/尽量俯拍、不可见则忽略。禁止用银行卡、证件或个人物品
  作参照；仍需用户校正，不能输出医学或精确测量结论。

### v1.3 实现

- `FoodImageAnalyzeRequest` 增加可选 `scale_reference_type`：
  `none`/`journey_card`/`plate_diameter`/`bowl_diameter`，以及只适用于盘/碗的
  `scale_reference_size_cm`。旧请求默认 `none`，无需数据库 migration。
- Prompt/Schema 更新为 `journey-food-image-1.3.0` /
  `journey-food-image-schema-3`。输出增加 `scale_reference_used`；只有参照完整可见且几何
  可信时才允许 true，无参照请求即使 Provider 声称使用也会被归一化为 false。
- Expo 共享页面增加俯拍/完整边缘引导、四种参照 Chip、盘/碗直径校验、Journey 卡隐私
  提示和结果中的“已使用/未可靠使用”解释。图片仍只在用户逐次同意后上传。
- 新增 `docs/assets/food-image/journey-scale-card.svg`：实体尺寸 90×50 mm、高对比棋盘格、
  100% 打印提示，无二维码、身份或个人信息。`xmllint` 与尺寸标记检查通过。
- Trace 只增加参照类型、尺寸和 Provider 声称是否使用；不保存图片、base64、文件名或 EXIF。
  OpenAPI 与 TypeScript 共享契约已同步。

### 密封 holdout 与真实结果

- 建立 `journey-food-image-holdout-v1`：Nutrition5k CC BY 4.0 单一食物 15、混合餐 15，
  资产 11,966,586 bytes。清单固定 source、许可、URL、SHA-256、尺寸、称重和热量金标。
- `prepare_holdout.py verify` 证明 30 个样本与 100 张调参集在 sample ID、Nutrition5k
  source ID 和 SHA-256 上均为 0 重叠；资产 Git ignored，当前 cohort 全部明确
  `scale_reference.type=none`。
- Qwen `qwen3.7-flash` 只对密封集执行一次，不依据失败案例继续调 Prompt：Schema/强制
  校正 100%，Top-3 23/30=76.67%（FAIL），单一食物份量误差中位数 36.36%（FAIL），热量
  区间覆盖 27/30=90%，p95 3473 ms，fallback/自动写入/隐私标记均 0。
- 无参照时 `scale_reference_used=false` 为 30/30；19,620 input / 9,609 output Token，
  总估算费用 `$0.00161268`。报告扫描未包含 `data:image`、`image_base64`、Key 或 `sk-`
  模式。该结果说明原 100 张上的 Top-3 84.44% 不能直接外推。
- 尺度参照真实收益继续 `Not evaluated`。必须另建至少 30 张许可清晰、同图无参照/有参照
  配对、实际称重的 cohort，达到份量误差 ≤30%、相对改善 ≥15%、参照判断 ≥95% 和全部
  原门禁，ADR 才能转 Accepted。

### 失败—修正与边界

- `prepare_holdout.py` 第一次直接执行因 Python 只把脚本目录放入 `sys.path`，报
  `ModuleNotFoundError: evals`；改为从脚本自身解析仓库根并加载既有数据工具后成功。
- 定向 pytest 第一次覆盖 test service 默认命令，跳过 Alembic，9 项在 fixture 处
  `UndefinedTable`；显式 `alembic upgrade head` 后 8/9 通过，唯一失败是预期的旧 OpenAPI
  快照。使用仓库导出脚本更新两份快照后，全量测试通过。
- 首次重建 test 镜像发现 `.dockerignore` 没有排除评测 `assets/`，导致 141 张图片、
  约 61 MB 进入镜像，与文档声明冲突。增加 `evals/**/assets` 后重建：构建上下文从
  12.20 MB 降至 7.13 kB，镜像 `/app/evals` 从 61 MB 降至 756 kB，图片文件数为 0。
- 一次人工 `comm` 零重叠核验在系统临时目录写入两份只包含公开 Nutrition5k source ID 的
  临时排序文件。这超出了“只在当前目录写入”的严格规则；未包含 Key、用户数据或其他项目
  内容，也未按禁止规则删除目录外文件。权威零重叠证据已改由仓库内
  `prepare_holdout.py verify` 直接在内存校验，后续不得重复该命令方式。

### 自动化与构建证据

- 后端全量 **54 passed**，覆盖率 **91.07%**；318 条 Mock Agent/RAG/图片评测、17 项门禁
  全部 PASS，`failure_count=0`、外部成本 `$0`。
- 移动端 Expo lint、TypeScript 通过；逻辑 5/5，组件 **7 suites / 31 tests** 全部通过，
  新增盘直径校验、Journey 卡固定尺寸/隐私提示与请求字段覆盖。
- Web production export 13 routes；iOS HBC 约 2.7 MB、Android HBC 约 3 MB，三端共享
  `/food-image` 页面打包通过。没有安装新原生依赖，因此未重复完整 Xcode/Gradle 编译。
- Ruff lint/format、holdout verify、XML、OpenAPI、Compose、`git diff --check` 和密钥扫描
  在最终收尾通过；隔离 `test-db` 完成后停止，本地 API/db 状态不由本单项改变。
- 本地 API 只重建 `api` 镜像并复用原 PostgreSQL；`/health/ready` 返回 database ok，本机
  OpenAPI 已包含 `scale_reference_type` 与 `scale_reference_used`。首次健康轮询把 zsh
  只读变量名 `status` 当作普通变量而立即失败，改名后通过，服务本身未失败。

---

## 2026-07-29：阶段 9 尺度配对公开数据调研（仍为 In Progress）

### 本轮范围

- 用户要求由 Codex 自行在互联网寻找尺度配对评测数据。本轮仍只处理食物图片单项，没有
  开始语音、视频、手机号、健康平台或通知能力。
- 开始前执行并展示 `pwd`、`git status`、`ls -la`，当前目录正确；既有未提交修改全部保留。
- 只核验官方数据页、官方仓库或论文。没有安装框架、提交外部申请、上传个人照片、发送邮件、
  修改模型供应商、提交或 push。

### 候选核验结果

- **SNAPMe（首选次级配对集）**：USDA Ag Data Commons 官方条目为 CC BY-SA 4.0，明确
  intended use 是评测而非训练；包含 1,475 张非包装食物 before 照片，使用 1.5×1.5 英寸
  棋盘格，每个格 0.75×0.75 英寸，并将图片关联到 ASA24 饮食记录。它适合比较同一张图在
  Prompt 中“不给 marker 尺寸”和“给出 3.81 cm 尺寸”的差异。
- **SNAPMe 限制**：ASA24 是参与者录入的传统食物记录，不是实验室实际称重。它只能回答
  真实场景参照提示是否有收益，不能把份量误差硬门禁改写成已通过。官方归档约 1.89 GB；
  当前环境经 DOI/旧 USDA 地址访问托管端点均返回 HTTP 403，因此没有下载或生成清单。
- **MetaFood3D（硬门禁候选）**：官方页声明 CC BY-NC 4.0，提供实际重量、营养、RGB-D
  视频和 fiducial marker 资料；但需填写申请表并由维护方发放密码。取得后仍须先确认
  marker 和食物是否在同一帧且尺寸可核验；仅允许非商业本机评测，不能把数据放入 Git、
  应用包或未来商业发布物。本轮没有代用户提交表单。
- **继续排除**：ECUSTFD 的 25 mm 一元硬币、质量/体积在技术上合适，但 “free public”
  不是正式图片许可；SimpleFood45 页面/仓库同样没有清晰数据许可证。Nutrition5k 有
  CC BY 4.0 和实际称重，但没有可核验的已知尺寸 2D marker，只保留无参照基线用途。

### 决策与阶段状态

- ADR-030 保持 `Status: Proposed`，尺度改善仍为 `Not evaluated`；不新增
  `checkerboard` API，不运行 Qwen，不消耗真实模型费用，也不把互联网搜索结果伪装为已完成
  cohort。
- 后续优先顺序：先取得并密封合法数据；SNAPMe 只建立 `record-referenced` 次级配对报告；
  MetaFood3D 只有在授权、共视和尺寸核验通过后才可能进入 `weighed` 硬门禁。若二者均不能
  满足条件，继续保持 Pending，而不是降低 ≥30 张、≤30%、改善 ≥15%、判断 ≥95% 的门槛。

## 2026-07-29：小红书公开帖子作为数据源的可行性复核

### 执行结果

- 用户提出搜索小红书中带准确食物名称和克重的帖子并保存截图。开始前重新执行并展示
  `pwd`、`git status --short --branch`、`ls -la`；当前目录正确，既有未提交改动保持不变。
- 使用小红书搜索页的直接访问未完成加载，本机 Chrome 控制连接也不可用；随后仅用一次
  `site:xiaohongshu.com` 定向公开检索核验可发现性，结果未提供可核验的具体帖子样本。
  本轮没有登录、绕过验证码、批量抓取、保存帖子截图或向第三方发送数据。
- 即使帖子正文列出名称和克重，也不能仅据截图确认电子秤读数、去皮、可食部和成品照片属于
  同一次记录；因此默认标记为 `self_reported`，不能进入 `weighed` 份量误差硬门禁。
- 公开可见不构成图片再利用许可，截图可能包含用户名、头像、位置和评论等个人信息。小红书
  只作为产品调研来源；只有作者明确授权 Journey 使用、完成去标识、并能核验同一食物的
  称重或尺度链路后，才可列入候选清单。该边界已同步写入 ADR-030 和唯一迁移计划。

### 阶段状态

- 没有新增评测样本，未运行 Qwen，未消耗模型费用，ADR-030 继续 `Status: Proposed`。
- 下一步仍是取得至少 30 张合法授权、真实称重且尺度可核验的配对样本；不得用内容社区截图
  降低或绕过现有量化门禁。

## 2026-07-29：用户授权小红书称重图片候选集加工

### 输入与授权状态

- 用户提供 16 张小红书图片，并明确表示作者均允许取用。原始帖子链接、作者标识和授权记录
  尚未逐条提供，因此清单使用 `user_attested / provenance_pending`，没有伪造 CC 许可证或
  将口头确认改写成已核验的公开授权。
- 开始前再次执行并展示 `pwd`、`git status --short --branch`、`ls -la`，随后读取
  `AGENTS.md` 与 `docs/README.md`；当前目录正确，既有未提交改动未被覆盖。
- 原图和拆分格子只保存于 `evals/food_image_scale_candidate/assets/`，该目录已加入
  `.gitignore`；不进入 Git、应用包、Docker 镜像、数据库或普通 CI。

### 加工结果

- 新建 `journey-food-image-scale-candidate-v0`、README、来源清单、格子清单和可复现的
  `prepare_candidates.py`。加工只使用 macOS `sips` 按拼图边界裁切，不使用生成式图片工具，
  不移除作者水印、不补画食物、不改变份量。
- 16 张来源中：1 张长图仅作普通份量参考；1 张 6×6 总览与已有来源重复而排除；其余
  14 张拆出 88 个单食物格子。
- 5 张 2×3 图片共拆出 30 个 `scale_pair_candidate`，每格同时可见食物、电子秤和带刻度
  尺子。另有 58 个格子用于称重/份量参考，但不具备同等尺度证据。
- 对鸡翅尖 10g、猪肝 50g、红苋菜约 100g 和苏打饼干单片参考等代表格子完成视觉抽查，
  裁切边界、食物、叠字、秤和尺子保持可见。

### 门禁与验证

- `python3 evals/food_image_scale_candidate/prepare_candidates.py prepare` 输出：
  `sources=16`、`panels=88`、`scale_pair_candidates=30`、`hard_gate_eligible=0`、
  `status=verified_candidate_only`。
- 所有图片仍含名称/克重叠字或秤读数，原样输入模型会泄露答案；`declared_mass_g` 只是
  叠字转录，`gold_mass_g` 保持空值。本轮没有运行 Qwen、没有消耗模型费用，也没有改变
  ADR-030 `Status: Proposed` 和尺度收益 `Not evaluated`。
- 下一步必须补齐来源/授权证据，人工核对实际秤读数，并在同一格上生成遮挡答案文字和秤
  读数的 `with_ruler`/`without_ruler` 输入；完成视觉 QA、固定哈希和新版本后，才能密封并
  运行一次配对评测。

## 2026-07-29：用户最终确认授权与尺度配对遮挡

### 决策变化

- 用户说明帖子已经关闭，但再次明确确认作者允许 Journey 使用这些图片并要求继续。授权字段
  从 `user_attested / provenance_pending` 更新为
  `user_attested_final / source_links_unavailable`。
- 缺少可恢复来源是永久 provenance 限制，不再作为本机加工的阻塞项；这批二进制只用于
  Journey 内部研发、评测和项目展示，不作为开放数据集再分发，也不声称第三方已独立核验。
- 开始前再次执行并展示 `pwd`、`git status --short --branch`、`ls -la`，读取
  `AGENTS.md` 和 `docs/README.md`；没有覆盖既有改动。

### 确定性遮挡结果

- 新增 `make_redacted_pairs.swift`，对 30 个 `scale_pair_candidate` 使用固定矩形遮挡食物
  名/克重叠字和电子秤显示。`with_ruler` 保留尺子；`without_ruler` 在同一图片上额外遮挡
  尺子。两版尺寸一致，不使用生成式工具、不补画食物、不修改原始食物像素。
- 生成 `pairs_manifest.jsonl` 和 60 张 Git 忽略图片：30 张有尺、30 张无尺。鸡翅尖 10g
  与猪肝 50g 两组完成双版本视觉抽查；答案文字/秤显示被覆盖，食物保持可见，有尺版保留
  刻度、无尺版不再显示尺子。全量 30 组视觉 QA 仍待完成。

### 验证与状态

- `prepare_candidates.py verify`：16 来源、88 格子、30 尺度候选、硬门禁资格 0，通过。
- `prepare_candidates.py verify-pairs`：30 配对、60 图片、有尺/无尺各 30、哈希和尺寸
  通过，状态 `verified_redacted_pairs_visual_qa_pending`。
- `python3 -m py_compile` 与 `swiftc -typecheck` 均通过；图片资产总计约 122MB，继续被
  `.gitignore` 排除。
- 当前没有运行 Qwen、没有产生模型费用。实际秤读数尚未人工转录、全量视觉 QA 和 sealed
  版本尚未完成，因此 ADR-030 继续 `Status: Proposed`，尺度收益仍为 `Not evaluated`。

## 2026-07-29：尺度配对全量 QA、金标转录与内部密封

### 授权与加工结论

- 用户最终确认作者允许 Journey 使用全部 16 张图片；帖子已经关闭，无法恢复逐条 URL。
  授权固定为 `user_attested_final / source_links_unavailable`，仅允许内部研发、评测和项目
  展示，不作为开放数据集再分发，也不宣称第三方已独立核验。
- 人工逐格读取并复核 30 个电子秤显示，写入 `gold_mass_g`；范围为 2.0—50.3g。金标来自
  同一原图的秤显示，不使用图片叠字的整数声明替代实际读数。
- 重新生成 30 组 `with_ruler`/`without_ruler` 配对并完成全量 contact sheet 检查；对
  低对比显示和疑难格继续放大复核。最终 60 张均未发现食物被遮挡、名称/克重叠字或秤显示
  残留；无尺版额外遮挡尺子，有尺版保留尺子。
- 首轮 contact sheet 暴露左列底行裁切异常，原因是 `sips` 对零裁切坐标采用默认行为；
  改为 1 像素安全偏移并重建 88 个格子后通过。首轮遮挡还残留少量叠字边缘，扩大固定遮挡
  矩形并重建后通过。两项均在密封前发现并修正。

### 密封与验证证据

- 新建 `journey-food-image-scale-holdout-v1`，固定 30 组、60 张二进制的 SHA-256、尺寸、
  食物名称、实际秤读数、授权边界和视觉 QA；二进制继续位于 Git 忽略的 `assets/`。
- 密封清单强制 `prompt_tuning_allowed=false`。候选与密封校验输出：
  - candidate：`sources=16`、`panels=88`、`scale_pair_candidates=30`；
  - pairs：`pairs=30`、`images=60`、`status=verified_redacted_pairs_qa_passed_unsealed`；
  - holdout：`pairs=30`、`images=60`、`gold_mass_complete=true`、
    `visual_qa=passed`、`provider_calls=0`。
- `prepare_candidates.py make-pairs/verify/verify-pairs`、
  `seal_holdout.py seal/verify` 与两份脚本 `py_compile` 全部通过。

### 为什么本轮没有运行 Qwen

- 公开 `FoodImageAnalyzeRequest` 的参照枚举只有 `none`、`journey_card`、
  `plate_diameter`、`bowl_diameter`，真实评测器严格复用 `/api/v1`。它目前无法声明
  “图中是厘米尺”。
- 把有尺图片按 `none` 发送会触发“不得根据未声明物体假设真实尺寸”的 Prompt，不能形成
  公平的有参照/无参照对照。因此 holdout 虽已密封，仍标记
  `hard_gate_eligible=false / blocked_public_contract_lacks_centimeter_ruler`。
- 本轮未修改后端或移动端契约、未调用真实 Provider、未产生 Token 或费用。下一步必须先以
  Proposed ADR 决定是否增加 `centimeter_ruler` 或只建立隔离试验适配器，再对密封集执行
  一次真实配对评测。ADR-030 保持 Proposed，尺度收益继续 `Not evaluated`。

## 2026-07-29：内部厘米尺隔离适配器与唯一一次真实配对评测

### 决策与运行前门禁

- 用户确认继续上一轮推荐：厘米尺只进入隔离评测适配器，不修改正式
  `FoodImageAnalyzeRequest`、OpenAPI、移动端选项或 v1.3 Prompt。该 Accepted 子决策写入
  ADR-030，但 ADR 整体继续 Proposed。
- 新增 `run_food_image_scale_pair.py`，固定
  `journey-food-image-scale-ruler-eval-1.0.0` /
  `journey-food-image-scale-ruler-schema-1`。预注册有尺误差 ≤30%、相对改善 ≥15%、
  参照判断 ≥95%、Schema/强制校正 100%、p95 ≤8 秒和 fallback 0。
- Docker 静态检查、Ruff、format 与纯函数测试通过。首次 format check 按设计发现 1 文件
  待格式化；修正后 4 项测试通过。首次 dry-run 因 API 镜像默认入口在挂载工作目录执行
  Alembic 而缺少 `script_location` 失败；改用明确 Python entrypoint 后通过，未产生
  Provider 调用。
- 最终 dry-run 固定：30 组、计划 60 调用、北京区域 `qwen3.7-flash`、运行上限 `$0.02`，
  配置每日预算 `$0.138889`；密封哈希、模型、区域、外发确认和正定价全部通过。

### 唯一一次真实结果

- 只生成一次原始报告 `STAGE9_QWEN_SCALE_RULER_PAIRED_V1.json`，输出文件已存在时评测器会
  拒绝覆盖。60/60 调用完成，没有重跑、没有修改冻结 Prompt，也没有改变正式 App/API。
- 53/60 结构化有效，7 次 `ValidationError`；有尺有效 24、无尺有效 29，只有 24/30 个
  同图配对两边都可评分。
- 正确同图口径：有尺份量误差中位数 **47.82%**，无尺 **48.87%**，相对改善
  **2.17%**；分别未达到 ≤30% 和 ≥15%。有效输出中的参照判断全部正确，但把失败计入后为
  53/60=88.33%，未达到 ≥95%；fallback 7 未达到 0。p95 3744 ms 通过。
- 原始报告错误地用 24 个有尺有效值和 29 个无尺有效值分别求中位数，得到 4.37%；随后只读
  复算生成 `STAGE9_QWEN_SCALE_RULER_PAIRED_V1_RESCORED.json`，Provider 调用数 0，修正为
  24 个完整配对和 2.17%。
- 7 个无效响应的用量在首版异常分支被清零，导致已记录 24,035 input / 7,032 output Token、
  `$0.00144897` 只是费用下限。评测器现已在失败分支保留已取得的 usage，并新增配对覆盖与
  usage 完整率门禁和回归测试；为了遵守密封集唯一运行规则，不再次调用模型补数。

### 验收与阶段状态

- 原始和修正版报告的图片/base64/Key/Bearer 模式扫描通过；报告只含样本 ID、金标、预测、
  错误类型、Token、费用和延迟。密封 30 组/60 图片哈希复验继续通过，二进制保持 Git ignored。
- 发现 `.gitignore` 的无锚点 `reports/` 同时忽略了 `evals/reports/`，会使版本化机器报告与
  文档链接在未来提交中丢失；改为仅忽略根目录 `/reports/`。`evals/reports/` 共 10 个既有
  版本化报告约 584KB，现可进入版本控制，图片资产仍保持忽略。
- 评测器 Ruff、format、`py_compile`、4 项测试及 `git diff --check` 通过。没有运行完整
  后端/移动端回归，因为正式业务代码、API 和客户端均未修改。
- 本次多数真实门禁失败，不能宣称尺度参照或图片份量已验收。ADR-030 保持 Proposed，阶段
  9 食物图片单项继续 In Progress；默认 Mock、必须用户校正与手动记录回退不变，不开始其他
  阶段 9 能力。

## 2026-07-29：食物图片失败收尾与实验性辅助定位

### 范围与决策

- 用户要求继续后，按上一轮建议采用“接受辅助定位并收尾”，没有擅自启动更强模型评测、
  语音、视频、手机号、健康平台或其他阶段 9 能力。
- 核对代码确认：后端图片分析只生成候选，用户必须打开表单校正并显式确认后才写入；
  staging 固定 `FOOD_IMAGE_ANALYSIS_ENABLED=false / FOOD_IMAGE_PROVIDER=mock`；
  EAS Preview/Production 固定关闭客户端入口；离线、失败和关闭均可回退手动记录。
- ADR-030 增加 Accepted 子决策：当前厘米尺改善路线和“照片可可靠称重”承诺 No-Go；
  保留图片隐私、结构化候选和确认链路作为 Development 受控实验，ADR 整体继续 Proposed。

### 最小产品改动

- 移动端标题改为“图片辅助估算（实验）”；首屏明确“模型不能通过照片准确称重”，结果点
  估计明确“不是称重值 · 必须校正”。
- 组件测试新增三项可见性断言，Web E2E 增加实验标题和不能准确称重提示；没有改 API、
  数据库、模型、Prompt、Schema、Feature Flag 默认或正式环境配置。
- 唯一计划、ADR、隐私评测文档、总评测报告和文档索引同步记录 No-Go 与重启条件：新的
  Proposed ADR、新独立 holdout、重新复核的视觉模型/隐私/预算。

### 验收证据

- `npm --workspace @journey/mobile run lint`：通过。
- `npm --workspace @journey/mobile run typecheck`：通过。
- `npm --workspace @journey/mobile run test:components -- --runTestsByPath
  tests/food-image-screen.test.tsx`：1 个 Suite、7 个测试全部通过。
- `node infra/verify_app_variants.mjs`：通过；Development 可显式开启，Preview 与
  Production 保持关闭。
- `npm --workspace @journey/mobile run web:build`：通过；Expo Web 成功导出 13 条静态
  路由，包含 `/food-image`。
- 当前本机 API 明确为 `FOOD_IMAGE_PROVIDER=qwen / qwen3.7-flash`。Web E2E 会直接连接
  该 API，因此没有执行会上传合成图片并产生真实调用的图片 E2E。新增文案由目标组件测试
  覆盖，E2E 断言已同步，待未来切回 Mock 隔离环境再运行。
- `git diff --check`：通过。

### 完成状态

- 本轮“失败收尾与实验性辅助定位”已完成；没有调用真实模型、没有产生新增模型费用，也
  没有开始其他阶段 9 能力。
- 阶段 9 食物图片单项整体仍为 `In Progress`，ADR-030 仍为 `Status: Proposed`。只有在
  新建 Proposed ADR、独立 holdout，并重新确认视觉模型、隐私与预算后，才能启动下一轮
  真实图片能力评估。

## 2026-07-30：ADR-031 识别优先方向与独立 holdout 预注册

### 范围与安全检查

- 用户要求按计划继续。开始前再次执行并展示 `pwd`、`git status`、`ls -la`，确认当前目录
  为 Journey，保留全部既有未提交迁移改动；读取 `AGENTS.md`、`docs/README.md`、唯一计划
  和 ADR-030。
- 本轮只继续阶段 9 食物图片单项，没有启动语音、视频、手机号、健康平台或通知能力；没有
  修改正式 App、API、数据库、Prompt、Schema 或环境开关。
- 没有调用真实 Provider、没有读取或输出 Key、没有上传图片、没有产生模型费用。

### 决策与数据审计

- 新增 ADR-031 `Status: Proposed`：下一候选方向把食物名称识别和份量确认解耦。视觉模型
  最多提供 3 个名称候选，不输出克重或热量点估计；用户在既有表单确认名称与份量，再由
  受控营养数据计算。ADR-030 的厘米尺 No-Go 和正式环境关闭不变。
- 预注册 `journey-food-image-recognition-holdout-v2`：60 张全新来源图片，覆盖 20 张中国
  家庭餐、15 张单一食物、10 张混合餐、10 张包装食品和 5 张非食物；固定 Top-3、拒答、
  Schema、禁止估重、延迟和预算门禁。
- 审计确认现有 100 张调试集、30 张泛化集和 30 组厘米尺集都已被模型使用，不能改名复用；
  用户提供图片的剩余格子同源且多有答案叠字，也不足以代表独立真实场景。当前缺少 60 张
  授权、隐私合格且零重叠的新图片，因此只建立 README 规格，不创建虚假 manifest/assets，
  不启动真实评测。

### 零 Provider 调用验证

- `prepare_dataset.py verify`：`journey-food-image-real-v1` 100 张、约 28.6MB，通过。
- `prepare_holdout.py verify`：`journey-food-image-holdout-v1` 30 张，与调试集在 ID、
  source ID 和 SHA-256 上零重叠，通过。
- `seal_holdout.py verify`：尺度集 30 组/60 图片，金标完整、禁止调参、Provider 调用 0，
  通过。
- `prepare_candidates.py verify-pairs`：30 组有尺/无尺配对通过，授权边界保持
  `user_attested_final_source_links_unavailable`。
- 验证 v2 目录只有规格 README，不存在 `manifest.jsonl` 或 `assets/`；`git diff --check`
  通过。

### 当前状态与下一启动条件

- ADR-031 仍为 Proposed，阶段 9 食物图片单项继续 In Progress；本轮完成的是重新启动前的
  产品决策与数据门禁，不代表新方案已经实现或质量通过。
- 下一步必须由用户接受 ADR-031，并确认候选视觉模型/区域/数据政策/价格；随后取得并在模型
  调用前密封 60 张合格新图片。两项均满足后才能修改产品契约或运行一次真实评测。

## 2026-07-30：ADR-031 用户确认与 60 张识别 holdout 密封

### 范围与安全检查

- 用户要求继续，视为接受 ADR-031 的“视觉模型只给名称候选、份量由用户确认”产品方向；
  本确认不代表候选模型质量通过，也不授权改正式 App/API。
- 开始和断网恢复后均重新执行并展示 `pwd`、`git status --short --branch`、`ls -la`，
  确认仍在 Journey 当前目录；读取 `AGENTS.md` 与 `docs/README.md`，保留既有大范围未提交
  迁移改动。
- 本轮只建立新独立评测数据与文档证据，没有修改移动端、后端、数据库、Prompt、Schema
  或环境开关，没有启动其他阶段 9 能力。

### 来源、下载与许可

- 审计既有数据：`food_image_real` 为 70 张 Nutrition5k、20 张 Open Food Facts、10 张
  Openverse；`food_image_holdout` 为 30 张 Nutrition5k；尺度集为用户确认授权的内部图片。
  新数据选择此前未使用的 Wikimedia Commons。
- 新增受限下载脚本：每次请求至少间隔 1 秒，HTTP 429/5xx 最多有界重试；单图最大 2 MiB、
  最小边 240 px、总量上限 60 MiB，只接受明确的 CC BY、CC BY-SA、CC0 或 Public domain。
- 初次连续检索在第 11 次请求收到 HTTP 429，脚本停止；加入节流和恢复机制后从已有进度
  继续，没有重复下载或高频绕过限流。
- 每条清单记录 Commons page ID、文件页、原图/缩略图 URL、作者/署名、许可名称和许可
  URL。最终许可为 CC BY 6、CC BY-SA 38、CC0 12、Public domain 4；44 张需要署名。

### 分层、人工 QA 与密封

- 建立 60 张全新数据：中国家庭餐 20、单一食物 15、混合餐 10、包装食品 10、非食物 5；
  图片总计 10,645,751 字节，位于 Git ignored `assets/`，不进入应用包或仓库。
- 首轮搜索排序产生 15 张语义不符、人物或非目标图；第二轮复核又替换 6 张；最后替换含
  未成年人的番茄图和混有吐司的水煮蛋图。每轮均重建分层联系表，最终五组 60 张全部完成
  人工目视检查。
- 最终图片不含可识别人脸、未成年人、证件、病历或个人标识，不含食物答案、克重或热量
  答案叠字；食物与金标一致，非食物均标为拒答。黑色未烹饪臭豆腐因来源标题与标签一致，
  保留为困难样本。
- `manifest.jsonl` 固定逐图 SHA-256、来源许可、金标、隐私/视觉 QA、
  `prompt_tuning_allowed=false` 和 `sealed=true`；封存后脚本拒绝重新抽样或替换。

### 验证与当前门禁

- `prepare_holdout.py verify`：60 张、分层 20/15/10/10/5、10,645,751 字节、
  `sealed=true`、旧数据集/source ID/SHA-256 重叠均为 0、Provider 调用 0，
  `status=verified_sealed`。
- `python3 -m py_compile prepare_holdout.py`、`swiftc -typecheck make_contact_sheets.swift`
  与 `git diff --check` 纳入本轮最终验收；联系表仅用于本机 QA 并保持 Git ignored。
- ADR-031 仍为 Proposed：数据门禁已完成，但候选视觉模型、区域、数据政策、价格、独立
  Key 和人民币 1 元/日预算尚待重新复核，一次真实识别质量评测尚未运行。
- 下一步只允许先完成上述模型政策复核，再建立只读评测器，对密封集运行唯一一次真实
  评测；不得使用 holdout 调 Prompt，不得恢复照片自动估重承诺。

## 2026-07-31：ADR-031 模型复核与唯一真实识别评测（Closed / No-Go）

### 范围与安全检查

- 用户要求继续。开始前执行并展示 `pwd`、`git status`、`ls -la`，确认当前目录仍为
  Journey；读取 `AGENTS.md`、`docs/README.md` 和阶段 9 单一事实源，保留全部既有未提交
  改动。
- 本轮只执行阶段 9 食物图片单项的 ADR-031 质量门禁，没有启动语音、视频、手机号、
  HealthKit/Health Connect、通知或其他能力。
- 没有修改正式 App、API、数据库、业务 Prompt/Schema 或环境默认值；没有提交、push、
  创建 PR、创建公网资源或输出 Key。输入仅为公开许可且无个人信息的密封评测图。

### 模型、区域、政策与预算复核

- 通过北京 OpenAI-compatible `/models` 只读探测确认 `qwen3.7-flash` 与固定快照
  `qwen3.7-flash-2026-07-15` 可用；正式评测固定调用快照而不是漂移 alias。
- 官方文档确认北京区域支持 Qwen 3.7 图片理解；混合思考默认开启，因此隔离评测器显式
  `enable_thinking=false`。
- 官方价格复核为小于等于 32K Token 时输入人民币 0.2 元/百万 Token、输出人民币
  0.8 元/百万 Token；根 `.env` 的美元换算分别为 `0.027778` / `0.111111`，每日预算
  `0.138889` 美元（按 7.2 汇率约人民币 1 元），单轮硬上限 `$0.02`。
- 官方隐私声明称调用数据不用于训练并使用 AES-256 加密，同时说明因法律要求会存储调用
  数据但未公布精确保留期。本轮只上传 Wikimedia Commons 公开许可、无个人信息图片；
  该残余风险不扩展为允许上传真实用户照片。
- 依据：
  [模型与快照](https://help.aliyun.com/en/model-studio/text-generation-model/)、
  [北京区域多模态支持](https://help.aliyun.com/zh/model-studio/batch-inference)、
  [价格](https://help.aliyun.com/en/model-studio/model-pricing)、
  [隐私声明](https://help.aliyun.com/zh/model-studio/privacy-notice)。

### 一次性评测器与零调用验收

- 新增 `evals/run_food_image_recognition.py`：冻结
  `journey-food-image-recognition-eval-1.0.0` Prompt、
  `journey-food-image-recognition-schema-1` Schema、评分器与模型快照；只允许最多 3 个
  名称候选，禁止克重、份量、热量、营养、价格、医学结论和自动写入。
- 评测器逐文件复验 60 张图片哈希、分层 20/15/10/10/5、许可、隐私/视觉 QA、密封状态
  和三重零重叠；报告不保存图片、base64、Key 或原始模型文本。
- `run_receipt.json`、不可覆盖输出和 Git ignored 原子检查点共同防止重跑；网络中断只能
  跳过已完成样本并继续剩余样本。Provider 重试、后备模型路由、缓存均为 0；单次 Schema
  失败仍按预注册 `fallback=0` 质量门禁计为一次降级失败。
- `python -m py_compile`：评测器与测试通过。
- `ruff check` 与 `ruff format --check`：2 个文件通过。
- `pytest -q -p no:cacheprovider evals/test_food_image_recognition.py
  evals/test_food_image_scale_pair.py`：11/11 通过。
- 首次 dry-run 因容器 `PYTHONPATH` 未指向 `/app/backend` 在导入阶段退出，Provider 调用
  仍为 0；显式设置容器 `PYTHONPATH` 后重跑通过：
  `samples=60`、`planned_calls=60`、`provider_calls=0`、模型/区域/预算/密封哈希全部通过。
- 正式报告生成后再次给出相同 `--execute --output`，评测器在 Provider 初始化前以
  `refusing to overwrite one-run report` 拒绝；收据保持 `provider_calls=60`、
  `status=completed`，防重复门禁通过。

### 唯一真实评测结果

- 对 `journey-food-image-recognition-holdout-v2` 运行 60 次，每张图片恰好一次；不重试、
  不调用后备模型、不写数据库。完成后报告、收据与检查点均为 60/60。
- 机器报告：`evals/reports/STAGE9_QWEN_RECOGNITION_V2.json`；
  SHA-256
  `e455f44ef12a547df509c50864926e3c1c35dd49fbf05b976ca218acab515afe`，收据和检查点
  哈希均一致。

| 指标 | 结果 | 门槛 | 状态 |
|---|---:|---:|---|
| 总体食物名称 Top-3 | 37/55 = 67.27% | ≥85% | FAIL |
| 中国家庭餐 Top-3 | 12/20 = 60% | ≥80% | FAIL |
| 单一食物 / 混合餐 / 包装食品 | 86.67% / 40% / 80% | 诊断 | — |
| 非食物拒答 | 5/5 = 100% | ≥95% | PASS |
| Schema / 强制校正 / 禁止估重 | 59/60 = 98.33% | 100% | FAIL |
| 评测降级/失败 / p95 | 1（无后备模型调用）/ 3416 ms | 0 / ≤8000 ms | FAIL / PASS |
| Token/成本记录 | 60/60 | 100% | PASS |
| 总费用 | `$0.00240432`（约人民币 0.0173 元） | ≤`$0.02` 且 ≤人民币 1 元/日 | PASS |
| 未确认自动写入 | 0 | 0 | PASS |

- 共记录 57,876 input / 7,170 output Token，中位延迟 2265 ms。唯一结构化失败为
  `recognition-mixed-meal-008` 的 `ValidationError`，按冻结规则没有重试。
- 不改分的事后审计发现评分器对“水饺/饺子”“牛排套餐/牛排餐”“肉酱螺旋意面/肉酱
  意面”等合理同义或更具体名称过严。因此正式 67.27% 不能被外推为模型真实准确率，但
  预注册门禁已经失败，也不能事后补别名、改 Prompt 或重跑来宣称通过。

### 完成状态与回退

- ADR-031 保持 `Status: Proposed`；正式 App/API 不接入 Qwen 真实图片识别，Preview、
  Production 和 staging 图片能力继续关闭。Mock 演示、文字 Agent 和手动饮食记录不受
  影响。
- 阶段 9 本次唯一获授权的食物图片单项执行完毕，以 **Closed / No-Go** 停止；不自动开始
  其他阶段 9 Backlog。
- 若未来重启，必须由用户另行批准新的 Proposed ADR，先用全新 development set 固化更
  完整的中英文标签本体和语义评分规则，再选择/复核模型并建立全新密封 holdout。不得重跑
  `journey-food-image-recognition-holdout-v2`，也不得借 ADR-031 恢复照片自动估重。

## 2026-07-31：语音转文字范围决策（Deferred）

- 阶段 9 食物图片单项关闭后，用户明确回复“不做语音转文字”。
- 新增 ADR-032 `Status: Accepted`：当前版本不实现录音、语音转文字或 Realtime Voice
  Agent；首页继续使用现有文字统一输入。
- 未申请麦克风权限，未增加音频 Provider、数据集、评测、依赖或业务代码，也未启动视频、
  手机号、HealthKit/Health Connect 或通知能力。
- 唯一计划将语音条目标记为 `Deferred / 当前范围外`，后续 Codex 不得把它当作默认
  下一步。只有用户未来单独明确改变该决定后，才能通过新的 Proposed ADR 重新立项。

## 2026-07-31：最终作品集交付复验与四类岗位材料

### 范围与安全

- 本轮目标是关闭阶段 8 交付基线，为开发、测试开发、产品和售前岗位形成可核验的演示与
  表述材料；没有启动新功能或新的阶段 9 能力。
- 开始前再次执行 `pwd`、`git status`、`ls -la`，目录为 Journey 工作区；保留已有大规模
  未提交迁移改动，没有 reset、clean、commit、push 或 PR。
- 主 Agent、CI 和 E2E 继续使用 Mock、空模型 Key 和零预算；没有调用真实文本/视觉模型。

### 后端、数据库与 Agent/RAG

- `docker compose --profile test run --rm --build test`：
  - 临时 PostgreSQL 18 自动迁移至 `0003_agent_rag`；
  - 65/65 pytest 通过，覆盖率 91.07%（门槛 70%）；
  - 318 条版本化评测样本，17 项 Agent/RAG/图片契约门禁全部通过；
  - `provider=mock`、`failures=0`、`cost=$0`。
- `alembic upgrade head → downgrade 0002_core_api → upgrade head → alembic check`：
  upgrade/downgrade 回环与模型差异检查通过，最终仍为 `0003_agent_rag (head)`。
- 按仓库锁定的 Ruff 0.12.12 执行 `ruff check` 和 `ruff format --check`。首次发现 6 个
  Python 文件格式差异及 1 个测试导入顺序问题，机械修复后 98 个 Python 文件检查通过，
  再次运行完整后端/评测门禁仍全绿。

### 移动端、Web E2E 与三端构建

- 移动端：
  - 5/5 Node 逻辑测试通过；
  - `test:logic` 显式使用 Node ESM 默认类型，消除 `.ts` 模块类型回退解析警告；
  - 7 个 Jest suite、31/31 组件/业务测试通过；
  - coverage：statements 81.46%、branches 70.93%、functions 73.91%、lines 84.30%；
  - TypeScript、Expo lint、development/preview/production 变体检查通过。
- 三端 JS：
  - Web production export 通过，生成 13 条静态路由；
  - iOS Hermes bundle 和 Android Hermes bundle 通过。
- 隔离 Web E2E：
  - 使用独立 Compose project、API `:18000`、DB `:55432`、空模型 Key、Mock 和临时数据；
  - 首次启动发现 `.env.example` 的测试账号密码不满足后端大小写/数字复杂度规则；
  - 修正示例密码，并在 `infra/verify_app_variants.mjs` 增加 10—72 UTF-8 字节、大小写和
    数字门禁；
  - 重跑后 2/2 Playwright 核心流程通过：画像/目标—Agent 食物和运动确认—建议—Journey
    周报，以及图片 Mock—用户校正—确认写入。

### 原生 Release 验收

- iOS：
  - Xcode 26.6、iOS 26.5、iPhone 17 Pro；
  - Release Simulator 首次完整构建 125 个依赖目标，`** BUILD SUCCEEDED **`；
  - `JourneyDev.app` 约 97 MB，安装并前台显示登录页，进程保持
    `running-active-Visible`；
  - 可执行文件 SHA-256：
    `f4341e2185907dc472e6cc48bf405a18aa263d7c50f9cd7dd858f64ce763d490`。
- Android：
  - Android SDK/compile/target 36、ARM64 Pixel 9；
  - 显式设置 `NODE_ENV=production`、`APP_VARIANT=development` 和
    `EXPO_PUBLIC_API_BASE_URL=http://10.0.2.2:8000` 后，832 个 Gradle task 的 Release
    构建成功；
  - 最终 APK 约 42 MB，SHA-256：
    `1da15b0d79df48b6641f93453b04712ce2d59681749f8ed6e950da61d781ad59`；
  - APK v2 签名验证通过，证书 `CN=Android Debug`，仅用于本机模拟器；
  - 最终 APK 在 Pixel 9 冷启动安装成功，`.MainActivity` 为 top resumed activity，
    5 秒后无 `FATAL EXCEPTION`/React Native fatal 日志，登录页视觉正常。
- Pixel 9 默认 4 GB 冷启动在 iOS/Gradle 并行时受到内存压力；关闭 iOS 后使用
  `-no-window -gpu swiftshader_indirect -memory 2048` 可稳定完成同一 APK 的验收。该回退
  已写入构建文档。

### 配置、密钥与供应链

- `docker compose config --quiet` 和带占位 staging secret 的
  `compose.yaml + compose.staging.yaml` 契约通过。
- `.env` 由 `.gitignore` 排除；Git 跟踪文件与生成 mobile bundle 未发现模型 Key 模式。
- `git diff --check` 和环境变体/测试账号模板检查通过。
- Web 静态 export 与 E2E 通过；Web Nginx 镜像本轮两次都在 Docker Hub 拉取
  `node:22.23.1-bookworm-slim`/`nginx:1.29.5-alpine` 元数据时
  `DeadlineExceeded`，与阶段 8 已记录的外部网络问题一致，未伪标通过。
- 当前 `npm audit` 报告 46 个传递依赖告警（34 high、12 moderate），集中在
  Expo/Jest/ESLint 构建测试工具的 `brace-expansion` 和 `uuid` 路径。npm 的自动方案要求
  breaking 降级 Jest 或改变 Expo 工具链；本轮未执行 `npm audit fix --force`，把它保留为
  独立依赖升级任务和生产发布前门禁。
- Android 构建仍有第三方插件弃用提示、SDK XML 兼容提示和首次 Metaspace 压力；当前
  Gradle 9 build/lint 成功，但升级到 Gradle 10 前必须核对 Expo/React Native 兼容矩阵。

### 求职交付与最终边界

- 更新 `docs/demo/RESUME_AND_INTERVIEW.md`：提供通用、测试开发、产品、售前四种简历讲法，
  60 秒开场、3 个 STAR 案例、高频问答和不可夸大的限制。
- 更新演示脚本、架构图、构建说明、阶段 8 报告、计划和文档索引，统一使用当前
  65/91.07%、318/17、31+5、2 E2E 口径。
- 当前结论：可用于本机作品集与秋招演示；不等同于公网生产、真实主模型质量、TestFlight/
  App Store、Play 商店签名或依赖风险清零。
- 当前没有自动下一阶段。可由用户另行授权的后续任务包括：本地 Git 提交、服务器/HTTPS
  部署、商店签名或上游依赖升级；本轮停止，不自动实施。

## 2026-08-01：文字与图片对应真实模型验收口径

### 范围与安全

- 用户确认当前功能范围暂时只保留文字与图片，并要求验收改为各自对应的真实模型。本轮没有
  启动语音、视频、手机号、HealthKit/Health Connect、通知、公网部署或商店签名。
- 开始前执行并展示 `pwd`、`git status --short`、`ls -la`，目录仍为 Journey；保留全部既有
  未提交迁移改动，没有 reset、clean、commit、push 或 PR。
- 读取 `AGENTS.md` 与 `docs/README.md` 后新增 ADR-033。普通 CI 继续使用 Mock，但 Mock 不再
  作为真实模型发布验收的充分证据。
- 所有探测和报告只记录 Provider、模型、版本、Token、延迟、费用和结构化结果；没有输出、
  写入仓库或发送到客户端的 API Key。

### 模型可用性与真实 API 冒烟

- 首次在本机系统 Python 运行只读探测因缺少 `python-dotenv` 在导入阶段退出；没有发出网络
  请求。改用项目锁定后端容器后，两端 `/models` 均返回成功：DeepSeek 列出
  `deepseek-v4-flash`，Qwen 北京端点列出 `qwen3.7-flash`。
- `docker compose up -d --build db api`：API 与 PostgreSQL 健康；`/health/ready` 返回 200。
- 首次 E2E 内联脚本因系统 Python 不支持 PEP 604 类型注解，在请求前退出；移除注解后重跑：
  - 文字：DeepSeek `deepseek-v4-flash` 对混合饮食/运动输入返回 `food`、`activity` 与两个
    候选，`fallback=false`，1344 input / 436 output Token，4819 ms，`$0.00031024`；
  - 图片：Qwen `qwen3.7-flash` 对 Nutrition5k CC BY 4.0 苹果图返回“苹果”候选，
    `needs_user_correction=true`、`image_retained=false`、`fallback=false`，665 input /
    210 output Token，2259 ms，`$0.00004181`。
- 图片冒烟只验证真实 API 和隐私/候选契约，不替代 ADR-031 的 60 张独立质量门禁。

### 真实文字量化门禁

- 新增 `evals/run_text_provider_acceptance.py` 和 3 条零外部调用回归测试；Ruff check/format
  通过，`pytest -q -p no:cacheprovider evals/test_text_provider_acceptance.py` 为 3/3 通过。
- 第一次容器 dry-run 因未设置 `PYTHONPATH=/app` 在导入阶段退出，Provider 调用 0；补齐后
  dry-run 返回 `planned_calls=28`、`provider_calls=0`、最大费用 `$0.02`。
- 首轮正式执行完成 28 次 DeepSeek：路由 17/18=94.44%，饮食 5/5、运动 5/5，0 retry/
  fallback，p95 1595 ms，费用 `$0.00240632`。唯一失败为“我的体重是多少”被真实模型误判
  为记录 `weight`；虽然总分通过 90% 门槛，但实际会选错工具，因此没有直接关闭问题。
- 最小修正把 Router Prompt 从 `intent-router-1.0.0` 升到 `1.0.1`，明确查询已有身高、体重、
  目标属于 `profile`，只有给出明确数值并表达记录/称重才属于 `weight`；新增 1 条 Prompt
  回归测试。修正后 dry-run 仍为 28 项、Provider 调用 0。
- 修正后再次完整执行 28 次：路由/饮食/运动全部 100%，Provider/模型、Schema/无 fallback、
  Token 记录均 28/28，0 retry、0 fallback，p95 1768 ms，共 13502 input / 2048 output Token，
  费用 `$0.00246372`，全部门禁通过。
- 修正后报告 `evals/reports/REAL_TEXT_DEEPSEEK_V4_FLASH_2026_08_01_AFTER_ROUTER_FIX.json`
  SHA-256 为 `bffd0e625924d26552c3122fa265c297f44992d0b2c8dbd17eebbd55b24d0e32`；修正前报告继续
  保留，SHA-256 为 `421f1ec717dbc34602fec46e27ee7a9259bb7f54a5686da4c2341e253f04e801`。
- `docker compose up -d --build api` 更新运行镜像后，通过公开 API 再次输入“我的体重是多少”：
  返回 `profile`、0 候选、存在画像回答、`fallback=false`，DeepSeek 1401 ms，估算费用
  `$0.00008918`；确认 Prompt 修正已进入实际服务链路。
- `docker compose --profile test run --rm --build test`：新增 3 条评测器测试和 1 条 Prompt
  回归后为 69/69，
  后端覆盖率 91.07%；318 条 Mock 样本、17 项门禁、`failures=0`、`provider=mock`、`cost=$0`
  继续通过。

### 结论与回退

- 文字真实模型验收 PASS；图片真实 API 功能 smoke PASS；图片真实质量仍 FAIL。总体
  “文字 + 图片”正式发布验收为 Conditional / 未通过。
- Development 可联网演示 DeepSeek 文字与 Qwen 实验性图片候选；图片必须用户校正和确认，
  Preview/Production/staging 继续关闭。失败或断网时回退 Mock/手动记录。
- 新增 `evals/reports/REAL_MODEL_ACCEPTANCE_2026_08_01.md` 作为验收报告，并同步更新计划、
  ADR、审计、文档索引与求职演示口径；本轮不自动开始新阶段。

## 2026-08-03：手机模拟器展示与自动化测试即时复验

### 模拟器与服务

- 开始前执行并展示 `pwd`、`git status`、`ls -la`，当前目录仍为 Journey；保留全部既有
  未提交迁移改动，没有 reset、clean、commit、push 或 PR。
- `docker compose ps` 显示 PostgreSQL 与 FastAPI 均为 healthy，`/health/ready` 返回 200。
- 使用已安装的 iOS 26.5 Runtime 启动 iPhone 17 Pro Simulator，重新安装并启动
  `apps/mobile/ios/build/acceptance/Build/Products/Release-iphonesimulator/JourneyDev.app`；
  `com.boom080.journey.dev` 启动成功并显示 Journey 登录页。
- 本次现场截图保存为
  `artifacts/final-acceptance/ios-live-demo-2026-08-03.png`。Android 的 Pixel 9 AVD 与
  Release APK 均仍存在，但本轮未重复启动 Android；iOS 是当前主要本机展示路径。

### 自动化测试

- `docker compose --profile test run --rm --build test` 通过：后端 69/69，覆盖率 91.07%；
  318 条确定性 Agent/RAG/图片契约样本和 17 项量化门禁全部通过，`provider=mock`、
  `failures=0`、`cost=$0`。
- `npm run test:logic --workspace @journey/mobile` 通过 5/5；
  `npm run mobile:test:ci` 通过 31/31，移动端统计覆盖率 81.46%、分支覆盖率 70.93%；
  `npm run mobile:typecheck` 与 `npm run mobile:lint` 均通过。
- GitHub Actions 仍包含后端/数据库迁移、Agent/RAG 门禁、移动端测试、类型检查、lint、
  Web/原生 JS 构建与核心 Web E2E。已有最终验收证据为 Web E2E 2/2；本次即时复验未重复
  运行浏览器 E2E。

### 结论与边界

- 当前可直接使用 iOS Simulator 完成本机手机界面展示；Android 也具备既有 AVD/APK 路径，
  但不是本次现场已启动的窗口。
- 自动化测试体系和 CI 已完成且当前复验通过。普通 CI 继续使用 Mock；DeepSeek 文字真实
  模型门禁已通过，但 Qwen 图片的 60 张真实质量门禁仍未通过，因此图片只作为 Development
  实验性候选，不得把“自动化测试通过”表述为“图片识别质量已达生产标准”。

## 2026-08-03：阶段 10 Agent v2 与测试报告增强

### 范围与安全基线

- 用户授权按建议把固定分支升级为更完整但不过度设计的单 Agent，并补齐 Allure 报告。
- 开始前执行并展示 `pwd`、`git status`、`ls -la`；当前目录为 Journey 工作区。保留阶段
  1—9 的全部既有未提交改动，没有 reset、clean、删除、commit、push 或 PR。
- 本阶段不启动语音、视频、手机号、HealthKit/Health Connect、新图片质量评测、公网部署
  或商店签名；真实模型只使用已有 DeepSeek 文字配置和固定小预算门禁，Key 未打印或落盘到
  报告。

### 决策与实现

- 新增并接受 ADR-034：采用一个 Agent 的 Planner → Policy Guard → Executor → Verifier
  条件执行图，不引入多 Agent 互聊或新微服务。每次最多 6 步、最多 1 次重规划。
- 新增 Pydantic `AgentPlan`/`AgentPlanStep`/`AgentVerification`、10 个工具的类型化服务端
  注册表和依赖/确认 Policy。模型不能创建任意工具名、访问数据库或绕过确认写入。
- `/api/v1/agent/runs` 保持旧字段兼容，同时返回 `thread_id`、计划、步骤状态和验证结果；
  饮食、运动、体重仍只生成候选，由现有 confirmation Token + 所有权 + Idempotency-Key
  完成用户确认后写入。
- 新增 Alembic `0004_agent_v2`：`agent_threads` 保存用户归属和最近 8 条结构化摘要；Agent
  Run 保存计划、验证和重规划计数。线程不保存原始输入、图片、Key 或完整 RAG 片段，画像与
  核心记录表仍是事实源。
- 首页保持“首页、Journey、我的”三个一级入口，在结果卡新增计划步骤、工具名、执行状态、
  校验结论、重规划次数和线程标识，不迁移或重做其他业务页面。
- `AGENT_V2_ENABLED=false` 可回退阶段 6 的 v1 固定工作流；公开 API 和核心业务数据不回退。

### Agent v2 评测与真实模型反馈闭环

- 新增 `evals/datasets/agent_v2_plans.json` 的 24 条固定样本，在确定性评测中增加计划 Schema、
  工具序列、工具参数、确认/写入 Policy 和步骤边界 5 项门禁；总量从 318 条/17 项增至
  342 条/22 项。
- 新增 `evals/run_agent_v2_provider_acceptance.py` 和 3 条自身回归测试。真实门禁固定 8 个
  任务、Router + Planner 共 16 次调用，不访问业务数据库、不写健康记录；报告只保存脱敏
  计划、Token、延迟、费用和 Provider 元数据。
- 首轮 DeepSeek `deepseek-v4-flash` 运行：意图和 Schema 100%、0 fallback，但模型对简单
  任务过度加入 `context.load`/`journey.read`，并产生不合法依赖；工具序列准确率 0、Policy
  合法率 75%，门禁失败。报告：
  `evals/reports/REAL_AGENT_V2_PROVIDER_ACCEPTANCE.json`。
- 根据失败样本把 Planner Prompt 从 `journey-agent-planner-2.0.0` 升到 `2.0.1`，冻结最小
  工具配方，明确只有建议/周总结加载上下文和知识、只有历史任务读取 Journey，并约束生成
  节点依赖。
- 第二轮固定验收：8/8 任务的意图、计划 Schema、工具序列、Policy、Provider/模型、无
  fallback 和 Token 记录均为 100%；16 次调用 0 retry、0 fallback，p95 3112 ms，费用
  `$0.00257824`，门禁通过。报告：
  `evals/reports/REAL_AGENT_V2_PROVIDER_ACCEPTANCE_2.json`。修正前报告继续保留，不能只展示
  成功结果。

### 自动化测试与报告

- `allure-pytest==2.16.0` 已锁入开发依赖；Agent v2 测试增加 epic/feature 元数据和脱敏附件。
  递归脱敏器覆盖 Authorization、Token、API Key、密码、secret、原始 message 和完整 segment。
- Compose 与 GitHub Actions 的后端 job 同时生成 `reports/backend/allure-results`、JUnit、
  Coverage 和 Agent JSON 报告。API 自动化继续使用 Pytest + FastAPI HTTPX/TestClient；
  Playwright 负责真实浏览器闭环，不为了名称额外引入 Requests。
- Mock 全量 Compose 回归：79/79 tests 通过，后端覆盖率 90.80%；342 条样本、22 项门禁全部
  PASS，`provider=mock`、外部调用 0、费用 `$0`。
- migration：`0004 → 0003_agent_rag → 0004` 成功，`alembic check` 返回无新操作；Ruff
  check/format 覆盖 `backend/app`、`backend/tests`、`evals` 共 110 个文件并通过。
- 移动端逻辑测试 5/5、Jest 31/31；statements 81.99%、branches 69.47%、lines 84.83%；
  TypeScript 和 Expo lint 通过。
- Playwright 核心 Web E2E 2/2 通过。第一次因断言仍匹配旧“校验通过”文案失败，改为匹配
  新的“所有计划步骤已完成或进入用户确认”后重跑通过。
- Web production export 成功生成 13 条路由；iOS 与 Android JS export 均成功。
- 最终镜像以 Mock、空真实 Key 和零预算重新创建；PostgreSQL/API 均 healthy，容器内 Planner
  版本为 `journey-agent-planner-2.0.1`。公开 API 输入“查询最近的 Journey 记录”返回单步
  `journey.read`、步骤 `completed`、Verifier `passed=true`、`replan_count=0`。
- `ruff check` 与 `ruff format --check` 按 CI 真实目录结构验证 110 个文件，Compose config、
  diff whitespace、仓库密钥模式扫描和真实报告脱敏断言均通过；Allure 目录生成 684 个原始
  结果/附件文件。

### 原生模拟器验收

- Android Pixel 9 / ARM64：Release APK 构建、安装和启动成功。终端最初缺少 `JAVA_HOME` 和
  `ANDROID_HOME`，仅在当前命令中使用 Android Studio JBR 与本机 SDK 路径修复，没有修改
  全局系统配置。真实界面输入 Journey 查询后显示 `journey.read` 计划步骤、完成状态、校验
  结果和 `0/1` 重规划；截图保存于
  `reports/mobile-native/android-agent-v2-result.png`。
- iPhone 17 Pro / iOS 26.5：Release 构建 0 error、2 warning，安装并启动
  `com.boom080.journey.dev` 成功；截图保存于
  `reports/mobile-native/ios-agent-v2.png`。
- Android 与 iOS 分时运行以避免本机内存竞争；移动端模拟器不进入 Docker，不影响应用在
  其他设备按同一源码重新构建运行。

### 阶段结论与边界

- 阶段 10 验收通过，ADR-034 转为 Accepted。Journey 现在可以准确表述为“Agent 增强应用”：
  模型参与意图和计划，服务端策略控制工具，执行结果被验证，失败可受限恢复，写入须人工确认，
  线程记忆与供应商解耦，并有真实/Mock 双层量化证据。
- 这不是后台自主长任务或多 Agent 平台，也不是医疗诊断系统；复杂度按当前业务维持单 Agent。
- 阶段 9 图片质量仍为 No-Go，Agent v2 通过不会改变该结论。普通 CI 继续 Mock/空 Key；公网
  部署、商店签名和新能力需要用户另行授权。本阶段完成后停止，不自动开始新阶段。

## 2026-08-04：阶段 11 Agent v3 人工确认检查点、有限重规划与 Requests 黑盒

### 范围与安全

- 用户确认执行 Agent v3 方案。开始前执行并展示 `pwd`、`git status`、`ls -la`，当前目录仍为
  Journey；保留阶段 1—10 的大量既有迁移改动，没有 reset、clean、删除、commit、push 或 PR。
- 新增并接受 ADR-035；范围只包含确认 checkpoint/恢复、Observation/Verifier/Replanner、
  两条确定性替代工具、移动端恢复交互、Requests 网络黑盒和量化门禁。没有启动多 Agent、
  语音、视频、长期偏好、图片复评、公网部署或商店签名。
- 普通 CI 与网络黑盒固定 Mock、空真实 Key、零外部成本；真实 DeepSeek 只运行固定小预算集。
  checkpoint、Trace 和 Allure 附件不保存原始消息、计划 segment、Authorization 或模型 Key。

### Agent v3 实现

- Alembic `0005_agent_v3` 为 `agent_runs` 增加 checkpoint、Observation、恢复次数和过期时间，
  为 Confirmation 增加计划步骤关联；已完成 `0005 → 0004 → 0005` 与 `alembic check`。
- Planner Schema 升至 v3，确认步骤固定在依赖它的上下文/知识/生成步骤之前。遇到候选后 Run
  返回 `waiting_for_user`，只持久化清空 segment 的安全 checkpoint；候选型单步任务在最后
  确认后直接完成，组合任务才开放显式 Resume。
- Confirmation 返回总数、已确认、待确认和 `resume_available`；新增
  `POST /api/v1/agent/runs/{run_id}/resume`，校验本人归属、状态、完整确认、checkpoint 过期和
  重复恢复，并在恢复时重新读取最新业务记录。
- 每个工具结果标准化为 Observation；Verifier 可返回 `done`、`wait_for_user`、`replan`、
  `clarify`、`fallback` 或 `stop`。可恢复错误最多进入 2 次 Replanner，模型输出还要重新通过
  Policy Guard；非法选择回退确定性 Recovery Policy。
- 工具白名单新增 `knowledge.safe_summary` 和 `recommendation.rules_fallback`，分别处理知识
  生成与建议生成失败；任何路径都不能直接写健康记录或自动切换数据供应商。
- `AGENT_V3_ENABLED=false` 可回退 Agent v2；`AGENT_V2_ENABLED=false` 仍可继续回退 v1。
  OpenAPI/TypeScript 契约、首页轨迹、候选确认页和失败后“继续执行”入口已同步。

### 测试、评测与构建证据

- `docker compose --profile test run --rm --build test`：85/85 通过，后端覆盖率 90.49%；
  362 条版本化样本、26 项 Agent/RAG/图片契约门禁全部 PASS，`provider=mock`、费用 `$0`。
- 通过 bind-mount 复核工作区源文件的 `ruff check --no-cache` 与 `ruff format --check --no-cache`：
  116 个 Python 文件已格式化；`docker compose config --quiet` 同样通过。
- 新增 Requests `>=2.34,<3`、Pytest、Allure 网络黑盒。第一次试跑错误指向主 API，读取了
  本机 DeepSeek 配置并在 Resume 等待 15 秒后超时；该次生成了本机临时演示记录/Run，未打印
  Key，未删除或伪装结果。随后改为独立 `blackbox-api` + `test-db`、强制 Mock/空 Key；
  `docker compose --profile blackbox run --rm --build blackbox` 为 1/1 通过（0.24 秒），生成
  `blackbox-junit.xml` 和 `blackbox-allure-results`。CI 使用同样的独立网络边界与零 Key。
- 移动端 Jest 31/31，statements 75.74%、branches 65.23%、functions 70.12%、lines 78%；
  逻辑测试 5/5，TypeScript 与 Expo lint 通过。
- 首次 Web E2E 暴露两项真实集成缺口：Playwright 的 `127.0.0.1:4173` 未在本地 CORS 白名单，
  以及 Web Alert 确认回调不自动返回首页。补齐固定 E2E Origin、CORS 回归和 Web 返回行为后，
  使用隔离 Mock 文字/图片配置复验 2/2 通过；组合任务确实暂停、确认、Resume 并显示建议。
- Web export 生成 13 条静态路由；iOS 和 Android JS export 均通过。现场可见 iPhone 17 Pro /
  iOS 26.5 Simulator 已启动；Android 本轮无已连接 AVD，阶段 10 的 Release 安装证据保持有效，
  本阶段没有伪报新的 Android 实机/模拟器安装。
- Allure、JUnit、Coverage、Agent JSON、Playwright HTML/JUnit/trace 均有生成路径；GitHub
  Actions 已包含 Ruff、migration、白盒测试、Requests 黑盒、26 项门禁、移动测试、E2E 和
  三端 JS 构建，普通 CI 不读取 `.env` 真实 Key。

### 真实 DeepSeek v3 门禁

- `evals/run_agent_v3_provider_acceptance.py` 先 dry-run：4 个 checkpoint 组合任务、2 个故障
  Observation、计划 10 次调用、实际 Provider 调用 0、预算上限 `$0.02`。
- 随后按预注册数据仅执行一次 `deepseek-v4-flash`：checkpoint 计划 4/4、恢复选择 2/2、
  Provider/模型匹配和 Schema 无 fallback 均为 100%，10 次调用总费用 `$0.00171864`，全部
  门禁通过。Planner 为 `journey-agent-planner-3.0.0`，Replanner 为
  `journey-agent-replanner-1.0.0`，Router 为 `intent-router-1.0.1`。
- 脱敏报告为 `evals/reports/REAL_AGENT_V3_PROVIDER_ACCEPTANCE.json`，SHA-256
  `f36a4f900b5feef0c1175dc8f79fd47ae52bebc76246c01f0597ad6b98d44302`；报告不包含 Key、
  Authorization 或原始用户消息。

### 收口状态

- 阶段 11 全部 Checklist 与 ADR-035 验收条件满足，状态转为 Completed / Accepted。Journey
  可以表述为有人工检查点、显式恢复、工具 Observation、Verifier 决策、有限 Replanner 和
  自动化量化门禁的单 Agent 应用，而不是一次 LLM 调用包装。
- 图片真实质量仍为 No-Go；系统不是医疗诊断、多 Agent 后台、自主无限循环、公网生产或商店
  已发布产品。主 API 在验收后恢复 `.env` 的用户选择配置，不更改或展示 API Key。
- 当前没有自动下一阶段。本阶段到此停止；长期偏好、主动教练、服务器部署或其他能力必须由
  用户另行确认并先建立 Proposed ADR。

## 2026-08-04：阶段 12 本地优先与 AI 原生体验定义（等待用户选择）

### 范围与安全

- 用户只授权先执行产品定义：离线矩阵、首页信息架构、两套视觉方向、量化标准，并询问当前
  Agent 是否能访问浏览器以及小红书接入可行性；未授权修改业务代码或实现网页工具。
- 开始前执行并展示 `pwd`、`git status`、`ls -la`；目录为 Journey 工作区，保留现有大量
  未提交改动，没有 reset、clean、删除、commit、push 或 PR。
- 只读核对 `backend/app/agent/tool_registry.py`、共享契约和移动端会话/待同步/离线分支。
  当前 App Agent 没有 browser/web/search/xiaohongshu 工具，`knowledge.retrieve` 是受控 RAG。

### 设计与决策产物

- 新增 `docs/product/LOCAL_FIRST_AI_UI_PROPOSAL.md`：当前截图问题、在线/离线能力矩阵、
  本地事实副本与冲突模型、首页信息架构、AI 状态文案、方案 A/B 和量化门禁。
- 新增 ADR-036 Proposed：PostgreSQL 保持同步事实源，移动端目标为账户隔离的本地副本；首页
  统一输入进入首屏，离线提示从大警告卡降为轻量状态。
- 新增 ADR-037 Proposed：不直接绑定小红书账号、不使用 Cookie/自动登录/后台抓取；近期候选
  是用户逐次主动分享公开链接，长期候选是有引用和安全边界的受控 Web Research Tool。
- 创建对话内可交互 `journey-home-concepts.html`，提供“温和 AI 健康伙伴”和“轻量数据智能”
  两套方向，并可切换在线/离线查看状态差异；该文件不是 App 源码。

### 小红书公开能力复核

- 小红书 Ark 官方简介当前聚焦商品、库存、价格和包裹管理；小程序开放平台介绍端内载体、
  经营入口与笔记发布能力。公开页面未证明存在可任意搜索消费者笔记或推荐流的公共 API。
- 开放平台协议要求合法渠道、用户同意和最小必要，禁止索取用户平台账号密码/认证凭据或代理
  自动登录，并约束平台内容及运营数据使用。因此当前不能把“用浏览器抓取小红书”写成确定
  方案，也不能声称 Journey 已绑定小红书。
- 实施任何官方 API 或 Web Research 前都必须重新核对最新 Scope、协议、隐私、版权和安全
  边界；社交内容只作为生活灵感，不能替代健康事实与受控 RAG。

### 当前结论与下一启动条件

- 阶段 12 当前为 `In Progress（仅提案）`：设计定义已交付，但用户尚未选择视觉方向、本地数据
  范围和小红书近期路径，因此不标记 Completed，也不启动实现。
- 下一步只等待用户确认三项：A/B/组合视觉；是否本机保存全部规范化记录并在退出时清除；
  是否采用“用户主动分享小红书链接”而不是账号绑定与后台抓取。

### 2026-08-04 视觉反馈迭代

- 用户明确否决阶段 12 第一轮 A/B 方向：两套稿都过于阴暗、偏灰，不符合旧版温暖的白＋薄荷绿
  气质；重新绘制的简化叶子吉祥物质量也不可接受。
- 只读复核旧版 `04-home-with-data.png`、色彩 token 和三张品牌角色资产。后续视觉禁止用自绘
  简化叶子替代原角色；首页应直接复用 `journey-leaf-home.png`，饮食/运动状态保留原版对应角色。
- 新增方案 C“暖白薄荷 Journey”对话稿：固定明亮浅色主题，暖白页面、明亮薄荷 Hero、原版
  行走叶子有机裁切、首屏输入、开放式今日指标和小型 Agent 状态条；在线/离线均不变暗。
- ADR-036、产品提案、阶段 12 Checklist、索引和 `AGENTS.md` 已同步：A/B 为已否决迭代，
  方案 C 仍为 Proposed。未修改 `apps/`、`backend/`、数据库或 Agent 工具。
- 下一步等待用户直接评价方案 C；未确认前继续停留在设计定义，不进入实现。

## 2026-08-04：阶段 12 方案 C 首页视觉子项实现与验收

### 授权与范围

- 用户确认“这一版看起来不错可以继续”，授权把方案 C 落到移动端首页。本次严格只改暖白薄荷
  视觉、原版吉祥物复用、首屏输入/指标/Agent 状态和相关测试；没有实现完整本地数据副本、
  数据库/API、Agent/RAG 或小红书能力。
- 开始前已执行并展示 `pwd`、`git status --short`、`ls -la`；目录仍为 Journey 工作区，保留
  既有未提交改动，没有 reset、clean、删除、commit、push 或 PR。
- 按 `apps/mobile/AGENTS.md` 复核 Expo SDK 57 的 `expo-image` 版本化文档；继续使用仓库已锁定
  的 `expo-image ~57.0.1`，没有新增或升级依赖。

### 实现

- 新增 `apps/mobile/src/components/home-overview.tsx`：固定暖白/明亮薄荷 palette、原版
  `journey-leaf-home.png` 圆形融合、首屏统一输入、图片/发送动作、快捷提示、开放式三指标和
  在线/离线/执行中/待确认/失败/完成状态条。
- 首页继续复用现有 `/api/v1`、Agent run/resume、候选确认、离线确定性常识和手动记录流程；
  移除占据首屏的黄色离线警告，但保留准确能力文案。
- `ScreenShell` 新增自定义 Hero 插槽，其他页面默认 Hero 不变；全局主题固定为已确认的暖白薄荷
  浅色品牌方向，不自动切换到已否决的暗灰主题。
- 更新首页 Jest、布局契约、覆盖率采集和 Web E2E 首页断言。首页组件纳入覆盖率，不用排除文件
  或降低门槛掩盖新增代码。

### 验收证据

- 初次运行 TypeScript 与 lint 通过；Jest 32/33，唯一失败是布局契约仍从旧首页文件查找已抽出
  的输入框。测试断言改为读取真实 `home-overview.tsx` 后，最终 33/33 通过。
- 最终 `typecheck`、Expo lint、5/5 本地逻辑测试、33/33 Jest 均通过；覆盖率为 statements
  75.56%、branches 65.16%、functions 72.09%、lines 77.77%，均高于既有门槛。
- 本地 Web 首轮 390 pt 截图发现“记”单字孤行；修正标题结构和吉祥物占位后，320 pt 又发现
  标题省略、指标数字截断；将单位移到标签行并再次收口后，390 × 844 与 320 × 844 均人工
  核对通过，统一输入在首屏、标题和数值完整、无横向滚动。
- `npm run mobile:e2e:web` 在强制 Mock、空模型 Key、零预算 API 下为 2/2 通过；测试后 API 已
  恢复 `.env` 的 `deepseek` Provider 并为 healthy。本次没有真实 Provider 调用。
- Web export 成功生成 13 条静态路由；iOS Hermes bundle 与 Android Hermes bundle 成功，
  两端均包含原版 `journey-leaf-home.png` 资产。这是三端 JS 构建证据，不冒充新的原生安装证据。
- `git diff --check` 及最终 Git 状态在文档更新后复验；未提交、未推送、未修改远端。

### 收口状态

- 方案 C 的视觉子决策已确认并实现；阶段 12 整体仍为 In Progress，ADR-036 保持 Proposed，
  因为完整本地副本、冲突处理和退出清理尚未获确认或实现。ADR-037 同样保持 Proposed。
- 下一步只能由用户选择“完整本地数据副本”或“小红书主动分享链接”中的一个单项，再先拆任务
  和门禁；本轮到此停止，不自动扩大范围。

## 2026-08-04：新对话交接审计与基线复验

### 范围与目录安全

- 用户只要求检查当前仓库并创建交接文档；本轮没有继续阶段 12 功能、修改数据库/API/Agent、
  删除文件、安装依赖、commit、push 或创建 PR。
- 开始前执行并展示 `pwd`、`git status`、`ls -la`；工作目录为 Journey 根目录，分支为 `main`，
  远程 `origin` 指向 `https://github.com/boom080/fitness.git`。
- 初始审计为 169 项变化（16 Modified、87 Deleted、66 Untracked）；新增根目录
  `PROJECT_STATUS.md` 和 `NEXT_TASK.md` 后，最终为 171 项（16 Modified、87 Deleted、
  68 Untracked）。当前 HEAD 仍为 `06b52f024547e76e1cd216e27f3ac41717dd3671`。

### 代码、运行态与测试复验

- 结合实际文件检查根 npm workspace、Expo 配置与源码、FastAPI 路由/模型/Agent/RAG、Alembic
  `0001`—`0005`、CI、契约、部署/演示文档和测试目录；没有只依赖聊天总结。
- `docker compose ps` 显示 `api`、`db`、`test-db` 运行，api/db healthy；`/health/live` 与
  `/health/ready` 均为 `status=ok`，数据库 ready；`alembic current` 为
  `0005_agent_v3 (head)`。
- `docker compose --profile test run --rm --build test`：85 passed，后端覆盖率 90.49%，
  362 条样本与 26 项 Mock 门禁全部 PASS，真实 Provider 调用 0、费用 0。
- `docker compose --profile blackbox run --rm --build blackbox`：Requests + Pytest + Allure
  独立网络黑盒 1 passed（0.24 s）。
- 移动端 `typecheck`、Expo lint 均通过；Jest 33/33、逻辑测试 5/5 通过。最新 Jest 覆盖率为
  statements 75.56%、branches 65.16%、functions 72.09%、lines 77.77%。
- 本轮没有重复真实模型调用或原生安装；最近已记录证据仍为 Mock Web E2E 2/2、Web 13 路由及
  iOS/Android Hermes export 成功。

### 交接产物与结论

- 新增 `PROJECT_STATUS.md`：记录目标、阶段、完成项、目录/文件职责、技术决策、近期代码、
  实际命令、问题、风险、未完成项与建议顺序。
- 新增 `NEXT_TASK.md`：唯一最近任务为在用户明确授权后创建
  `codex/journey-migration-baseline`，复验后 stage 并建立一次本地提交；禁止 push/PR。
- 更新根 `README.md`：补入阶段 12 状态、移动 Jest 33 条和新对话交接入口。
- `.env` 仍被忽略，本轮未读取或输出内容；检查到权限为 `0644`，只记录后续收紧至 `0600` 的
  建议，没有擅自修改。本轮最终停在交接，不执行 `NEXT_TASK.md`。

## 2026-08-05：迁移 Git 基线与 GitHub 私有仓库

### 授权、分支与边界

- 用户明确授权执行 `NEXT_TASK.md`，并将原定的“本地提交、不 push”扩展为：在 GitHub 账号
  `boom080` 创建 `journey_v1` 仓库并推送。仓库创建为 `PRIVATE`；保留旧 `origin` 指向
  `boom080/fitness`，新增远端 `journey-v1` 指向 `boom080/journey_v1`，未创建 PR。
- 开始前重新执行并展示 `pwd`、`git status --short --branch`、`ls -la`；仍在 Journey 根目录，
  初始为 171 项变化（16 Modified、87 Deleted、68 Untracked），HEAD 为旧微信版提交
  `06b52f024547e76e1cd216e27f3ac41717dd3671`。
- 创建分支 `codex/journey-migration-baseline`。先 stage 新架构/文档，再 stage 旧微信端删除；
  识别并排除生成文件 `apps/mobile/junit.xml`，同时补充忽略规则。

### 敏感信息与迁移验证

- `.env` 未被跟踪；`reports/`、`artifacts/`、原生 `ios/`/`android/`、三端 export、coverage、缓存、
  签名文件均被忽略。高置信 API token/private-key 模式的文件名扫描无命中，`git diff --check`
  通过；没有读取或打印 `.env` 内容。
- `docker compose config --quiet` 通过。独立临时数据库完成 Alembic
  `upgrade head → downgrade base → upgrade head`，最终为 `0005_agent_v3 (head)`；临时数据库
  随后删除，开发数据库未参与迁移循环。
- `docker compose --profile test run --rm --build test`：85/85 通过，覆盖率 90.49%，362 条样本的
  26 项门禁全部 PASS，报告为 `provider=mock cost=$0`。
- `docker compose --profile blackbox run --rm --build blackbox`：独立 Requests + Pytest + Allure
  黑盒 1/1 通过（0.23 s）。
- 移动端 TypeScript、Expo lint 通过；Jest 33/33、逻辑测试 5/5 通过，覆盖率仍为
  75.56% / 65.16% / 72.09% / 77.77%。Web 13 条静态路由、iOS Hermes bundle、Android Hermes
  bundle 均 export 成功；这不是新的原生安装证据。

### E2E 环境偏差与修复

- 首次直接运行 `npm run mobile:e2e:web` 时，Playwright 复用了读取本机 `.env` 的常驻 API，
  并未自动强制 Mock；2/2 失败，失败上下文显示发生 DeepSeek/Qwen 外部调用，其中 DeepSeek
  trace 记录 `$0.000451`。这与交接文档所写的 Mock 前置条件不一致，未隐藏该失败。
- 随后用显式环境覆盖重建 API，核对 `agent_provider=mock`、`food_image_provider=mock`、预算 0，
  同一 E2E 为 2/2 通过；完成后重建并恢复用户原有 DeepSeek/Qwen 本地 API 配置。后端、黑盒与
  最终 E2E 的验收轮均为 Mock，首次误跑的真实调用作为已知执行偏差保留。
- 三端 export 中第一次从 workspace 目录误用了根脚本名 `mobile:web:build`，该子命令报
  `Missing script`；iOS/Android export 仍成功，随后使用正确的 `npm run web:build` 补跑 Web
  并通过。

### 基线结果

- 基线只创建一次迁移提交，提交消息为
  `refactor: migrate Journey to cross-platform agent app`。本条记录所在提交即基线提交，可用
  `git rev-parse HEAD` 获取不可自引用写入的最终哈希。
- GitHub 目标为 `https://github.com/boom080/journey_v1`（private）；推送后以远端分支和本地
  HEAD 一致为验收。没有 push 到旧 `origin`，没有创建 PR，也没有启动 ADR-036 产品实现。

## 2026-08-05：单服务器 Docker production 部署基线

### 授权与范围

- 用户要求继续完善产品，并明确希望未来上线可通过 Docker 直接部署到服务器。本轮只执行阶段 8
  的服务器 production 复验，不同时启动 ADR-036 本地数据、ADR-037 Web Research、小红书、
  数据库/API/Agent 工具或新多模态能力。
- 开始前执行并展示 `pwd`、`git status --short --branch`、`ls -la`；分支为
  `codex/journey-migration-baseline`，迁移基线 HEAD 为
  `2654c4308279a95f9fd8d45109807373b518202d`，工作区初始干净。
- 没有租用服务器、购买域名、修改 DNS/防火墙、创建公网资源、commit、push 或 PR。

### 实现

- 新增独立 `compose.production.yaml`，一次编排 PostgreSQL 18、FastAPI、Expo Web/Nginx 和
  Caddy 2.11.4；只有 gateway 发布 TCP 80/443 与 UDP 443，数据库/API 不映射宿主端口，数据库
  使用 internal network 和持久卷。
- 新增 `.env.production.example` 与 Git 忽略规则；production 必须提供域名 Origin、数据库密码
  和应用密钥，禁止测试账号播种，真实图片识别固定关闭，Agent 默认 Mock/零预算。
- 新增 `infra/caddy/Caddyfile`：Caddy 自动 HTTPS、HTTP 跳转、证书持久化、API/health 路由、
  Web fallback、安全响应头和 JSON access log；新增只读 HTTPS health smoke 脚本。
- Web Dockerfile 增加 `APP_VARIANT=production` 与 HTTPS API 构建门禁；移动 app config 同样拒绝
  Preview/Production 的缺失或明文 API URL，EAS profile 绑定同名远程环境，变体验证脚本加入
  正反向契约。
- CI 新增 production Compose、Caddyfile 和 HTTPS Web runtime image 契约；补充
  `SERVER_DOCKER.md`，记录服务器前置、初始化、部署、日志、备份、升级、回退和移动端边界。
- 新增 ADR-038 Accepted；唯一计划将阶段 8 标为 Revalidated，并把四容器公网复验保留为未完成
  门禁。`NEXT_TASK.md` 更新为阶段 12 ADR-036 的单一本地数据任务，不自动执行。

### 验证证据

- Docker 官方 production Compose 文档与 Caddy Automatic HTTPS/官方镜像复核完成；Caddy 官方
  当前 tag 为 `2.11.4-alpine`。
- `docker compose --env-file .env.production.example -f compose.production.yaml config --quiet`
  通过；展开后只有 gateway 发布 80/443，API/db/web 无 published ports，backend network 为
  internal。缺失 production env 会拒绝配置。
- production API 镜像构建成功。第一次隔离启动错误使用 `--no-build` 且 project 名对应镜像不存在，
  容器未启动；命令链没有 `set -e`，末尾误打印 PASS。该结果未计入验收，资源已清理。严格重跑
  先构建对应镜像后，独立 API/PostgreSQL project healthy，live/ready 为 200，Alembic 为
  `0005_agent_v3 (head)`，环境为 production、provider mock、图片 false、测试账号 false；随后只
  删除本轮创建的验证容器、网络和临时卷。
- `APP_VARIANT=production EXPO_PUBLIC_API_BASE_URL=https://journey.example.com` Web export 成功，
  生成 13 条静态路由；EAS profile 环境绑定契约通过，明文 production URL 与 HTTP smoke 均按
  预期拒绝。
- 通过 Caddy 2.11.4 官方 macOS arm64 release binary 执行 `caddy fmt`、`validate` 和 `adapt`，
  Caddyfile 有效并确认启用 automatic HTTPS 与 HTTP→HTTPS。
- API/Web Docker build 中 API 成功；Web 在读取项目文件前失败于 Docker Hub anonymous token
  端点连接超时，Node/Nginx 元数据无法拉取。Caddy 容器同样未能通过 Docker daemon 拉取，故本机
  四容器整栈、真实 DNS/证书、外部备份恢复和跨网络移动端仍未验收，不宣称已经上线。
- `docker compose config --quiet`、production config、`sh -n`、CI YAML、`git diff --check` 通过。
  后端/评测 85/85、覆盖率 90.49%、362 样本/26 门禁通过，`provider=mock cost=$0`；移动端
  TypeScript、Expo lint、变体契约、Jest 33/33、逻辑测试 5/5 通过，覆盖率未回退。

### 当前结论与启动条件

- 服务器侧现在具备“仓库 + `.env.production` + 一条 Docker Compose 命令”的生产配置基线；
  PostgreSQL/FastAPI/Web/HTTPS 均纳入容器设计。iOS/Android 仍需签名构建和商店/内部分发，
  Docker 只承载服务器和 Web。
- 实际上线前仍需用户提供或确认服务器供应商/区域/预算、域名/DNS、运营与隐私信息、外部备份
  位置；在网络正常的服务器补跑四容器 `up -d --build --wait`、HTTPS smoke、备份恢复、跨网络
  移动端和最小负载测试。
- 本轮到此停止。下一产品任务是 `NEXT_TASK.md` 中 ADR-036 的本地数据范围确认；不得把公网部署、
  本地数据和小红书/Web Research 混成同一阶段。

## 2026-08-05：阶段 12 ADR-036 原生 local-first 第一批实现

### 授权与范围

- 用户要求“继续下一项任务”。按当时 `NEXT_TASK.md` 的唯一推荐项执行 ADR-036：原生端保存
  每账户画像、目标、最近 90 天饮食/运动/体重与 Journey，支持离线 CRUD Outbox、显式版本冲突
  和退出彻底清理；不启动 ADR-037、小红书、Web Research、长期偏好、多 Agent 或新图片能力。
- 开始前执行并展示 `pwd`、`git status --short --branch`、`ls -la`，保留同一工作区中尚未提交的
  production Docker 变更；未清理或覆盖用户已有改动。
- 没有调用真实模型 Provider、上传真实健康数据、commit、push、创建 PR 或部署公网资源。

### 实现

- 新增 `local-replica.ts`：iOS/Android 以每账户 AES-256-GCM 密文保存规范化 JSON，密钥放在
  SecureStore 并使用 `WHEN_UNLOCKED_THIS_DEVICE_ONLY`；Web 明确只用进程内副本，不承诺刷新后
  保留。Outbox 上限为 1000 条，到达上限时明确拒绝而不是丢弃数据。
- Sync Provider 首次在线拉取画像、目标和最近 90 个日历日；离线记录新增/编辑/删除与画像/目标
  修改先写副本和 Outbox，联网后合并连续动作并同步。创建沿用幂等键；响应丢失、删除 404、
  更新 404 和 409 冲突都有确定性收敛或显式暂停规则。
- 最终集成审查发现首版按 `3 × 31` 个有记录日期拉取，稀疏数据可能越过 90 个日历日；已改为按
  画像时区计算“今天至前 89 天”的截止日、每页 30 天并严格过滤，新增回归测试确认旧记录不进入
  副本。
- 首页、Journey、我的、画像/目标设置和三类记录页均接入同一 Sync Provider；冲突页并排显示
  本机/云端字段，由用户选择保留本机或采用云端，不做静默 last-write-wins。
- 显式退出、401 会话失效和账户切换清除密文、副本、Outbox、冲突、账户密钥、旧离线队列与
  React Query 缓存；generation/purge 门禁阻止在途同步在退出后写回。
- 新增 Alembic `0006_local_first`，为画像、目标、饮食、运动、体重增加正整数 `version`；更新/
  删除要求 `If-Match-Version`，服务层锁行并递增版本，过期请求返回结构化
  `409 sync_conflict` 与服务端快照。OpenAPI 和 TypeScript 契约同步更新。
- `apps/mobile/AGENTS.md` 要求写代码前核对 Expo SDK 57 精确文档；该嵌套规则在首轮编辑后才被
  发现。随后完整核对 Expo 57 Crypto/SecureStore 文档，重新审查加密 API、密钥存储、备份和
  大对象限制，并按精确 API 完成测试；此执行顺序偏差未隐藏。

### 自动化与迁移证据

- Alembic 完成 `0006 → 0005 → 0006`、`alembic check`，最终为
  `0006_local_first (head)`。
- 后端/评测全量 **87 passed**，覆盖率 **90.94%**；362 条版本化样本与 26 项门禁全部 PASS，
  `provider=mock cost=$0`。新增冲突、版本、删除和 OpenAPI 契约测试。
- 移动 TypeScript、Expo lint、变体契约通过；最终 Jest **41/41**、逻辑测试 **5/5**。新增账户隔离、
  加密副本、退出清理、Outbox 合并、成功响应丢失、404 收敛、409 冲突和冲突选择测试。
- Web production export 生成 13 路由；强制 Mock 的核心 Web E2E **2/2**，iOS/Android Hermes
  export 均通过。
- 提供者级账户切换测试首轮因 Jest mock 提升变量规则失败，改名后又暴露测试 mock 每次 render
  返回新 QueryClient 导致 effect 重订阅；把测试依赖改为稳定实例并使用异步 `act` 后，断言账户
  A 副本/旧队列在切到 B 时清理，最终全量 41/41 通过。未降低业务断言。

### 原生与 Docker 复验

- Android 16 `Pixel_9`：使用 Android Studio JBR 和本机 SDK 完成当前 Debug Development Build，
  495 个 Gradle task 成功，APK 安装并启动；Metro 打包 1502 modules，Activity 在前台，日志有
  `Running "main"` 且无业务 fatal。额外 Release 构建停在 `lintVitalRelease`，重复尝试仍未
  收敛后中止，因此本轮只记 Debug 通过；阶段 10 的既有 Release 证据不被覆盖。
- iOS 26.5 `iPhone 17 Pro`：Debug Development Build 0 error，ExpoCrypto/ExpoSecureStore pods
  实际链接，安装并启动；初次 Metro localhost 只监听 IPv6，客户端访问 127.0.0.1 被拒绝，改用
  LAN listen 后打包 1366 modules 并由 App 取得 200，无业务 fatal。
- production Compose 配置再次通过；当前 API 镜像重新构建后，以隔离 project 启动 PostgreSQL
  与 FastAPI，两个容器均 healthy，live/ready 为 200，Alembic 自动到达
  `0006_local_first (head)`，环境为 production、Agent Mock、禁测试账号、禁真实图片识别。完成
  后只删除本轮隔离容器、网络和临时数据库卷。
- Web/Nginx/Caddy 四容器整栈和真实公网证书仍受既有 Docker Hub 网络问题及缺少服务器/域名
  阻塞；因此结论是“当前代码可按 Compose 部署”，不是“已经上线”。iOS/Android 仍需单独签名
  构建和分发，不能运行在 Docker 中。

### 当前边界与下一项

- ADR-036 转为 Accepted，但 1000 条长离线故障注入、5 人盲测、真实设备密钥取证、公网多设备
  同步和正式隐私流程仍属于发布加固；Web 只提供进程内副本。
- 阶段 12 继续为 In Progress，仅因 ADR-037 仍为 Proposed。下一项需要用户单独确认是否采用
  “用户主动粘贴公开分享链接”的受控路径；不得绑定小红书账号、接收密码/Cookie、自动登录或
  批量抓取。

## 2026-08-09—10：阶段 12 ADR-037 生活灵感主动分享实现与验收

### 授权、目录与产品边界

- 用户要求“执行下一步计划”，并要求新建 `qiuzhaomianshi.md`、按岗位记录项目问题/解决方式/
  日期，同时把“每次项目更新必须同步该文档”写入 `AGENTS.md`。按当时 `NEXT_TASK.md` 的四项
  保守默认执行：只支持用户逐次主动分享公开链接，保存最小字段，社交内容只作灵感，本轮不租
  服务器、不接入通用 Web Research 或新模型。
- 开始前已执行并展示 `pwd`、`git status`、`ls -la`；当前目录为 Journey 根目录，分支
  `codex/journey-migration-baseline`，HEAD `2654c4308279`。初始工作区已有阶段 8/ADR-036 的
  68 项变化（57 项已跟踪修改、11 项未跟踪），全部保留，没有 reset、clean 或覆盖。
- 重新检查小红书 Ark、小程序开放平台和开发者协议公开页面；没有找到可证明 Journey 可任意
  搜索消费者笔记/推荐流的公开 API。实现不接收账号、密码、Cookie、验证码或登录态浏览器，
  不自动/批量抓取，不复制正文和图片。

### 实现

- 新增 `LifeInspiration` 与 Alembic `0007_life_inspirations`：按用户保存规范化来源 URL、来源名、
  标题、短摘要、用户确认标签、检查日期和固定 `inspiration_only`；同一用户 URL 唯一。
- 新增认证后的 `/api/v1/inspirations/preview`、create/list/delete。preview 只允许
  `xiaohongshu.com`/`xhslink.com` HTTPS 白名单，禁止凭据 URL 和自定义端口；逐跳校验 DNS、
  私网地址和重定向，最多 3 次重定向、8 秒超时、256 KB 上限、不发送 Cookie，只解析
  title/description 元数据。网络/访问控制/类型/体积/Prompt Injection 失败统一
  `manual_required`，不绕过登录或反爬。
- 移动端新增“我的 → 生活灵感”：离线提示、主动粘贴、预览或手动填写、可编辑标签、显式确认、
  来源跳转与两步删除。该能力不新增一级入口，不接入首页 Agent、工具注册表、RAG 或健康事实。
- `.env.example` 与本机 Compose 默认允许开发预览；`.env.production.example` 和 production
  Compose 默认 `LIFE_INSPIRATION_FETCH_ENABLED=false`，关闭后保留手动填写/确认回退。
- OpenAPI 双快照和 TypeScript 共享契约同步；新增根 `qiuzhaomianshi.md`，`AGENTS.md` 已规定
  每次代码/配置/数据库/测试/ADR/交付更新都必须同步岗位案例或记录“无新增问题”。

### 测试、迁移与构建证据

- 后端专项 **6/6**：认证、HTTPS/域名、最小元数据、显式确认、去重、用户隔离/删除、私网 DNS、
  跨域重定向、超时、大小上限、Prompt Injection 和 Cookie 不转发；Ruff 通过。
- 移动专项与 API 定向 **10/10**；全量 TypeScript、Expo lint 通过，Jest **45/45**、逻辑测试
  **5/5**。覆盖率 statements 76.27%、branches 65.98%、functions 73.33%、lines 78.51%。
- 隔离数据库完成 `0007 → 0006 → 0007` 与 `alembic check`，最终
  `0007_life_inspirations (head)`，无待生成操作。
- `docker compose --profile test run --rm --build test`：最终后端/评测 **93 passed**（19.20 s），
  覆盖率 **90.72%**；362 条版本化样本和 26 项门禁全部 PASS，Provider Mock、费用 `$0`。
- `docker compose --profile blackbox run --rm --build blackbox`：最终 Requests + Pytest + Allure
  网络黑盒 **1/1**（0.29 s）。
- Web E2E 前显式覆盖 Agent/图片 Provider 为 Mock、所有模型 Key 为空、预算 0；确认运行环境无
  外部 Key 后，核心 E2E **2/2**（4.7 s）。随后恢复本机 `.env` 的 DeepSeek/Qwen Provider，
  API healthy；没有读取或输出 Key，也没有真实模型调用。
- Web export 生成 **14** 条静态路由并包含 `/inspirations`；iOS、Android Hermes bundle 均成功。
  这是三端 JS 构建证据，不冒充本轮新的原生安装或商店签名证据。
- local 与 production Compose config 均通过；production 配置确认生活灵感自动预览为 `false`。
- 最终主 API 按本机原配置重新构建并恢复，ready 为 `database=ok`，Alembic 为
  `0007_life_inspirations (head)`；只核对 Provider 名称为 DeepSeek/Qwen，没有读取或输出 Key。
- `git diff --check`、41 个 Markdown 文件本地链接检查和仓库高置信 Key/私钥文件名扫描均 PASS；
  `.env` 继续被 Git 忽略。

### 发现的问题与处理

- 第一次启动 E2E API 时宿主 `5432` 已被其他 PostgreSQL 占用；没有停止现有进程，改用临时
  宿主端口 `55432`，容器内数据库地址与迁移不变。
- 健康轮询第一次把 zsh 只读变量 `status` 当普通变量；改名 `health_state` 后通过。随后一次
  设置检查误引用不存在的 Settings 属性，只输出 AttributeError，没有输出 Key；改为仅检查
  环境变量是否非空的布尔值后确认 Mock 环境所有外部 Key 均为空。
- 移动测试首轮暴露 Expo 路由类型、异步断言和 Jest mock 提升命名问题；分别使用 `Href`、
  `waitFor`/异步事件和 `mockItems` 修正，未降低业务断言。
- 重复 URL 测试暴露唯一约束在 `flush` 阶段抛出；服务层把 flush 纳入冲突处理后稳定返回 409。

### 收口

- ADR-037 转 Accepted，阶段 12 Completed。生活灵感是用户主动收藏，不是小红书账号绑定、
  通用浏览器、Agent Tool、RAG 摄取或健康证据；production 自动预览默认关闭。
- 当前最终工作区为 85 项变化（65 项已跟踪修改、20 项未跟踪），包括此前阶段 8/ADR-036 与
  本轮 ADR-037。没有 commit、push、PR、公网部署、依赖批量升级或真实模型调用。
- 下一项只是在用户单独授权后完成最终差异/敏感信息复核并创建本地提交；默认不 push、不创建
  PR，不自动启动新产品功能。

## 2026-08-10：阶段 13 秋招 Demo 封板——真实 LLM、Multi-Agent、RAG Eval 与交付收口

### 授权、目录与审计

- 用户要求先扫描真实 Agent、RAG、evals、API、Run State、前端 Trace、Provider/Mock 切换和
  Docker，再直接按“真实 LLM → Multi-Agent → RAG Eval → Journey → 图片 → E2E → 文档”实施；
  同时冻结语音、视频、第三方登录、验证码/找回密码、健康平台、Push、自动小红书、通用浏览器、
  自由网页搜索和复杂社交。
- 开始和恢复时均执行 `pwd`、`git status`、`ls -la`；当前目录始终为 Journey 根目录。工作区
  原本已有阶段 8/12 大量未提交变化，全部保留；没有 reset、clean、commit、push 或 PR。
- 审计确认旧 Agent v3 已有 Router/Planner/Policy/Executor/Observation/Verifier/Confirmation，
  但没有明确 Specialist 角色；RAG 为 4 份文档、420 字符无 overlap、96 维本地哈希 embedding、
  PostgreSQL JSON vector、top-3/0.16；旧评测没有 Recall@1/5、MRR 和真实生成分层指标。

### Multi-Agent 与 Journey 实现

- 新增 `specialists.py`，把现有工具明确归属 Orchestrator、Record Agent、Health Knowledge Agent、
  Journey Summary Agent；Policy 拒绝角色/工具不匹配，仍为同一 FastAPI 模块化单体，不新增
  Agent 群聊或微服务。
- Router 支持“中午记录 + 晚上运动 + 本周减脂情况”的精确分段；Plan/Step/Observation/Tool
  Trace 增加 `specialist`、`selected_agents`、`duration_ms`、候选数、检索文档/分数和数据范围。
  原始输入仍只保留 hash/长度，不保存模型思维链。
- 精确输入会生成 food/activity 两个候选并暂停；两个候选全部经 Confirmation Gate 写库后，
  显式 Resume 读取更新后的画像、目标、7 天记录与体重趋势，再组合知识引用和周总结。
- Journey API/客户端增加 7/30 个日历日窗口、摄入/运动/体重趋势、目标与 AI 总结；继续保留按
  日期的 food/activity/weight/summary 多日语义。
- `/health/ready` 与启动日志增加非敏感 REAL/MOCK、Provider、Model；模型 Key 未打印。

### RAG Eval 与真实结果

- 新增 60 题 `rag_eval_v1`（40 有答案/20 拒答）、Dataset/bundle hash、Retrieval 与 Generation
  分层评测、不可覆盖输出和跨版本基线一致性检查。Mock Generation 明确
  `SKIPPED_REAL_MODEL`。
- `rag-v1`：Recall@1 0.7083、Recall@3/5 0.9625、MRR 0.9500；
  `rag-v2-candidate`：Recall@1 0.7083、Recall@3/5 1.0、MRR 0.9625。
- 第一次真实 DeepSeek 报告 `rag-v2-real-2026-08-10.json`：60 次调用，Groundedness/Relevance
  0.9625、Citation 0.9083，但 Abstention 0.6833，门禁失败。未覆盖或删除该报告。
- 定位到 Retrieval 无 Context 时仍调用模型，且 scorer 未统一识别结构化拒答；改为直接返回
  `insufficient_context` 并升级固定 scorer。第二份不可覆盖报告
  `rag-v2-real-2026-08-10-r2.json`：41 次真实调用 + 19 次确定性拒答，输入/输出 Token
  27,696/8,446，费用 `$0.00624232`；Groundedness/Relevance 0.9625、Citation 0.9083、
  Abstention 1.0；Generation p50/p95 1584/2873 ms、总 p50/p95 1585/2874 ms，全部门禁通过。

### E2E、超时与离线恢复

- 真实复合 Requests 黑盒首轮业务完成但测试固定 15 秒超时；改为环境变量控制，Mock/CI 保持
  15 秒，真实验收显式 75 秒。随后一次模型成功但文案为“过去的7天”，补充语义等价断言；再一次
  Provider 的周总结在 12 秒阈值重试后 `model_timeout` 并进入可解释 degraded。
- 结构化工具日志证明一次成功周总结实际约 24.3 秒，因此把 Demo `AGENT_TIMEOUT_SECONDS` 从
  12 调整为 30、仍最多重试 1 次。最终精确复合真实黑盒 **1/1 passed，28.02 秒**；不把供应商
  波动隐藏成成功。
- 隔离 Mock API 的 Requests + Pytest + Allure **2/2 passed，0.50 秒**，生成 JUnit/Allure；
  Playwright 首轮因工具名同时出现在 Plan/Trace 而触发 strict locator，限定到计划完整文本后
  **2/2 passed，3.3 秒**。图片 E2E 仍验证 Mock 候选经用户校正后保存。
- 新增离线 `create → Outbox → reconnect → create API → pull snapshot → Outbox 清空` 回归；专项
  5/5，通过服务端 ID/version 对齐验证，不只检查“队列存在”。

### 全量测试、构建与 Docker

- `docker compose --profile test run --rm --build test`：**100 passed**，覆盖率 **90.60%**；
  362 条既有样本/26 项门禁、60 题 RAG v1/v2 全部 PASS，Provider Mock、费用 0。
- 移动 Jest **46/46**，逻辑 **5/5**；Statements 71.76%、Branches 61.62%、Functions 69.79%、
  Lines 74.41%；TypeScript、Expo lint、应用变体检查通过。
- Web export 14 路由；iOS/Android Hermes export 通过；Web 真浏览器 E2E 2/2。
- iPhone 17 Pro / iOS 26.5：Debug Build Succeeded，0 error、36 条 Xcode 缓存/脚本警告，安装并
  获取 1367-module Metro bundle；Pixel 9 / Android 16：首次因终端无系统 Java 失败，显式使用
  Android Studio JBR 21 后 495 tasks、`BUILD SUCCESSFUL in 4m 39s`，APK 安装，MainActivity
  前台并获取 1498-module bundle，无业务 fatal。截图保存在被忽略的 `reports/`。
- `infra/demo/preflight.py` 检出另一 Compose Project `mall` 使用宿主 5432；未停止或修改它，
  Journey 使用 API 8000、PostgreSQL 55432，容器内仍为 `db:5432`。新增 `demo_up.sh` 执行
  preflight → build/up/wait → health/migration/rag 检查。
- 最终执行 `docker compose down`（不删卷）和 `./infra/demo/demo_up.sh`。旧 test/blackbox profile
  容器仍占 Journey network，因此 down 提示 network still in use；核心 API/DB 仍按新镜像重建，
  `docker compose ps` healthy，live/ready 200，REAL DeepSeek、RAG ok，Alembic
  `0007_life_inspirations (head)`。未执行任何全局 Docker prune。

### 当前结论与边界

- ADR-039 Accepted，阶段 13 Completed。Journey 现在可以诚实描述为“有界、可解释、确认后写入、
  真实模型与 RAG 可分层评测的 Multi-Agent 健康记录 Demo”，不能描述为 Agent 群聊、医疗诊断、
  公网生产或商店发布。
- 食物图片仍为 Experimental/No-Go；生活灵感不进入 RAG；Post-Demo / Future 能力没有实现或
  启动。没有真实 Key、私钥、原图或原始健康文本写入跟踪文档。
- 本阶段到此停止；下一步只有用户单独授权后才能做最终差异/敏感信息复核与本地 Git 提交，
  默认不 push、不创建 PR。

### 中断恢复后的最终一致性检查

- 任务恢复后再次核对目录与工作区；仍为 Journey 根目录、分支
  `codex/journey-migration-baseline`、HEAD `2654c4308279`。最终收口时共有 115 项未提交变化
  （87 项已跟踪修改、28 项未跟踪），没有 reset、clean、commit、push 或 PR。
- 修正 `PROJECT_STATUS.md`、`NEXT_TASK.md`、当前项目审计和 Agent 技术结论中残留的阶段 12、
  单 Agent、93 条后端和 45 条移动测试旧口径；阶段 10/11 的历史描述保留为历史事实。
- `git diff --check` 首轮发现 ADR-039 状态行尾空格，使用最小补丁去除；复跑通过。44 个 Markdown
  文件的本地链接检查通过。
- 高置信 API Key、GitHub Token、AWS Key 与私钥头扫描只输出命中文件名，最终 0 个命中文件；
  `.env` 未被 Git 跟踪且权限为 `0600`，没有读取或打印其中的值。
- local Compose config、带无密钥示例环境的 production Compose config、`demo_up.sh` shell 语法
  和 `preflight.py` Python 语法均通过。production Compose 在不提供必需的 `PUBLIC_ORIGIN` 等
  变量时按设计 fail-fast，使用 `.env.production.example` 后配置验证通过。
- 当前 `docker compose ps` 显示 Journey API/DB healthy；`/health/live` 正常，`/health/ready`
  返回 database/rag=`ok`、Agent Mode=`REAL`、Provider=`deepseek`、Model=`deepseek-v4-flash`。
  旧 test/blackbox profile 容器仍属于 Journey namespace，没有影响另一 Compose Project。

## 2026-08-13：封板维护——真实 Agent 超时/Resume 对账与静息能量口径

### 现场证据与根因

- 用户在 iOS Simulator 复合场景中看到三条错误：候选确认
  `Idempotency-Key was already used with a different payload`、首页继续执行
  `Run is not waiting`、Journey 周总结“网络不可用”；同时指出热量指标未包含基础代谢。
- 开始前执行并展示 `pwd`、`git status`、`ls -la`，只操作 Journey 根目录并保留既有大量未提交
  变化；没有 reset、clean、commit、push、PR 或全局 Docker 清理。
- PostgreSQL 只读核对确认问题 Run `df8c...` 已是 `completed/consumed`，两个候选均在
  09:27:16/09:27:23 UTC 写入，确认 2/2、resume 1 次；Run 累计工具 latency 24,756 ms。
  09:29 的独立周总结 Run 同样 completed，latency 21,939 ms。移动端却对全部 API 固定 10 秒，
  因而先报网络错误，后端继续完成，再留下过期 Resume 和二次确认冲突。
- 幂等保护工作正确，阻止了同一候选不同 Payload 的重复写入；根因不是数据库、RAG 或模型未执行，
  不能通过放宽幂等约束修复。

### 实现

- `apps/mobile/src/lib/api.ts` 将普通 API 保持 10 秒，Agent Run/Resume 单独设为 120 秒；增加
  `fetchAgentRunTrace`。确认页和首页在响应不确定或 Resume 409 时读取 Run Trace，Run 已完成则
  清理过期继续状态；候选此前已写入时提示编辑既有记录，不重复保存。
- `AgentRunTrace` 增加 confirmation progress，继续只返回脱敏计划、Observation、工具、用量和
  状态，不返回原始输入或思维链。
- 新增服务端与离线共口径的 Mifflin–St Jeor 静息能量预测；缺少生日/身高/最新体重/适用性别，
  或年龄不在原始健康成人 19—78 岁范围时返回原因而非默认值。Home 增加静息估算和记录口径
  余量，旧 `net_kcal` 兼容保留但 UI 改为“记录差值”；Journey/Agent Context 同步提示不等于 TDEE。
- 新增 ADR-040，并同步 README、API、文档索引与求职面试材料。公式依据为 Mifflin 等 1990
  原始论文 PubMed PMID 2305711。

### 验收

- Python 语法与 TypeScript 通过；移动 Jest **48/48**、逻辑 **5/5**。
- Docker 定向后端 **17/17**；全量后端/评测 **100/100**，覆盖率 **90.69%**；26 项 Agent 门禁、
  60 题 `rag-v1`/`rag-v2-candidate` Eval 全部运行，Provider 明确 Mock，未冒充真实 Generation。
- OpenAPI 双快照更新；`git diff --check` 通过。
- 重建主 API 后 `docker compose ps` 显示 API/DB healthy，live/ready 均 200；ready 为
  database/rag=`ok`、Agent Mode=`REAL`、Provider=`deepseek`、Model=`deepseek-v4-flash`。
- 实际测试账号 `/home/today`：摄入 600、已记录运动 300、记录差值 300、静息估算 1,591.5
  kcal/天、记录口径估算余量 −1,291.5；问题 Run Trace 为 completed/consumed、确认 2/2、
  `resume_available=false`。
- 新发起真实 DeepSeek v4 Pro 7 天总结：HTTP 200、端到端 20,434 ms、Agent 19,975 ms、答案存在、
  3 条引用、`fallback_used=false`。没有打印 API Key。
- 使用 iOS Simulator 的本地测试账号完成页面级复验：首页实际渲染“记录差值 300 / 静息估算
  1,592 / 今日估算余量 −1,292”及 TDEE 边界；在 Journey 点击“生成”后约 27 秒出现真实 7 天
  总结和 3 条依据，没有再显示“网络不可用”。对应最新 Run completed、DeepSeek v4 Pro、
  latency 21,798 ms、fallback=false；截图保存在被 Git 忽略的 `reports/manual/2026-08-13/`。

### 结论与边界

- 截图中的 AI 总结并非业务执行失败，而是客户端超时与状态对账缺失；修复后仍保留真实失败、
  超时和降级提示，不承诺生产 SLA。
- 静息能量是预测值，不是完整 TDEE 或医疗测量；漏记数据会影响余量。本轮是阶段 13 后 bug fix
  和指标语义修正，不启动阶段 14 或任何外围产品功能。

## 2026-08-13：秋招跨岗位项目素材知识库

### 范围与事实源

- 按用户授权新增一份用于其他 Codex 生成 Journey 简历内容的事实素材库；本轮只修改文档，不改
  前端、后端、数据库、Agent、RAG、Compose 或 CI 行为，也不启动新阶段。
- 开始前执行并展示 `pwd`、`git status`、`ls -la`，确认处于 Journey 根目录并保留既有大量未提交
  变化；未执行 reset、clean、commit、push、PR 或任何 Docker 清理。
- 重新读取当前 `package.json`/`pyproject.toml`/lock、OpenAPI、Agent/RAG 源码、Compose/CI、
  移动端离线实现、ADR、执行日志和现有报告，而不是只复述旧交接文档；未读取或输出 `.env` 值。

### 产物

- 新增 `docs/demo/JOURNEY_CAREER_MATERIAL_KNOWLEDGE_BASE.md`，以快照日期、状态标签和素材编号组织：
  项目演进、产品设计、跨端/后端技术、Multi-Agent、RAG/Eval、测试、Docker/CI、安全隐私、
  14 个问题解决案例、Agent/测试/运维/售前/产品/AI 产品六类岗位地图、面试叙事和禁用陈述。
- 指标使用当前可核验证据：OpenAPI 25 Path/34 Operation；后端 100/100、覆盖率 90.69%；
  362 条 Agent/契约样本和 26 项门禁；60 题 RAG；真实复合黑盒 1/1；图片 Top-3 67.27%
  门禁失败。Mock、真实模型、图片 No-Go、本机 Demo 和 production Conditional 均单独标记。
- 同步更新根 README、文档索引与 `qiuzhaomianshi.md`；没有建立平行 Roadmap，也没有修改 ADR
  状态。

### 验收与边界

- 本轮仅为文档编写，未重复运行完整业务测试；引用的是 2026-08-13 最近一次已落盘的测试/报告
  快照，知识库明确要求后续使用者在更晚日期先重新核验。
- 对本轮涉及的 5 份 Markdown 执行相对链接检查，共检查 49 个本地链接，缺失 0；
  `git diff --check` 通过；高置信 API Key、GitHub Token 与私钥头扫描命中 0。未读取或打印 `.env`。
- 知识库共 1072 行、14 个问题解决案例、7 组岗位素材（六个目标岗位 + 后端/全栈补充），所有
  量化数字均附事实源或明确引用执行日志快照。
- 知识库不能作为已上线、生产 SLA、商店发布、图片质量通过、医疗准确性或 Future 功能已实现的
  证明。

## 2026-08-21：公开 GitHub 作品集发布与云端 CI 收口

### 授权与发布边界

- 用户明确授权将 Journey 上传 GitHub 作为公开作品集，并指定仓库名为 `Journey v0.1`；按 GitHub
  合法仓库名落为 public `boom080/Journey-v0.1`，默认分支为 `main`。
- 开始前执行并展示 `pwd`、`git status`、`ls -la`，确认只在 Journey 根目录操作；没有 reset、
  clean、全局 Docker 清理、PR 或对其他项目的停止/修改。
- 旧 `boom080/fitness` 保持不变，私有 `boom080/journey_v1` 保持为迁移备份。公开仓库使用已审计
  当前树生成的干净快照，不公开旧迁移历史中的邮箱元数据。

### 敏感信息与仓库体积审计

- `.env` 已被 Git 忽略且未跟踪；没有读取或打印其中的值。对待发布工作树及完整 Git blob 执行
  高置信 API Key、GitHub Token、AWS Key 与私钥头扫描，命中 0。
- `.env.example`、`.env.production.example` 只保留空值或显式占位；`reports/`、原始图片评测集、
  Expo/原生构建目录、`node_modules` 与缓存未发布。
- 待发布 Git 文件没有超大文件，最大文件约 799 KB；公开仓库添加项目描述与 AI Agent、RAG、
  Expo、FastAPI、PostgreSQL、Docker、Pytest 等 Topics。

### 发布前与云端验收

- Docker 后端/评测全量 **100/100 PASS**，覆盖率 **90.69%**；26 项 Agent 门禁及 `rag-v1`、
  `rag-v2-candidate` 两组固定 60 题 Mock Eval 通过。Requests + Pytest + Allure 网络黑盒 **2/2**。
- 移动端逻辑 **5/5**、Jest **48/48**、TypeScript 通过；Expo lint 为 0 error、1 个既有未使用参数
  warning；Web/iOS/Android JS export 通过，Web 共 14 路由。
- 独立 Compose Project 使用单独端口与临时 Volume 验证 Web E2E **2/2**；第一次图片用例因 Compose
  自动读取本机 `.env` 而误用真实图片 Provider，随后显式覆盖为 Mock 后通过，未停止其他项目。
- GitHub Actions 前三轮分别暴露 Ruff 格式、Python `app/evals` 模块路径和测试依赖本机默认模型
  三类环境一致性问题；失败记录全部保留。通过代码格式化、`python -m pytest` +
  `PYTHONPATH=.:..`、测试内显式无敏感占位模型修复。
- 最终应用代码快照 run
  [`32452754248`](https://github.com/boom080/Journey-v0.1/actions/runs/32452754248) 的 backend、
  mobile、web-e2e 三个 job 全部通过；CI 固定 Mock、空 API Key、零预算，不能冒充真实模型质量。

### 结论与回退

- 公开源码作品集已可访问：`https://github.com/boom080/Journey-v0.1`。这只证明源码、构建契约、
  测试和 CI 可复现，不代表 Web 已公网部署、App 已上架或已形成生产 SLA。
- `portfolio` remote 专用于公开干净快照，本地 `codex/journey-migration-baseline` 保留完整迁移历史；
  如需撤回公开发布，应只针对 `boom080/Journey-v0.1` 操作，不影响旧仓库与私有备份。
