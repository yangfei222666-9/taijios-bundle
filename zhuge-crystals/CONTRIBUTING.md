# Contributing to zhuge-crystals

## 字段白名单（PR 通过的前提）

每一行晶体 JSON 必须且**只能**包含以下 keys：

| Field | Type | Required | Example |
|---|---|:---:|---|
| `crystal_id` | string | ✅ | `"xtl-abc12345"` (8-char hex hash) |
| `version` | string | ✅ | `"v1"` |
| `trigger` | object | ✅ | `{"hexagram": "履", "yang_count": 5}` |
| `outcome` | string | ✅ | `"1x2=home"` or `"total_2_5=over"` etc. |
| `stats` | object | ✅ | `{"matches": 12, "hits": 10, "rate": 0.833, "ci_95": [0.65, 0.95]}` |
| `tags` | array[string] | ✅ | `["football"]` |

任何其它字段（`discovered_by`, `user_id`, `match_name`, `timestamp`, `api_key`, `note`, ...）都会导致 **PR 被直接拒绝**。

## 统计合理性

- `stats.matches` ≥ 3（样本太少不收）
- `stats.rate` ≥ 0.60（命中率太低不收）
- `stats.ci_95[0]` ≥ 0.55（置信区间下界太低不收，防噪声）

## PR 模板

```
### 新增晶体数量: N

### 来源场景
简述你跑了多少场、什么联赛（不要写具体比赛名）

### 自我审计清单
- [ ] 每行都通过了 sanitize_crystal() 过滤
- [ ] 没有原始比赛记录泄露
- [ ] 没有时间戳 / 用户信息
- [ ] 没有 API key
- [ ] stats 样本量符合要求

### 可选：跑过的命中率汇总
（抽象统计，不含原始数据）
```

## 自动化审核（计划中）

未来会加 GitHub Actions，自动用 JSON Schema 卡字段白名单 + 跑基本脱敏检查。PR 先走人工。
