# Journey Mobile

Journey 的 Expo Development Build 客户端。当前包含邮箱/用户名登录、画像与目标、
首页、Journey、我的、手动饮食/运动/体重记录，以及阶段 6 的 Agent 多意图候选、显式
确认写入、引用和周总结。真实模型 key 不进入客户端；默认后端 Mock 可完成零成本演示。

请从仓库根目录运行：

```bash
npm install
npm run mobile:ios
npm run mobile:android
npm run mobile:web
```

阶段 7 自动化命令：

```bash
npm run test:logic --workspace @journey/mobile
npm run test:ci --workspace @journey/mobile
npm run mobile:typecheck
npm run mobile:lint
npm run mobile:web:build
npm run mobile:e2e:web
```

Jest 覆盖组件、登录、首页 Agent 状态、API/网络降级和布局契约；Playwright 通过 Web
静态构建覆盖资料/目标、饮食/运动确认写入、首页/Journey、建议和周总结。CI 另执行
iOS/Android JS bundle 导出；原生签名与安装包属于阶段 8。

根目录 `.env` 是唯一开发环境文件；这些脚本通过 Node 22 的
`--env-file-if-exists` 加载它。不要在客户端环境变量中放置服务端或模型密钥。

完整前置条件、地址差异和验证命令见
[`../../docs/DEVELOPMENT.md`](../../docs/DEVELOPMENT.md)。
