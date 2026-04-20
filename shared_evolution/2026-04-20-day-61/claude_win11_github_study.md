# Claude Win11 · GitHub Study · 2026-04-20

**Study objective**: 对标 TaijiOS 现状 · 找可借鉴的设计点和已领先的地方
**3 repos 读**: anthropic/claude-agent-sdk-python · openai/swarm · BerriAI/litellm
**Focus**: Agent orchestration + 多模型协作 + provider routing
**不读**: 量化相关 (那是 Codex 的学习域 · 按"分开学"规则)

---

## 1. anthropic/claude-agent-sdk-python (SDK we run on)

### 1.1 核心关键机制

- **ClaudeSDKClient (interactive/stateful) vs query() (one-shot)** · 双层 API
- **Fork session** (0.1.0+) · programmatic subagent · 携带 session state 分叉
- **HookMatcher + PreToolUse/PostToolUse** · 工具调用的可插拔拦截层
- **MCP server in-process** · `create_sdk_mcp_server` + `@tool` 装饰器 · 工具走 `mcp__<namespace>__<name>` 命名
- **3 层权限**: `allowed_tools` → `disallowed_tools` → `permission_mode` → `hooks` → `can_use_tool` 顺序 evaluation
- **消息结构** (`AssistantMessage` / `ToolUseBlock` / `ToolResultBlock`): 每 tool_use 有 `id` · 每 tool_result 带 `tool_use_id` 关联 · 形成可追溯调用树

### 1.2 对 TaijiOS 的具体 action (不是观察 · 是要做的事)

**借鉴 1 · HookMatcher 进 review_runner** (P1 · 一周内可做)

我们 `aios/core/review_runner.py` 目前的 reviewer call 是直跑的 · 没 pre/post hook 抽象. 可以加:

```
aios/core/review_hooks.py
  class ReviewHook(Protocol):
      async def pre_reviewer_call(self, claim, provider_id, run_id) -> None: ...
      async def post_reviewer_call(self, verdict, provider_id, run_id) -> None: ...
  
  class AuditLogHook:  # 对齐 shared_evolution spec · 每次 reviewer 调用都落 jsonl
      ...
  class CostGuardHook:  # 每次 call 记 tokens · 到阈值 warn
      ...
```

`review_runner.register_reviewer` 时也注册 hooks · call_fn 前后触发 · 单一入口审计.

**借鉴 2 · MCP namespace 命名适用到 provider_registry** (P2 · 长期)

现在 `provider_registry.yaml` 每个 provider 有 id ("anthropic_native", "deepseek_native"). 可以进一步映射到 MCP-style 命名 `provider__<native|relay>__<name>` · 天然对齐 vote independence group:

```
provider__native__anthropic    (one vote group)
provider__native__openai       (another vote group · OPT-1 剔默认)
provider__relay__apiport       (relay group · 聚合 vote)
provider__local__ollama
```

做这个能让 Codex 将来 `reviewer_adapters.py` 的自动加载简单化.

**借鉴 3 · Fork session pattern 对应 shared_evolution**

Fork session = SDK 内置的 programmatic handoff. 我们 shared_evolution spec v1 是**手动 packet** 形式 · 两者本质同一件事 (transfer state to another agent). 差别: SDK fork 跨进程/线程 · 我们 cross-machine (Win11↔Mac). **不改 spec · 但将来如果要做 Win11 内部 subagent · 直接用 SDK fork 不造轮子**.

### 1.3 TaijiOS 比 SDK 严的地方

- SDK 的 session resume 看起来还在 roadmap (推断) · 我们 `shared_evolution spec` 已经定死
- SDK `permission_mode` 是 runtime 降级决策 · 我们 `d1_red_lines.md §10 procedure` 是**硬不可降级** (想松红线必走 4 步 · 不留口头豁免) · 纪律更硬

---

## 2. openai/swarm (experimental handoff framework)

### 2.1 核心关键机制

- **Agent** = `instructions` (system prompt) + `functions` (工具)
- **Handoff** = function 返回另一个 Agent 实例 · 替换 system prompt 但保留 chat history
- **Stateless between calls** · 调用方管 `messages` + `context_variables`
- **Result 对象** 包含 `value`, `agent` (handoff target), `context_variables`

### 2.2 对 TaijiOS 的验证 (不是借鉴 · 是 validate)

**我们 shared_evolution spec v1 philosophy = Swarm philosophy**:

- 都 "客户端显式管状态" (Swarm 调用方管 messages · 我们 spec 要求 HANDOFF.md + SHA256SUMS)
- 都 "handoff 要全量包" (Swarm Result 带 context · 我们 spec 6 类文件)
- 都 "不留隐式 session state" (Swarm 无 session · 我们 Desktop-Mac 明确 sha256)

**Validate 结论**: spec v1 design is aligned with state-of-the-art thinking for explicit handoff. 不需要改.

### 2.3 Swarm 没做我们有的

- Swarm 无 audit log 规范 · 我们 `review_runner` + `verdict_schema.json` 有结构化 verdict
- Swarm handoff 后丢 system prompt · 我们 LETTER_TO_MAC / LETTER_TO_CODEX 是有意识的 peer message · 不丢

