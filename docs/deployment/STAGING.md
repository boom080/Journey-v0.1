# Journey staging 运行手册

> Status: Accepted（阶段 8 采用本机隔离 staging）
> 本轮已验收：本机隔离 staging；用户确认暂不创建外部云资源。

## 当前基线

- 平台：本机 Docker Compose，不依赖公网平台。
- 预算：`$0`；只使用 Mock、临时演示数据和本机备份。
- API：FastAPI 模块化单体；数据库：独立 PostgreSQL 18；Agent：`mock`；模型 Key：空；
  每日模型预算：`0`。
- 编排：`compose.staging.yaml`。根目录 `render.yaml` 只保留为未启用参考，不表示已选择 Render。

未来云部署前必须重新确认服务器供应商、费用、数据区域、域名、隐私文本和密钥托管；不要把
本地默认 secret、测试密码或模型密钥复制到服务器配置。

## 本地隔离演练

```bash
export STAGING_DATABASE_PASSWORD='replace-with-local-only-value'
export STAGING_APP_SECRET_KEY='replace-with-at-least-32-characters'
export STAGING_TEST_ACCOUNT_PASSWORD='replace-with-test-only-value'
API_PORT=18000 POSTGRES_PORT=55432 \
  docker compose -p journey-stage8 -f compose.yaml -f compose.staging.yaml up -d --build
curl -fsS http://127.0.0.1:18000/health/ready
python3 infra/staging/smoke.py --base-url http://127.0.0.1:18000 \
  --email demo@journey.local --password "$STAGING_TEST_ACCOUNT_PASSWORD"
```

该 Compose project 使用独立端口、网络和数据卷，不读取开发数据库。停止时不要添加 `-v`，
除非已确认备份且明确要删除 staging 数据：

```bash
docker compose -p journey-stage8 -f compose.yaml -f compose.staging.yaml down
```

## 自租服务器发布门禁

单服务器 production Compose、Web 容器和 Caddy HTTPS 网关已形成可复验基线，完整操作见
[`SERVER_DOCKER.md`](SERVER_DOCKER.md)。当前仍未租用服务器或执行公网发布；以下外部门禁
保持有效。

1. 用户单独授权租用或接入服务器，并确认供应商、区域、期限和预算。
2. 配置域名、HTTPS 证书、反向代理、防火墙、服务端 secrets、日志和最小监控。
3. PostgreSQL 使用独立持久卷，建立加密异地备份并实际演练恢复。
4. 等待 `/health/ready` 为 200，确认 migration 成功；用 HTTPS URL 运行
   `infra/staging/smoke.py`，输出必须为 provider `mock`、cost `0`、
   Prompt/Schema/Knowledge 版本与阶段 7 基线一致。
5. 在 iOS/Android Preview 构建中注入该 HTTPS URL，做跨网络登录和核心只读检查。
6. 真实模型仍须另行确认供应商、隐私、价格和正预算；不得因服务器上线自动启用。

## 备份与恢复

```bash
STAGING_DATABASE_URL='postgresql://...' infra/staging/backup.sh
RESTORE_CONFIRM=journey-staging \
  STAGING_DATABASE_URL='postgresql://...' \
  infra/staging/restore.sh artifacts/staging/backups/<file>.dump
```

备份脚本使用 PostgreSQL 18 客户端、自定义格式和 SHA-256；恢复脚本强制确认并在恢复后运行
数据库连通性检查。Free PostgreSQL 无托管备份，仓库外的加密副本才是灾难恢复依据。

## 最小监控与故障判定

- 可用性：`GET /health/live`、`GET /health/ready`。
- 数据库：Ready 必须验证真实查询，而不是只检查进程。
- Agent：trace 中记录 provider、模型、耗时、Token、估算成本和错误码，不保存原始健康文本。
- 告警基线：连续 3 次 Ready 失败、5xx 比例超过 5%、P95 超过 3 秒或成本非 0，立即切换
  本地 Docker + Mock 演示并停止外部环境。

## 回退

云端不可用时，按本页“本地隔离演练”恢复；客户端切回本机 API；用
`infra/demo/reset_demo.py` 重置单一测试账号。不得通过手工删表或复制生产数据恢复演示。
