# Journey 演示故障预案

## 现场分级

1. **客户端问题**：强制退出重开；确认运行的是匹配版本和变体。
2. **API 问题**：检查 `/health/ready`；失败则切本地 Docker。
3. **数据问题**：只运行测试账号 reset；禁止删库。
4. **Agent 问题**：展示 Mock/fallback trace；手动饮食/运动记录仍可完成。
5. **全链路问题**：播放版本匹配的备用录屏，同时展示测试报告和架构图。

## 快速命令

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:8000/health/ready

RESET_CONFIRM=journey-demo-account \
DEMO_BASE_URL=http://127.0.0.1:8000 \
DEMO_ACCOUNT_EMAIL=demo@journey.local \
DEMO_ACCOUNT_PASSWORD='<local-test-password>' \
python3 infra/demo/reset_demo.py
```

## 常见问题

- **Render 首次请求慢**：Free 实例可能冷启动；开场前请求 Ready。连续失败就切本地。
- **Android 访问不了 localhost**：模拟器使用 `10.0.2.2`；真机必须使用 HTTPS staging。
- **Android Release 登录超时**：确认构建的是 development 变体且 Manifest 仅此变体允许
  cleartext；Preview/Production 不得为修演示而放宽。
- **iOS API 不通**：Simulator 用 `127.0.0.1`；真机不能把本机 localhost 当服务器。
- **测试账号状态混乱**：运行幂等 reset；该脚本只删除该账号的核心记录。
- **Agent 不可用**：展示明确降级消息、手动记录和已保存历史；不要声称 Mock 是真实模型。
- **无网**：已登录用户可查看缓存、排队少量记录；新登录和 Agent 不可用。Web 不持久化健康队列。
- **Docker Hub 超时**：先使用已构建镜像或本机 Python/Expo；不要在面试现场首次拉镜像。
- **签名失败**：Simulator/Emulator 不依赖商店签名；发布签名留到账号与证书确认后。

## 演示前 15 分钟检查

- Docker/API Ready；测试账号 reset 成功；Mock cost=0。
- iOS Simulator 主流程走一遍；Android APK 至少冷启动一次。
- 关闭系统升级、通知和自动锁屏；电源与网络稳定。
- 打开架构图、阶段 7 报告和备用录屏；记下本次版本与 SHA-256。
- 准备一句边界说明：“当前展示为 Mock 可重复基线，真实供应商尚未获准接入。”
