#!/usr/bin/env python3
"""
🎴 TaijiOS 自检 / 自动修 (doctor)

跑: python doctor.py            # 诊断 + 能修的自动修
    python doctor.py --dry      # 只诊断不改任何文件

10 项检查:
  1. Python 版本 ≥3.8
  2. 7 个 repo 目录齐全
  3. zhuge-skill 2 个 deps (requests/python-dotenv) 已装
  4. taijios-soul 已 pip install -e (editable)
  5. zhuge-skill/.env 存在
  6. .env 里 LLM_PROVIDER 设了
  7. LLM_PROVIDER 对应的 key 非空
  8. PYTHONIOENCODING (Windows 检查 cmd 会不会崩)
  9. ~/.taijios/ 可写
  10. Ollama 端口 (如果 LLM_PROVIDER=openai + localhost) 可达
"""
import sys, os, pathlib, subprocess, socket, shutil, platform, argparse

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent
ZHUGE = ROOT / "zhuge-skill"
SOUL = ROOT / "TaijiOS" / "taijios-soul"

G, Y, R, D, B, C, X = "\033[38;5;82m", "\033[38;5;226m", "\033[38;5;196m", "\033[2m", "\033[1m", "\033[38;5;51m", "\033[0m"

ISSUES = []        # (label, severity, hint, auto_fix or None)
FIXED = []


def ok(label):
    print(f"  {G}✓{X} {label}")


def warn(label, hint, fixer=None):
    print(f"  {Y}⚠{X} {label}  {D}· {hint}{X}")
    ISSUES.append((label, "warn", hint, fixer))


def fail(label, hint, fixer=None):
    print(f"  {R}✗{X} {label}  {D}· {hint}{X}")
    ISSUES.append((label, "fail", hint, fixer))


# ─── Checks ─────────────────────────────────────────────

def check_python():
    v = sys.version_info
    if (v.major, v.minor) >= (3, 8):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        fail(f"Python {v.major}.{v.minor} < 3.8", "升级 Python 到 3.8+")


def check_repos():
    needed = ["zhuge-skill", "TaijiOS", "TaijiOS-Lite", "zhuge-crystals",
              "self-improving-loop", "taijios-landing", "taiji"]
    missing = [r for r in needed if not (ROOT / r).exists()]
    if not missing:
        ok(f"7 个 repo 目录齐全")
    else:
        fail(f"缺目录: {missing}", "zip 解压不完整? 重下 bundle")


def check_deps_zhuge(dry=False):
    try:
        import requests, dotenv
        ok("zhuge-skill deps (requests + python-dotenv)")
    except ImportError as e:
        fix = None if dry else lambda: subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-r", str(ZHUGE / "requirements.txt")],
            check=False
        )
        fail(f"zhuge-skill deps 缺 ({e.name})", "自动修: pip install -r zhuge-skill/requirements.txt", fix)


def check_deps_soul(dry=False):
    try:
        sys.path.insert(0, str(SOUL / "src"))
        import taijios
        ok("taijios-soul (editable install)")
    except ImportError:
        fix = None if dry else lambda: subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-e", str(SOUL)],
            check=False
        )
        warn("taijios-soul 未 pip install -e", f"自动修: pip install -e {SOUL}", fix)


def check_env_exists(dry=False):
    env_f = ZHUGE / ".env"
    ex_f = ZHUGE / ".env.example"
    if env_f.exists():
        ok(f".env 存在 ({env_f})")
    elif ex_f.exists():
        fix = None if dry else lambda: shutil.copy(ex_f, env_f)
        warn(".env 不存在 (但 .env.example 在)", "自动修: cp .env.example .env", fix)
    else:
        fail(".env 和 .env.example 都不在", "bundle 损坏? 重下")


def _read_env():
    f = ZHUGE / ".env"
    if not f.exists():
        return {}
    out = {}
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"): continue
        if "=" in line:
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def check_llm_provider():
    env = _read_env()
    prov = env.get("LLM_PROVIDER", "").strip()
    if prov and prov.lower() != "none":
        ok(f"LLM_PROVIDER = {prov}")
    else:
        warn("LLM_PROVIDER 未设 (孔明亲笔不会出)", "编辑 .env 加 LLM_PROVIDER=deepseek")


