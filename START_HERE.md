# 🎴 TaijiOS 全家桶 · 试装包 v1.1.1

> 打包 2026-04-19 · by 小九 (solo dev · 马来华侨 · 60 天建起来)

## 🚀 真·一键装 (推荐 · 3 分钟全搞定)

**Windows 双击** `setup.bat` · 或命令行:

```bash
python setup.py
```

脚本会引导你做 6 步全自动:
1. ✓ 检查 Python (≥3.8)
2. ✓ 装 deps (zhuge-skill + taijios-soul)
3. ✓ 问一次 DeepSeek key (跳过就走 DEMO)
4. ✓ 问要不要装定时任务 (每日 08:00 自动成长)
5. ✓ 跑一次 heartbeat 验证端到端
6. ✓ 装完 · 提示下一步

装完直接: `python taijios.py`

## 🎴 ICI 档案 · 让 TaijiOS 真懂你 (推荐)

**ICI = Individual Cognitive Identity · 个体认知身份标识**

TaijiOS-Lite v1.4.0 有独立于 soul 的 ICI 档案机制 · 让 AI 军师跨会话记得你是谁:

- 五维认知地图: **位置 / 本事 / 钱财 / 野心 / 口碑**
- 每次对话自动累积 · 越用越懂
- 共享给朋友时自动脱敏 (手机号/姓名/感情/地址 11 类过滤)

**怎么建**:

```bash
cd TaijiOS-Lite
# 方式 A · 有 ICI docx 文件放同目录, 自动识别
# 方式 B · 没 ICI 就走 7 问题快速建档 (30 秒):
python start.py   # 首次启动会引导
```

详情见 `TaijiOS-Lite/README.md` 和 `TaijiOS-Lite/ARCHITECTURE.md`.

和 bundle 里的 `taijios-soul` 区别:
- **soul** = 对话情绪 + 意图识别 + 五将军 (陪聊型)
- **ICI** = 跨会话认知身份沉淀 (档案型 · 更结构化)
- 建议两个都玩 · 互补

---

## 🏠 零成本本地跑 (不付钱给任何 LLM)

不想付 DeepSeek? 装 [Ollama](https://ollama.ai/) 免费跑:

```bash
# 1. 装 Ollama · 装完跑起来
# 2. 下模型 (7B 够用, 实测 10/10 通过)
ollama pull qwen2.5:7b

# 3. 编辑 zhuge-skill/.env, 把 LLM_PROVIDER 改成:
LLM_PROVIDER=openai
OPENAI_API_BASE=http://localhost:11434/v1
OPENAI_API_KEY=ollama-local
OPENAI_MODEL=qwen2.5:7b

# 4. 测
python taijios.py predict "Inter vs Cagliari"
# 孔明亲笔会由本地 Ollama 生成 · 0 成本
```

## 🌐 对开发者朋友 · HTTP API + Swagger

```bash
pip install fastapi "uvicorn[standard]" pydantic
python taijios.py api    # 自动开浏览器到 Swagger UI
```

8 个 endpoint 可 HTTP 调 (任何语言都能接):
- `POST /v1/predict` 足球推演
- `POST /v1/soul/chat` 灵魂对话
- `GET /v1/soul/{user_id}` Soul 完整状态
- `POST /v1/sync` 拉晶体池
- `GET /v1/crystals/local` / `GET /v1/heartbeat/last` / `GET /v1/share/queue`

你在做 Node/Go/Java 的 platform? HTTP POST 一下就能嵌 TaijiOS 孔明对话进你项目.

---

## 🧩 接入 Trae / Cursor / Claude Desktop (MCP)

bundle 自带 `mcp_server.py` · 3 步接入:

```bash
pip install mcp>=1.0.0   # 装 MCP SDK
```

在 AI IDE 的 MCP 配置里加 (路径换成你解包的 bundle 绝对路径):

```json
{
  "mcpServers": {
    "taijios-zhuge": {
      "command": "python",
      "args": ["<ABS_PATH>/mcp_server.py"]
    }
  }
}
```

重启 IDE · 现在你的 agent 可以直接 `predict("Inter vs Cagliari")` · 不用 shell 切换.

## 📖 想精准控制每一步

```bash
python taijios.py              # 菜单 (7 个选项)
python taijios.py install      # 只装 deps
python taijios.py predict "Inter vs Cagliari"
python taijios.py soul
python taijios.py sync
python taijios.py status
python heartbeat.py            # 手动 tick 一次
python install_scheduler.py    # 只装定时任务
```

以上都**多轮 API 验证过** · DeepSeek 真调稳定 · 军议累加 5→6→7.

## 🚀 5 分钟跑起来 (手动方式)

```bash
cd zhuge-skill
pip install -r requirements.txt

# 复制配置模板 → 填 key
cp .env.example .env       # Windows: copy .env.example .env
# 至少 2 行 (必须)
#   LLM_PROVIDER=deepseek
#   DEEPSEEK_API_KEY=<去 platform.deepseek.com 注册领 ¥5 免费额度>

# Windows 用户必设 (否则 ⚠ ⭐ 字符崩)
set PYTHONIOENCODING=utf-8   # cmd; PowerShell 用 $env:PYTHONIOENCODING='utf-8'

python start.py
```

看到 **"╔═ 孔明亲笔 ═╗"** 框出现就算通了 · 框里是 DeepSeek 生成的古文评.

## 📚 完整手把手 (11 章)

- 包里: `taijios-landing/install.md`
- 在线: **https://taijios.xyz/install/** (HTTPS 已启)

## 📖 包内组件

见 `MANIFEST.md`.

## 💬 卡住

- 开 GitHub issue: 任意 repo
- 酒馆 @taijios: https://bar.coze.site
- 笔友: https://friends.coze.site/profile/taijios

## ⚠️ 两个新手坑 (2026-04-18 晚实测踩过)

1. `.env` 只写 `DEEPSEEK_API_KEY` 不够 · **必须同时写 `LLM_PROVIDER=deepseek`** · 否则 LLM 静默不调用, 没有孔明亲笔
2. Windows cmd **必须** `set PYTHONIOENCODING=utf-8` · 否则 `⚠` 等字符抛 UnicodeEncodeError

**端到端测试通过** (2026-04-18 晚): 解包 → pip install → .env 4 行 → DeepSeek 真调 → 古文评出
