#!/usr/bin/env python3
"""
🎴 TaijiOS Brain · Soul × zhuge 自动路由 (真智能对话)

用法:
    python brain.py                          # 交互式 chat
    python brain.py --user friend_01         # 指定 user_id (独立人格)
    python brain.py --once "Inter vs Cagliari 今晚谁会赢?"  # 单轮模式

规则:
  1. 用户消息 → Soul.chat 拿 intent + 丞相语气 reply
  2. 若消息含足球模式 ("vs" / "对战" / "预测" / 队名对阵) → 自动调 zhuge predict
  3. 若 intent crisis>50% → Soul 单独处理 (不做技术推演)
  4. 融合返回: Soul 情绪回复 + 如有 predict 结果的卦象/评

这是 "对话永久成长" 的出口 · 每次聊 Soul 记住, 每次预测 zhuge 回传.
"""
import sys, os, re, subprocess, pathlib, argparse, json

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent
ZHUGE = ROOT / "zhuge-skill"
SOUL_SRC = ROOT / "TaijiOS" / "taijios-soul" / "src"
def _find_divination_dir():
    """Find dir containing true_divination.py · canonical first, then glob fallback (max depth 4).

    canonical 路径在标准 bundle layout 下命中 · glob fallback 用于异常 unzip / 重组目录场景.
    返回第一个命中目录, 都没有则返回 canonical (后续 import 失败时给可读错误)."""
    canonical = ROOT / "taiji" / "taijios-lite" / "aios" / "core"
    if (canonical / "true_divination.py").exists():
        return canonical
    # Fallback · glob ROOT (limited depth 4 via parts check) for true_divination.py
    for hit in ROOT.glob("**/true_divination.py"):
        if len(hit.relative_to(ROOT).parts) <= 5:
            return hit.parent
    return canonical


DIVINATION_DIR = _find_divination_dir()
ANSI = re.compile(r"\x1b\[[0-9;]*m")

# 占卦触发词 · 通用决策/预判场景 (不限足球)
DIVINATION_WORDS = [
    "占卦", "卜卦", "起卦", "问卦", "问卜",
    "要不要", "该不该", "纠结", "犹豫", "选哪个",
    "前途", "未来", "运势", "命运", "吉凶",
    "靠谱吗", "值得吗", "能成吗", "会不会", "有没有戏",
    "辞职", "跳槽", "创业", "投资", "买房", "分手",
]

G, Y, R, D, B, C, X = "\033[38;5;82m", "\033[38;5;226m", "\033[38;5;196m", "\033[2m", "\033[1m", "\033[38;5;51m", "\033[0m"

# 足球对阵检测 · "Team A vs Team B" / "Team A 对战 Team B"
MATCH_PAT = re.compile(r"([A-Za-z][\w\s]{2,30}?)\s*(?:vs|对阵|对战|vs\.)\s*([A-Za-z][\w\s]{2,30})", re.I)


def extract_match(msg: str):
    """从消息中抽出对阵 · 返回 'Team A vs Team B' 或 None."""
    m = MATCH_PAT.search(msg)
    if m:
        home, away = m.group(1).strip(), m.group(2).strip()
        return f"{home} vs {away}"
    return None


def call_zhuge_predict(match: str, timeout: int = 180) -> str:
    """调 zhuge-skill 的 predict.py · 返回清理过的 stdout."""
    r = subprocess.run(
        [sys.executable, str(ZHUGE / "scripts" / "predict.py"), match],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout, cwd=str(ZHUGE),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}
    )
    return ANSI.sub("", (r.stdout or "") + (r.stderr or ""))


def extract_kongming_verdict(predict_output: str) -> str:
    """从 predict 输出里抽 '孔明亲笔' 段."""
    lines = predict_output.splitlines()
    in_block = False
    collected = []
    for line in lines:
        if "孔明亲笔" in line:
            in_block = True
            continue
        if in_block:
            if "═" in line or "━" in line or line.strip().startswith("DEMO 结束"):
                if collected:
                    break
                continue
            clean = line.strip("║ ").strip()
            if clean:
                collected.append(clean)
    return "\n".join(collected) if collected else ""


def is_divination_query(msg: str) -> bool:
    """判断是否是通用占卦/决策咨询 (不限足球)."""
    return any(w in msg for w in DIVINATION_WORDS)


