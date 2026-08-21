# Journey 构建与发布路径

> 版本：`0.1.0`；production application id 已确认为 `com.boom080.journey`。
> 本轮只验证本机/模拟器路径，不声称已完成商店签名或上架。

## 变体

| `APP_VARIANT` | 名称 | 标识 | API/用途 |
|---|---|---|---|
| `development` | Journey (Dev) | `com.boom080.journey.dev` | 本机模拟器；Android 仅此变体允许明文 localhost |
| `preview` | Journey (Preview) | `com.boom080.journey.preview` | HTTPS staging；内部安装 |
| `production` | Journey | `com.boom080.journey` | HTTPS production；商店候选 |

`apps/mobile/app.config.js` 是事实源，`apps/mobile/eas.json` 定义 Development、Preview、
iOS Simulator 和 Production profile。Preview/Production 均禁止 Android cleartext traffic。

## Web

```bash
EXPO_PUBLIC_API_BASE_URL=https://example.invalid npm run mobile:web:build
docker build -f infra/web/Dockerfile \
  --build-arg APP_VARIANT=production \
  --build-arg EXPO_PUBLIC_API_BASE_URL=https://example.invalid \
  -t journey-web:0.1.0 .
```

静态产物位于 `apps/mobile/dist/`。Web 只用于补充展示，不是主演示。
单服务器的 Web/API/PostgreSQL/HTTPS 一体化部署见
[`SERVER_DOCKER.md`](SERVER_DOCKER.md)。

## Android Emulator 与 APK

```bash
cd apps/mobile
APP_VARIANT=development npx expo prebuild --clean --platform android
cd android
JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home" \
ANDROID_HOME="$HOME/Library/Android/sdk" \
NODE_ENV=production \
APP_VARIANT=development \
EXPO_PUBLIC_API_BASE_URL=http://10.0.2.2:8000 \
./gradlew app:assembleRelease -PreactNativeArchitectures=arm64-v8a
```

安装包是 `apps/mobile/android/app/build/outputs/apk/release/app-release.apk`。当前本机 Release
APK 使用自动生成的 Android debug certificate，仅用于模拟器验收，不得上传 Google Play。

发布 AAB 需要用户持有并备份 upload key，或由 EAS credentials 管理；再运行 Production
profile 生成 AAB。密钥、keystore、密码和 credentials JSON 不得进入仓库。Google Play
开发者账号、包名所有权、隐私披露和 Data safety 表单是发布门禁。

### Android 签名是什么意思

Android 要求每个可安装 APK 都带数字签名，可理解为发布者给安装包加的不可伪造印章。
系统用它确认安装包来源，并只允许持有同一长期密钥的人给已安装应用发布更新。当前 APK
使用开发工具自动生成的 debug certificate，足够在模拟器和本机安装；用户当前不发布到
Google Play，因此阶段 8 不创建 upload key。未来准备上架时再生成并离线备份长期 upload
key；丢失或随意更换它可能导致用户无法正常升级。

若 Pixel 9 首次冷启动因本机内存压力被系统结束，可先关闭 iOS Simulator，再用同一 AVD 的
低资源验收模式启动：

```bash
"$HOME/Library/Android/sdk/emulator/emulator" \
  -avd Pixel_9 -no-window -no-audio -no-boot-anim \
  -gpu swiftshader_indirect -memory 2048
```

该模式仍可通过 `adb install`、`adb shell am start` 和 `adb exec-out screencap` 验证安装、
前台 Activity 与渲染结果；它只改变模拟器资源配置，不改变 APK。

## iOS Simulator 与 archive

```bash
cd apps/mobile
npx pod-install
APP_VARIANT=development EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 \
  npx expo run:ios --configuration Release --device "iPhone 17 Pro"
```

Simulator 不需要发布证书。用户当前没有付费 Apple Developer Program，因此本阶段接受
Simulator 为 iOS 验收路径。未来真机 archive/TestFlight/App Store 需要：

- 已确认 `com.boom080.journey` 可注册；
- 付费 Apple Developer Program 团队；
- Distribution certificate 与 provisioning profile；
- App Store Connect 应用、隐私标签、年龄分级、截图和审核资料；
- Xcode Archive/Validate 成功。

本机当前 `security find-identity -v -p codesigning` 为 0 个有效身份，所以 Simulator 成功不能
等同于签名 archive 成功。

## EAS 可选路径

```bash
cd apps/mobile
npx eas-cli build --platform android --profile preview
npx eas-cli build --platform ios --profile ios-simulator
```

以上会要求 Expo 登录并可能产生云构建费用；执行前必须由用户确认账号和预算。APK profile
用于内部安装；Production Android 默认应输出 AAB。

## 制品规则

- 版本由 `version`、`ios.buildNumber`、`android.versionCode` 三项共同标识。
- 交付前记录文件大小、SHA-256、构建命令、Git commit（如有）、配置变体和签名证书摘要。
- `artifacts/` 只存本机临时证据并被忽略；长期交付物另行放到批准的发布介质。
- 任何构建不得注入真实模型 Key；客户端永远不持有模型密钥。
