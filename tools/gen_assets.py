# -*- coding: utf-8 -*-
"""生成「节律提醒」应用图标与提示音资源"""
import math, os, struct, wave
from PIL import Image, ImageDraw

OUT = r"D:/WorkBuddyProject/rhythm-reminder/assets"
os.makedirs(OUT, exist_ok=True)

BG_TOP = (26, 38, 52)      # #1a2634
BG_BOT = (14, 17, 22)      # #0e1116
BLUE_L = (43, 140, 255)    # #2b8cff
BLUE_M = (76, 194, 255)    # #4cc2ff
BLUE_H = (140, 220, 255)   # #8cdcff
AMBER  = (255, 184, 77)    # #ffb84d


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgrad(size, top, bot):
    """竖向渐变底图"""
    col = Image.new("RGB", (1, size))
    for y in range(size):
        col.putpixel((0, y), lerp(top, bot, y / (size - 1)))
    return col.resize((size, size))


def draw_bars(draw, cx, cy, scale, bar_w, heights, colors, dot=True):
    """以 (cx,cy) 为中心画一组圆角竖条 + 顶部提示点"""
    n = len(heights)
    gap = bar_w * 0.62
    total_w = n * bar_w + (n - 1) * gap
    x0 = cx - total_w / 2
    for i in range(n):
        h = heights[i] * scale
        x = x0 + i * (bar_w + gap)
        y0 = cy - h / 2
        draw.rounded_rectangle([x, y0, x + bar_w, y0 + h], radius=bar_w / 2, fill=colors[i])
    if dot:
        mid_h = heights[n // 2] * scale
        dy = cy - mid_h / 2 - bar_w * 1.15
        r = bar_w * 0.34
        draw.ellipse([cx - r, dy - r, cx + r, dy + r], fill=AMBER)


def make_app_icon(size, rounded_bg=True, pad_ratio=0.0):
    """完整应用图标；pad_ratio>0 时留透明边（用于自适应前景）"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inner = int(size * (1 - pad_ratio * 2))
    layer = Image.new("RGBA", (inner, inner), (0, 0, 0, 0))
    if rounded_bg:
        bg = vgrad(inner, BG_TOP, BG_BOT).convert("RGBA")
        mask = Image.new("L", (inner, inner), 0)
        md = ImageDraw.Draw(mask)
        md.rounded_rectangle([0, 0, inner - 1, inner - 1], radius=int(inner * 0.22), fill=255)
        layer.paste(bg, (0, 0), mask)
    d = ImageDraw.Draw(layer)
    bar_w = int(inner * 0.085)
    heights = [0.30, 0.46, 0.60, 0.46, 0.30]
    colors = [lerp(BLUE_L, BLUE_H, i / 4) for i in range(5)]
    draw_bars(d, inner / 2, inner / 2, inner, bar_w, heights, colors)
    img.paste(layer, (int(size * pad_ratio), int(size * pad_ratio)), layer)
    return img


def make_small_icon(size):
    """白色通知小图标（24dp 各密度）"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bar_w = int(size * 0.16)
    gap = int(size * 0.10)
    heights = [0.42, 0.62, 0.42]
    total_w = 3 * bar_w + 2 * gap
    x0 = (size - total_w) / 2
    for i, h in enumerate(heights):
        bh = size * h
        x = x0 + i * (bar_w + gap)
        y0 = (size - bh) / 2
        d.rounded_rectangle([x, y0, x + bar_w, y0 + bh], radius=bar_w / 2, fill=(255, 255, 255, 255))
    return img


# ---------- 1. Electron 图标 ----------
icon512 = make_app_icon(512)
icon512.save(os.path.join(OUT, "icon.png"))
icon512.save(os.path.join(OUT, "icon.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

# ---------- 2. Android mipmap 图标 ----------
mipmap = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
for den, px in mipmap.items():
    d = os.path.join(OUT, "mipmap-" + den)
    os.makedirs(d, exist_ok=True)
    ic = make_app_icon(px)
    ic.save(os.path.join(d, "ic_launcher.png"))
    ic.save(os.path.join(d, "ic_launcher_round.png"))
    fg = make_app_icon(px, rounded_bg=False, pad_ratio=0.18)
    fg.save(os.path.join(d, "ic_launcher_foreground.png"))

# 自适应背景（渐变）
fg108 = make_app_icon(432, rounded_bg=False, pad_ratio=0.18)
fg108.save(os.path.join(OUT, "ic_launcher_foreground_432.png"))

# ---------- 3. 通知小图标 ----------
drawable = {"mdpi": 24, "hdpi": 36, "xhdpi": 48, "xxhdpi": 72, "xxxhdpi": 96}
for den, px in drawable.items():
    d = os.path.join(OUT, "drawable-" + den)
    os.makedirs(d, exist_ok=True)
    make_small_icon(px).save(os.path.join(d, "ic_stat_bell.png"))

print("icons done")


# ---------- 4. 提示音 WAV（复刻 App 内叮咚音色） ----------
SR = 44100

def tone_samples(freq, dur_s, delay_s, gain=0.7):
    start = int(delay_s * SR)
    n = int(dur_s * SR)
    out = [0.0] * (start + n + int(0.05 * SR))
    attack = int(0.015 * SR)
    for i in range(n):
        t = i / SR
        env = 1.0
        if i < attack:
            env = i / attack
        else:
            env = math.exp(-3.2 * (t - 0.015))
        v = math.sin(2 * math.pi * freq * t) * env * gain
        out[start + i] = v
    return out

def ding_once(buf, offset_ms):
    s1 = tone_samples(880, 0.26, offset_ms / 1000.0)
    s2 = tone_samples(1318, 0.20, (offset_ms + 80) / 1000.0, gain=0.35)
    m = max(len(s1), len(s2))
    if len(buf) < m:
        buf.extend([0.0] * (m - len(buf)))
    for i in range(len(s1)):
        buf[i] += s1[i]
    for i in range(len(s2)):
        buf[i] += s2[i]

def save_wav(path, buf):
    peak = max(0.0001, max(abs(v) for v in buf))
    norm = 0.89 / peak
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        frames = bytearray()
        for v in buf:
            s = max(-1, min(1, v * norm))
            frames += struct.pack("<h", int(s * 32767))
        w.writeframes(bytes(frames))

GAP_MS = 400
small = []
for i in range(2):
    ding_once(small, i * GAP_MS)
save_wav(os.path.join(OUT, "ding_small.wav"), small)

big = []
for i in range(4):
    ding_once(big, i * GAP_MS)
save_wav(os.path.join(OUT, "ding_big.wav"), big)

print("sounds done")
print(os.listdir(OUT))