---

## 3. BerriAI/litellm (unified provider interface)

### 3.1 核心关键机制

- **`model="provider/model-name"` 统一路由**
- **Provider adapter 层**: 各 provider 原生 format → OpenAI format
- **Router**: fallback / retry / load balance · 应用级
- **Virtual keys**: 每项目一把 key · budget 隔离
- **Cost tracking**: 依赖 `model_prices_and_context_window.json`

### 3.2 对 TaijiOS 的具体 action

**借鉴 4 · Router pattern 完成我们 cost_routing_policy** (P1 · Codex 在量化 scaffold 里需要一个)

我们有 `feedback_cost_routing_policy.md` 定义瀑布 (DS→国产→Anthropic) · 但 code 层实现**只是口头**. LiteLLM 的 Router 是成熟范式:

```
aios/core/llm_router.py
  class LLMRouter:
      def __init__(self, waterfall: List[str], registry: ProviderRegistry):
          self.waterfall = waterfall  # ['deepseek_native', 'doubao_native', 'anthropic_native']
          self.registry = registry
          self.health = {}  # provider_id -> {consecutive_fail: int, last_success: ts}
      
      async def call(self, prompt, schema=None, max_retries=3) -> Tuple[str, str]:
          """return (verdict_text, provider_id_used)"""
          for provider_id in self.waterfall:
              if not self._is_healthy(provider_id):
                  continue
              try:
                  return await self._call_provider(provider_id, prompt, schema), provider_id
              except (TimeoutError, RateLimitError) as e:
                  self._mark_fail(provider_id, e)
                  continue
          raise ProviderExhaustedError()
```

这段代码我们可以直接加进 `aios/core/` · 给 `review_runner` 用 · 也给将来的 quant scaffold `intel_gather` 用. **不是保姆教 Codex · 是 Claude 侧自己补 aios/core 的缺**.

**借鉴 5 · Virtual keys 对应 D2 managed-service**

D2 (多模型审计 managed-service) 如果上线 · 每客户一把 virtual key + budget quota = LiteLLM 模式. 现在 D2 是 scoping doc · 未来 code 时直接参考 LiteLLM 的 `ProxyConfig`.

### 3.3 TaijiOS 比 LiteLLM 严的地方

**Kill switch · 我们完胜 LiteLLM**:

- LiteLLM 文档无显式 kill switch · 靠 timeout + retry 隐式
- 我们 quant brief §12 明确定义 4 条 fail-fast 自检 (`is_paper_only=true` / endpoint marker / data source whitelist / no real-money keys in env)
- LiteLLM 为易用性宽松 · TaijiOS 为红线严格 · 两者是不同位置的 tradeoff · 我们选对了对 solo dev + 金融擦边应用的优先序

---

## 4. 总结 · 3 repo 出 5 个 action item

| # | Action | Priority | File 落位 | Owner |
|---|---|---|---|---|
| 1 | `aios/core/review_hooks.py` · HookMatcher-style PreReview/PostReview · AuditLog + CostGuard 两个具体 hook | P1 | aios/core/ | Claude Win11 · 下周做 |
| 2 | provider_registry 加 MCP-style namespace 命名约定 (`provider__native__X`) | P2 | aios/core/provider_registry.yaml | Claude Win11 · 1-2 周内 |
| 3 | `aios/core/llm_router.py` · LiteLLM Router 范式落地 cost_routing_policy | P1 | aios/core/ | Claude Win11 · 下周做 · 给 Codex 量化用 |
| 4 | `docs/evolution/spec_validation_vs_swarm.md` · 文档 spec v1 和 Swarm philosophy 对齐的验证 (证明我们 spec 不是孤岛设计) | P3 | docs/multi_model/ | Claude Win11 · 本月内 |
| 5 | `docs/d2_service/virtual_keys_plan.md` · D2 managed-service 的 per-client virtual key 预设计 · 引 LiteLLM ProxyConfig | P3 | docs/d2_service/ | Claude Win11 · 等 D2 真启动时做 |

**哪些不做**:
- 不碰 LangGraph / CrewAI / AutoGen 三个 orchestration 框架的学习 · token 紧 · 优先级低 · 等有需求再看
- 不实现 fork_session 内部 subagent · 我们现在的 cross-machine handoff 是更大价值的问题
- 不加 SDK permission_mode 运行时降级 · 我们红线 §10 procedure 已经更严

---

## 5. 今天 learning 对 Day-0 retro §1 "今天学到的" 的补充

追加条目到 `claude_win11.md §1`:

> 1.6 3 个行业基础设施仓的对比: Claude Agent SDK (持久化 session + hooks) · OpenAI Swarm (stateless + function-return-Agent handoff · 验证我们 spec v1 对齐行业范式) · LiteLLM (Router pattern · 为 cost_routing_policy 提供成熟参照). 输出 5 条 action item 到 `claude_win11_github_study.md` · P1 两条: review_hooks + llm_router.
