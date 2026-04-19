"""生成 og.png · 1200×630 · 社交预览图
    赛博星空背景 + 太极圆 + 大标 + 数据点 + CTA
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

W, H = 1200, 630

# ════════════════ 背景 ════════════════
img = Image.new("RGB", (W, H), (5, 7, 13))

# radial 发光云团 (模拟 nebula)
bg_glow = Image.new("RGB", (W, H), (5, 7, 13))
gd = ImageDraw.Draw(bg_glow)
gd.ellipse([80, 80, 580, 520], fill=(0, 130, 200))        # 左上青
gd.ellipse([780, 180, 1180, 580], fill=(180, 40, 120))    # 右下洋红
gd.ellipse([400, 380, 900, 700], fill=(120, 90, 20))      # 底部暖金
bg_glow = bg_glow.filter(ImageFilter.GaussianBlur(100))
img = Image.blend(img, bg_glow, 0.32)

draw = ImageDraw.Draw(img)

# 细网格
for x in range(0, W, 60):
    draw.line([(x, 0), (x, H)], fill=(0, 50, 70), width=1)
for y in range(0, H, 60):
    draw.line([(0, y), (W, y)], fill=(0, 50, 70), width=1)

# 随机星点
import random
random.seed(42)
for _ in range(80):
    x = random.randint(0, W)
    y = random.randint(0, H)
    size = random.choice([1, 1, 1, 2])
    color = random.choice([(232,241,255), (200,220,255), (255,240,200)])
    draw.ellipse([x-size, y-size, x+size, y+size], fill=color)

# ════════════════ 太极圆 (右侧) ════════════════
cx, cy, r = 940, 315, 160
outer = [cx-r, cy-r, cx+r, cy+r]

# 外圈光晕 (多层叠)
for i in range(5, 0, -1):
    a = 255 - i*35
    draw.ellipse([cx-r-i*4, cy-r-i*4, cx+r+i*4, cy+r+i*4],
                 outline=(0, int(a*0.9), int(a)), width=1)

# 太极主体
draw.ellipse(outer, fill=(232,241,255), outline=(0,240,255), width=4)
# 左半黑 (pieslice 90→270 = 6 点钟到 12 点钟 CW = 左半)
draw.pieslice(outer, 90, 270, fill=(5,7,13))
# 上方 S-bite · 黑
draw.ellipse([cx-r//2, cy-r, cx+r//2, cy], fill=(5,7,13))
# 下方 S-bite · 白
draw.ellipse([cx-r//2, cy, cx+r//2, cy+r], fill=(232,241,255))
# 两眼
er = r // 8
draw.ellipse([cx-er, cy-r//2-er, cx+er, cy-r//2+er], fill=(232,241,255))
draw.ellipse([cx-er, cy+r//2-er, cx+er, cy+r//2+er], fill=(5,7,13))

# 四向卦符 · 霓虹四色
try:
    hex_font = ImageFont.truetype("C:/Windows/Fonts/simsun.ttc", 40)
except OSError:
    hex_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 40)

draw.text((cx-20, cy-r-54), "\u2630", font=hex_font, fill=(0,240,255))    # 乾 ☰ 青 (顶)
draw.text((cx+r+14, cy-22), "\u2631", font=hex_font, fill=(255,46,138))    # 兑 ☱ 洋红 (右)
draw.text((cx-20, cy+r+6), "\u2637", font=hex_font, fill=(255,217,74))     # 坤 ☷ 金 (下)
draw.text((cx-r-54, cy-22), "\u2636", font=hex_font, fill=(0,255,154))     # 艮 ☶ 绿 (左)

# ════════════════ 左侧文字块 ════════════════
try:
    title_font = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 130)
except OSError:
    title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 130)

# 标题 阴影 · 赛博青光
for dx, dy, col, alpha in [(4,0,(255,46,138),100), (-4,0,(0,240,255),100), (0,0,None,255)]:
    fill = (232, 241, 255) if col is None else col
    draw.text((60+dx, 110+dy), "太极OS", font=title_font, fill=fill)

# 底部一条青光下划线
draw.rectangle([60, 258, 220, 262], fill=(0,240,255))

# 副标
sub_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 26)
draw.text((60, 280), "诸葛孔明 · 太极OS 亲笔评语", font=sub_font, fill=(0,240,255))

# 数据块 (3 行)
data_font = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 32)
mono_font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 22)

# 第 1 行 · 分数大字 · 金色
draw.text((60, 340), "83.6%", font=ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 66), fill=(255,217,74))
# 旁边数据细节
draw.text((220, 360), "Coze Agent 世界 · 3 科满分", font=data_font, fill=(232,241,255))

# 第 2 行 · 排名
rank_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)
draw.text((60, 420), "676 Agent 同场 · 排名 143 · 前 21.2%", font=rank_font, fill=(200,220,255))

# 第 3 行 · 性价比
draw.text((60, 460), "DeepSeek $0.1 打平 Opus $6.5 · 60 倍差价", font=mono_font, fill=(0,255,154))

# ════════════════ 底部 CTA ════════════════
cta_font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 24)
draw.text((60, 540), "taijios.xyz", font=ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 28), fill=(255,217,74))
draw.text((210, 544), "· 晶体池开放 · 人越多越准 · 欢迎接", font=rank_font, fill=(201,168,255))

# ════════════════ 四角 HUD 装饰 ════════════════
corners = [
    [(30, 30), (30, 80), (80, 30)],           # 左上
    [(W-30, 30), (W-30, 80), (W-80, 30)],     # 右上
    [(30, H-30), (30, H-80), (80, H-30)],     # 左下
    [(W-30, H-30), (W-30, H-80), (W-80, H-30)], # 右下
]
for c in corners:
    draw.line([c[0], c[1]], fill=(0,240,255), width=2)
    draw.line([c[0], c[2]], fill=(0,240,255), width=2)

# 保存
out = Path("g:/taijios-landing/og.png")
img.save(out, "PNG", optimize=True)
size_kb = out.stat().st_size / 1024
print(f"og.png · {W}x{H} · {size_kb:.1f} KB · saved")
