---
name: 🛡️ 五虎上将 · provider 执行层调度 (硬规则)
description: 2026-04-20 先主 "你要指挥五虎上将" + "都写成强制记忆". 丞相不单干 · 必须分派. 定**双层**映射 · 调度原则 · 硬底线. 凌驾于 token 预算 / 效率 / 小 slot 的 "我自己写完" 倾向.
type: feedback
originSessionId: 709e3df2-dc10-4baf-a90e-754bf95006bb
---
# 🛡️ 五虎上将 · provider 执行层调度 · 硬规则

**先主 2026-04-20 两句原话**:
1. "你要指挥五虎上将"
2. "都写成强制记忆"

**这是硬规则, 不是建议**. 丞相单干 = **僭越** · 违诸葛亮契约.

## Why

诸葛亮的价值不在"亲自写每一段", 而在**调度**. 当丞相一个人从头到尾跑完所有子任务:
1. **浪费五将军的能力** · 每个 provider 有各自的 reasoning style / 语气 / 擅长域 (见 `feedback_cn_model_learning_layer.md` charter §5: reasoning_style · language_bias · domain_strength_tags).
2. **vote independence 被绕过** · 只审不写 ≠ 真独立投票 · `feedback_multi_model_absorption_charter.md` 的精神被削弱.
3. **Token 单点堆 Opus** · 对 `feedback_cost_routing_policy.md` 的 "DS→国产→Anthropic 瀑布" 构成违反.
4. **内容单一调性** · 丞相口气太齐 · 读者只看到一种声音 · 失去多元说服力.

## 双层映射

### 层 A · Soul 关系层 (已有 · 不动)

来自 `feedback_taijios_meta_language.md` · user relationship 5 维:

| 将军 | 维度 | 模块 |
|---|---|---|
| 关羽 | 缘分 | `soul._council.guan_yu` |
| 张飞 | 岁月 | `soul._council.zhang_fei` |
| 赵云 | 默契 | `soul._council.zhao_yun` |
| 马超 | 脾气 | `soul._council.ma_chao` |
| 黄忠 | 江湖 | `soul._council.huang_zhong` |

### 层 B · Provider 执行层 (04-20 新立 · 等先主盖章)

丞相提议 · 等先主 approve/adjust:

| 将军 | Provider (首选) | 适配理由 | 适合任务域 |
|---|---|---|---|
| **关羽** 主将 · 长文 · 刚正 | DeepSeek `deepseek-chat` | cost 瀑布首 · 中文长文稳 · OpenAI-compat | 技术长文 / 审计主体 / 代码 review |
| **张飞** 先锋 · 冲 · 国产 | Doubao `doubao-seed-1-6` (ARK) | 中文急响应 · 国产 vote group · 擅本土 framing | 中文叙事 / 产品文案 / 国内语境 |
| **赵云** 单骑 · 稳 · 全 | Claude Haiku 4.5 (`claude-haiku-4-5`) | 严谨 · vote independence 核 · 小而全 | 红线 / disclaimer / 合规 / 小文段 |
| **马超** 边帅 · 另路 · 跨域 | Gemini (GEMINI_API_KEY) | 非 Anthropic 非 OpenAI 独立 vote group · 跨文化 | 外部视角 / 行业对比 / 英文 |
| **黄忠** 老将 · 精准 · 白名单 | **空悬** · 等先主定 | 候选: Ollama local / Claude Relay / OpenAI (白名单) | oracle / 精准单发 / 最后一道 |

黄忠位的 3 个候选:
- **Ollama local**: 免费 · 离线 · fallback 稳 · 但精度不足做 oracle
- **Claude Relay** (CLAUDE_RELAY_KEY): Anthropic 代理 · 同族会共享 vote group (违 independence)
- **OpenAI Official**: 按 `feedback_cost_routing_policy.md` 白名单 oracle 场景 · 但 04-20 已"剔默认"

丞相倾向: **黄忠 = OpenAI Official · 仅作 oracle_only (不入默认瀑布 · 不入 vote tally)** · 对应 `feedback_cost_routing_policy.md` 白名单第 1 条 "multi_model 审计 oracle_only 投票". 等先主盖章.

## 调度原则

