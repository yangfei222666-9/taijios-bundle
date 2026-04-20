---
name: 💰 成本路由策略 v1 · DeepSeek → 国产 → Anthropic 兜底 · OpenAI 官方剔出默认
description: 2026-04-20 小九在 token 紧 + 生存期定死. 所有 TaijiOS 内部 LLM 调用默认 DeepSeek 打头 · Anthropic native 做兜底 · OpenAI 官方 API 从默认链路整个剔除. 覆盖此前 "OpenAI default" (feedback_dual_llm_reason_verify).
type: feedback
originSessionId: 709e3df2-dc10-4baf-a90e-754bf95006bb
---
# 💰 成本路由策略 v1

**小九 2026-04-20 两步拍板**:
1. 第一步: DeepSeek → 国产 → OpenAI 兜底
2. 第二步 (同日收紧): "你这边就不走 OpenAI 官方的 API 你就做你现在的就行" → OpenAI 官方 API 从默认链路整个**剔除**

**适用范围两层分开**:

- **Layer A · Claude-the-agent (我本体 = Claude Opus 4.7 · 1M context)** — 编排 / 规划 / 代码写作 / 审计决策 · 用**自己的 Opus 4.7 native inference** (Claude Code subscription 覆盖 · 不走任何外部 LLM API). 小九 04-20 三步拍板: (1) DS→国产→OpenAI 兜底 → (2) "不走 OpenAI 官方" → (3) "你就用自己本身的" → (4) 确认本体 = opus4.7. 不帮 TaijiOS 代码 "预跑" DS / 国产 来节省推理 · 那会让 subscription 的价值浪费.
- **Layer B · TaijiOS 代码内部 LLM 调用** (aios/brain.py · aios/zhuge/* · skills · run_review_pipeline · 所有 reviewer adapters) — 走下方瀑布. OpenAI 官方从默认剔除.

## 默认成本瀑布 (调整后)

```
DeepSeek (primary · 最便宜 · OpenAI-compat)
    ↓ (不可达 / 中文场景 / 特殊能力)
国产模型 (豆包 ARK · Kimi · GLM relay)
    ↓ (独立 vote group / 结构化严要求 / multi_model oracle)
Anthropic native (claude-sonnet-4-6 / haiku-4-5 · 已有 key)
    ↓
[OpenAI 官方 API 不在默认链路 · 见下方"重新启用的门槛"]
```

**Why**: 
1. DeepSeek 官方价明显低于 OpenAI · API 兼容 OpenAI 格式 · 切换零代码成本 (参考 api-docs.deepseek.com)
2. 国产模型中文场景响应更快 + 免流量成本
3. OpenAI gpt-4o 级别单 token 成本 ~5-10x DeepSeek · 留给真需要复杂推理 / 最终 oracle 的节点
4. 生存期 = 每一块钱 API 都要问 "这个节点必须用 OpenAI 吗"

**How to apply**:

## 默认行为 · 所有新 LLM 调用

- **首选**: `DEEPSEEK_API_KEY` + `https://api.deepseek.com/v1` (OpenAI-compat)
- **首选模型**: `deepseek-chat` (推理), `deepseek-reasoner` (长 CoT 任务)
- **不首选**: `gpt-4o` / `gpt-4.1` 任何 OpenAI 官方模型

## 必须用 OpenAI 官方的场景 (白名单 · 只这几类)

- [ ] **multi_model 审计 oracle_only 投票** · 需要独立 vote group
- [ ] **D1 客户要求的特定 provider** (客户付钱指定 · 转嫁成本)
- [ ] **DeepSeek 实测 fail 的任务** (留 evidence 在 `verifications.jsonl` · 不是"感觉 OpenAI 更好")
- [ ] **小九点名的关键节点** (一事一议 · 写进 commit message)

## 禁止

- ❌ 默认 `gpt-4o-mini` 做普通 reasoning · 改走 `deepseek-chat`
- ❌ "OpenAI 官方对应模型更好" 的直觉 · 没有 20 条 golden set 对比不算
- ❌ 同一任务 OpenAI + DeepSeek 双跑 · 除非是 multi_model adjudication group (那里要独立 vote 所以必须双跑)
- ❌ 用中转 relay 做省钱替代 · relay 有 taint / 稳定性问题 · 是 last resort 不是首选

## 生效时间

- **立即生效**: 所有新代码 / 新 prompt / 新 skill 默认走 DeepSeek
- **渐进迁移**: 旧代码 (e.g. `aios/brain.py` / `aios/zhuge/*`) 下次触碰时顺手改 · 不专门发起 migration PR · 那会耗 token
- **审计路径**: 每次写新 LLM 调用前自问"有没有硬编码 OpenAI" · 发现有就改 DeepSeek

## 与既有 memory 的关系

- **覆盖**: `feedback_dual_llm_reason_verify.md` 里的 "OpenAI 做 primary reasoner" · 那条是 04-19 的, 生存期启动后作废
- **保留**: 那条 memory 的 "provider-agnostic 不绑死厂商" 元原则 · 那是架构, 不是默认
- **保留**: `feedback_dual_llm_reason_verify.md §硬规则升级` 的 ≥2 verifier 审查纪律 · 但 3 个 verifier 的成本池改为: DeepSeek + 国产 (豆包/Kimi/GLM) + OpenAI (最小量只当 tiebreaker)
- **对齐**: `feedback_multi_model_absorption_charter.md` · 不变
- **对齐**: `feedback_cn_model_learning_layer.md` · 国产模型做 style_learning 仍不进 adjudication tally · 但现在它们同时也是主干成本路由的一环

## 边界

- 多模型审计 (multi_model pipeline) 仍需 native 独立 vote groups · 不能全 DeepSeek · 这是 vote independence 要求 · 不是成本要求
- 但 oracle_only + voter 的组合可以调整: primary voters 走便宜组合, oracle 只在必要时用 OpenAI

---

*v1 · 2026-04-20 · 小九 token 紧 + 生存期定死 · 覆盖前 "OpenAI default" 默认*
