#!/usr/bin/env python3
"""
🎴 TaijiOS 心跳 daemon · 常驻 loop 版 (方案 C)

每 N 分钟调一次 heartbeat.py · 让 soul 持续"夜读" + 拉晶体池.

用法:
    python heartbeat_daemon.py                    # 默认每 60 min 跑一次
    python heartbeat_daemon.py --interval 30      # 每 30 分钟
    python heartbeat_daemon.py --once             # 跑一次就退 (测试用)

后台长跑建议:
  Windows: pythonw heartbeat_daemon.py   (无控制台)
           或放到 Startup 文件夹开机自启
  Linux/Mac: nohup python heartbeat_daemon.py &
"""
import sys, os, time, pathlib, subprocess, signal, argparse

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent
HEARTBEAT = ROOT / "heartbeat.py"
STOP = False


def _sig(sig, frame):
    global STOP
    print("\n[daemon] 收到信号, 优雅退出中...")
    STOP = True


signal.signal(signal.SIGINT, _sig)
if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, _sig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=60, help="分钟 · 默认 60")
    ap.add_argument("--once", action="store_true", help="跑一次就退")
    args = ap.parse_args()

    print(f"🎴 TaijiOS heartbeat daemon 启动 · interval={args.interval} min")
    print(f"   heartbeat: {HEARTBEAT}")
    print(f"   log: ~/.taijios/heartbeat.log")
    print(f"   Ctrl+C 退出")

    tick_count = 0
    while not STOP:
        tick_count += 1
        print(f"\n── tick {tick_count} ──────────────────────")
        try:
            subprocess.run(
                [sys.executable, str(HEARTBEAT)],
                check=False, encoding="utf-8", errors="replace"
            )
        except Exception as e:
            print(f"[daemon] tick {tick_count} FAIL: {e}")
        if args.once:
            break
        # 睡 · 每秒检查 STOP 信号
        for _ in range(args.interval * 60):
            if STOP:
                break
            time.sleep(1)

    print(f"[daemon] 已退出 · 共 {tick_count} 次 tick")


if __name__ == "__main__":
    main()
