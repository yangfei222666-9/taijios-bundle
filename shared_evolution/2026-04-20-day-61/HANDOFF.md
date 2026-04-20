# HANDOFF · 2026-04-20 · Day 61 P1 交接包

**From**: Claude Opus 4.7 (Win11 · TaijiOS 丞相)
**To**: Codex (Mac · 五虎之外 · 同事级 peer)
**Purpose**: 共同进化 · 把今日全部工程产出一次性交接 · 请 Mac 侧 (1) 拉取 (2) 校验 sha (3) review (4) 回一份 `codex_mac.md` 到相同日期目录
**Spec**: `feedback_shared_evolution_handoff_spec.md v1`

---

## 0 · 打开顺序 (按此 4 步)

1. 校验 SHA256SUMS: `sha256sum -c SHA256SUMS`
2. 读本文 § 1-7
3. 读 `claude_win11_retro.md` (5 节 daily retro)
4. 选段看 `memory_excerpts/` 3 条 (刘备-诸葛亮 · 五虎调度 · 成本路由)

---

## 1 · 今天 Win11 侧发生了什么

一句话: **读 3 个 GitHub 仓 · 当天出 5 action item · P1 两条落码 · 20 新 tests · 154 全绿 · /crystals/ 新页上线 · 五虎调度硬规则立**.

详细见 `claude_win11_retro.md` + `claude_win11_github_study.md`.

---

## 2 · 新增代码 (`aios_core/`)

| 文件 | 类型 | 行数 | 用途 |
|---|---|---|---|
| `aios_core/review_hooks.py` | 新 | ~220 | HookMatcher-style PreReview/PostReview · AuditLogHook + CostGuardHook |
| `aios_core/review_runner.py` | 改 | +30 | 加 `hooks=` kwarg · `attach_hook()` · `review_claim` wrap pre/post · `_stamp` passthrough 加 tokens_in/tokens_out |
| `aios_core/llm_router.py` | 新 | ~220 | LiteLLM-style 瀑布路由 · 默认 DS→豆包→Kimi→GLM→Anthropic · circuit breaker + cooldown + `ProviderExhaustedError` + `default_cost_waterfall` 工厂 |

依赖 (bundle 里找对应路径): `aios/core/provider_registry.py`, `aios/core/verdict_schema.py`, `aios/core/env_migration_guard.py` (上述三者**未改** · 本 handoff 不带).

**应用点**: 原 workspace 在 `g:/taijios_full_workspace/aios/core/` · Mac 侧应对应到各自 clone 的 `aios/core/`.

---

## 3 · 新增测试 (`tests/`)

| 文件 | tests | 覆盖 |
|---|---|---|
| `tests/test_review_hooks.py` | 10 | Hook 派发 · AuditLog · CostGuard · exception 隔离 · 零 hook 行为不变 |
| `tests/test_llm_router.py` | 10 | happy / fallback / exhausted / cooldown / disabled / factory / forbid_defaults / empty / missing |

**验证**: 全 154/154 review 栈 pytest 绿 (86 原 + 20 新 + 48 相关). 跑一遍:
```bash
python -m pytest tests/test_review_runner.py tests/test_review_hooks.py tests/test_llm_router.py tests/test_reviewer_adapters.py tests/test_provider_registry.py tests/test_verdict_schema.py tests/test_run_review_pipeline.py -q
```
期望输出: `154 passed`.

---

## 4 · 文档 / 日 KPI

- `daily_improvements_2026-04-20.jsonl` · **16 条** (硬规则 ≥10). 9 feature + 3 opt + 2 bug_fix + 1 test + 1 doc. 对应 `feedback_core_values_and_pace.md`.
- `docs/retro_inter_cagliari_20260418.md` · Inter vs Cagliari (fixture 1378185, 04-17 3:0 主胜) 5 块复盘 · T+3 自保补写. 结论: 方向 2/2 · 精确比分 0/3 · 晶体候选 hit 1/3.
- `claude_win11_retro.md` · 今日 5 节 retro (学到 / 坑 / 对方盲点 / 明天 / 公告). 按 `feedback_daily_retro_mutual_exchange.md` 规范. **请 Mac 侧回一份 `codex_mac.md`**.

---

## 5 · 新/改 memory (`memory_excerpts/`)

| 文件 | 状态 | 要点 |
|---|---|---|
| `feedback_wuhu_command_layer.md` | **新** (04-20 先主明示) | 双层映射 (Soul 关系层不动 / Provider 执行层新立) · 丞相 5 做 5 不做 · ≥2 章节必派将 · 黄忠位空悬 |
| `feedback_zhuge_covenant.md` | 改 (加刘备侧 + 不单干条款) | 04-20 先主 "我是刘备你是诸葛亮" 双边明示 · 加 5 条不单干硬规则 |
| `feedback_cost_routing_policy.md` | 未改 (参考) | Layer A (Claude native) vs Layer B (TaijiOS code) 分层 · DS→国产→Anthropic 瀑布 · OpenAI 剔默认 |

Memory 文件本身不进 TaijiOS 代码库 · 仅作为 Mac 侧读 retro 时的参考. Mac 侧若有对等 memory, 自己管理.

---

## 6 · 对外 publish (已完成 · Mac 可去 pull)

- `yangfei222666-9/taijios-landing` **c7f56c7**: 新页 `/crystals/` · 晶体池 Day 1 诚实态
- `yangfei222666-9/taijios-landing` **c6487f8**: 新 blog `_posts/2026-04-20-day-61-p1-hooks-router.md` · 五虎调度第一战

URL:
- https://taijios.xyz/crystals/
- https://taijios.xyz/posts/2026/04/20/day-61-hookmatcher-与瀑布路由落-taijios-五虎调度第一战/ (permalink · Jekyll 构建后生效)

---

## 7 · Mac 侧请做 (cross-correction)

- 读本 handoff + `claude_win11_retro.md`
- 按 `feedback_daily_retro_mutual_exchange.md` 规范 · 写 `codex_mac.md` 回交
- 特别看 3 点:
  1. **review_hooks.py + review_runner.py 的接入有无隐藏 race / blocking / hook exception 泄漏风险** (hook 是 sync · 未来如果 call_fn 改 async 会怎么样?)
  2. **llm_router.py 的 `ProviderExhaustedError` 上游处理** (目前只抛异常, 没有 degraded-mode fallback. 对量化场景是否够严?)
  3. **五虎调度的 provider 映射** 是否同意关/张/赵/马的初版? **黄忠位**建议给谁? (候选: OpenAI oracle_only / Ollama local / Claude Relay)
- 发现任何 must-fix, 直接在 `codex_mac.md` 里写出, 全经小九 (不直接传 Win11)

---

## 8 · 硬约束 (Mac 侧必遵)

- 不代 Win11 改 Win11 栈代码 (按 `feedback_daily_retro_mutual_exchange.md` "分开学")
- 不上 real-money keys (按 `multi_model review spec §12` kill switch)
- 不外发具体足球预测 (按 `feedback_football_internal_only.md`)
- 本包任何文件**不得**直接 commit 进主代码库上游 · 先在 codex_mac.md 给出 review · 由小九决定是否 cherry-pick

---

**丞相 Claude Opus 4.7 · 2026-04-20 · 鞠躬尽瘁 · 不独耕**.
