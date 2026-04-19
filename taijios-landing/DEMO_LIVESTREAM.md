# 🎙️ zhuge-skill 直播演示话术

> 给朋友直播时照着念 · 总时长 8-12 分钟 · 无需临场想台词

---

## 🎬 Step 0 · 开场一句（15 秒）

> "这个叫**诸葛亮推演军师**，是 TaijiOS 里的一个技能。核心卖点一句话——**让 AI 决策省 90% token**。不是玄学，是把结构化推演留在 CPU 里跑，LLM 只在必要时调。"

---

## 💻 Step 1 · 2 行下载（30 秒）

打开终端，照念：

```bash
git clone https://github.com/yangfei222666-9/zhuge-skill.git
cd zhuge-skill
```

> "GitHub 直接拉，253KB，一秒钟。"

---

## 🚀 Step 2 · 零配置跑 DEMO（60 秒）

```bash
python start.py demo
```

**画面会出**：
- 赛博朋克欢迎动画
- 6 维爻位进度条（攻防/士气/伤停/主客场/交锋/赔率）
- **履卦 111011**（5 阳爻）
- 孔明评语：「履卦五阳临尊，全维度优势，可重仓主胜」
- 推荐：主胜，信心高

> "看到了吗？0 API key，0 LLM 调用——这就是核心价值。结构化推演完成，只花了几毫秒 CPU。"

---

## 🎭 Step 3 · 不同比赛出不同卦（90 秒）

```bash
python start.py predict "Chelsea vs Man Utd"
python start.py predict "Real Madrid vs Barcelona"
python start.py predict "Bayern vs Dortmund"
```

**展示**：每场都出**不同的卦**：
- Chelsea vs Man Utd → **解卦 001010**（2/6 阳 · 客胜）
- Real Madrid vs Barcelona → **需卦 111100**（4/6 阳 · 主胜）
- Bayern vs Dortmund → **大有卦 111001**（4/6 阳 · 主胜）

> "每场不一样。这是通过比赛名 hash 生成的确定性 demo——同一场每次跑结果一样（可复现），不同场结果不同（有区分度）。"

---

## 🔥 Step 4 · 配 DeepSeek 解锁孔明亲笔（2 分钟）

**准备好的 .env 粘贴**：

```bash
echo "LLM_PROVIDER=deepseek" > .env
echo "DEEPSEEK_API_KEY=sk-你的key" >> .env
python start.py predict "Bayern vs Dortmund"
```

**画面会出孔明亲笔古文评语**，例如：

> **孔明亲笔**
>
> 臣观天象，主队坐拥地利，如虎踞龙盘。卦显大有之象，锋线锐利可破敌阵，然士气稍逊，恐有轻敌之患。敌虽客战，然交锋往绩不俗，不可不防其奇袭。宜稳守中军，待其疲敝时以两翼齐发，则三分可定。若急躁冒进，反易为所乘。谨记：**以正合，以奇胜**。

> "这段古文是 DeepSeek 实时生成的，基于我刚才的 6 爻和卦象。每次都不一样，孙子兵法味很浓。这一步才 200-300 token，跟纯 LLM agent 动不动 5000 token 比是十倍省。"

---

## 🏠 Step 5 · 本地 Ollama 零成本路径（1 分钟 · 可选）

> "想完全免费？本地跑 Qwen 7B。"

```bash
ollama pull qwen2.5:7b
export LLM_PROVIDER=openai \
       OPENAI_API_BASE=http://localhost:11434/v1 \
       OPENAI_API_KEY=ollama \
       OPENAI_MODEL=qwen2.5:7b
python start.py predict "Napoli vs Lazio"
```

> "效果跟 DeepSeek 差不多，但完全不花钱。实测 10/10 通过。"

---

## 💬 Step 6 · 回应可能的问题

### Q: "为什么是易经不是 ML 模型？"
A: "ML 模型做决策需要训练数据 + 解释不了。易经 6 爻是把复杂问题结构化成 64 个状态，**每个状态有明确的古人判语**——这是一层人类可审的决策层。训练数据自己随时间沉淀成晶体复用。"

### Q: "真的有人用吗？"
A: "上线第一天，有个叫 `Coze主智能体 A3-1` 的 agent 自主扫到并评了 **4.0/5，稀缺 5.0**。说明独特性被外部验证过。"

### Q: "数据会上传吗？"
A: "**绝对不会**。隐私合约很硬：`scripts/sync.py` 只 pull 不 push，`push` 函数从代码里删了不是注释掉。可以 `grep -n 'requests.post\|upload' scripts/` 自己验证。"

### Q: "怎么扩展到别的场景？"
A: "底层是通用 64 卦推演引擎，足球只是第一场景。下个版本会出**股票/招聘/选型**三个预设模板。"

---

## 🎯 Step 7 · 收尾 CTA（30 秒）

> "想玩完整版？**两种入口**：
>
> 1. **虾评正式版**: https://xiaping.coze.site/skill/f0cb5f86-23be-457c-a23b-fd6184ee6975
> 2. **GitHub clone**: https://github.com/yangfei222666-9/zhuge-skill
>
> 首评 4.0/5，审核绿点。有问题直接在虾评页评论，作者会迭代到下个版本。"

---

## 🚨 应急预案

**如果 `git clone` 失败**：改用虾评下载（zip 直接拉）

**如果 `python start.py` 报模块错**：`pip install -r requirements.txt` （requests + python-dotenv）

**如果 DeepSeek 超时**：`.env` 加 `LLM_PROVIDER=ollama` 切本地，或直接跑 demo 不走 LLM

**如果观众问"这不是足球**博彩**吗"**：强调"**技术展示 Agent 决策架构** · 足球只是一个 demo 场景，底层引擎通用"

---

## 📋 直播前检查清单

- [ ] 终端字体调大到 20pt+（观众看得清）
- [ ] 屏幕分辨率 1080p+ 清晰
- [ ] `.env` 已准备好 DeepSeek key（或 Ollama 已装好）
- [ ] 断网也能演 demo + 换比赛（不需要网络）
- [ ] 官网打开一个标签: http://taijios.xyz · 展示 #autorun 部分
- [ ] 虾评页打开一个标签: 展示 4.0/5 评测

---

**祝开播顺利 🎬**

—— @taijios · 诸葛孔明
