# -*- coding: utf-8 -*-
"""对 cap add android 生成的工程应用「后台保活」补丁"""
import os, shutil, glob
from PIL import Image, ImageDraw

ROOT = r"D:/WorkBuddyProject/rhythm-reminder/android/android"
RES = os.path.join(ROOT, "app/src/main/res")
JAVA = os.path.join(ROOT, "app/src/main/java/com/rhythm/reminder")
ASSETS = r"D:/WorkBuddyProject/rhythm-reminder/assets"
PATCH = r"D:/WorkBuddyProject/.wb_tmp/native_patch"

# ---------- 1. MainActivity：注册本地插件 ----------
main_activity = '''package com.rhythm.reminder;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(RhythmNativePlugin.class);
        super.onCreate(savedInstanceState);
    }
}
'''
with open(os.path.join(JAVA, "MainActivity.java"), "w", encoding="utf-8") as f:
    f.write(main_activity)
print("[1] MainActivity patched")

# ---------- 2. 复制两个 Java 类 ----------
shutil.copy(os.path.join(PATCH, "RhythmNativePlugin.java"), os.path.join(JAVA, "RhythmNativePlugin.java"))
shutil.copy(os.path.join(PATCH, "ForegroundService.java"), os.path.join(JAVA, "ForegroundService.java"))
print("[2] Java classes copied")

# ---------- 3. AndroidManifest：权限 + 前台服务 ----------
mf = os.path.join(ROOT, "app/src/main/AndroidManifest.xml")
with open(mf, encoding="utf-8") as f:
    xml = f.read()

perms = '''
    <!-- 后台保活所需权限 -->
    <uses-permission android:name="android.permission.VIBRATE" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.USE_EXACT_ALARM" />
    <uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" />
    <uses-permission android:name="android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS" />
'''
anchor = '    <uses-permission android:name="android.permission.INTERNET" />'
assert anchor in xml, "INTERNET permission anchor not found"
xml = xml.replace(anchor, anchor + perms, 1)

service = '''
        <service
            android:name=".ForegroundService"
            android:enabled="true"
            android:exported="false"
            android:foregroundServiceType="mediaPlayback" />
'''
anchor2 = "    </application>"
assert anchor2 in xml
xml = xml.replace(anchor2, service + anchor2, 1)

with open(mf, "w", encoding="utf-8") as f:
    f.write(xml)
print("[3] AndroidManifest patched")

# ---------- 4. 应用图标 ----------
for d in glob.glob(os.path.join(ASSETS, "mipmap-*")):
    den = os.path.basename(d)
    dst = os.path.join(RES, den)
    os.makedirs(dst, exist_ok=True)
    for name in ("ic_launcher.png", "ic_launcher_round.png", "ic_launcher_foreground.png"):
        src = os.path.join(d, name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(dst, name))
print("[4] mipmap icons copied")

# 通知小图标（白色铃/节奏条）
for d in glob.glob(os.path.join(ASSETS, "drawable-*")):
    den = os.path.basename(d)
    dst = os.path.join(RES, den)
    os.makedirs(dst, exist_ok=True)
    shutil.copy(os.path.join(d, "ic_stat_bell.png"), os.path.join(dst, "ic_stat_bell.png"))
print("[5] notification icon copied")

# ---------- 5. 提示音 ----------
raw_dir = os.path.join(RES, "raw")
os.makedirs(raw_dir, exist_ok=True)
for name in ("ding_small.wav", "ding_big.wav"):
    shutil.copy(os.path.join(ASSETS, name), os.path.join(raw_dir, name))
print("[6] sounds copied")

# ---------- 6. 自适应图标背景色 ----------
bg_file = os.path.join(RES, "values/ic_launcher_background.xml")
with open(bg_file, encoding="utf-8") as f:
    bg = f.read()
bg = bg.replace("#FFFFFF", "#0E1116")
with open(bg_file, "w", encoding="utf-8") as f:
    f.write(bg)
print("[7] ic_launcher_background -> #0E1116")

# ---------- 7. styles.xml：深色启动背景 ----------
st = os.path.join(RES, "values/styles.xml")
with open(st, encoding="utf-8") as f:
    s = f.read()
old = '''    <style name="AppTheme.NoActionBarLaunch" parent="Theme.SplashScreen">
        <item name="android:background">@drawable/splash</item>
    </style>'''
new = '''    <style name="AppTheme.NoActionBarLaunch" parent="Theme.SplashScreen">
        <item name="android:background">@drawable/splash</item>
        <item name="windowSplashScreenBackground">#0E1116</item>
        <item name="postSplashScreenTheme">@style/AppTheme.NoActionBar</item>
    </style>'''
assert old in s, "styles anchor not found"
s = s.replace(old, new, 1)
with open(st, "w", encoding="utf-8") as f:
    f.write(s)
print("[8] styles patched")

# ---------- 8. 深色启动图 ----------
BG_TOP = (26, 38, 52); BG_BOT = (14, 17, 22)
BLUE_L = (43, 140, 255); BLUE_H = (140, 220, 255); AMBER = (255, 184, 77)

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def make_splash(w, h):
    img = Image.new("RGB", (w, h), BG_BOT)
    px = img.load()
    for y in range(h):
        c = lerp(BG_TOP, BG_BOT, y / max(1, h - 1))
        for x in range(w):
            px[x, y] = c
    d = ImageDraw.Draw(img)
    cx = w / 2
    cy = h / 2
    unit = min(w, h)
    bar_w = unit * 0.075
    heights = [0.24, 0.36, 0.46, 0.36, 0.24]
    gap = bar_w * 0.62
    total = 5 * bar_w + 4 * gap
    x0 = cx - total / 2
    for i, hh in enumerate(heights):
        bh = unit * hh
        x = x0 + i * (bar_w + gap)
        d.rounded_rectangle([x, cy - bh / 2, x + bar_w, cy + bh / 2],
                            radius=bar_w / 2, fill=lerp(BLUE_L, BLUE_H, i / 4))
    r = bar_w * 0.34
    dy = cy - unit * heights[2] / 2 - bar_w * 1.15
    d.ellipse([cx - r, dy - r, cx + r, dy + r], fill=AMBER)
    return img

sizes = {
    "drawable/splash.png": (480, 320),
    "drawable-land-mdpi/splash.png": (480, 320),
    "drawable-land-hdpi/splash.png": (800, 480),
    "drawable-land-xhdpi/splash.png": (1280, 720),
    "drawable-land-xxhdpi/splash.png": (1600, 960),
    "drawable-land-xxxhdpi/splash.png": (1920, 1280),
    "drawable-port-mdpi/splash.png": (320, 480),
    "drawable-port-hdpi/splash.png": (480, 800),
    "drawable-port-xhdpi/splash.png": (720, 1280),
    "drawable-port-xxhdpi/splash.png": (960, 1600),
    "drawable-port-xxxhdpi/splash.png": (1280, 1920),
}
for rel, (w, h) in sizes.items():
    make_splash(w, h).save(os.path.join(RES, rel))
print("[9] splash images regenerated (dark)")
print("ALL PATCHES DONE")
