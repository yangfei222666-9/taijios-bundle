# TaijiOS Bundle · Security Posture

## Threat Model

TaijiOS Bundle 默认部署假设:

1. **本地单用户** (loopback 127.0.0.1:8787) · dev 模式友好
2. 通过 `TAIJIOS_API_TOKEN` 环境变量切换成 **shared / production 模式** · 非 loopback client 强制带 Bearer
3. **所有外部 LLM 调用** 通过 provider-agnostic 抽象 · 任一厂商 key 泄露不致全链路暴露

### 不在 threat model 内 (out-of-scope)

- 主机物理安全 · 硬盘加密
- 内核级 sidecar / syscall audit
- 内部攻击者已获得 shell / 可读 `~/.taijios/`

## Hardened in v1.1.2

| ID | 风险 | 对策 |
|---|---|---|
| BUG-1 | 服务器 Traceback + 本地路径泄露到 HTTP response | `sanitize_output()` · 脱敏后回客户端 · 完整写服务端 `api_errors.jsonl` |
| BUG-2 | `user_id` path-traversal 写任意文件 | `^[a-zA-Z0-9_-]{1,64}$` 白名单 · Pydantic + URL path 双层 |
| BUG-3 | 任何 client 可调 subprocess + LLM | 可选 `TAIJIOS_API_TOKEN` Bearer 认证 · Strict 模式关 loopback 豁免 |
| BUG-4 | 无限并发 → DoS | `asyncio.Semaphore(3)` predict · `Semaphore(1)` sync |
| BUG-5 | Demo fallback 伪造真实预测 | 显式 `demo_mode: true` 标识 · client 可区分 |
| BUG-6 | 空 `user_id` 单一 JSON 文件互覆 | `min_length=1` reject |
| BUG-8 | CORS 缺失 + 任意 Origin 可调 | `CORSMiddleware` allow-list (localhost + taijios.xyz) |
| BUG-10 | 超长 / shell meta 字符串 match | 长度 + 正则白名单 (`\u4e00-\u9fa5` 支持中文) |
| BUG-11 | placeholder/弱 token 默认值 (e.g. `your-token`) | 启动时 `_is_weak_token()` 检测; 非 loopback bind + 弱 token = `sys.exit(2)` |

## Deployment Modes

### Dev (default)

```bash
python api_server.py --port 8787
```

- `/health`, `/` 公开
- `/v1/*` 在 loopback (`127.0.0.1` / `::1`) 无鉴权
- 非 loopback client **仍然可以调**(无 token 要求) · 仅在内网/个人机上 OK

### Shared (token-protected)

```bash
TAIJIOS_API_TOKEN="$(openssl rand -hex 32)" python api_server.py --host 0.0.0.0 --port 8787
```

- 非 loopback client 必须带 `Authorization: Bearer <token>`
- Loopback 仍豁免 (monitoring 友好)

### Strict (production)

```bash
# Generate strong token first
TAIJIOS_API_TOKEN=$(python tools/gen_token.py) TAIJIOS_STRICT_AUTH=1 \
  python api_server.py --host 0.0.0.0
```

- 全部 `/v1/*` 强制 Bearer · 包括 loopback
- Token 强度: ≥ 32 字符 (16 byte) hex · 不在 `WEAK_TOKEN_PATTERNS` 列表内
- 弱 token + 非 loopback bind = 启动直接 exit(2)

### Token 强度策略 (`_is_weak_token`)

启动时如设了 `TAIJIOS_API_TOKEN`, 检测以下:
- 长度 < 32 字符 → 弱
- 在 `WEAK_TOKEN_PATTERNS` (case-insensitive) 列表内 → 弱: `your-token`, `your-access-token`, `your-secret`, `your-key`, `secret`, `password`, `test`, `dev`, `demo`, `example`, `changeme`, `admin`, `token`, `api-token`, `placeholder`, `xxx`, `xxxx`, `...`

行为:
- **loopback bind (127.0.0.1)** + 弱 token → stderr WARNING + 启动 (dev 友好)
- **非 loopback bind** + 弱 token → stderr FATAL + `sys.exit(2)` (拒启)

生成强 token: `python tools/gen_token.py` (256-bit secrets.token_hex)

## Environment Variables

| 变量 | 默认 | 作用 |
|---|---|---|
| `TAIJIOS_API_TOKEN` | `""` | Bearer 认证 token (未设 = dev 模式) |
| `TAIJIOS_STRICT_AUTH` | `""` | `=1` 关 loopback 豁免 |
| `TAIJIOS_PREDICT_CONCURRENCY` | `3` | `/v1/predict` 并发上限 |
| `TAIJIOS_SYNC_CONCURRENCY` | `1` | `/v1/sync` 并发上限 |
| `TAIJIOS_SYNC_CACHE_TTL` | `60` | `/v1/sync` 结果缓存秒数 |
| `TAIJIOS_CORS_ORIGINS` | `http://127.0.0.1:*,...,https://taijios.xyz` | CORS 白名单 (逗号分隔) |

## Reporting Vulnerabilities

目前为单人 solo 项目. 发现安全问题请私信 [小九](https://github.com/yangfei222666-9) · 不要发 public issue.

Response SLA: 72h 内初步反馈 · 2 周内发补丁.

## Test Coverage

所有 v1.1.2 修复均有 pytest 用例防回归:

```bash
cd g:/tmp/taijios-bundle
python -m pytest tests/test_security.py -v
```

**19 tests · 1.51s · all pass** (2026-04-19).

## Deferred (not yet hardened)

- **Rate limit per-client** (`/v1/sync` 仅加了 server-side cache; 未做 per-IP 限流). 引入 slowapi 后补上.
- **Soul prompt injection defense-in-depth**. 当前基于规则 + 本地 LLM, 低风险; 接 tool-calling 前必补.
- **Request ID propagation**. 客户端可发 `X-Trace-Id` 但 server 不强制读 · 后续统一.

## Disclosure

本文件是企业级 security posture 的公开声明. 任何对外文案 (BP / 博客 / PR) 若提到 TaijiOS API 的安全属性, 必须以此文件为准 · 不吹牛 · 不藏缺口 · 参 [Manual §4.2](../../C:/Users/A/.claude/projects/g--AIOS-Backups/memory/TAIJIOS_OPERATING_MANUAL.md).
