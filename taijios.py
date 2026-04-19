#!/usr/bin/env python3
"""
🎴 TaijiOS 一键启动器 · v1.1.1 bundle

用法:
    python taijios.py                        # 交互菜单
    python taijios.py predict "Inter vs Cagliari"  # 足球预测
    python taijios.py soul                   # 灵魂对话
    python taijios.py sync                   # 拉共享晶体池
    python taijios.py status                 # 全系统状态
    python taijios.py install                # 重装所有依赖

功能一键接:
  [1] zhuge-skill 足球预测 (64 卦 + 孔明亲笔)
  [2] taijios-soul 灵魂对话 (意图/关系/记忆)
  [3] zhuge-crystals 晶体池同步
  [4] 全系统状态检查
  [5] 装 / 重装依赖
"""
import sys, os, subprocess, pathlib, shutil

# ─── 跨平台编码处理 (Windows 必须) ──────────────────────
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent
ZHUGE = ROOT / "zhuge-skill"
SOUL = ROOT / "TaijiOS" / "taijios-soul"


# ─── 美化输出 ──────────────────────────────────────────
C = "\033[38;5;51m"  # cyan
P = "\033[38;5;201m"  # magenta
G = "\033[38;5;82m"  # green
Y = "\033[38;5;226m"  # yellow
R = "\033[38;5;196m"  # red
D = "\033[2m"  # dim
B = "\033[1m"  # bold
X = "\033[0m"  # reset


def banner():
    print(f"{C}╔══════════════════════════════════════════╗{X}")
    print(f"{C}║  {B}{P}🎴 TaijiOS 一键启动 · v1.1.1{X}{C}            ║{X}")
    print(f"{C}║  {D}孔明 · 64 卦 · 晶体池 · 五虎列阵{X}{C}          ║{X}")
    print(f"{C}╚══════════════════════════════════════════╝{X}")


