# 部署清单 · taijios.xyz

## 一 · 买域名 (5 分钟)

- 打开 https://porkbun.com/products/domains
- 搜 `taijios.xyz` · 加购 · 付 ~$70/yr (Visa/Mastercard)
- **勾选 WHOIS Privacy** (免费 · 避免个人信息公开)
- **勾选 SSL 自动续签** (免费)
- 结账 · 收邮件确认

## 二 · 推到 GitHub (3 分钟)

```bash
cd g:/taijios-landing
git init
git add index.html DEPLOY.md
git commit -m "init: taijios.xyz landing v0.1"
gh repo create yangfei222666-9/taijios-landing --public --source=. --push
```

## 三 · 开 GitHub Pages (2 分钟)

1. 打开 https://github.com/yangfei222666-9/taijios-landing/settings/pages
2. Source: `Deploy from a branch`
3. Branch: `main` · folder `/ (root)`
4. Save · 等约 30 秒出现 `https://yangfei222666-9.github.io/taijios-landing/` · 先验证站跑通

## 四 · 绑定 taijios.xyz (10 分钟 + DNS 传播)

### Step 1 · GitHub 侧
1. 仓库根目录新建文件 `CNAME` (无后缀) · 内容就一行 `taijios.xyz`
2. commit push
3. Settings → Pages → Custom domain 填 `taijios.xyz` · Save
4. 等 DNS Check 绿 · 勾 Enforce HTTPS

### Step 2 · Porkbun DNS 侧
进 Porkbun 控制台 · Domain Management → taijios.xyz → DNS → 添加:

```
A       @     185.199.108.153
A       @     185.199.109.153
A       @     185.199.110.153
A       @     185.199.111.153
CNAME   www   yangfei222666-9.github.io
```

### Step 3 · 等传播
- DNS 传播 5-30 分钟 · 查 https://dnschecker.org/ 看 A 记录全球命中
- GitHub 侧自动签 Let's Encrypt SSL · 耐心等 · 不要反复切换 HTTPS 开关

## 五 · 上线后验证

- `https://taijios.xyz/` 打开 · 出内容 · HTTPS 绿锁
- `curl -I https://taijios.xyz/` 返回 200
- `https://taijios.xyz/` vs `https://www.taijios.xyz/` 都要能跳
- Telegram / 微信发链接 · 看 og:image 预览 (og.png 还没做 · 可以后补)

## 六 · 待补 (非阻塞)

- [ ] 生成 `og.png` · 1200x630 · 太极图 + 标题 + 83.6% 数字
- [ ] `favicon.ico` · 32x32 太极图
- [ ] `sitemap.xml` · 单页目前可以不做
- [ ] Google Analytics / Plausible · 上线后装一个看流量
- [ ] 加 sub-path `/api/` 指向 GitHub README · 或单独 soul_api 文档站 (未来)

## 七 · 改内容

全部在 `index.html` · 无 build step · 改完 push 即生效。

改完预览: `powershell -Command "Start-Process 'g:/taijios-landing/index.html'"`
