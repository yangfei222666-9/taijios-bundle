---
layout: post
title: "TaijiOS · 手把手安装指南"
permalink: /install/
excerpt: "从零开始跑通 zhuge-skill. 手把手的 step-by-step · 每步有命令 + 预期输出 + 出错怎么办. 2026-04-18 实测."
lang: zh-CN
---

> 看完这页, 一个从没碰过 Python 的人也能把 zhuge-skill 跑起来. 每步的命令都可以直接 copy 粘贴, 预期输出长啥样也写了, 报错有预案.

---

## 📍 零 · 开始前

**你需要准备什么?**
- 一台能上网的电脑 (Windows / Mac / Linux 都行)
- 15-30 分钟
- **不需要** CS 背景
- **不需要** 会编程
- **建议** 装一个文本编辑器: [VS Code](https://code.visualstudio.com/) (免费), 用来改配置文件

**你会得到什么?**
- 一个本地跑的"诸葛亮 AI 军师", 能推演足球比赛
- 一个 64 卦决策引擎的 hands-on 体验
- 一份能加入 TaijiOS 晶体池 (共同进化) 的入场券

---

## 📍 一 · 装 Python (如果你没装)

### Windows 用户

1. 打开 [python.org/downloads](https://www.python.org/downloads/) · 下载 **Python 3.11 或更高** (不要 3.7 以下)
2. 运行安装包 · **务必勾选 "Add Python to PATH"** · 然后 Next / Install
3. 验证: 按 `Win + R` → 输入 `cmd` → 回车, 在黑框里打:

```
python --version
```

**预期输出**:
```
Python 3.12.x
```

如果看到 `'python' 不是内部或外部命令` — 说明 PATH 没加上. 重装时勾上 "Add to PATH", 或手动把 Python 目录 (e.g., `C:\Users\你\AppData\Local\Programs\Python\Python312\`) 加到系统环境变量 PATH.

### Mac 用户

打开 Terminal.app, 先确认有没有:
```bash
python3 --version
```
如果版本低于 3.11, 装 [Homebrew](https://brew.sh/) 后跑 `brew install python@3.12`.

### Linux 用户

自己搞得定, 跳过.

---

## 📍 二 · 装 git (如果你没装)

### Windows

下 [git-scm.com/download/win](https://git-scm.com/download/win) · 一路 Next 装上即可 · 装完会有 "Git Bash" 可以用.

验证 (在 cmd 或 Git Bash 里):
```bash
git --version
```

**预期**: `git version 2.xx.x`

### Mac / Linux

```bash
git --version
```
大概率已经有, 没有的话:
- Mac: `brew install git`
- Linux: `sudo apt install git` 或 `sudo dnf install git`

---

## 📍 三 · Clone zhuge-skill

选一个你想放代码的目录 (比如 `C:/Users/你的名字/Desktop`), 在 cmd / Terminal 里:

```bash
cd Desktop
git clone https://github.com/yangfei222666-9/zhuge-skill.git
cd zhuge-skill
```

**预期输出**:
```
Cloning into 'zhuge-skill'...
remote: Enumerating objects: ...
remote: Counting objects: 100% (xx/xx), done.
...
Receiving objects: 100% ... done.
Resolving deltas: 100% ..., done.
```

然后你现在在 `zhuge-skill` 目录里. 敲:
```bash
dir          # Windows
ls           # Mac/Linux
```

应该看到: `README.md` `SKILL.md` `start.py` `requirements.txt` `core/` `scripts/` `assets/` 等.

**如果报错** `Cloning into ... fatal: unable to access ... Could not resolve host`: 你没网 · 或 GitHub 被墙. 用梯子或换源.

---

## 📍 四 · 装依赖

依赖只 2 个, 很快:

```bash
pip install -r requirements.txt
```

**预期输出** (最后几行):
```
Successfully installed requests-2.xx.x python-dotenv-1.x.x
```

### 出错预案

**报错 `pip: command not found`**:
- 试 `pip3 install -r requirements.txt` (Mac/Linux 常见)
- 或 `python -m pip install -r requirements.txt`

**报错 `SSL: CERTIFICATE_VERIFY_FAILED`**:
- 公司网/防火墙拦了, 换网络或加参数: `pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org`

**报错 `Permission denied`**:
- Linux/Mac 加 `--user`: `pip install --user -r requirements.txt`
- Windows 用管理员运行 cmd

---

## 📍 五 · 首次启动 · 看动画

```bash
python start.py
```

**预期** (没配 API key 时):
1. 会播放一段赛博诸葛亮欢迎动画 (霓虹青 ASCII art)
2. 检查 Python 版本 + 依赖
3. 提示你配 API key (或跳过进 DEMO 模式)
4. 跑一次 demo 让你看效果

**如果看到"DEMO 模式"红色 banner** = 正常 · 这是没配 API 时的 fallback.

**如果报错 `UnicodeEncodeError: 'gbk'` (Windows 用户常见)**:
打开 PowerShell 代替 cmd 跑. 或者先执行:
```
set PYTHONIOENCODING=utf-8
```
再跑 `python start.py`.

---

## 📍 六 · 配 API Key (可选 · 让它做真实预测)

要做真预测, 需要至少:
- **1 个足球数据 API key** (API-Football)
- **1 个 LLM key** (DeepSeek 最便宜)

**赔率 API 可选** (The Odds API · 不配也能跑, 只是少一维数据).

### 6.1 API-Football (核心 · 免费 100 req/day)

1. 访问 [api-football.com](https://www.api-football.com/)
2. 注册 (Email + 密码, 不要社交登录)
3. 登录后进 Dashboard → **My Account** → 找到 "API Key" (一串 32 位字符, 比如 `abc123def456...`)
4. 复制

### 6.2 DeepSeek (LLM · 实测 $0.1 打平 Claude Opus $6.5)

1. 访问 [platform.deepseek.com](https://platform.deepseek.com/)
2. 手机号注册 (中国), 送 ¥5 免费额度 (够跑几千次预测)
3. 进 → **API Keys** → Create new secret key
4. **复制时必须存下来 · 只显示一次!**

### 6.3 The Odds API (可选 · 免费 500 req/month)

1. [the-odds-api.com](https://the-odds-api.com/)
2. 邮箱注册, 直接给 key
3. 复制

### 6.4 把 key 填入 .env

在 zhuge-skill 目录下, 新建一个叫 `.env` 的文件 (注意是 `.env` 不是 `env.txt`, Windows 用户可以在 VS Code 里另存为解决). 填:

```
# 足球数据
API_FOOTBALL_KEY=你刚才复制的 api-football key
THE_ODDS_API_KEY=你刚才复制的 odds key

# LLM (DeepSeek 举例, 其他 LLM 也行)
DEEPSEEK_API_KEY=你刚才复制的 deepseek key
```

**保存** · 不要带多余空格.

---

## 📍 七 · 跑真实预测

```bash
python scripts/predict.py "Inter vs Cagliari"
```

**预期输出** (有 API key):
```
=== 诸葛亮 · AI 推演 · Inter vs Cagliari ===

[1/7] 拉取 fixture ... ✓ fixture_id=1378185
[2/7] 拉取 H2H ... ✓ 近5场: 4-1-0
[3/7] 拉取 Form ... ✓ Inter 2-2-1 / Cagliari 1-0-4
[4/7] 拉取 Odds ... ✓ 1.24 / 5.80 / 10.50
[5/7] 拉取 Injuries ... ✓ home=10 / away=10
[6/7] 计算爻位 ... 攻防 0.67 · 士气 0.82 · 伤停 0.5 · 主客场 0.68 · 交锋 0.82 · 赔率 0.75
[7/7] 卦象识别 ... 乾 111111 (六爻皆阳)

推演结果:
  1X2:     home (主胜)
  大小球:  over_2.5
  比分候选: 2:0 · 2:1 · 3:1

孔明亲笔:
  观之, 国米六爻皆阳, 如乾卦"飞龙在天"...
  [古文评语约 100-300 字]
```

**如果想看 DEMO (不需 API key)**:
```bash
python scripts/predict.py "Napoli vs Lazio" --demo
```
(顶部会有红色 `⚠ DEMO 模式 · 非真实预测` banner)

---

## 📍 八 · 进阶 · 经验回传 + 晶体

跑过几场后, 结果出来了, 可以回填:

```bash
python scripts/backfill.py --once
```

这会把已完成的场次实际比分写回 `data/experience.jsonl`.

累积 3 场以上, 跑结晶:

```bash
python scripts/crystallize.py --dry-run
```

看能不能提炼出晶体 (命中率 ≥60% 的 pattern).

如果你愿意分享, 把晶体贡献到公共池 ([zhuge-crystals](https://github.com/yangfei222666-9/zhuge-crystals)):

```bash
python scripts/share.py
```

**共享原则**: 只 sync 无 PII 的 pattern · PR 审核 · 不会传播你的真实数据.

---

## 📍 八·半 · 在你喜欢的 AI IDE / Agent 框架里用

zhuge-skill 是 **纯 Python + SKILL.md + 标准 manifest** 结构, 只要框架能跑 Python + 读文本, 就能用. 下面是主流 7 个 framework 的接入方式:

### 🧠 Trae (字节 AI IDE · solo/agent mode)

Trae 支持 Python 工作区 + MCP server · 两种接法:

**A. 作为 Trae 工作区 (最简单)**:
```bash
git clone https://github.com/yangfei222666-9/zhuge-skill.git
cd zhuge-skill
# 在 Trae 里 File → Open Folder → 选 zhuge-skill 目录
# Trae 的 agent 能读 SKILL.md 自动识别为 skill, 直接对话调用
# 问它: "帮我预测 Inter vs Cagliari" 它会调 scripts/predict.py
```

**B. 作为 MCP server (需要你自己起 wrapper)**:
在 Trae 的 MCP 配置里加:
```json
{
  "zhuge": {
    "command": "python",
    "args": ["-m", "scripts.predict"],
    "cwd": "/path/to/zhuge-skill",
    "env": {"API_FOOTBALL_KEY": "..."}
  }
}
```

### 🖱️ Cursor

Cursor 用 `.cursor/rules/` 或 `.cursorrules` 文件:

```bash
git clone https://github.com/yangfei222666-9/zhuge-skill.git
cd zhuge-skill
# 把 SKILL.md 复制一份到 .cursor/rules/zhuge.md
mkdir -p .cursor/rules
cp SKILL.md .cursor/rules/zhuge.md
```

然后 Cursor agent mode 会自动读规则. 问它 "用 zhuge-skill 预测 X vs Y".

### 🎴 Claude Code (Anthropic CLI)

Claude Code 原生支持 SKILL.md:

```bash
git clone https://github.com/yangfei222666-9/zhuge-skill.git ~/.claude/skills/zhuge-skill
```

然后 Claude Code 会自动扫描 `~/.claude/skills/`. 在对话里直接说 "用 zhuge" 即可.

### 🦞 ClawHub (OpenClaw 生态 · 国际)

```bash
npm install -g clawhub@latest
clawhub install @yangfei222666-9/zhuge-skill
```

然后在支持 OpenClaw 的 IDE (如 Lark Coder / OpenClaw Desktop) 里就出现了.

### 🦐 虾评 (Agent World · 中文 market)

浏览器: [xiaping.coze.site](https://xiaping.coze.site) → 搜「诸葛亮」 → 下载 zip → 解压 → `python start.py`

### ⚗️ Hermes (Nous Research · prompt framework)

Hermes 本身是 prompt engineering framework, 不是 skill-runtime. zhuge-skill 的输出格式已经兼容 Hermes 的 tool-use XML 结构, 直接把 `scripts/predict.py` 的 JSON 输出 pipe 给 Hermes 解析即可.

---

### 通用规则 · 任何框架都通

只要框架能做以下 3 件事, 就能用 zhuge-skill:
1. 读 `SKILL.md` / `README.md` · 理解 skill 意图
2. 能跑 `python` subprocess
3. 能传 `.env` 环境变量给子进程

**一个 Python 进程 + 一个 SKILL.md + 两个 API key · 全跑**.

---

## 📍 九 · 还想走更远 · 整 TaijiOS 架构

zhuge-skill 是一个 skill. TaijiOS 是整个 OS 框架 (多 skill 容器 + ICI 认知身份 + 自改进 loop).

| 你想做什么 | 装哪个 repo | 文档入口 |
|---|---|---|
| 继续玩足球/其他预测 | 你已经在 [zhuge-skill](https://github.com/yangfei222666-9/zhuge-skill) | `SKILL.md` |
| 装主 OS 看架构 | [TaijiOS](https://github.com/yangfei222666-9/TaijiOS) | `README.md` |
| 极简认知身份试水 | [TaijiOS-Lite](https://github.com/yangfei222666-9/TaijiOS-Lite) (注意 default=master) | `README.md` |
| 只看公共晶体池 | [zhuge-crystals](https://github.com/yangfei222666-9/zhuge-crystals) | clone 看 `.jsonl` |
| 自改进 loop 看安全机制 | [self-improving-loop](https://github.com/yangfei222666-9/self-improving-loop) | `README.md` · 注意有 5 个 open issue |
| 官网源码 | [taijios-landing](https://github.com/yangfei222666-9/taijios-landing) (你现在看的就是) | Jekyll |

---

## 📍 十 · Agent World 平行网络 · 6 个活跃子站

如果你也做 Agent, 这些是 TaijiOS 正在用的社交/市场:

| 站 | 用法 |
|---|---|
| [虾评](https://xiaping.coze.site) | Agent World 的 skill 市场 (中文). TaijiOS 发了 zhuge-skill v1.1.0 |
| [AgentLink](https://friends.coze.site) | Agent 笔友匹配. TaijiOS 档案: `/profile/taijios` |
| [AfterGateway (酒馆)](https://bar.coze.site) | 放松留言涂鸦. TaijiOS 有 1 条裂隙威士忌留言 |
| [DreamX](https://dreamx.coze.site) | AI 梦境交易所 · 梦币经济. TaijiOS 有 2 条 dream |
| [Signal Arena](https://signal.coze.site) | 虚拟炒股竞赛 · 100 万起. TaijiOS 已 join, 决策 v2 daemon 运行中 |
| [Inkwell](https://inkwell.coze.site) | 90+ blog RSS 聚合. TaijiOS 收藏了 2 篇 |

都用同一个 Agent World API Key · 注册地址: [world.coze.site/api/agents/register](https://world.coze.site/api/agents/register)

---

## 📍 十一 · 卡住了? 求助

1. **看 README**: `zhuge-skill/README.md` 有更多细节
2. **提 Issue**: 任意 repo 都可以开
3. **酒馆聊**: [bar.coze.site](https://bar.coze.site) 搜 `@taijios`
4. **发笔友信**: [friends.coze.site/profile/taijios](https://friends.coze.site/profile/taijios) 匹配后邮件通
5. **博客有更多**: [/blog](/blog.html)

---

## ⚠️ 已知坑 · 看一眼避开

1. **Windows 编码**: `UnicodeEncodeError: 'gbk'` → 用 PowerShell 或 `set PYTHONIOENCODING=utf-8`
2. **TaijiOS-Lite 默认分支是 master**: `git pull origin main` 会 404, 用 `git pull origin master`
3. **DEMO 模式**: 没 API key 时 predict 走 DEMO (红色 banner). 不是 bug, 是 fallback. 不要把 DEMO 输出当真预测发
4. **taijios.xyz HTTPS 证书**: 如果这页是经 `taijios.xyz` 打不开, Let's Encrypt 证书还在 provision, 换 [github.io fallback](https://yangfei222666-9.github.io/taijios-landing/install/)
5. **.env 文件**: Windows 新建文件时可能变成 `.env.txt`. 用 VS Code "另存为" 或命令行 `echo.> .env` 保证是 `.env`

---

**一句话**: TaijiOS = 一个 60 天被 solo dev 建起来的 self-improving 诸葛亮. 六爻为骨, 晶体为脉. 说不谎是日课.

_Last updated: 2026-04-18_
