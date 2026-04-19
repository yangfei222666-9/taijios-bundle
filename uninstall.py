#!/usr/bin/env python3
"""
🎴 TaijiOS 一键卸载

撤销 setup.py 装的东西 · 不删你自己的 zhuge-skill/TaijiOS 源码.

撤什么:
  1. 删 Windows schtasks (TaijiOS_Heartbeat)
  2. 删 ~/.taijios/ 目录 (soul 记忆 / 心跳日志 / 共享队列)
  3. pip uninstall taijios-soul (editable)
  4. 删 zhuge-skill/.env (敏感) + data/experience.jsonl (可选)

不删 · 留给你的:
  - 本 bundle 目录本身 (你要完全删 · 自己删整个文件夹)
  - zhuge-skill/.env.example 模板
  - pip 装的 mcp/fastapi/requests 等共享 deps (删了可能影响其他项目)

用法:
    python uninstall.py             # 交互
    python uninstall.py --yes       # 无确认 · 全撤
    python uninstall.py --keep-env  # 保留 .env (只撤 schtasks + ~/.taijios)
"""
import sys, os, subprocess, pathlib, platform, shutil, argparse

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent
ZHUGE = ROOT / "zhuge-skill"
SOUL = ROOT / "TaijiOS" / "taijios-soul"
HOME_TAIJIOS = pathlib.Path.home() / ".taijios"

G, Y, R, D, B, C, X = "\033[38;5;82m", "\033[38;5;226m", "\033[38;5;196m", "\033[2m", "\033[1m", "\033[38;5;51m", "\033[0m"


def ok(m): print(f"  {G}✓{X} {m}")
def warn(m): print(f"  {Y}⚠{X} {m}")
def fail(m): print(f"  {R}✗{X} {m}")


def uninstall_schtasks():
    print(f"\n{B}[1/4]{X} 撤销 Windows 定时任务")
    if platform.system() != "Windows":
        ok("非 Windows · 跳过 (Linux/Mac crontab 需你手动 crontab -e 删含 heartbeat.py 那行)")
        return
    r = subprocess.run(["schtasks", "/delete", "/tn", "TaijiOS_Heartbeat", "/f"],
                       capture_output=True, encoding="gbk", errors="replace")
    if r.returncode == 0:
        ok("已删 TaijiOS_Heartbeat 定时任务")
    else:
        warn(f"schtasks 删失败或不存在 · {r.stdout + r.stderr}")


def delete_home_taijios(yes: bool):
    print(f"\n{B}[2/4]{X} 删 ~/.taijios/ (soul 记忆 + 心跳日志 + 共享队列)")
    if not HOME_TAIJIOS.exists():
        ok("不存在 · 无需删")
        return
    size = sum(f.stat().st_size for f in HOME_TAIJIOS.rglob("*") if f.is_file())
    print(f"  目录大小: {size/1024:.1f} KB")
    if not yes:
        c = input(f"  {Y}确认删? [y/N]: {X}").strip().lower()
        if c != "y":
            warn("跳过 · 保留数据")
            return
    try:
        shutil.rmtree(HOME_TAIJIOS)
        ok(f"已删 {HOME_TAIJIOS}")
    except Exception as e:
        fail(f"删失败: {e}")


def uninstall_soul_pkg():
    print(f"\n{B}[3/4]{X} pip uninstall taijios-soul")
    r = subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "taijios-soul"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode == 0 and "Successfully uninstalled" in (r.stdout or ""):
        ok("taijios-soul 已卸载")
    else:
        warn("pip uninstall 无效果 (可能本来就没装)")


def delete_env(yes: bool, keep: bool):
    print(f"\n{B}[4/4]{X} 删 zhuge-skill/.env (敏感 · 防 key 泄漏)")
    if keep:
        ok("按 --keep-env 跳过")
        return
    env_f = ZHUGE / ".env"
    exp_f = ZHUGE / "data" / "experience.jsonl"
    if env_f.exists():
        if not yes:
            c = input(f"  删 .env (含 API key)? [Y/n]: ").strip().lower() or "y"
            if c != "y":
                warn("保留 .env")
            else:
                env_f.unlink()
                ok("已删 zhuge-skill/.env")
        else:
            env_f.unlink()
            ok("已删 zhuge-skill/.env")
    else:
        ok(".env 不存在")
    if exp_f.exists():
        if not yes:
            c = input(f"  删 experience.jsonl (你的预测历史)? [y/N]: ").strip().lower()
            if c == "y":
                exp_f.unlink()
                ok("已删 experience.jsonl")
            else:
                warn("保留预测历史")


def main():
    ap = argparse.ArgumentParser(description="TaijiOS 一键卸载")
    ap.add_argument("--yes", action="store_true", help="无确认 · 全撤")
    ap.add_argument("--keep-env", action="store_true", help="保留 .env (不删 key)")
    args = ap.parse_args()

    print(f"{C}╔════════════════════════════════════╗{X}")
    print(f"{C}║  {B}🎴 TaijiOS 卸载{X}{C}                     ║{X}")
    print(f"{C}╚════════════════════════════════════╝{X}")

    if not args.yes:
        print(f"\n{Y}将撤销:{X}")
        print(f"  1. Windows 定时任务 TaijiOS_Heartbeat")
        print(f"  2. ~/.taijios/ 目录 (soul 记忆 · 心跳日志)")
        print(f"  3. taijios-soul pip 包 (editable)")
        print(f"  4. zhuge-skill/.env (API key)")
        print(f"\n{Y}{B}不会删:{X} bundle 文件夹本身 · 共享 deps (mcp/fastapi 等)")
        c = input(f"\n{C}继续卸载? [y/N]: {X}").strip().lower()
        if c != "y":
            print(f"{Y}取消{X}")
            return

    uninstall_schtasks()
    delete_home_taijios(args.yes)
    uninstall_soul_pkg()
    delete_env(args.yes, args.keep_env)

    print(f"\n{G}{B}✅ 卸载完成{X}\n")
    print(f"{D}要完全删 · 手动 rm -rf 本 bundle 目录即可.{X}")


if __name__ == "__main__":
    main()
