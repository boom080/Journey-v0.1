# 阶段 8 交付与测试报告

> 日期：2026-07-21
> 状态：Completed；用户接受本机 staging/自动化录屏，并确认发布标识与签名延期边界。
>
> 说明：下方“已验证基线”和“全量门禁结果”保留阶段 8 当日历史数字；2026-07-31 的最终
> 交付复验见文末附录，附录是当前求职演示口径。

## 已验证基线

| 项目 | 结果 | 证据 |
|---|---|---|
| 隔离 staging Compose | 通过 | API `:18000`、DB `:55432`，Mock/空 Key/预算 0 |
| Alembic/启动 | 通过 | 容器启动自动 upgrade，Ready 200 |
| demo reset | 通过 | 连续两次执行均回到 6 条固定记录 |
| staging smoke | 通过 | 身份、Journey、Agent trace、版本、cost=0 |
| 备份/恢复 | 通过 | PostgreSQL 18 custom dump + SHA-256，恢复后 smoke 通过 |
| 离线敏感队列 | 通过 | AES-256-GCM、24h、50 条、按用户清除、Web 内存态 |
| Android Debug APK | 通过 | ARM64 构建、Pixel 9 安装/启动 |
| Android Release APK | 通过 | ARM64、本地 debug certificate；不用于商店 |
| Web production export | 通过 | 12 条静态路由、2.1 MB、34 文件 SHA-256 清单 |
| Web 容器镜像 | 受限 | 三次 Docker Hub OAuth TLS timeout；不是源代码失败 |
| iOS Release Simulator | 通过 | Xcode Build Succeeded，安装并显示已登录首页 |
| 签名 AAB / iOS archive | 按范围延期 | 无 Apple 会员且暂不上架 Android；本机 Apple identity=0 |
| HTTPS 云 staging | 按范围延期 | 用户接受本机 staging，未来自租服务器另立任务 |

## Android 制品

- Debug APK：约 88 MB；首次通过 SHA-256
  `1a77129bf161b63389a23500a75c60c0256e9abecef0890e2b7832afa3bab104`。
- 最终 Release APK：约 42 MB；SHA-256
  `e5a73e6233d82b7a9375535f5f411798604718bdd12aed19c38dbd9cd68c413e`。
- Release APK 使用 `CN=Android Debug`，只用于本地安装；在 Pixel 9 登录返回 200，并读取
  `/api/v1/home/today`。Preview/Production 的 cleartext 配置均验证为 false。

## 全量门禁结果

- 后端：35 passed；覆盖率 90.96%（门槛 70%）。
- Agent/RAG：296 条版本化样本，13 项门禁全部通过，关键准确率/Schema/安全/引用均 1.0，
  provider `mock`，cost `$0`，failures `0`。
- Alembic：`0003 → 0002 → 0003` 和 `alembic check` 通过。
- 移动端：5 条逻辑测试 + 23 条 Jest 测试通过；statements 81.18%、branches 70%、
  functions 73.13%、lines 84.02%；TypeScript、Expo lint、3 个应用变体检查通过。
- E2E：完整核心闭环通过（22.2 秒）；备用录屏
  `docs/demo/assets/journey-fallback-demo-0.1.0.webm`，535 KB，SHA-256
  `8ab0dd3b43edb1ca2906f4d14f573b0b53511ca223d6d153d6fb9808a89e401d`。
- 原生 JS bundle：iOS 3.1 MB、Android 4.4 MB；原生 Release 构建均成功。
- 供应链：`npm audit --omit=dev --audit-level=high` 无 high/critical，但仍有 11 个 Expo
  工具链传递的 moderate `uuid` 告警；官方给出的自动修复会造成 Expo breaking change，
  本阶段不强制升级，发布前继续跟踪。

## 已发现并关闭的问题

1. macOS 同步目录使 Android 生成产物出现 `PackageList 2.class`；通过官方 Expo CNG
   `prebuild --clean --platform android` 重建被忽略目录后关闭。
2. Android Release 默认拒绝 `10.0.2.2` 明文 HTTP；通过 `expo-build-properties` 仅为
   development 变体开放，preview/production 明确为 false。
3. staging smoke 最初从 run response 读取 Prompt 版本；实际契约在 trace endpoint，脚本已按
   `/api/v1/agent/runs/{run_id}` 修正。
4. Web 镜像构建三次在拉取 Docker Hub base image 的 OAuth HTTPS 阶段超时，保留本地静态
   export 和已有运行环境作为回退。
5. Web 切换 API 地址时 Metro 曾复用旧环境值；production export 增加 `--clear`，重建后
   bundle 明确包含目标地址，E2E 通过。
6. E2E 文本选择器同时匹配 textarea 和候选名称；改为 exact locator 后关闭歧义。

## 用户确认后的阶段结论

- 已接受本机等价 staging、`$0`、Mock、临时演示数据和自动化录屏作为阶段 8 证据。
- production id 已确认为 `com.boom080.journey`。
- 用户当前没有 Apple Developer Program；本阶段只验收 Simulator，不声称可上架。
- Android 当前只保留 debug-certificate APK 安装路径，不创建 Play upload key 或商店 AAB。
- 未来自租服务器、真实模型和商店发布均须单独授权并重新通过对应门禁。

