# ShockPath 邮箱账号

本切片根据用户新增登录/注册要求启用独立账号服务。历史 Phase 4/5 的账号延期规则保留作为冻结记录；当前实现采用邮箱验证码免密码登录、独立 MySQL 账号库和独立登录/注册页面。

## 使用

开始页右上角的登录/注册进入 `/login`、`/register`。首次使用先注册；登录/注册均验证邮箱中的六位验证码，注册成功直接登录。未登录进入 `/home`、新建计算或运行工作台，会先转到登录页，验证成功后继续原地址。论文详情、机制解释与既有科研证据仍可浏览。

SMTP 使用 `smtp.qq.com:465`、证书及主机名验证、十秒超时。发件邮箱与授权码仅放在 Git 忽略的 `.env`；验证码投递到表单填写的邮箱。QQ SMTP 接受邮件后返回 `SMTP_ACCEPTED`，该状态不表示收件箱已实际收到邮件。

```dotenv
ENABLE_ACCOUNTS=true
QQ_SMTP_EMAIL=your-sender@qq.com
QQ_SMTP_AUTH_CODE=your-smtp-authorization-code
AUTH_DATABASE_URL=mysql+pymysql://USER:PASSWORD@127.0.0.1:3308/shockpath_accounts
AUTH_SECRET_KEY=
AUTH_COOKIE_SECURE=false
AUTH_TRUSTED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

Python 或 PowerShell 后端入口读取 `.env`，进程环境变量优先。URL 中账号密码的特殊字符必须按 URL 编码。MySQL 数据库需预先存在；服务只创建 `auth_` 账号表，不操作科研数据。账号、验证码摘要、会话摘要和限流记录都保存在账号库中。未提供签名密钥时，在忽略的 `runtime/auth/secret.key` 持久保存随机密钥。HTTPS 部署设置 `AUTH_COOKIE_SECURE=true`；非 loopback 主机默认也使用 Secure Cookie。

## 接口与边界

| 接口 | 作用 |
| --- | --- |
| `GET /api/v1/auth/session` | 恢复会话并提供与 Cookie 绑定的 CSRF 令牌 |
| `POST /api/v1/auth/email-verification-challenges` | 发送 `login` 或 `register` 用途的验证码 |
| `POST /api/v1/auth/register` | 原子验证验证码、创建账号并建立会话 |
| `POST /api/v1/auth/login` | 验证登录用途的验证码并旋转会话 |
| `POST /api/v1/auth/logout` | 吊销会话并清除登录 Cookie |

账号 POST 与启用账号后的 V2 写操作需要同源请求及 `X-CSRF-Token`。未登录直接调用 V2 写接口返回 401，前端路由不是唯一拦截。已有科研读取接口与工作台运行记录仍遵循原有共享项目模式，本切片没有新增按用户隔离的 Run 工作区。

Vite 代理后的后端 Host 可能与浏览器 Origin 不同；通过 `AUTH_TRUSTED_ORIGINS` 显式登记前端来源。部署到其他域名或端口时同步更新此名单，不使用通配来源或信任客户端传入的转发 Host。

验证码有效期十分钟、单次使用、最多五次错误验证。邮箱发送间隔六十秒、每小时五次；IP 每小时二十次，验证每十五分钟二十次。数据库事务锁保证并发占用与验证码消费原子性；SMTP 不持数据库锁，发送失败保留已激活的旧码。验证码以服务端 HMAC 摘要保存，不返回到前端或写入日志。会话有效期二十四小时，数据库只保存随机令牌摘要；Cookie 使用 HttpOnly、SameSite=Lax，退出后立即吊销。

## 验证

`./.venv/Scripts/python.exe -B -m pytest tests/auth tests/test_bootstrap.py -q` 覆盖注册、登录、持久会话、验证码有效期、重复消费、用途绑定、错误次数、发送限流、SMTP 失败、并发消费、CSRF 与 V2 写接口拦截。邮件测试使用测试进程内的独立发送器，不发送真实邮件，不在生产接口提供验证码读取能力。

关闭账号时仍保留兼容匿名模式，可使用进程环境变量 `ENABLE_ACCOUNTS=false` 运行历史科学/浏览器验收；生产账号页面和数据库配置不应复制到公开素材。
