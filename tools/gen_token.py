#!/usr/bin/env python3
"""
gen_token · 生成强 API token (32 byte hex = 64 char)

用法:
    python tools/gen_token.py             # 打印一个 token
    python tools/gen_token.py --bytes 48  # 自定义长度
    python tools/gen_token.py --env       # 输出 export TAIJIOS_API_TOKEN=... 行
    python tools/gen_token.py --setx      # 输出 Windows setx ...

设计:
    使用 secrets.token_hex (CSPRNG) · 不依赖第三方
    默认 32 byte = 256 bit 熵 · 远超 api_server WEAK_TOKEN_PATTERNS 阈值
"""
from __future__ import annotations
import argparse
import secrets
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else "")
    ap.add_argument("--bytes", type=int, default=32, help="token entropy bytes (default 32 = 256 bits)")
    ap.add_argument("--env", action="store_true", help="output as 'export TAIJIOS_API_TOKEN=...' line")
    ap.add_argument("--setx", action="store_true", help="output as Windows 'setx TAIJIOS_API_TOKEN ...' line")
    args = ap.parse_args()

    if args.bytes < 16:
        print("X refusing to generate token with < 16 bytes entropy (security)", file=sys.stderr)
        sys.exit(1)

    tok = secrets.token_hex(args.bytes)
    if args.env:
        print(f"export TAIJIOS_API_TOKEN={tok}")
    elif args.setx:
        print(f"setx TAIJIOS_API_TOKEN {tok}")
    else:
        print(tok)


if __name__ == "__main__":
    main()
