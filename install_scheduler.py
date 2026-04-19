#!/usr/bin/env python3
"""
🎴 一键装 TaijiOS 心跳定时任务 · 跨平台

Windows: 注册 schtasks · 每天 08:00 跑 heartbeat.py
Mac/Linux: 打印 crontab 行, 用户自己 `crontab -e` 粘贴

用法:
    python install_scheduler.py           # 装 (默认每日 08:00)
    python install_scheduler.py --time 22:00   # 每日 22:00
    python install_scheduler.py --uninstall    # 卸载
"""
import sys, os, platform, subprocess, pathlib, argparse

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent
HEARTBEAT = ROOT / "heartbeat.py"
BAT = ROOT / "_taijios_heartbeat_tick.bat"
TASK = "TaijiOS_Heartbeat"


def windows_install(run_time: str):
    """创建 Windows schtasks 每日任务."""
    py = sys.executable
    BAT.write_text(
        f'@echo off\r\n'
        f'"{py}" "{HEARTBEAT}" >> "%USERPROFILE%\\.taijios\\heartbeat.out" 2>&1\r\n',
        encoding="utf-8"
    )
    r = subprocess.run(
        ["schtasks", "/create", "/tn", TASK,
         "/tr", str(BAT),
         "/sc", "daily", "/st", run_time, "/f"],
        capture_output=True, encoding="gbk", errors="replace"
    )
    if r.returncode == 0:
        print(f"✓ 已装 Windows schtasks '{TASK}' · 每日 {run_time}")
        print(f"  触发: {BAT}")
        print(f"  查看: schtasks /query /tn {TASK}")
        print(f"  手动跑一次: schtasks /run /tn {TASK}")
    else:
        print(f"✗ schtasks 失败 (rc={r.returncode})")
        print(r.stdout + r.stderr)


def windows_uninstall():
    r = subprocess.run(["schtasks", "/delete", "/tn", TASK, "/f"],
                       capture_output=True, encoding="gbk", errors="replace")
    print(r.stdout + r.stderr if r.returncode else f"✓ 已删除 '{TASK}'")
    if BAT.exists():
        BAT.unlink()


def unix_instructions(run_time: str):
    hh, mm = run_time.split(":")
    print("Linux/Mac 用 crontab 手动加一行:")
    print(f"  crontab -e   # 打开编辑器")
    print(f"  粘贴:")
    print(f"    {mm} {hh} * * * cd {ROOT} && {sys.executable} heartbeat.py >> ~/.taijios/heartbeat.out 2>&1")
    print()
    print("或直接跑常驻 daemon:")
    print(f"  nohup {sys.executable} {ROOT / 'heartbeat_daemon.py'} --interval 60 &")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", default="08:00", help="HH:MM · 默认 08:00")
    ap.add_argument("--uninstall", action="store_true")
    args = ap.parse_args()

    if platform.system() == "Windows":
        if args.uninstall:
            windows_uninstall()
        else:
            windows_install(args.time)
    else:
        if args.uninstall:
            print(f"Linux/Mac: crontab -e → 删掉含 '{HEARTBEAT}' 那行")
        else:
            unix_instructions(args.time)


if __name__ == "__main__":
    main()
