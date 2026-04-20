# Inter vs Cagliari · 复盘 · fixture_id 1378185

- **Kickoff**: 2026-04-17 18:45 UTC (2026-04-18 02:45 CEST)
- **Final**: Inter 3 : 0 Cagliari
- **Retro written**: 2026-04-20 (T+3 · 晚补 · memory `project_inter_cagliari_retro.md` 要求的 5 块)

---

## Block 1 · 命中校准 ✅ DONE

- Backfill entry: [news_archive/predictions.jsonl](g:/taijios_full_workspace/news_archive/predictions.jsonl) · `logged=2026-04-18T01:50:02` · `type=prediction_backfill`
- **Result**:
  - `hit_1x2 = true` (predicted home · actual home)
  - `hit_total = true` (predicted over_2.5 · actual 3 goals)
  - `hit_exact = false` (predicted `[2:0, 2:1, 3:1]` · actual `3:0` 未覆盖)
- 核心方向预测 100% · 精确比分 miss · 精度缺口记入 Block 4 action item

---

## Block 2 · L2 虚假精确审计 ✅ DONE

- Full audit: [docs/external_claims_sources.jsonl](g:/taijios_full_workspace/docs/external_claims_sources.jsonl) · 1 条完整 record · DeepSeek cross-validation 已做
- 结论分档:
  - **hard_fake_precision**: 士气 (离散 W/D/L 不可能产 3 位小数) · 交锋 (H2H 5 场整数只 11 档)
  - **weak_fake_precision**: 攻防 (gf/ga 整数派生)
  - **edge**: 主客场 (2 位 OK · 3 位过) · 赔率 (16 位 float 表达是 bug)
  - **ok**: 伤停 (0.5 对称合理)
- **Action items (未执行 · 下个 touch yao.py 时做)**:
  1. `zhuge-skill/core/yao.py` 出 yao 时按 source 类型 rounding · 离散源 → 1 位 + 定性词
  2. 赔率字段截到 3 位小数 (现是 float 原样)
  3. Reasoning 面向用户输出用 1 位 + 定性 ("士气 强阳" > "0.820")

---

## Block 3 · 晶体结晶 ✅ DONE (候选已登记 · 待促成)

- Candidate: [docs/crystal_seed_candidates.jsonl](g:/taijios_full_workspace/docs/crystal_seed_candidates.jsonl)
- Pattern: `乾_全阳_主场_实力悬殊_v0.1`
- Conditions: `home_team` + `yao_all_阳` + `h2h近5 主队>=4胜` + `客队近5 >=3 败`
- 核心预测: `1X2_home` + `over_2.5`
- **状态**: `hit_count=1 · miss_count=0 · 需 N=3 连续命中才 promote 成正式晶体`
- **下次待观察**: 满足条件的下一场 · 进来自动 `+1 hit` 或 `+1 miss`

---

## Block 4 · 孔明亲笔质量评

- Reasoning 样本 (提交到虾猜的版本):
  > "乾卦·六爻皆阳。Inter 近5 2-2-1；H2H 近5 4-1-0；赔率 1.24/5.8/10.5；客队近5仅1胜、十人伤停。孙子云\"先为不可胜\"——主胜+大球双线。"

| 维度 | 评分 | 理由 |
|---|---|---|
| 方向准确 | 5/5 | 主胜 + 大球 双线 100% 命中 |
| 数据引用 | 5/5 | 近5 wdl / H2H / 赔率 / 伤停 4 维都点到 · 可复现 |
| 古文典故契合度 | 4/5 | "先为不可胜" (孙子) 对应 H2H 4-1-0 压倒性 · 合理但稍套话 |
| 边界覆盖 | 2/5 | 无闷 0-0 或上半场僵局的 downside 讨论 · 顺风单边判断 |
| 精度纪律 | 3/5 | 没写 3 位小数 (100 字内限制逼出简洁) · 但 yao 数据来源有 L2 虚假精确 (Block 2) |

**综合**: **4.0/5** · 方向和典故都到位 · 缺 downside + 精度来源 (Block 2 下游问题)

**权重判断**:
- 满足条件 (乾全阳 + 主场 + H2H 压倒 + 客弱) 的场次 · **孔明评语权重保持** · 不降
- 不满足条件的场次 (五阳一阴 / 客强主弱混合) · **孔明评语权重降 0.5x** 直到新晶体养成
- **Action**: 比分预测组合扩到 `[3:0, 3:1, 2:0, 2:1, 4:0, 4:1]` · 覆盖大胜场景 · 不要只押窄比分

---

## Block 5 · 三平台一致性 + 推送

- **平台提交**: 虾猜 `pred-group-1776364190736-630wtj` · match_id `match-odds-3c0a6c55120809a87abc49406bb86657` · 状态 success (第三次 reasoning 精简到 100 字内才通过)
- **飞机推送**: 本次 **未** 主动 push 结果 · 补推一条:
  - 发到 tg_push.py · 内容: "Inter 3:0 Cagliari · 1X2 ✅ · 大小球 ✅ · 精确比分 miss · 乾卦晶体候选 hit#1 (待 N=3)"
- **evidence gate**: 本场不触发新 manual_v2 gate · 常规命中 · 已在 backfill 归档

---

## 综合结论

- **命中**: 核心方向 2/2 · 精确比分 0/3
- **虚假精确**: 6 个爻里 2 强假 + 1 弱假 + 2 边缘 + 1 OK · L2 pitfall #3 的最佳 case study
- **晶体**: 第一个晶体候选诞生 `乾_全阳_主场_实力悬殊_v0.1` · 待 2 次再 promote
- **孔明**: 4.0/5 · 方向对 · 缺 downside 覆盖
- **推送**: 虾猜 ✅ · tg_push 当时 miss · 本复盘补推
- **不该再犯**: 命中场景不复盘是规则违约 · T+3 才补是自保边缘 · 下次 4:45 (或第二天早上) 必动手

---

*2026-04-20 · 本复盘用于 zhuge-skill 自校准 · 不外发*
