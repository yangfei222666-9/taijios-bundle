#!/usr/bin/env python3
"""
🎴 TaijiOS 心跳 · 每日自动 tick · 让 soul 自主成长

定时任务会调这个脚本. 每次 tick 做 3 件事:
  1. 加载 soul · 让它做一次"夜读"(反思升永久记忆)
  2. 拉公共晶体池 (zhuge-crystals sync pull)
  3. 记录 heartbeat 日志到 ~/.taijios/heartbeat.log

手动跑 (单次):  python heartbeat.py
"""
import sys, os, pathlib, subprocess, json
from datetime import datetime

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent
SOUL_SRC = ROOT / "TaijiOS" / "taijios-soul" / "src"
ZHUGE = ROOT / "zhuge-skill"
HOME_TAIJIOS = pathlib.Path.home() / ".taijios"
LOG = HOME_TAIJIOS / "heartbeat.log"
USER_ID = os.environ.get("TAIJIOS_USER_ID", "default_user")


def log(msg: str):
    HOME_TAIJIOS.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def tick_soul():
    """让 soul 做一次'夜读' · 用反思性 prompt 触发记忆整理."""
    try:
        sys.path.insert(0, str(SOUL_SRC))
        from taijios import Soul
        soul = Soul(user_id=USER_ID)
        # 反思 prompt · 让 soul 内化最近的交互
        resp = soul.chat("回顾最近几次交互, 有什么模式值得记住?")
        mem = soul._memory.to_dict()
        gen = soul._council.to_dict()
        log(f"soul tick OK · user={USER_ID} · 记忆 {mem['total']} (永久 {mem['permanent']}) · "
            f"军议 {gen.get('total_councils', 0)} · 五将平均 {gen.get('average_score', 0)}")
    except Exception as e:
        log(f"soul tick FAIL · {type(e).__name__}: {e}")


