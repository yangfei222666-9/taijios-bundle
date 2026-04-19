# TaijiOS · LLM Observability

## Langfuse self-host

**Why**: Token 纪律 (feedback_token_budget_discipline.md) 要求 "WC 后按任务分级降模型"。没 cost/quality trend 数据做不了决策。Langfuse 提供每次 LLM 调用的 trace + token count + latency + evals，自 host 免 vendor lock + 不外发数据。

**Status**: docker-compose + client 写好，**未启动**（需你先起 Docker 实例）。

### 第一次 setup (约 10 分钟)

```bash
cd deploy/langfuse
cp .env.example .env

# 生三个 secret (每个至少 32 字符)
python ../../tools/gen_token.py --bytes 32   # 用作 NEXTAUTH_SECRET
python ../../tools/gen_token.py --bytes 16   # 用作 SALT
python ../../tools/gen_token.py --bytes 32   # 用作 ENCRYPTION_KEY

# 编辑 .env 填上面 3 个值，也改掉 POSTGRES_PASSWORD

docker compose up -d
docker compose logs -f langfuse    # 等看到 "ready · 0.0.0.0:3000"
```

然后浏览器开 http://localhost:3000：

1. **Sign up** — 第一个注册的 email 自动是 admin
2. **Create Project** → 名字写 `taijios`
3. **Settings → API Keys** → Create new pair
4. 复制 `pk-lf-...` 和 `sk-lf-...`
5. 加到 `G:/taijios_full_workspace/.env`:

   ```env
   LANGFUSE_HOST=http://localhost:3000
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   ```

### 使用（最小集成）

```python
from aios.observability.langfuse_client import LangfuseTracer

lf = LangfuseTracer()  # 读 .env · 无 key 时 lf.enabled=False

if lf.enabled:
    with lf.trace("predict_match", user_id="taijios") as t:
        # 正常调 LLM
        reply = openai_client.chat.completions.create(...)
        t.log_generation(
            name="gpt-4o-mini",
            model="gpt-4o-mini",
            input=messages,
            output=reply.choices[0].message.content,
            usage={
                "input": reply.usage.prompt_tokens,
                "output": reply.usage.completion_tokens,
                "total": reply.usage.total_tokens,
            },
        )
```

集成点（建议 P1 补）:

- `zhuge-skill/core/llm.py` 的 `LLMClient.chat()` 里加 tracer hook
- `api_server.py` 每个 `/v1/predict` 请求开一个 trace，trace_id 同步到 response `meta.trace_id`（§5.3 provenance 对齐）

### Fail-soft 设计

`LangfuseTracer` 所有 flush 都在 try/except 内 — 如果 Langfuse 挂了 / 网络不通 / timeout，**决不会阻断 LLM 调用**。最多 stderr 一条 `[langfuse-warn]`。这是观测性工具的铁律：观测挂了不能杀业务。

### Smoke test

```bash
python aios/observability/langfuse_client.py
```

输出会显示 `host / enabled / ping / flushed trace_id`. 然后去 Langfuse UI 看 Traces 应该有新 trace "smoke_test"。

### 成本观察

Langfuse 本身 0 成本（self-host）。Docker 占用 ~500MB RAM + 200MB disk 起步。Postgres volume 按 trace 数量增长，约 1KB/trace。10k traces/day ≈ 10MB/day。

### 未来扩展

- **Evals**: Langfuse 支持 LLM-as-judge eval，自动打分每个 trace（correctness / toxicity）
- **Dataset**: 把 crystal 导出成 eval dataset 做回归测
- **Prompt management**: 把 TaijiOS 各 prompt 中心化，A/B test 支持
- 这些都是 P2 · 现在先跑通 tracer ingest 即可
