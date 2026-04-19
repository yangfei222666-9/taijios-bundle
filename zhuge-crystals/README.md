# zhuge-crystals · 诸葛亮晶体公共池

> **匿名、脱敏、可审计**的决策晶体共享池，供 [zhuge-skill](https://github.com/yangfei222666-9/zhuge-skill) 消费。

## 这里是什么

zhuge-skill 运行在各地用户的本地机器上，经过大量预测 + 回传 + 结晶后，用户可以**自愿**把提炼出的**抽象晶体**贡献到这里，供全网 zhuge-skill 实例下载复用。

晶体是**纯结构化的决策模式**，不含任何用户信息。

## 晶体数据结构（强制白名单）

```json
{
  "crystal_id": "xtl-abc12345",
  "version": "v1",
  "trigger": {
    "hexagram": "履",
    "yang_count": 5
  },
  "outcome": "1x2=home",
  "stats": {
    "matches": 12,
    "hits": 10,
    "rate": 0.833,
    "ci_95": [0.65, 0.95]
  },
  "tags": ["football"]
}
```

**禁止字段**（PR 会被拒）：
- 任何用户 ID / 账号 / 机器指纹
- 比赛原名 / 球队名 / 时间戳
- IP / 地理位置
- API key 或供应商
- 赔率原始值 / 投注金额
- 任何自由文本（评语、note 等）

## 贡献流程（PR）

1. 在你本地 zhuge-skill 跑 `python scripts/crystallize.py`
2. 把 `data/crystals_local.jsonl` 里**你愿意公开**的那几行，用 [sanitize_crystal()](https://github.com/yangfei222666-9/zhuge-skill/blob/main/scripts/sync.py) 脱敏
3. 开 PR 把脱敏后的行追加到本仓库的 `crystals.jsonl`
4. Maintainer 审核（检查字段白名单、统计合理性、去重）
5. Merge 后，所有 zhuge-skill 用户 `python scripts/sync.py pull` 就能拉到你的贡献

## 消费流程（Pull）

zhuge-skill 用户无需注册、无需认证，直接：

```bash
python scripts/sync.py pull
```

这是一个只读的 HTTPS GET，不携带任何本地数据。

## 维护者

[@yangfei222666-9](https://github.com/yangfei222666-9) — 人工审核每个 PR，保证池子质量

## License

MIT-0（所有晶体）