## 2026-07-31 最终交付复验附录

### 当前通过项

| 层级 | 当前证据 |
|---|---|
| Python 质量 | Ruff check/format 按锁定配置通过；修复 6 个格式文件和 1 个测试导入顺序 |
| 后端/API/数据库 | 65 passed，覆盖率 91.07%；PostgreSQL 18 隔离库 |
| Migration | `0003 → 0002 → 0003`、`alembic check` 和 head 校验通过 |
| Agent/RAG | 318 条版本化 Mock 样本，17 项门禁全通过，failures=0，cost=$0 |
| 移动端 | 5 条逻辑测试、31 条 Jest 测试；statements 81.46%、branches 70.93%、functions 73.91%、lines 84.30% |
| 静态检查 | TypeScript、Expo lint、development/preview/production 变体与环境模板校验通过 |
| Web E2E | 独立 Compose/API/数据库、空模型 Key、Mock；2/2 核心流程通过 |
| JS 构建 | Web 13 条静态路由；iOS、Android Hermes bundle 均通过 |
| iOS 原生 | Xcode 26.6 Release Simulator build 成功；97 MB `.app` 安装到 iPhone 17 Pro 并前台运行 |
| Android 原生 | ARM64 Release APK 构建、签名验证、Pixel 9 安装和前台运行，无 fatal 日志 |
| 配置/密钥 | `.env` 被 Git 忽略；跟踪文件和三端生成 bundle 未发现模型 Key 模式 |

当前 Android APK 约 42 MB，最终 SHA-256 为
`1da15b0d79df48b6641f93453b04712ce2d59681749f8ed6e950da61d781ad59`。证书仍是
`CN=Android Debug`，只用于本机模拟器。iOS 可执行文件 SHA-256 为
`f4341e2185907dc472e6cc48bf405a18aa263d7c50f9cd7dd858f64ce763d490`，只代表 Simulator
制品，不代表 App Store 签名 archive。

### 本轮发现并修复

1. 根环境模板的测试账号密码不满足后端复杂度规则，导致全新隔离 E2E 无法启动；已改为有效
   示例，并将 10—72 字节、大小写和数字要求加入 `infra/verify_app_variants.mjs`。
2. Ruff 在 CI 配置下发现格式和导入顺序差异；已机械格式化并重新跑过完整后端与评测门禁。
3. Android Release 命令没有显式 `NODE_ENV`；构建文档已补充 `NODE_ENV=production`、
   `APP_VARIANT` 和模拟器 API 地址，并用该命令重新生成最终 APK。
4. Pixel 9 默认 4 GB 冷启动在本机并行运行 iOS/Gradle 时受到内存压力；已验证关闭 iOS 后，
   用 2 GB 无窗口 SwiftShader 模式可完成相同 APK 的安装、启动和截图。

### 未关闭但不阻断本机演示的风险

- `npm audit` 当前报告 46 个告警（34 high、12 moderate），路径集中在 Expo/Jest/ESLint
  构建和测试工具的 `brace-expansion`/`uuid` 传递依赖。npm 只提供会降级 Jest 或改变 Expo
  链路的 breaking `--force` 方案，因此本轮未破坏性升级；发布前需在独立依赖升级任务中处理。
- Web 静态 export 和 Playwright E2E 通过，但 Web Nginx 镜像复验两次都在 Docker Hub
  拉取 `node`/`nginx` 元数据时超时；与阶段 8 的外部网络限制一致，不是源代码编译失败。
- Gradle 9 构建成功但报告第三方插件弃用提示和首次构建 Metaspace 压力；升级到 Gradle 10
  前必须先验证 Expo/React Native 官方兼容矩阵。
- 没有公网 staging、Apple 付费会员、iOS distribution identity、Android upload key 或
  真实主 Agent 质量验收，不能表述成“已生产发布”。

### 当前结论

项目已达到本机作品集和秋招演示基线：核心产品闭环、自动化测试、Mock Agent/RAG、三端构建
和双模拟器原生运行都有可复现证据。生产发布仍需另立服务器、HTTPS、签名、依赖升级和真实
模型评测任务。

## 2026-08-01 真实模型验收补充

- 当前功能范围收敛为文字 Agent 与食物图片候选；普通 CI 的 Mock 工程门禁保持不变。
- DeepSeek `deepseek-v4-flash` 首轮 28 次门禁发现一条画像查询误路由；Router Prompt 升级
  后复验为路由/饮食/运动 100%、0 fallback、p95 1768 ms、费用 `$0.00246372`。
- 新增 3 条评测器测试和 1 条 Prompt 回归后完整 Compose 回归为 69/69，后端覆盖率保持
  91.07%，318 条 Mock
  样本与 17 项门禁继续全绿。
- DeepSeek 文字和 Qwen 苹果图的真实 API E2E 冒烟均通过；图片不保留且强制用户校正。
- Qwen 60 张独立图片质量门禁仍失败，所以整体真实模型发布状态为 Conditional；本补充
  不改变 Stage8 本机工程交付 Completed，也不把图片能力包装为正式上线。
- 完整证据见 `evals/reports/REAL_MODEL_ACCEPTANCE_2026_08_01.md`。