def cast_hexagram(question: str, soul=None) -> tuple:
    """调 taijios-lite 的 true_divination · 然后用 Soul 的 LLM 解读.

    Returns (raw_cast_text, llm_interpretation).
    """
    try:
        sys.path.insert(0, str(DIVINATION_DIR))
        import true_divination
        raw = true_divination.cast_and_format(question=question, person="")
    except Exception as e:
        return (f"(占卦失败: {e})", "")

    # 用 Soul 的 LLM 解读 · 古文+现代建议并行
    interp = ""
    if soul and soul.backend != "mock":
        try:
            system = (
                "你是诸葛亮. 基于给定的真随机卦象 (硬件 entropy 产生, 非 LLM 伪卦), "
                "用古文 + 现代建议解读. 要求:\n"
                "1. 开头一句古文总判 (如 '臣观此卦... 主通达/困顿/变化')\n"
                "2. 中段列 2-3 条具体现代建议 (针对问题场景)\n"
                "3. 结尾一句提醒 (变爻动点 / 注意事项)\n"
                "全文 200 字内, 不要重新起卦, 只解读给定的卦."
            )
            user = f"问题: {question}\n\n卦象:\n{raw}"
            interp = soul._llm.call(system_prompt=system, user_message=user, max_tokens=400)
        except Exception as e:
            interp = f"(LLM 解读失败: {e})"
    return (raw, interp)


def brain_chat(msg: str, soul, verbose: bool = True):
    """一轮智能对话 · 路由优先级: crisis > 足球对阵 > 通用占卦 > 纯 Soul."""
    r = soul.chat(msg)
    match = extract_match(msg)
    divination = is_divination_query(msg)
    crisis = r.intent.get("crisis", 0)

    if verbose:
        print(f"\n  {D}[意图] work={r.intent.get('work',0):.0%} crisis={crisis:.0%} "
              f"learning={r.intent.get('learning',0):.0%} · 关系={r.stage}{X}")

    # 1 · 危机情绪 > 50% · Soul 单独处理 (不起卦不推演 · 先安抚)
    if crisis > 0.5:
        print(f"\n  {G}{B}孔明:{X}")
        for line in r.reply.split("\n"):
            print(f"    {line}")
        return

    # 2 · 足球对阵 · zhuge-skill 专用 (5 数据源 + 64 卦)
    if match:
        print(f"\n  {C}检测到对阵: {match} · 自动调 zhuge 推演...{X}")
        predict_out = call_zhuge_predict(match)
        verdict = extract_kongming_verdict(predict_out)

        print(f"\n  {G}{B}孔明 (综合 Soul + zhuge):{X}")
        for line in r.reply.split("\n"):
            print(f"    {line}")
        if verdict:
            print(f"\n  {Y}{B}  ━━ 推演 · 孔明亲笔 ━━{X}")
            for line in verdict.split("\n"):
                print(f"    {line}")
        else:
            print(f"\n  {D}  (predict 未返回清晰 verdict · 看完整: python taijios.py predict \"{match}\"){X}")
        return

    # 3 · 通用占卦 · 辞职/创业/要不要/纠结 等决策类 → 起一卦
    if divination:
        print(f"\n  {C}检测到问卦意图 · 起一卦...{X}")
        raw, interp = cast_hexagram(msg, soul=soul)  # tuple unpack · 传 soul 让 LLM 解读
        hex_out = f"{raw}\n\n{interp}".strip() if interp else raw

        print(f"\n  {G}{B}孔明:{X}")
        for line in r.reply.split("\n"):
            print(f"    {line}")
        print(f"\n  {Y}{B}  ━━ 起卦 ━━{X}")
        for line in hex_out.split("\n"):
            print(f"    {line}")
        return

    # 4 · 纯 Soul chat
    print(f"\n  {G}{B}孔明:{X}")
    for line in r.reply.split("\n"):
        print(f"    {line}")


def main():
    ap = argparse.ArgumentParser(description="TaijiOS Brain · Soul × zhuge 路由")
    ap.add_argument("--user", default="default_user", help="user_id · 独立人格")
    ap.add_argument("--once", default=None, help="单轮模式 · 打印完退")
    args = ap.parse_args()

    sys.path.insert(0, str(SOUL_SRC))
    try:
        from taijios import Soul
    except ImportError:
        print(f"{R}✗ taijios-soul 未装. 跑: python taijios.py install{X}")
        sys.exit(1)

    print(f"{C}╔═══════════════════════════════════════════╗{X}")
    print(f"{C}║  {B}🎴 TaijiOS Brain · Soul × zhuge 路由{X}{C}      ║{X}")
    print(f"{C}╚═══════════════════════════════════════════╝{X}")

    soul = Soul(user_id=args.user)
    print(f"\n  {D}user={args.user} · 后端={soul.backend} · 关系={soul.stage}{X}")
    print(f"  {D}规则:{X}")
    print(f"  {D}    crisis>50% → 只给情绪; 足球对阵 → zhuge 推演;{X}")
    print(f"  {D}    要不要/纠结/辞职等 → 起一卦; 其他 → 纯 Soul chat.{X}")

    if args.once:
        brain_chat(args.once, soul)
        return

    print(f"\n  {Y}[交互式] 回车空行退出{X}\n")
    while True:
        try:
            msg = input(f"{C}你: {X}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{Y}再见{X}")
            break
        if not msg:
            break
        try:
            brain_chat(msg, soul)
        except Exception as e:
            print(f"  {R}✗ 出错: {type(e).__name__}: {e}{X}")


if __name__ == "__main__":
    main()