def check_llm_key():
    env = _read_env()
    prov = env.get("LLM_PROVIDER", "").strip().lower()
    if not prov or prov == "none":
        return  # 上一检查已覆盖
    key_map = {"deepseek": "DEEPSEEK_API_KEY", "doubao": "DOUBAO_API_KEY",
               "kimi": "KIMI_API_KEY", "qwen": "QWEN_API_KEY",
               "zhipu": "ZHIPU_API_KEY", "yi": "YI_API_KEY",
               "openai": "OPENAI_API_KEY", "claude": "ANTHROPIC_API_KEY",
               "gemini": "GEMINI_API_KEY", "relay": "CLAUDE_RELAY_KEY"}
    needed = key_map.get(prov)
    if not needed:
        warn(f"LLM_PROVIDER={prov} 非标准 (可能自定义)", "跳过 key 检查")
        return
    val = env.get(needed, "").strip()
    if val:
        ok(f"{needed} 非空")
    else:
        fail(f"{needed} 是空的", f"编辑 .env 填入 LLM provider 的 key")


def check_encoding():
    if platform.system() != "Windows":
        ok(f"编码: {platform.system()} 无需设 PYTHONIOENCODING")
        return
    if os.environ.get("PYTHONIOENCODING", "").lower() == "utf-8":
        ok("PYTHONIOENCODING=utf-8 (Windows OK)")
    else:
        warn("Windows PYTHONIOENCODING 未设",
             "临时: set PYTHONIOENCODING=utf-8  |  永久: 系统环境变量里加")


def check_home_taijios(dry=False):
    home = pathlib.Path.home() / ".taijios"
    try:
        home.mkdir(parents=True, exist_ok=True)
        test = home / ".writetest"
        test.write_text("x", encoding="utf-8")
        test.unlink()
        ok(f"~/.taijios 可写")
    except Exception as e:
        fail(f"~/.taijios 不可写 ({e})", "检查权限或手动建目录")


def check_ollama_if_used():
    env = _read_env()
    prov = env.get("LLM_PROVIDER", "").lower()
    base = env.get("OPENAI_API_BASE", "")
    if not (prov == "openai" and "localhost" in base):
        return  # 没用 Ollama 就跳过
    port = 11434
    if ":" in base:
        try: port = int(base.rsplit(":", 1)[1].split("/")[0])
        except: pass
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect(("localhost", port))
        s.close()
        ok(f"Ollama 端口 {port} 可达")
    except Exception:
        fail(f"Ollama 端口 {port} 不通",
             "跑: ollama serve  (或启动 Ollama 程序)")


# ─── Main ─────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="TaijiOS 自检 / 自动修")
    ap.add_argument("--dry", action="store_true", help="只诊断不改任何文件")
    args = ap.parse_args()

    print(f"{C}╔════════════════════════════════════╗{X}")
    print(f"{C}║  {B}🎴 TaijiOS 自检 (doctor){X}{C}           ║{X}")
    print(f"{C}╚════════════════════════════════════╝{X}\n")

    print(f"{B}Running 10 checks...{X}\n")

    check_python()
    check_repos()
    check_deps_zhuge(args.dry)
    check_deps_soul(args.dry)
    check_env_exists(args.dry)
    check_llm_provider()
    check_llm_key()
    check_encoding()
    check_home_taijios(args.dry)
    check_ollama_if_used()

    # 自动修
    fixable = [(l, h, f) for (l, s, h, f) in ISSUES if f]
    if fixable and not args.dry:
        print(f"\n{Y}{B}自动修 {len(fixable)} 项:{X}")
        for label, hint, fixer in fixable:
            try:
                fixer()
                FIXED.append(label)
                print(f"  {G}✓ 已修{X} {label}")
            except Exception as e:
                print(f"  {R}✗ 修失败{X} {label}: {e}")

    # summary
    print()
    total = 10
    n_issues = len(ISSUES)
    if n_issues == 0:
        print(f"{G}{B}✅ 全绿 · {total}/{total} 通过 · 系统健康{X}")
        return 0
    print(f"{Y}发现 {n_issues} 个问题:{X}")
    for label, sev, hint, _ in ISSUES:
        color = R if sev == "fail" else Y
        print(f"  {color}[{sev}]{X} {label} · {D}{hint}{X}")
    if FIXED:
        print(f"\n{G}自动修复 {len(FIXED)} 项:{X} {', '.join(FIXED)}")
    # 还剩未解决
    remaining = [l for l, s, h, f in ISSUES if l not in FIXED]
    if remaining:
        print(f"\n{R}{B}还剩 {len(remaining)} 项需要手动:{X}")
        for lbl in remaining:
            print(f"  · {lbl}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
