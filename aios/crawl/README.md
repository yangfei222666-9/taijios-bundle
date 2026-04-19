# TaijiOS · Web Crawl / Search

## Firecrawl adapter

**Why**: 让 agent 主动采集网页 → 结晶到 crystal pool · 闭合 self-improving-loop "主动探索"环。
**Status**: adapter 写好，未激活（需要 key）。

### 激活步骤

1. 去 [firecrawl.dev](https://firecrawl.dev) 注册 → free tier 500 credits
2. Dashboard → API Keys → 拷 `fc-...` 开头的 key
3. 加到 `G:/taijios_full_workspace/.env`:

   ```env
   FIRECRAWL_API_KEY=fc-<your-key>
   ```

4. 验证:

   ```bash
   python aios/crawl/firecrawl_adapter.py scrape https://docs.openclaw.ai/
   ```

   成功会打印 title + markdown 前 300 字符。

### 三种用法

```python
from aios.crawl.firecrawl_adapter import scrape, crawl, search

# 单页 → markdown
data = scrape("https://example.com/article")
print(data["data"]["markdown"])

# 整站 (async)
job = crawl("https://docs.firecrawl.dev/", limit=20)
print(job["id"])  # 后续用 GET /v1/crawl/{id} 取结果

# 搜索 (需 search-enabled plan)
hits = search("诸葛亮 六出祁山")
for h in hits["data"]:
    print(h["title"], h["url"])
```

### Cost/credits 说明

| Endpoint | Credits 消耗 |
|---|---|
| `/v1/scrape` 单页 | 1 / page |
| `/v1/crawl` | 1 / page × limit |
| `/v1/search` | 1 / query (搜索 + 可选 onpage scrape) |

Free tier 500 credits ≈ 500 单页抓取 / 月. 升级 Hobby $19/mo = 3000 credits.

### Provenance 集成

所有响应的 `X-Trace-Id` header 可以跟 sentinel / LLM 调用 log 关联（§5.3 规范）。建议 crystal metadata 里带 `{source: "firecrawl", trace_id, url, fetched_at}`。

### Why not Beautiful Soup / playwright?

- **BS4**: 只能拿 static HTML · Cloudflare / SPA 抓不到
- **Playwright**: 本地起 Chrome · 耗资源 · 不 scale
- **Firecrawl**: 云端抓 + anti-bot 处理 + 自动清洗 markdown · 省本机资源

### 限流 + 错误

- 401: key 错 / 失效
- 429: 超 quota · adapter 抛 `QuotaExceededError` 带 `retry_after_s` 供上游退避
- 500: Firecrawl 自己挂 · 上游重试 3 次
