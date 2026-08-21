# Journey 隐私、安全与预算门禁

> Status: Proposed（正式隐私政策、数据保留期和发布地区仍需用户/法律审阅确认）。

阶段 8 已接受 `$0`、Mock、临时演示数据和本机 staging 作为演示边界；该接受不等于已经具备
面向公众运营所需的正式隐私政策。未来自租服务器或接入真实模型前仍须完成下列门禁。

## 当前已实现边界

- 产品只提供健身、营养和生活方式管理，不做医疗诊断或治疗。
- 外部模型默认关闭：provider `mock`、API Key 空、每日预算 `$0`。
- Agent run 只保存输入 SHA-256、字符数、路由、版本、Token、耗时、成本和错误码；不保存
  原始健康文本或完整 Prompt。
- 登录 Token 使用 SecureStore；Android backup 按 SecureStore 规则配置。
- 原生 local-first 副本使用 AES-256-GCM；每账户密钥保存在 SecureStore，并设为
  `WHEN_UNLOCKED_THIS_DEVICE_ONLY`。AsyncStorage 只保存密文，第一批范围是画像、目标、最近
  90 天饮食/运动/体重与 Journey、Outbox 和冲突。
- Outbox 最多 1000 条且达到上限时明确拒绝继续写入，不静默截断。退出、账户切换或 401 会话
  失效会清除该账户密文、副本、Outbox、冲突、密钥、旧队列和 React Query 缓存；在途同步不能
  在清除后写回。
- Web 不持久化本地健康副本，只保留当前进程内存；刷新后不保证保留，不能宣称与原生加密
  local-first 等价。
- 生活灵感只接受用户主动提供的小红书公开 HTTPS 链接，不接收平台账号、密码、Cookie、验证码
  或登录态。自动预览只提取 title/description 元数据，不保存正文、HTML、图片或响应 Cookie；
  每条由用户编辑并显式确认，可追溯来源并删除。
- 生活灵感预览采用域名白名单、DNS/重定向 SSRF 校验、无 Cookie、8 秒超时、最多 3 次重定向、
  256 KB 响应体上限和 Prompt Injection 词标门禁；失败直接回退手动填写，不绕过访问控制。
  内容固定为 `inspiration_only`，与 Agent、RAG 和健康事实层隔离。
- production 默认 `LIFE_INSPIRATION_FETCH_ENABLED=false`。若未来启用，必须重新复核当日平台
  协议、公开访问稳定性、运营主体的数据删除流程与服务器出站审计。
- Preview/Production Android 禁止明文 HTTP；仅 development 模拟器允许 localhost HTTP。

## 发布前必须确认

- 运营主体、联系邮箱、服务地区、最低年龄和未成年人处理方式。
- 数据类型：身份、画像、饮食、运动、体重、Agent 轨迹；用途、保存期、删除/导出流程。
- 模型供应商是否接收数据、所在地区、是否训练、保留期、子处理者和退出机制。
- Apple Privacy Nutrition Labels、Google Play Data safety 与实际代码一致。
- 日志、备份、错误报告不包含密码、Token、模型 Key 或原始健康输入。
- 测试账号与 staging 数据可随时删除，绝不复制真实用户数据。

## 预算闸门

| 项目 | 当前 | 变更条件 |
|---|---:|---|
| 模型调用 | `$0/day` | 确认供应商、价格、数据政策、硬上限和降级后单独 ADR |
| 本地 Docker | `$0` 云成本 | 仅本机资源 |
| 本机 staging | `$0` | 阶段 8 已接受，不上传公网 |
| 未来自租服务器 | 配置已实现 / 未部署 | Compose/HTTPS 基线已形成；仍需确认供应商、地区、期限、域名、隐私、备份和预算 |
| EAS/Apple/Google | Proposed | 用户确认账号、签名与费用 |

任何非零账单、真实模型请求、外部健康数据上传或长期云资源创建都需要单独确认。
