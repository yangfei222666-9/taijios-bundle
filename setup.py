#!/usr/bin/env python3
"""
🎴 TaijiOS 一键安装器 · 真·一条命令全装完

用法:
    python setup.py                # 完整交互安装
    python setup.py --unattended   # 无人值守 (从 env var 读 key)
    python setup.py --no-auto      # 不装定时任务

流程 (6 步 · 全自动):
  1. 检查 Python 版本 (≥3.8)
  2. pip install zhuge-skill + taijios-soul deps
  3. 交互引导填 DeepSeek key (可跳 · 跳了走 DEMO)
  4. 写 .env
  5. (可选) 装 Windows schtasks / Linux cron · 每日 08:00 自动 heartbeat
  6. 跑一次 heartbeat 验证端到端

装完直接: python taijios.py
"""
import sys, os, subprocess, pathlib, platform, argparse, shutil

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent
ZHUGE = ROOT / "zhuge-skill"
SOUL = ROOT / "TaijiOS" / "taijios-soul"

C = "\033[38;5;51m"
G = "\033[38;5;82m"
Y = "\033[38;5;226m"
R = "\033[38;5;196m"
D = "\033[2m"
B = "\033[1m"
X = "\033[0m"


def banner():
    print(f"{C}╔════════════════════════════════════╗{X}")
    print(f"{C}║  {B}🎴 TaijiOS 一键安装 v1.1.1{X}{C}         ║{X}")
    print(f"{C}╚════════════════════════════════════╝{X}")


def step(n, msg):
    print(f"\n{B}{C}[{n}/6]{X} {msg}")


def ok(msg):
    print(f"  {G}✓{X} {msg}")


def warn(msg):
    print(f"  {Y}⚠{X} {msg}")


def fail(msg):
    print(f"  {R}✗{X} {msg}")


def run(cmd, **kw):
    return subprocess.run(cmd, encoding="utf-8", errors="replace", **kw)


def check_python():
    step(1, "检查 Python 版本")
    v = sys.version_info
    if (v.major, v.minor) < (3, 8):
        fail(f"Python {v.major}.{v.minor} 过老, 需 ≥ 3.8")
        sys.exit(1)
    ok(f"Python {v.major}.{v.minor}.{v.micro}")


def install_deps():
    step(2, "装依赖 (zhuge-skill + taijios-soul + 高级: MCP + FastAPI)")
    req = ZHUGE / "requirements.txt"
    if req.exists():
        r = run([sys.executable, "-m", "pip", "install", "-q", "-r", str(req)])
        if r.returncode == 0:
            ok("zhuge-skill deps (requests + python-dotenv)")
        else:
            warn("pip install 有警告, 但可能 OK")
    if (SOUL / "pyproject.toml").exists():
        r = run([sys.executable, "-m", "pip", "install", "-q", "-e", str(SOUL)])
        if r.returncode == 0:
            ok("taijios-soul (editable install)")
        else:
            warn("soul install 有警告")
    # 高级集成 · 一次性装好 · 免朋友后面踩 "缺 mcp/fastapi/edge-tts"
    r = run([sys.executable, "-m", "pip", "install", "-q",
             "mcp>=1.0.0", "fastapi", "uvicorn[standard]", "pydantic", "edge-tts"])
    if r.returncode == 0:
        ok("高级: mcp + fastapi + uvicorn + pydantic + edge-tts (MCP/API/语音 全可用)")
    else:
        warn("高级 deps 有问题 · MCP/API/TTS 可能不可用 · 但核心功能 OK")


def configure_env(unattended: bool):
    step(3, "配 zhuge-skill/.env (LLM key)")
    env_file = ZHUGE / ".env"
    example = ZHUGE / ".env.example"

    if env_file.exists():
        ok(f".env 已存在, 跳过 ({env_file})")
        return True

    if not example.exists():
        fail(".env.example 不存在, bundle 可能损坏")
        return False

    shutil.copy(example, env_file)

    # 读 key
    if unattended:
        ds_key = os.environ.get("DEEPSEEK_API_KEY", "")
    else:
        print(f"  {D}DeepSeek 免费注册 ¥5 额度: https://platform.deepseek.com/{X}")
        print(f"  {D}直接回车 = 跳过 (走 DEMO 模式, 不调 LLM){X}")
        ds_key = input(f"  输入 DEEPSEEK_API_KEY (sk-xxx): ").strip()

    if ds_key:
        txt = env_file.read_text(encoding="utf-8")
        txt = txt.replace("DEEPSEEK_API_KEY=\n", f"DEEPSEEK_API_KEY={ds_key}\n")
        # 确保 LLM_PROVIDER 是 deepseek (.env.example 默认就是, 但保险起见 verify)
        if "LLM_PROVIDER=deepseek" not in txt:
            txt = "LLM_PROVIDER=deepseek\n" + txt
        env_file.write_text(txt, encoding="utf-8")
        ok("DeepSeek key 已写入 .env")
    else:
        ok(".env 生成 · 无 key · 走 DEMO 模式")
    return True