def run(cmd, cwd=None, check=True):
    """Run subprocess with live output."""
    if isinstance(cmd, str):
        cmd = cmd.split()
    r = subprocess.run(cmd, cwd=cwd, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        print(f"{R}✗ command failed: {' '.join(cmd)}{X}")
        return False
    return True


def ensure_env():
    """Check .env present in zhuge-skill. If not, guide user."""
    env_file = ZHUGE / ".env"
    example = ZHUGE / ".env.example"
    if not env_file.exists():
        if example.exists():
            print(f"{Y}⚠  zhuge-skill/.env 不存在, 从模板复制...{X}")
            shutil.copy(example, env_file)
            print(f"{G}✓ 已复制 {example} → {env_file}{X}")
            print(f"{Y}⚠  打开 {env_file} 填入 LLM_PROVIDER + 一个 LLM 的 API key.{X}")
            print(f"{D}   至少 2 行必填: LLM_PROVIDER=deepseek  +  DEEPSEEK_API_KEY=sk-xxx{X}")
            print(f"{D}   DeepSeek 免费注册领 ¥5: https://platform.deepseek.com/{X}")
            return False
        print(f"{R}✗ zhuge-skill/.env 和 .env.example 都不存在, 解包是否完整?{X}")
        return False
    # 粗检查 LLM_PROVIDER
    txt = env_file.read_text(encoding="utf-8", errors="replace")
    has_provider = any(
        line.strip().startswith("LLM_PROVIDER=") and "=" in line and line.strip().split("=", 1)[1].strip() and not line.strip().startswith("#")
        for line in txt.splitlines()
    )
    if not has_provider:
        print(f"{Y}⚠  .env 里没设 LLM_PROVIDER · 孔明亲笔将不会出.{X}")
        print(f"{D}   加一行: LLM_PROVIDER=deepseek (或 kimi/qwen/claude 等){X}")
    return True


def cmd_install():
    banner()
    print(f"{G}[1/2] 装 zhuge-skill 依赖...{X}")
    if (ZHUGE / "requirements.txt").exists():
        run([sys.executable, "-m", "pip", "install", "-q", "-r", str(ZHUGE / "requirements.txt")])
    print(f"{G}[2/2] 装 taijios-soul (editable)...{X}")
    if (SOUL / "pyproject.toml").exists():
        run([sys.executable, "-m", "pip", "install", "-q", "-e", str(SOUL)])
    print(f"\n{G}✓ 依赖装好. 现在可以 `python taijios.py` 开菜单.{X}")


def cmd_predict(match: str = ""):
    banner()
    if not ensure_env():
        return
    if not match:
        match = input(f"{C}输入对阵 (如 'Inter vs Cagliari'): {X}").strip()
    if not match:
        return
    print(f"{G}→ 调 zhuge-skill · {match}{X}\n")
    run([sys.executable, str(ZHUGE / "scripts" / "predict.py"), match], cwd=str(ZHUGE), check=False)


def cmd_soul():
    banner()
    print(f"{G}→ 启动 taijios-soul quickstart · 5 轮对话 demo{X}\n")
    if not (SOUL / "quickstart.py").exists():
        print(f"{R}✗ TaijiOS/taijios-soul/quickstart.py 不存在{X}")
        return
    run([sys.executable, str(SOUL / "quickstart.py")], cwd=str(SOUL), check=False)


def cmd_sync():
    banner()
    print(f"{G}→ 拉公共晶体池 (HTTP GET · 只读 · 不传任何本地数据){X}\n")
    run([sys.executable, str(ZHUGE / "scripts" / "sync.py"), "pull"], cwd=str(ZHUGE), check=False)


def cmd_status():
    banner()
    print(f"{B}系统状态:{X}")
    # Python 版本
    print(f"  {D}Python:{X}       {sys.version.split()[0]}")
    # 7 repo 存在
    repos = ["zhuge-skill", "TaijiOS", "TaijiOS-Lite", "zhuge-crystals",
             "self-improving-loop", "taijios-landing", "taiji"]
    for r in repos:
        exists = (ROOT / r).exists()
        mark = f"{G}✓{X}" if exists else f"{R}✗{X}"
        print(f"  {mark} {r}")
    # .env
    env_file = ZHUGE / ".env"
    if env_file.exists():
        txt = env_file.read_text(encoding="utf-8", errors="replace")
        has_provider = "LLM_PROVIDER=" in txt and not all(
            l.strip().startswith("#") for l in txt.splitlines() if "LLM_PROVIDER=" in l
        )
        providers_with_key = [k.split("_")[0].lower() for k in
                              ["DEEPSEEK_API_KEY", "DOUBAO_API_KEY", "KIMI_API_KEY",
                               "QWEN_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
                              if any(l.strip().startswith(k + "=") and "=" in l and
                                     l.strip().split("=", 1)[1].strip() and
                                     not l.strip().startswith("#") for l in txt.splitlines())]
        print(f"  {G if has_provider else Y}{'✓' if has_provider else '⚠'}{X} .env LLM_PROVIDER 设了" if has_provider
              else f"  {Y}⚠{X} .env 没设 LLM_PROVIDER")
        print(f"  {G if providers_with_key else Y}{'✓' if providers_with_key else '⚠'}{X} key 齐全: {providers_with_key or 'none'}")
        # API-Football
        has_api_foot = any(l.strip().startswith("API_FOOTBALL_KEY=") and
                           l.strip().split("=", 1)[1].strip() and not l.strip().startswith("#")
                           for l in txt.splitlines())
        print(f"  {G if has_api_foot else D}{'✓' if has_api_foot else '○'}{X} API-Football key: {'ok' if has_api_foot else '(没配 · 走 DEMO)'}")
    else:
        print(f"  {R}✗{X} zhuge-skill/.env 不存在")
    # 晶体池
    cl = ZHUGE / "data" / "crystals_local.jsonl"
    cs = ZHUGE / "data" / "crystals_shared.jsonl"
    exp = ZHUGE / "data" / "experience.jsonl"
    print(f"  {D}experience:{X}   {len(exp.read_text(encoding='utf-8').splitlines()) if exp.exists() else 0} 条")
    print(f"  {D}local 晶体:{X}   {len(cl.read_text(encoding='utf-8').splitlines()) if cl.exists() else 0} 个")
    print(f"  {D}shared 晶体:{X}  {len(cs.read_text(encoding='utf-8').splitlines()) if cs.exists() else 0} 个")


def cmd_doctor():
    banner()
    run([sys.executable, str(ROOT / "doctor.py")], check=False)


def cmd_info():
    """全功能一览 + 运行状态 · 一页看全."""
    banner()
    import platform, datetime, pathlib
    home = pathlib.Path.home() / ".taijios"
    env_f = ZHUGE / ".env"
    env_txt = env_f.read_text(encoding="utf-8") if env_f.exists() else ""

    print(f"\n{B}━━━━━━━━━━━━━━━━━━━━━ 核心功能 (装完即可用) ━━━━━━━━━━━━━━━━━━━━━{X}")
    features = [
        ("足球推演", "python taijios.py predict 'A vs B'",
         "zhuge-skill · 6 爻 + 64 卦 + 孔明亲笔",
         lambda: "✓" if any(l.strip().startswith("DEEPSEEK_API_KEY=") and l.strip().split("=",1)[1].strip() and not l.strip().startswith("#") for l in env_txt.splitlines()) else "⚠ 无 LLM key · 走 DEMO"),
        ("灵魂对话", "python taijios.py soul",
         "taijios-soul · 意图/关系/五将军/记忆",
         lambda: "✓"),
        ("智能对话 · 自动路由 ⭐", "python taijios.py brain",
         "Soul × zhuge · 闲聊→Soul · 对阵→自动调 zhuge · crisis→情绪",
         lambda: "✓"),
        ("晶体池同步 (只读)", "python taijios.py sync",
         "zhuge-crystals · HTTP GET 单向 · 不上传",
         lambda: "✓"),
        ("共享经验 · 脱敏 queue", "python taijios.py share",
         "本地生成 GitHub issue body · 用户自行 PR",
         lambda: "✓"),
    ]
    for name, cmd, desc, state_fn in features:
        print(f"  {G}{state_fn()}{X} {B}{name}{X}")
        print(f"     {D}{cmd}{X}")
        print(f"     {D}  → {desc}{X}")

    print(f"\n{B}━━━━━━━━━━━━━━━━━━━━━ 自动化 (后台不用管) ━━━━━━━━━━━━━━━━━━━━━{X}")
    # schtasks 状态
    import subprocess
    sch_installed = False
    sch_next = None
    if platform.system() == "Windows":
        r = subprocess.run(["schtasks", "/query", "/tn", "TaijiOS_Heartbeat", "/fo", "LIST", "/v"],
                          capture_output=True, encoding="gbk", errors="replace")
        if r.returncode == 0:
            sch_installed = True
            for line in r.stdout.splitlines():
                low = line.lower()
                if "下次运行时间" in line or "next run time" in low:
                    sch_next = line.strip()

    print(f"  {G if sch_installed else Y}{'✓' if sch_installed else '⚠'}{X} {B}定时任务 (schtasks){X}")
    if sch_installed:
        print(f"     {D}{sch_next or '装上了 · 具体时间 schtasks /query /tn TaijiOS_Heartbeat{X}'}{X}")
    else:
        print(f"     {Y}未装 · 跑 python install_scheduler.py{X}")
    print(f"     {D}手动: python taijios.py heartbeat (5 步 tick){X}")

    # 心跳日志状态
    log = home / "heartbeat.log"
    if log.exists():
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        last = lines[-1] if lines else ""
        age_hr = "?"
        if last and "[" in last:
            try:
                ts = last.split("]")[0].lstrip("[")
                last_dt = datetime.datetime.fromisoformat(ts)
                age_hr = f"{(datetime.datetime.now() - last_dt).total_seconds()/3600:.1f}"
            except Exception:
                pass
        alive = age_hr != "?" and float(age_hr) < 25
        print(f"  {G if alive else Y}{'✓' if alive else '⚠'}{X} {B}心跳日志{X} ({len(lines)} 行 · 最近 {age_hr}h 前)")
        print(f"     {D}文件: {log}{X}")
    else:
        print(f"  {Y}○{X} {B}心跳日志{X} · 还没 tick 过 · 跑 python heartbeat.py")

    print(f"\n{B}━━━━━━━━━━━━━━━━━━━━━ 对外集成 (开发者用) ━━━━━━━━━━━━━━━━━━━━━{X}")
    # MCP
    try:
        import mcp  # noqa
        mcp_ok = True
    except ImportError:
        mcp_ok = False
    print(f"  {G if mcp_ok else Y}{'✓' if mcp_ok else '⚠'}{X} {B}MCP Server{X} (Trae/Cursor/Claude Desktop)")
    print(f"     {D}启: 不用 · 配 MCP config 指向 {ROOT / 'mcp_server.py'}{X}")
    if not mcp_ok:
        print(f"     {Y}装: pip install mcp>=1.0.0{X}")

    # FastAPI
    try:
        import fastapi  # noqa
        fa_ok = True
    except ImportError:
        fa_ok = False
    print(f"  {G if fa_ok else Y}{'✓' if fa_ok else '⚠'}{X} {B}HTTP API Server{X} (8 endpoints · Swagger)")
    print(f"     {D}启: python taijios.py api  → http://127.0.0.1:8787/docs{X}")
    if not fa_ok:
        print(f"     {Y}装: pip install fastapi 'uvicorn[standard]' pydantic{X}")

    print(f"\n{B}━━━━━━━━━━━━━━━━━━━━━ 诊断 (问题排查) ━━━━━━━━━━━━━━━━━━━━━{X}")
    print(f"  {C}python taijios.py doctor{X}         {D}10 项自检 + 能修的自动修{X}")
    print(f"  {C}python taijios.py daemon-status{X}  {D}schtasks 装没装 + 心跳日志最后 N 行{X}")
    print(f"  {C}python taijios.py status{X}         {D}7 repo + .env + 晶体数{X}")
    print(f"  {C}python uninstall.py{X}              {D}一键撤 · 清 schtasks + ~/.taijios + .env{X}")


def cmd_brain():
    """智能对话 · Soul × zhuge 自动路由."""
    banner()
    run([sys.executable, str(ROOT / "brain.py")], check=False)


def cmd_speak():
    """TTS · 孔明开口说话 (edge-tts 免费微软 Edge 声音)."""
    banner()
    print(f"{G}→ 孔明开口 · TTS 试用{X}")
    text = input(f"{C}要孔明说什么? (回车跳过): {X}").strip()
    if not text:
        text = "臣观天象, 察地利, 此战可图"
    print(f"{D}  合成并播放: {text}{X}")
    run([sys.executable, str(ROOT / "tts.py"), "--text", text], check=False)


def cmd_uninstall():
    banner()
    run([sys.executable, str(ROOT / "uninstall.py")], check=False)


def cmd_api():
    """启 FastAPI · 打开 Swagger UI · 给开发者朋友 HTTP 接口."""
    banner()
    print(f"{G}→ 启动 TaijiOS API Server · http://127.0.0.1:8787/docs{X}")
    print(f"{D}  首次: pip install fastapi 'uvicorn[standard]' pydantic{X}")
    print(f"{D}  Ctrl+C 退出{X}\n")
    # 尝试自动开浏览器
    try:
        import webbrowser, threading, time
        def _open():
            time.sleep(2.5)
            webbrowser.open("http://127.0.0.1:8787/docs")
        threading.Thread(target=_open, daemon=True).start()
    except Exception:
        pass
    run([sys.executable, str(ROOT / "api_server.py")], check=False)


def cmd_daemon_status():
    """看后台定时任务 + 最近 heartbeat 日志."""
    banner()
    import platform, datetime, pathlib
    print(f"{B}后台运行状态:{X}\n")

    # 1. schtasks 或 cron
    if platform.system() == "Windows":
        r = subprocess.run(
            ["schtasks", "/query", "/tn", "TaijiOS_Heartbeat", "/fo", "LIST", "/v"],
            capture_output=True, encoding="gbk", errors="replace"
        )
        if r.returncode == 0:
            # 摘关键 3 行
            for line in r.stdout.splitlines():
                low = line.lower()
                if any(k in low for k in ["任务名", "任务状态", "上次运行时间", "下次运行时间",
                                           "taskname", "status", "last run", "next run"]):
                    print(f"  {G}✓{X} {line.strip()}")
            print(f"\n  {D}手动触发: schtasks /run /tn TaijiOS_Heartbeat{X}")
            print(f"  {D}删: schtasks /delete /tn TaijiOS_Heartbeat /f{X}")
        else:
            print(f"  {Y}⚠ schtasks 未装 · 跑 python install_scheduler.py{X}")
    else:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        has = "heartbeat.py" in (r.stdout or "")
        print(f"  {'✓' if has else '⚠'} crontab 里 heartbeat: {'已装' if has else '未装'}")

    # 2. heartbeat.log 最近 N 行
    log = pathlib.Path.home() / ".taijios" / "heartbeat.log"
    print(f"\n{B}最近 heartbeat 日志:{X} ({log})")
    if log.exists():
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        print(f"  共 {len(lines)} 行 · 最后 {min(8, len(lines))} 行:\n")
        for line in lines[-8:]:
            print(f"  {D}{line}{X}")
        # 判断最近是否正常运行
        if lines:
            last = lines[-1]
            try:
                ts = last.split("]")[0].lstrip("[")
                last_dt = datetime.datetime.fromisoformat(ts)
                age_hr = (datetime.datetime.now() - last_dt).total_seconds() / 3600
                if age_hr < 25:
                    print(f"\n  {G}✓ 最近 {age_hr:.1f} 小时前有 tick · daemon 活着{X}")
                elif age_hr < 48:
                    print(f"\n  {Y}⚠ {age_hr:.1f} 小时前最后一次 · 可能没跑{X}")
                else:
                    print(f"\n  {R}✗ {age_hr:.1f} 小时未 tick · 后台可能挂了{X}")
            except Exception:
                pass
    else:
        print(f"  {Y}⚠ 日志不存在 · 还没 tick 过 · 跑 python heartbeat.py 手动试{X}")

    # 3. share queue
    q = pathlib.Path.home() / ".taijios" / "share_queue"
    if q.exists():
        files = list(q.glob("*.jsonl"))
        print(f"\n  {B}共享队列:{X} {len(files)} 批待审")


def cmd_share():
    """列 share queue + 生成 GitHub issue body 给用户 copy 贡献."""
    banner()
    import json as _json
    queue_dir = pathlib.Path.home() / ".taijios" / "share_queue"
    if not queue_dir.exists() or not any(queue_dir.iterdir()):
        print(f"{Y}share queue 空 · 还没累积到可分享的晶体 (需先有 ≥3 条 hit 经验){X}")
        return
    files = sorted(queue_dir.glob("*.jsonl"))
    print(f"{G}queue: {len(files)} 个 batch{X}\n")
    all_crystals = []
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    all_crystals.append(_json.loads(line))
                except Exception:
                    pass
    print(f"{B}{len(all_crystals)} 个已脱敏晶体 · 贡献 GitHub issue 模板:{X}")
    print(f"\n{D}--- 复制下面 → 发到 https://github.com/yangfei222666-9/zhuge-crystals/issues ---{X}\n")
    print(f"**标题**: 贡献 {len(all_crystals)} 个晶体")
    print(f"\n```json")
    for c in all_crystals[:5]:
        print(_json.dumps(c, ensure_ascii=False))
    if len(all_crystals) > 5:
        print(f"... ({len(all_crystals) - 5} 个更多, 全部见: {queue_dir})")
    print(f"```")
    print(f"\n{D}--- end ---{X}")


def cmd_heartbeat():
    banner()
    print(f"{G}→ 手动跑一次 heartbeat (soul 夜读 + 晶体 sync){X}\n")
    run([sys.executable, str(ROOT / "heartbeat.py")], check=False)


def cmd_auto_install():
    banner()
    print(f"{G}→ 装定时任务 (Windows schtasks / Linux cron){X}\n")
    run([sys.executable, str(ROOT / "install_scheduler.py")], check=False)
    print(f"\n{Y}💡 装完后 soul 每天 08:00 自动 tick · 看 ~/.taijios/heartbeat.log{X}")


def menu():
    banner()
    print()
    print(f"  {B}[1]{X} 足球预测 (zhuge-skill)")
    print(f"  {B}[2]{X} 灵魂对话 (taijios-soul)")
    print(f"  {B}[3]{X} 拉共享晶体池 (zhuge-crystals)")
    print(f"  {B}[4]{X} 全系统状态")
    print(f"  {B}[5]{X} 装 / 重装依赖")
    print(f"  {B}[6]{X} 手动跑一次心跳 (5 步: soul+回传+结晶+待审+同步)")
    print(f"  {B}[7]{X} 装自动化 · 每日自成长 {Y}⭐{X}")
    print(f"  {B}[8]{X} 共享经验 (列 queue · 生成 GitHub issue body)")
    print(f"  {B}[9]{X} 🩺 自检 / 自动修 (doctor · 10 项)")
    print(f"  {B}[0]{X} 🔍 查后台运行状态 (schtasks + 日志)")
    print(f"  {B}[a]{X} 🌐 启 API Server · Swagger UI (给开发者朋友 HTTP 接口)")
    print(f"  {B}[b]{X} 🧠 智能对话 · Soul × zhuge × 起卦 自动路由 {Y}⭐{X}")
    print(f"  {B}[s]{X} 🔊 孔明开口 · TTS 语音 (edge-tts 免费)")
    print(f"  {B}[i]{X} 📋 全功能一览 + 运行状态")
    print(f"  {D}  (Ctrl+C 随时退出){X}")
    print()
    try:
        choice = input(f"{C}选择: {X}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    actions = {
        "1": cmd_predict, "2": cmd_soul, "3": cmd_sync,
        "4": cmd_status, "5": cmd_install,
        "6": cmd_heartbeat, "7": cmd_auto_install, "8": cmd_share,
        "9": cmd_doctor, "0": cmd_daemon_status, "a": cmd_api,
        "b": cmd_brain, "i": cmd_info,
    }
    if choice in actions:
        actions[choice]()
    elif choice:  # 只有输了但不识别的才报 · 空回车直接 loop
        print(f"{R}✗ 未知选项: {choice}{X}")
    return True  # 继续 loop


def main():
    args = sys.argv[1:]
    if not args:
        # 自动链接上 · 选完一个功能自动回菜单 · Ctrl+C 退
        try:
            while menu():
                print(f"\n{D}────────── 回到菜单 ──────────{X}\n")
        except KeyboardInterrupt:
            print(f"\n{Y}再见{X}")
        return
    cmd = args[0].lower()
    rest = args[1:]
    if cmd in ("predict", "p"):
        cmd_predict(" ".join(rest))
    elif cmd in ("soul", "s"):
        cmd_soul()
    elif cmd in ("sync",):
        cmd_sync()
    elif cmd in ("status", "st"):
        cmd_status()
    elif cmd in ("install", "i", "deps"):
        cmd_install()
    elif cmd in ("share", "contribute"):
        cmd_share()
    elif cmd in ("heartbeat", "hb", "tick"):
        cmd_heartbeat()
    elif cmd in ("auto", "scheduler"):
        cmd_auto_install()
    elif cmd in ("doctor", "check", "diagnose"):
        cmd_doctor()
    elif cmd in ("daemon-status", "running", "ps"):
        cmd_daemon_status()
    elif cmd in ("api", "server", "swagger"):
        cmd_api()
    elif cmd in ("brain", "chat", "smart"):
        cmd_brain()
    elif cmd in ("uninstall", "remove"):
        cmd_uninstall()
    elif cmd in ("info", "功能"):
        cmd_info()
    elif cmd in ("-h", "--help", "help"):
        print(__doc__)
    else:
        print(f"{R}未知命令: {cmd}{X}. 跑 `python taijios.py --help` 看用法.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + Y + "中断" + X)
    except Exception as e:
        print(f"{R}✗ 异常: {type(e).__name__}: {e}{X}")
        raise
