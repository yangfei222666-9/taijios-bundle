# TaijiOS Bundle

TaijiOS Bundle is a release snapshot and installer package for trying the TaijiOS ecosystem locally.

It is not the canonical source repo for every component. Treat this repository as the packaged entry point:
install, run the local demos, inspect the included components, then follow the component repos for active development.

## What This Bundle Is

- A local trial bundle for TaijiOS components.
- A snapshot of several related repos, scripts, and docs.
- A fast path to run Zhuge prediction, Soul/API endpoints, heartbeat, MCP, and local status checks.
- A packaging layer, not the only source of truth for the full TaijiOS codebase.

## Quick Start

Windows:

```bat
setup.bat
```

macOS / Linux / Windows terminal:

```bash
python setup.py
python taijios.py
```

If you want manual control:

```bash
python taijios.py install
python taijios.py status
python taijios.py predict "Inter vs Cagliari"
python heartbeat.py
```

Read the full setup guide first if this is your first run:

- [START_HERE.md](START_HERE.md)
- [MANIFEST.md](MANIFEST.md)
- [SECURITY.md](SECURITY.md)

## Included Components

| Path | Purpose |
|---|---|
| `zhuge-skill/` | Football/data reasoning demo with hexagram-style decision output. |
| `self-improving-loop/` | Agent reliability loop snapshot. Active work should follow the upstream repo. |
| `taiji/` | Main TaijiOS system snapshot and hub. |
| `TaijiOS/` | Legacy prototype snapshot. |
| `TaijiOS-Lite/` | Lite/ICI prototype snapshot. |
| `zhuge-crystals/` | Shared crystal/data-pool snapshot. |
| `taijios-landing/` | Website/docs snapshot. |
| `aios/` | Bundled AIOS support modules. |
| `tools/` | Utility scripts such as token generation. |
| `tests/` | Bundle-level regression tests, mostly security/API hardening checks. |

## Root Script Map

| File | Role |
|---|---|
| `setup.py` / `setup.bat` | Interactive installer/bootstrapper. This is not a standard packaging `setup.py`. |
| `taijios.py` | Main local menu/CLI entry. |
| `api_server.py` | FastAPI HTTP API server. See [SECURITY.md](SECURITY.md) before exposing it beyond localhost. |
| `doctor.py` | Local environment diagnostics. |
| `heartbeat.py` / `heartbeat_daemon.py` | Manual or daemon heartbeat checks. |
| `mcp_server.py` | MCP integration entry for compatible AI IDEs. |
| `brain.py` | Local brain/coordination helper. |
| `embed.py`, `vision.py`, `imagegen.py`, `tts.py` | Optional feature adapters. |
| `install_scheduler.py` / `uninstall.py` | Local scheduler install/uninstall helpers. |

## Security Rules

- Keep `.env` local. Do not commit API keys, bot tokens, or private credentials.
- Do not expose `api_server.py` publicly without a strong `TAIJIOS_API_TOKEN`.
- For shared or production-like use, read [SECURITY.md](SECURITY.md) and use strict auth.
- Demo output is not evidence of live provider health. Verify provider keys and logs before claiming live capability.

## Verification

Bundle-level security tests:

```bash
python -m pytest tests/test_security.py -v
```

If dependencies are missing:

```bash
python -m pip install -r requirements.txt pytest
python -m pytest tests/test_security.py -v
```

## 中文说明

这个仓库是 TaijiOS 全家桶试装包，不是所有组件的唯一主仓。它的用途是让用户快速安装、运行本地 demo、查看组件结构和安全说明。

最重要的入口:

- 第一次安装: [START_HERE.md](START_HERE.md)
- 组件清单: [MANIFEST.md](MANIFEST.md)
- API 安全边界: [SECURITY.md](SECURITY.md)

不要把本仓库里的历史原型、bundle 快照、官网源码和当前主开发仓混为一谈。对外说明时，本仓库只承担“试装包 / 分发入口 / 本地验证入口”的角色。

