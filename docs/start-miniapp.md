# Journey 小程序首次联调启动方式

## 1. 安装前端依赖
- 在项目根目录执行 `npm install`

## 2. 配置后端环境变量
- 复制 `backend/.env.example` 为 `backend/.env`
- 填入：
  - `WECHAT_APP_ID`
  - `WECHAT_APP_SECRET`

## 3. 启动后端
- 进入 `backend`
- 执行 `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## 4. 配置前端接口地址
- 复制根目录 `.env.example` 为 `.env`
- 按需修改 `TARO_APP_API_BASE_URL`
- 真机或开发者工具常见写法：
  - 本地后端映射地址
  - 局域网 IP，例如 `http://192.168.x.x:8000`

## 5. 编译微信小程序
- 日常联调用 `npm run dev:weapp`
- `npm run build:weapp` 只用于一次性生成 `dist`，不是日常 watch 命令
- 如果微信开发者工具里出现 `timeout`
  - 先确认后端正在运行在 `8000` 端口
  - 再确认根目录 `.env` 里的 `TARO_APP_API_BASE_URL` 可被当前环境访问
  - 真机联调不要用 `127.0.0.1`，要改成你的局域网 IP

## 6. 导入微信开发者工具
- 打开微信开发者工具
- 导入项目根目录
- `AppID` 填真实小程序 AppID
- 若只是本地预览，可继续使用测试号或体验配置
- 确认 `project.config.json` 的 `miniprogramRoot` 指向 `dist/`

## 7. 首次联调顺序
- 打开登录页
- 点击微信登录
- 未激活用户跳邀请码页
- 输入种子邀请码：
  - `JOURNEY-MINT-001`
  - `JOURNEY-MINT-002`
  - `JOURNEY-MINT-003`
- 激活后进入首页
- 新增 food / activity 记录
- 回首页看摘要
- 去里程页看多天记录
