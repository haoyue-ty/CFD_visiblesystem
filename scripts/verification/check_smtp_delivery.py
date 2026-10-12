"""诊断 ShockPath 验证码邮件（QQ SMTP）投递链路。

只做只读探测，不发送任何邮件：
  1. 读取 .env 中的 QQ_SMTP_EMAIL / QQ_SMTP_AUTH_CODE
  2. 解析 smtp.qq.com，识别是否被本地代理（Clash TUN + fake-ip）劫持
  3. 对 smtp.qq.com:465 / :587 执行一次 SMTP 登录探测
  4. 按故障类别给出结论

用法（在项目根目录）：
    ./.venv/Scripts/python.exe -B -m scripts.verification.check_smtp_delivery

背景：本机 Clash Verge 若处于「全局模式」且开启 TUN，DNS 会被替换为
198.18.0.0/15 的 fake-ip，所有出站连接（含 SMTP 465）都会被送进代理节点，
导致 TLS 握手被切断，后端 send_code() 抛异常并返回 503
「验证码邮件发送失败」，注册用户永远收不到验证码。
"""
from __future__ import annotations

import ipaddress
import smtplib
import socket
import ssl
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAKE_IP_NETS = (ipaddress.ip_network('198.18.0.0/15'), ipaddress.ip_network('2001:2::/48'))
SMTP_HOST = 'smtp.qq.com'


def load_env() -> dict:
    values: dict[str, str] = {}
    env_path = ROOT / '.env'
    if not env_path.exists():
        return values
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=True, interpolate=False)
    except ImportError:
        print('[warn] python-dotenv 不可用，改用简易解析')
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, raw = line.partition('=')
            raw = raw.strip()
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in '"\'':
                raw = raw[1:-1]
            import os
            os.environ[key.strip()] = raw
    import os
    for key in ('QQ_SMTP_EMAIL', 'QQ_SMTP_AUTH_CODE', 'ENABLE_ACCOUNTS', 'AUTH_DATABASE_URL'):
        if os.getenv(key) is not None:
            values[key] = os.environ[key]
    return values


def mask(secret: str) -> str:
    if not secret:
        return '(空)'
    if len(secret) <= 4:
        return '*' * len(secret)
    return secret[:2] + '*' * (len(secret) - 4) + secret[-2:]


def dns_probe(host: str) -> tuple[list[str], bool]:
    try:
        infos = socket.getaddrinfo(host, 465, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        print(f'  !! DNS 解析失败: {exc}')
        return [], False
    ips = sorted({info[4][0] for info in infos})
    hijacked = False
    for ip in ips:
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if any(addr in net for net in FAKE_IP_NETS):
            hijacked = True
    print(f'  {host} -> {", ".join(ips)}')
    if hijacked:
        print('  !! 命中 198.18.0.0/15 fake-ip 段：DNS 正被本地代理接管')
    return ips, hijacked


def smtp_probe(email: str, auth_code: str, port: int, use_ssl: bool) -> str:
    label = f'{SMTP_HOST}:{port}'
    started = time.time()
    server = None
    try:
        context = ssl.create_default_context()
        if use_ssl:
            server = smtplib.SMTP_SSL(SMTP_HOST, port, timeout=15, context=context)
        else:
            server = smtplib.SMTP(SMTP_HOST, port, timeout=15)
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
        server.login(email, auth_code)
        print(f'  [OK] {label} 登录成功 ({time.time() - started:.1f}s)')
        return 'OK'
    except smtplib.SMTPAuthenticationError as exc:
        print(f'  [授权码无效] {label} {exc.smtp_code} {exc.smtp_error!r}')
        return 'AUTH'
    except (socket.timeout, TimeoutError):
        print(f'  [超时] {label} ({time.time() - started:.1f}s) —— 连接被丢弃，通常是代理在拦截')
        return 'TIMEOUT'
    except ssl.SSLError as exc:
        print(f'  [TLS 被切断] {label} {type(exc).__name__}: {exc}')
        return 'TLS'
    except OSError as exc:
        print(f'  [网络不可达] {label} {type(exc).__name__}: {exc}')
        return 'NET'
    except smtplib.SMTPException as exc:
        print(f'  [SMTP 异常] {label} {type(exc).__name__}: {exc}')
        return 'SMTP'
    finally:
        if server is not None:
            try:
                server.close()
            except Exception:
                pass


def main() -> int:
    print('=== ShockPath 验证码邮件链路诊断 ===')
    env = load_env()
    email = (env.get('QQ_SMTP_EMAIL') or '').strip()
    auth_code = (env.get('QQ_SMTP_AUTH_CODE') or '').strip()
    print(f'ENABLE_ACCOUNTS : {env.get("ENABLE_ACCOUNTS")!r}')
    print(f'发件邮箱        : {email or "(未配置)"}')
    print(f'SMTP 授权码     : {mask(auth_code)} (长度 {len(auth_code)})')
    if not email or not auth_code:
        print('\n结论：QQ_SMTP_EMAIL / QQ_SMTP_AUTH_CODE 未配置，')
        print('      后端 send_code() 会直接返回 503「验证码邮件服务尚未配置」。')
        return 2

    print('\n--- DNS ---')
    _, hijacked = dns_probe(SMTP_HOST)

    print('\n--- SMTP 登录探测（不发送邮件）---')
    results = [smtp_probe(email, auth_code, 465, True), smtp_probe(email, auth_code, 587, False)]

    print('\n--- 结论 ---')
    if any(r == 'OK' for r in results):
        print('链路正常：SMTP 可登录。若用户仍收不到，请检查')
        print('  1) QQ邮箱「自助查询 → 发信查询」是否有被退信记录')
        print('  2) 是否落入收件方垃圾箱（个人 QQ 邮箱发信信誉较低）')
        print('  3) 是否超过 QQ 邮箱每日 SMTP 发信上限')
        return 0
    if hijacked or any(r in ('TLS', 'TIMEOUT') for r in results):
        print('链路不通：出站 SMTP 连接被本地代理拦截，QQ 服务器根本没收到请求。')
        print('处理办法：')
        print('  a) 把 Clash Verge 从「全局模式(global)」切到「规则模式(rule)」')
        print('     —— 规则集中 cn_domain 会让 *.qq.com 走 DIRECT 直连；或')
        print('  b) 直接关闭 TUN 模式后再启动后端；或')
        print('  c) 在 Clash 里为 smtp.qq.com / 465 显式添加 DIRECT 规则。')
        print('  注意：TUN 模式在网络层拦截，Python smtplib 不读系统代理，')
        print('        所以代码里设代理白名单没用，必须在 Clash 侧放行。')
        return 1
    if any(r == 'AUTH' for r in results):
        print('链路可达，但 QQ SMTP 授权码被拒。')
        print('处理办法：到 QQ邮箱 → 设置 → 账户 → 开启或重置「IMAP/SMTP 服务」，')
        print('          重新生成授权码并写入 .env 的 QQ_SMTP_AUTH_CODE。')
        return 3
    print('链路状态未知，请把上面的原始输出贴出来。')
    return 4


if __name__ == '__main__':
    sys.exit(main())
