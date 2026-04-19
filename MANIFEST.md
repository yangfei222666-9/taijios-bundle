# MANIFEST · 7 repo 快照

| 目录 | 作用 | 默认分支 | 版本 |
|---|---|---|---|
| `zhuge-skill/` | ⭐ 最 mature · 足球预测 + 64 卦 + 孔明亲笔 | main | **v1.1.1** |
| `TaijiOS/` | 主 OS 框架 · 多 skill 容器 · 含 `taijios-soul/` 灵魂 API | main | — |
| `TaijiOS-Lite/` | ICI 极简版 (认知身份标识) · ⚠ 默认分支是 **master** | master | v1.3.0 |
| `zhuge-crystals/` | 公共晶体池 · PR-audited · 只读 | main | — |
| `self-improving-loop/` | 安全自改进引擎 (已 merge 到 TaijiOS) | main | — |
| `taijios-landing/` | 官网源 · 含 **`install.md` 11 章手把手** | main | — |
| `taiji/` | 中文 landing + 部分 aios 聚合 | main | v0.1.0 |

## 入口建议

1. **5 分钟体验**: 读本包根目录的 `START_HERE.md`
2. **详细手把手**: `taijios-landing/install.md` (11 章 · 从装 Python 到晶体)
3. **在线完整指南**: https://taijios.xyz/install/
4. **先跑起来**: `cd zhuge-skill && pip install -r requirements.txt && python start.py`
5. **零配置玩 Soul API**: `cd TaijiOS/taijios-soul && pip install -e . && python quickstart.py`

## 已测试能力 (2026-04-19 凌晨)

- ✅ zhuge-skill v1.1.1 · 6 core module import + `start.py` + `predict.py`
- ✅ DeepSeek 真调孔明亲笔古文评 (端到端打通)
- ✅ taijios-soul quickstart 5 轮对话意图分类
- ✅ zhuge-crystals sync pull (HTTP 只读 · 透明)
- ✅ 三平台发布一致性: GitHub v1.1.1 + ClawHub @1.1.1 + 虾评 safe 4.0★

## 新手必知 (2 个坑)

见 `START_HERE.md` 末尾. 核心:
- `LLM_PROVIDER=deepseek` 必写
- Windows 必 `PYTHONIOENCODING=utf-8`