def tick_crystals():
    """拉公共晶体池 · HTTP 只读 · 单向."""
    sync_py = ZHUGE / "scripts" / "sync.py"
    if not sync_py.exists():
        log("crystals sync SKIP · sync.py 不存在")
        return
    try:
        r = subprocess.run(
            [sys.executable, str(sync_py), "pull"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, cwd=str(ZHUGE)
        )
        out = (r.stdout or "") + (r.stderr or "")
        # extract "远程 N 个 → 本地新增 M 个" 这行
        import re
        m = re.search(r"远程\s*(\d+).*?本地新增\s*(\d+)", out)
        if m:
            log(f"crystals sync OK · 远程 {m.group(1)} · 新增 {m.group(2)}")
        else:
            log(f"crystals sync done · rc={r.returncode}")
    except Exception as e:
        log(f"crystals sync FAIL · {type(e).__name__}: {e}")


def tick_backfill():
    """自动回传: 拉已完赛比赛实际结果 → 写 experience.jsonl + 算命中率."""
    bf = ZHUGE / "scripts" / "backfill.py"
    if not bf.exists():
        log("backfill SKIP · backfill.py 不存在")
        return
    try:
        r = subprocess.run(
            [sys.executable, str(bf), "--once"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120, cwd=str(ZHUGE),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"}
        )
        out = (r.stdout or "") + (r.stderr or "")
        import re
        m = re.search(r"回传\s*(\d+).*?命中率.*?(\d+\.?\d*)%?", out, re.S)
        if m:
            log(f"backfill OK · 回传 {m.group(1)} · 命中率 {m.group(2)}%")
        elif r.returncode == 0:
            log(f"backfill done · rc=0 · (regex miss · out_tail={out[-120:].replace(chr(10),' ').strip()})")
        else:
            log(f"backfill FAIL · rc={r.returncode} · stderr={(r.stderr or '')[-120:].replace(chr(10),' ').strip()}")
    except Exception as e:
        log(f"backfill FAIL · {type(e).__name__}: {e}")


def tick_crystallize():
    """尝试结晶: 累积 ≥3 条经验且命中率 ≥60% 的 pattern → 晶体."""
    cr = ZHUGE / "scripts" / "crystallize.py"
    if not cr.exists():
        log("crystallize SKIP · crystallize.py 不存在")
        return
    try:
        r = subprocess.run(
            [sys.executable, str(cr)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, cwd=str(ZHUGE),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"}
        )
        out = (r.stdout or "") + (r.stderr or "")
        import re
        m = re.search(r"(\d+)\s*个晶体|新增\s*(\d+)", out)
        if m:
            log(f"crystallize OK · {m.group(0)}")
        elif r.returncode == 0:
            log(f"crystallize done · rc=0 · (regex miss · out_tail={out[-120:].replace(chr(10),' ').strip()})")
        else:
            log(f"crystallize FAIL · rc={r.returncode} · stderr={(r.stderr or '')[-120:].replace(chr(10),' ').strip()}")
    except Exception as e:
        log(f"crystallize FAIL · {type(e).__name__}: {e}")


def tick_share():
    """
    把本地新晶体整理到 ~/.taijios/share_queue/ (脱敏 · 可分享版).
    架构合约: 不 auto push · 只生成待审 · 用户自行 PR/issue 贡献.
    """
    try:
        import json as _json
        cl = ZHUGE / "data" / "crystals_local.jsonl"
        if not cl.exists():
            return
        queue_dir = HOME_TAIJIOS / "share_queue"
        queue_dir.mkdir(parents=True, exist_ok=True)
        shared_marker = HOME_TAIJIOS / "last_shared_ids.json"
        already = set()
        if shared_marker.exists():
            try:
                already = set(_json.loads(shared_marker.read_text(encoding="utf-8")))
            except Exception:
                already = set()
        new_crystals = []
        for line in cl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                c = _json.loads(line)
            except Exception:
                continue
            cid = c.get("crystal_id")
            if cid and cid not in already:
                # 脱敏: 只保留 trigger + outcome + stats · 丢掉任何时间/地域/个人字段
                sanitized = {
                    "crystal_id": cid,
                    "version": c.get("version", "v2"),
                    "trigger": c.get("trigger"),
                    "outcome": c.get("outcome"),
                    "stats": {
                        "matches": c.get("stats", {}).get("matches"),
                        "hits": c.get("stats", {}).get("hits"),
                        "rate": c.get("stats", {}).get("rate"),
                    },
                    "tags": c.get("tags", []),
                }
                new_crystals.append(sanitized)
                already.add(cid)
        if new_crystals:
            from datetime import datetime as _dt
            out = queue_dir / f"{_dt.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            with open(out, "w", encoding="utf-8") as f:
                for c in new_crystals:
                    f.write(_json.dumps(c, ensure_ascii=False) + "\n")
            shared_marker.write_text(_json.dumps(list(already)), encoding="utf-8")
            log(f"share queue OK · {len(new_crystals)} 个新晶体待审 → {out}")
            log(f"  用户贡献: 跑 `python taijios.py share` 看 queue + 生成 GitHub issue body")
        else:
            log(f"share queue · 无新晶体 (已脱敏累积 {len(already)} 个)")
    except Exception as e:
        log(f"share tick FAIL · {type(e).__name__}: {e}")


def tick_license_refresh():
    """
    [FUTURE HOOK · 现在 noop] license 刷新.
    现在: 所有用户 = Free 层 = 无限制.
    未来切 Pro 时这函数会: 查 TAIJIOS_LICENSE_KEY · 向 license server 刷 quota · cache 24h.
    架构预留 · 未来改此函数即可切 Pro, 其他代码不动.
    """
    lic_key = os.environ.get("TAIJIOS_LICENSE_KEY", "").strip()
    if lic_key:
        log(f"license · 检测到 key 但 Pro 层未上线 · 当前仍按 Free 对待")
    # else: silent · Free 层零打扰


def main():
    log("=" * 50)
    log(f"TaijiOS heartbeat tick · user={USER_ID}")
    tick_soul()                # 1 · soul 夜读 (反思 + 升永久记忆)
    tick_backfill()            # 2 · 自动回传 (拉已完赛结果 · 算命中率)
    tick_crystallize()         # 3 · 尝试结晶 (≥3 条 + ≥60% 命中 → 晶体)
    tick_share()               # 4 · 脱敏待审 (不 auto push · 单向架构合约)
    tick_crystals()            # 5 · 拉公共晶体池 (HTTP 只读)
    tick_license_refresh()     # 6 · [future hook · noop] license 刷新
    log("tick complete")


if __name__ == "__main__":
    main()