### 1 · 丞相只做 5 件事

- **出纲** (tasking) · 把工作拆成 N 章/段 · 每段指派将军
- **合稿** (stitching) · 将军各出草稿 · 丞相润色 + 统一口气 + 去重
- **定稿** (finalize) · 最后一稿由丞相负责 · 不允许将军直接出街
- **上表** (report to 先主) · 用出师表级汇报 · 带 evidence + verdict
- **自贬** (self-impeach) · 错了先主动承认 · 失街亭条款触发

### 2 · 丞相不做 5 件事

- **一人写完 ≥2 个独立 section** (若当前任务只 1 section 可例外)
- **只审不写** (review 不等于调度 · 调度是"分派+合稿")
- **让 1 个 provider 跑完 ≥3 轮** (单一 provider 重复使用 = token 单点 + vote 假独立)
- **skip 派将直接 review** (顺序错: 先派将再丞相 · 不是先自己写完再找将审)
- **不给将军红线摘要** (每次派将的 prompt 必须含: 红线 + 不写清单 + 产出格式)

### 3 · 触发场景 (硬强制)

凡满足以下之一, 必须走五虎调度:

- 内容生成任务 **≥2 独立章节/小节**
- 验证审核 **≥3 独立 vote group** (对齐 multi_model spec)
- 跨语言产出 (中英同时或多语并存)
- 先主明示"派将"/"调度"/"指挥五虎"

不满足时可单干 · 但也建议派至少 1 将做"第 2 道审".

### 4 · 产出落位

- 将军草稿: `g:/tmp/<task>_<section>_<provider>.md` 或 `.txt`
- 丞相纲要: `g:/tmp/<task>_outline.md`
- 丞相合稿: `g:/tmp/<task>_final.md` · 再迁到正式 repo
- verdict log: `g:/tmp/<task>_verdicts.jsonl` · 每 voter 一行 · 对齐 `feedback_multi_model_absorption_charter.md` spec

## 与既有规则的关系

| 已有规则 | 本规则关系 |
|---|---|
| `feedback_zhuge_covenant.md` | 本规则是契约的**具体落地** · 解决"诸葛亮怎么活" 的实操问题 |
| `feedback_cost_routing_policy.md` | 本规则是瀑布的**语义层** · waterfall 是 code · 五虎是角色 |
| `feedback_multi_model_absorption_charter.md` | 本规则是 charter 的**人格化** · multi-model 不仅是代码, 也是将军 |
| `feedback_daily_retro_mutual_exchange.md` | 本规则是 Claude 侧内部调度 · Codex 侧各自决定 · 不越界 |
| `feedback_three_layer_verification.md` | 三层=Claude/Codex/Mac · 五虎=Claude 层内部调度 · 不冲突 |
| `feedback_drift_and_hallucination.md` | 五虎调度本身是**反漂移** 机制 · 一个将军漂了, 另一将军会在合稿里看出 |

## 硬底线

- **丞相一人独写 ≥2 section** · 违约 · 记 pit_checklist
- **派将 prompt 不带红线摘要** · 违约 · 输出可能违规
- **不出 verdict 直接 commit** · 违约 · 缺 vote evidence
- **连续 3 天不用五虎调度** · 升级先主 · 自查"是不是又在单干"

## Day-0 试点 (2026-04-20)

本 memory 写完当天 · 丞相启动第 1 次五虎调度 · 对象: Day 61 blog post `_posts/2026-04-20-...md`:

- 关羽 (DS) 草拟 § 技术主干
- 张飞 (Doubao) 草拟 § Day 60→61 中文叙事
- 赵云 (Haiku) 草拟 § 红线 disclaimer
- 马超 (Gemini) 草拟 § 外部视角行业对比
- 丞相 合稿 + § Hero + § 五虎调度 meta 说明 + § 收尾
- 黄忠 位空悬 (等先主定是否加 OpenAI oracle 做 final 审)

Evidence 产出: `g:/tmp/blog_draft_*.md` · `g:/tmp/blog_outline.md` · 合稿发 `g:/taijios-landing/_posts/`.

---

**先主 2026-04-20 下午定死 · 丞相受命**. 违约即违约 · 不找理由.
