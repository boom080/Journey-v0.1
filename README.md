<p align="center">
  <img src="assets/brand/journey-sticker-logo.svg" width="120" alt="Journey logo" />
</p>

<h1 align="center">Journey</h1>

<p align="center">
  一个使用 Expo、FastAPI 和 PostgreSQL 构建的跨平台健身、营养与生活方式记录应用。
</p>

Journey 支持饮食、运动和体重记录，并通过 Agent 与受控知识库提供记录解析、建议和周总结。
本地默认运行 Mock Agent，不需要模型密钥，也不会向外部 AI 服务发送数据。

## 快速开始

### 1. 准备环境

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Node.js 22（项目包含 `.node-version`）
- npm 10
- Python 3

运行 iOS 客户端还需要 macOS 和 Xcode；只使用 Web 不需要安装 Xcode 或 Android Studio。

### 2. 获取项目并安装依赖

```bash
git clone https://github.com/boom080/Journey-v0.1.git
cd Journey-v0.1
cp .env.example .env
chmod 600 .env
npm ci
```

### 3. 启动数据库和 API

```bash
./infra/demo/demo_up.sh
```

脚本会检查本机环境、构建并启动 PostgreSQL 与 FastAPI、执行数据库迁移，并等待服务健康。

启动后可访问：

- API 健康状态：<http://127.0.0.1:8000/health/ready>
- API 文档：<http://127.0.0.1:8000/docs>

### 4. 启动客户端

Web：

```bash
npm run mobile:web
```

iOS Simulator：

```bash
npm run mobile:ios
```

客户端地址会显示在 Expo 终端中。iOS Simulator 和 Web 默认连接
`http://127.0.0.1:8000`。

### 5. 创建本地账号

打开客户端，在登录页选择“创建账号”，填写昵称、邮箱、用户名和密码，完成注册后即可登录。
账号和业务数据保存在本机启动的 PostgreSQL 中，不会上传到 Journey 的公共服务器。

## 常用命令

| 命令 | 作用 |
|---|---|
| `npm run mobile:web` | 启动 Web 客户端 |
| `npm run mobile:ios` | 启动 iOS Simulator 客户端 |
| `npm run mobile:typecheck` | 检查 TypeScript 类型 |
| `npm run mobile:lint` | 检查客户端代码规范 |
| `npm run mobile:test` | 运行客户端测试 |
| `docker compose --profile test run --rm test` | 运行后端测试和 Agent/RAG 评测 |
| `docker compose logs -f api` | 查看 API 日志 |
| `docker compose down` | 停止服务并保留数据库数据 |

## 项目结构

```text
apps/mobile/       Expo / React Native 客户端
backend/           FastAPI、Agent、RAG 与数据库迁移
packages/          API 契约与设计 Token
evals/             Agent 和 RAG 自动化评测
infra/             本地启动、测试与部署脚本
docs/              版本开发文档与问题记录
```

## 使用说明

- 默认配置为本地 Mock Agent，零外部调用、零模型费用。
- `.env`、本地数据库、测试报告、备份和密钥不会提交到 Git。
- Journey 只提供一般健身、营养和生活方式信息，不提供医疗诊断、处方或治疗建议。