def install_scheduler(skip: bool, unattended: bool, has_key: bool):
    step(4, "装自动化 · 每日 08:00 自成长 (5 步: soul+回传+结晶+待审+同步)")
    if skip:
        warn("按 --no-auto 跳过")
        return

    # 有 key = 默认装 (符合小九"贴了 API 就全自动"要求)
    # 无 key = 问用户 (因为 backfill 需要 API-Football, 不装也 OK)
    if unattended or has_key:
        choice = "y"
        if has_key:
            print(f"  {D}检测到 API key · 默认装自动化 (贴 key 即后台全自动){X}")
    else:
        print(f"  {D}没检测到 LLM key, DEMO 模式不需要自动化也能跑.{X}")
        choice = input(f"  还是要装定时任务? [y/N]: ").strip().lower() or "n"

    if choice != "y":
        warn("未装 (可随时 python install_scheduler.py 补装)")
        return

    installer = ROOT / "install_scheduler.py"
    r = run([sys.executable, str(installer)], cwd=str(ROOT))
    if r.returncode == 0:
        ok("定时任务已装 (Windows schtasks / Linux crontab 指南已打)")
    else:
        warn("装定时任务有问题, 可手动跑 python install_scheduler.py")


def test_heartbeat():
    step(5, "跑一次 heartbeat 验证端到端 (soul + crystal sync)")
    hb = ROOT / "heartbeat.py"
    r = run([sys.executable, str(hb)], cwd=str(ROOT))
    if r.returncode == 0:
        ok("heartbeat tick 通过")
    else:
        warn("heartbeat 返回非 0 · 看上面输出")


def demo_soul_round():
    """装完秀 1 轮 Soul 对话 · 让朋友立刻感觉 '哇真能聊'."""
    print(f"\n{B}{C}[额外]{X} 跑一次 Soul 对话 demo · 让你立刻看到孔明亲笔...\n")
    try:
        sys.path.insert(0, str(SOUL / "src"))
        # reload in case .env was just set
        for m in list(sys.modules):
            if "taijios" in m:
                del sys.modules[m]
        from taijios import Soul
        s = Soul(user_id="setup_demo")
        print(f"  {D}后端: {s.backend}{X}")
        r = s.chat("我刚装好 TaijiOS, 以后多指教")
        print(f"\n  {G}孔明回复:{X}")
        for line in r.reply.split("\n"):
            print(f"    {line}")
        print(f"\n  {D}意图: {r.intent} · 关系: {r.stage}{X}")
        if s.backend == "mock":
            print(f"\n  {Y}⚠  后端是 mock · 没配 LLM key 所以走模板. 配 DeepSeek 能看真回复.{X}")
    except Exception as e:
        print(f"  {R}Soul demo 失败: {e}{X}")


def final_notes():
    step(6, "装完")
    print(f"\n{G}{B}✅ TaijiOS 全家桶已装好.{X}\n")
    print(f"下一步:")
    print(f"  {C}python taijios.py{X}                菜单 (足球预测/灵魂对话/状态...)")
    print(f"  {C}python taijios.py predict \"A vs B\"{X}   直接预测")
    print(f"  {C}python taijios.py soul{X}              5 轮对话 demo")
    print(f"  {C}python heartbeat.py{X}                 手动 tick 一次")
    print(f"")
    print(f"引导: {D}START_HERE.md{X} · 手把手: {D}taijios-landing/install.md{X}")
    print(f"在线: {D}https://taijios.xyz/install/{X}\n")


def main():
    ap = argparse.ArgumentParser(description="TaijiOS 一键安装")
    ap.add_argument("--unattended", action="store_true", help="无人值守 · 从 env var 读 key")
    ap.add_argument("--no-auto", action="store_true", help="不装定时任务")
    args = ap.parse_args()

    try:
        banner()
        check_python()
        install_deps()
        if not configure_env(args.unattended):
            fail("配置失败")
            sys.exit(1)
        # detect if key was configured
        env_txt = (ZHUGE / ".env").read_text(encoding="utf-8") if (ZHUGE / ".env").exists() else ""
        has_key = any(
            line.strip().startswith(("DEEPSEEK_API_KEY=", "DOUBAO_API_KEY=", "OPENAI_API_KEY=",
                                     "ANTHROPIC_API_KEY=", "KIMI_API_KEY=", "QWEN_API_KEY="))
            and "=" in line and line.strip().split("=", 1)[1].strip()
            and not line.strip().startswith("#")
            for line in env_txt.splitlines()
        )
        install_scheduler(args.no_auto, args.unattended, has_key)
        test_heartbeat()
        demo_soul_round()
        # 装完跑一次 doctor 兜底
        print(f"\n{B}{C}[额外]{X} 跑 doctor 自检确认全绿...")
        run([sys.executable, str(ROOT / "doctor.py"), "--dry"], check=False)
        final_notes()
    except KeyboardInterrupt:
        print(f"\n{Y}中断 · 已装部分可能有效, 再跑一次 setup.py 继续.{X}")
        sys.exit(130)


if __name__ == "__main__":
    main()
