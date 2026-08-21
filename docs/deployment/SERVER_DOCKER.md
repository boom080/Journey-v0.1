# Journey 单服务器 Docker 部署

> Status: Implemented / Conditional local validation（2026-08-05）
> 本页提供单台 Linux 服务器的 production 基线，不表示已经租用服务器或完成公网发布。
> Compose、production API/PostgreSQL（当前 `0006_local_first`）、Web export 和 Caddyfile
> 已分别通过；本机 Docker Hub
> token 网络超时阻塞了 Node/Nginx/Caddy 镜像拉取，因此四容器整栈仍需在网络正常的服务器复验。

## 容器化边界

服务器侧由 `compose.production.yaml` 一次编排：

- `db`：PostgreSQL 18，只有 Docker 内部网络可访问，数据保存在命名卷；
- `api`：FastAPI、Alembic、Agent/RAG；启动时先迁移数据库，再启动 Uvicorn；
- `web`：Expo Web production export，由 Nginx 容器提供静态文件；
- `gateway`：Caddy，只暴露 80/443，自动申请和续期 HTTPS 证书，把 `/api/*`、`/health/*`
  转发给 API，其余请求转发给 Web。

iOS/Android 安装包不在 Docker 中交付。它们仍需 Expo/EAS 或 Xcode/Gradle 签名构建，但统一连接
这里的 HTTPS API。Docker 解决的是服务器运行环境和 Web 发布，不替代应用商店分发。

## 服务器前置条件

1. 一台安装 Docker Engine 和 Docker Compose plugin 的 Linux 服务器；
2. 域名 A/AAAA 记录指向该服务器；
3. 防火墙允许公网 TCP 80/443 和 UDP 443；PostgreSQL 5432、API 8000 不对公网开放；
4. Git 只读拉取权限，或预先把仓库放到服务器；
5. 服务器地区、费用、隐私政策、备份位置和运营主体已确认。

Caddy 自动 HTTPS 要求域名解析正确、80/443 可达，并持久化 `/data` 中的证书状态。参考
[Caddy Automatic HTTPS](https://caddyserver.com/docs/automatic-https) 和
[Docker Compose production](https://docs.docker.com/compose/how-tos/production/)。

## 首次部署

在服务器仓库根目录执行：

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

至少替换以下值：

- `SERVER_DOMAIN`：仅域名，例如 `journey.example.com`；
- `PUBLIC_ORIGIN`：同一域名的完整 HTTPS Origin，例如 `https://journey.example.com`；
- `POSTGRES_PASSWORD`：至少 32 位 URL-safe 随机值；
- `APP_SECRET_KEY`：至少 64 位随机值。

可用 `openssl rand -hex 32` 分别生成数据库密码和应用密钥。`.env.production` 已被 Git 忽略，
不得放入仓库、客户端、截图或聊天记录。

先验证配置，再启动：

```bash
docker compose --env-file .env.production -f compose.production.yaml config --quiet
docker compose --env-file .env.production -f compose.production.yaml up -d --build --wait
infra/production/smoke.sh "https://journey.example.com"
```

`api` entrypoint 会执行 `alembic upgrade head`，不需要在服务器手工改表。production 强制关闭
测试账号播种和真实图片识别；Agent 默认 `mock`、预算 `$0`。真实文字模型需要另行确认供应商、
隐私、价格和预算，再在服务端 `.env.production` 配置，客户端永远不保存模型 Key。

## 日常检查

```bash
docker compose --env-file .env.production -f compose.production.yaml ps
docker compose --env-file .env.production -f compose.production.yaml logs --tail=200 api gateway
curl -fsS https://journey.example.com/health/live
curl -fsS https://journey.example.com/health/ready
```

所有容器使用 `unless-stopped`，Docker 重启后自动恢复；日志采用本机 `json-file` 轮转，每个容器
最多保留 5 个 10 MB 文件。长期运行仍应接入服务器磁盘、可用性和备份告警。

## 备份与恢复门禁

升级前先生成 PostgreSQL 自定义格式备份，并把副本加密保存到服务器之外：

```bash
mkdir -p backups
docker compose --env-file .env.production -f compose.production.yaml exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' \
  > "backups/journey-$(date +%Y%m%d-%H%M%S).dump"
```

恢复会覆盖数据，不在自动部署命令中提供。必须先确认目标数据库、备份哈希和停机窗口，再按
`docs/deployment/STAGING.md` 的恢复门禁单独执行并复验 `/health/ready`。

## 更新与回退

更新前确认工作区干净、拉取已验收提交并完成备份：

```bash
git pull --ff-only
docker compose --env-file .env.production -f compose.production.yaml build --pull api web
docker compose --env-file .env.production -f compose.production.yaml up -d --wait
infra/production/smoke.sh "https://journey.example.com"
```

若新版本失败，停止继续迁移或写入，切回已知可用的 Git tag/commit 后重新构建；数据库只能使用
对应版本明确支持的 downgrade 或已验证备份恢复，禁止手工删表和 `git reset --hard`。

## 移动端连接服务器

Preview/Production 构建必须使用 EAS 对应环境显式注入相同 HTTPS Origin。该 URL 是公开配置，
不是密钥；模型 Key 和 `APP_SECRET_KEY` 仍只能留在服务器。首次配置 production 环境：

```bash
cd apps/mobile
npx eas-cli env:create \
  --environment production \
  --name EXPO_PUBLIC_API_BASE_URL \
  --value https://journey.example.com \
  --visibility plaintext
npx eas-cli env:list --environment production
npx eas-cli build --platform android --profile production
```

iOS 使用同一 `production` EAS 环境执行 `--platform ios`。`eas.json` 已把 development、preview、
production profile 分别绑定到同名 EAS 环境；Preview 需另行在 `preview` 环境配置 HTTPS URL。

iOS 还需要 Apple Developer Program、Distribution certificate 和 provisioning profile；Android
商店发布需要长期 upload key。Docker production 栈就绪不代表应用商店签名已经完成。

## 当前未完成

- 尚未选择或租用公网服务器、域名和 DNS 服务；
- 尚未在真实公网完成证书签发、外部备份恢复、跨网络移动端和负载测试；
- 当前是单机部署，不提供跨节点高可用、零停机数据库迁移或 Kubernetes；
- 正式隐私政策、数据保留/导出/删除流程仍需发布前确认。
