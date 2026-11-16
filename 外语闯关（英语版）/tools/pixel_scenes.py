# -*- coding: utf-8 -*-
"""
像素风场景图生成器 —— 程序化，零积分

⚠️ 重要说明（打包给其他设备使用前必读）
────────────────────────────────────────────────
    本文件是【参考实现】，用于让你理解场景是怎么画出来的、以及想改造时从哪下手。
    它【不是】当前 assets/scenes/ 里那 11 张图的权威生成器 ——

    现存资产在开发过程中经过多轮手工调整（构图适配选项区高度、前景桌下移、
    窗外城市细节微调等），而本文件的版本是事后凭结构复现的，
    像素级比对约 60%~98% 不一致。

    【规则】
      · 不要用本脚本直接覆盖 assets/scenes/，那会替换掉已在游戏中验证过的资产
      · 想换配色/风格 → 先输出到临时目录对比，确认更好再替换：
            python tools/pixel_scenes.py --out _preview
      · 确认满意后再：
            python tools/pixel_scenes.py --out assets/scenes
            python tools/make_ui_scenes.py
      · 只想改一张：
            python tools/pixel_scenes.py coffee --out _preview

为什么用程序化而不是 AI 生成：
    像素风本质就是「有限调色板 + 几何色块」，程序化正好是它的原生方式。
    好处：质量完全可控、风格绝对统一、改参数即可重新生成、一分钱不花。
    NPC 立绘不适合程序化（人物结构易崩），所以那一半用 AI 生成 + 后处理。

用法：
    python tools/pixel_scenes.py              # 生成全部 11 张
    python tools/pixel_scenes.py coffee       # 只生成指定场景
    python tools/pixel_scenes.py --palette cool   # 换一套配色重新生成

输出：
    assets/scenes/scene_xxx.png   原版（1280x720）
    assets/scenes_ui/scene_xxx.png UI 版（加半透明白蒙版，供文字叠加）

改配色的正确姿势：
    只改下面 PALETTE 里的色值，其余不用动。
    全部场景共用这一套调色板，是风格统一的根本原因。
"""
import os
import random
import sys

from PIL import Image, ImageDraw

# ============================ 全局配置 ============================

SCALE = 8                 # 每个"像素"放大 8 倍
BASE_W, BASE_H = 160, 90  # 逻辑像素尺寸（16:9）
SRC_DIR = "assets/scenes"      # 原版输出目录（默认，勿覆盖已验证资产）
DST_DIR = "assets/scenes_ui"   # UI 版输出目录

# 统一调色板 —— 所有场景共用，改这里就能整体换风格
PAL = {
    "ink":    (44, 44, 42),     # 轮廓线 / 深色
    "dark":   (95, 94, 90),     # 次级深色
    "cream":  (241, 239, 232),  # 主背景 / 瓷白
    "green":  (234, 243, 222),  # 浅绿
    "amber":  (250, 199, 117),  # 暖黄
    "orange": (216, 90, 48),    # 主强调色
    "blue":   (55, 138, 221),   # 冷强调色
    "red":    (163, 45, 45),    # 警示色
    "olive":  (99, 153, 34),    # 深绿
    "white":  (255, 255, 255),
    "wood":   (196, 152, 104),  # 桌面
    "wood2":  (178, 134, 88),   # 深木纹
    "night":  (38, 52, 84),     # 窗外夜色
    "sky":    (172, 200, 226),  # 白天窗景
    "floor":  (198, 190, 180),  # 地面
}

# 备用配色方案：python tools/pixel_scenes.py --palette cool
PALETTES = {
    "warm": {},   # 默认
    "cool": {
        "orange": (196, 108, 62), "blue": (48, 118, 190),
        "amber": (236, 196, 132), "olive": (86, 138, 62),
        "wood": (176, 150, 116), "wood2": (152, 126, 94),
        "cream": (238, 240, 242), "green": (228, 238, 236),
    },
    "muted": {
        "orange": (178, 108, 76), "blue": (92, 122, 152),
        "amber": (214, 190, 148), "olive": (108, 130, 82),
        "wood": (186, 164, 132), "wood2": (162, 140, 110),
        "cream": (242, 241, 236), "green": (232, 236, 228),
    },
}


def apply_palette(name):
    if name in ("warm", None, ""):
        return
    for k, v in PALETTES.get(name, {}).items():
        PAL[k] = v


# ============================ 绘图基元 ============================

def new_canvas(w=BASE_W, h=BASE_H, bg="cream"):
    img = Image.new("RGB", (w * SCALE, h * SCALE), PAL[bg])
    return img, ImageDraw.Draw(img)


def px(d, x, y, color, w=1, h=1):
    """画一个逻辑像素块"""
    d.rectangle([x * SCALE, y * SCALE, (x + w) * SCALE - 1, (y + h) * SCALE - 1],
                fill=PAL.get(color, color))


def vgrad(d, x, y, w, h, top, bottom):
    """垂直渐变；h 为从 y 开始的行数"""
    for i in range(h):
        t = i / max(1, h - 1)
        c = tuple(int(top[j] + (bottom[j] - top[j]) * t) for j in range(3))
        yy = y + i
        d.rectangle([x * SCALE, yy * SCALE, (x + w) * SCALE - 1, yy * SCALE + SCALE - 1],
                    fill=c)


def hline(d, x, y, w, color):
    d.rectangle([x * SCALE, y * SCALE, (x + w) * SCALE - 1, y * SCALE],
                fill=PAL.get(color, color))


def vline(d, x, y, h, color):
    d.rectangle([x * SCALE, y * SCALE, x * SCALE, (y + h) * SCALE - 1],
                fill=PAL.get(color, color))


def outline(d, x, y, w, h, color="ink", width=2):
    d.rectangle([x * SCALE, y * SCALE, (x + w) * SCALE - 1, (y + h) * SCALE - 1],
                outline=PAL.get(color, color), width=width)


def picture(d, x, y, w, h, frame="dark", art="amber"):
    """墙上挂画"""
    d.rectangle([x * SCALE, y * SCALE, (x + w) * SCALE, (y + h) * SCALE],
                fill=PAL[frame])
    d.rectangle([(x + 1) * SCALE, (y + 1) * SCALE, (x + w - 1) * SCALE, (y + h - 1) * SCALE],
                fill=PAL["cream"])
    px(d, x + 3, y + 3, art, w - 6, h - 6)


def plant(d, x, y):
    """绿植"""
    px(d, x, y, "wood2", 6, 5)
    for dx, dy, hh in [(0, -8, 8), (3, -6, 6), (-3, -7, 7)]:
        px(d, x + 1 + dx, y + dy, "olive", 4, hh)
    px(d, x + 2, y - 11, "olive", 3, 4)


OUT_DIR = SRC_DIR


def save(img, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"scene_{name}.png")
    img.save(path, "PNG")
    print(f"  -> {path}  {img.size[0]}x{img.size[1]}")
    return path


# ============================ 各场景 ============================

def scene_coffee():
    img, d = new_canvas()
    vgrad(d, 0, 0, BASE_W, 55, (238, 228, 210), (250, 244, 230))
    hline(d, 0, 54, BASE_W, "amber")
    # 左侧窗户（夜色城市）
    d.rectangle([12 * SCALE, 8 * SCALE, 52 * SCALE, 44 * SCALE], fill=PAL["night"])
    random.seed(7)
    for _ in range(28):
        px(d, random.randint(14, 50), random.randint(10, 26), "cream")
    for bx in range(14, 50, 6):
        bh = random.randint(6, 16)
        for wy in range(42 - bh, 42, 3):
            for wx in range(bx + 1, bx + 4, 2):
                if random.random() < .6:
                    px(d, wx, wy, "amber")
    outline(d, 12, 8, 40, 36, "dark", 2)
    vline(d, 32, 8, 36, "dark")
    # 菜单板
    d.rectangle([60 * SCALE, 10 * SCALE, 84 * SCALE, 40 * SCALE], fill=PAL["ink"])
    d.rectangle([62 * SCALE, 12 * SCALE, 82 * SCALE, 38 * SCALE], fill=PAL["cream"])
    for i in range(6):
        hline(d, 64, 15 + i * 4, 14, "dark")
    # 咖啡机
    d.rectangle([96 * SCALE, 18 * SCALE, 116 * SCALE, 46 * SCALE], fill=PAL["dark"])
    d.rectangle([98 * SCALE, 20 * SCALE, 114 * SCALE, 30 * SCALE], fill=(60, 59, 56))
    d.rectangle([102 * SCALE, 32 * SCALE, 110 * SCALE, 42 * SCALE], fill=PAL["ink"])
    # 柜台
    d.rectangle([0 * SCALE, 52 * SCALE, BASE_W * SCALE, 66 * SCALE], fill=PAL["orange"])
    hline(d, 0, 52, BASE_W, "ink")
    hline(d, 0, 64, BASE_W, "ink")
    for cx in (24, 34, 120, 132):
        d.rectangle([cx * SCALE, 47 * SCALE, (cx + 6) * SCALE - 1, 52 * SCALE - 1],
                    fill=PAL["cream"])
        d.rectangle([cx * SCALE, 46 * SCALE, (cx + 6) * SCALE - 1, 48 * SCALE - 1],
                    fill=PAL["white"])
    for bx in (60, 70, 90):
        px(d, bx, 49, "ink")
    # 前景桌面
    d.rectangle([0 * SCALE, 66 * SCALE, BASE_W * SCALE, BASE_H * SCALE], fill=PAL["wood"])
    hline(d, 0, 66, BASE_W, "ink")
    for i in range(0, BASE_W, 9):
        d.line([i * SCALE, 68 * SCALE, (i + 5) * SCALE, 68 * SCALE], fill=PAL["wood2"], width=1)
    # 桌面上的杯子
    d.rectangle([70 * SCALE, 56 * SCALE, 82 * SCALE, 66 * SCALE - 1], fill=PAL["cream"])
    d.rectangle([70 * SCALE, 54 * SCALE, 82 * SCALE, 57 * SCALE - 1], fill=PAL["white"])
    d.ellipse([72 * SCALE, 55 * SCALE, 80 * SCALE, 58 * SCALE], fill=(90, 55, 35))
    d.rectangle([82 * SCALE, 57 * SCALE, 86 * SCALE, 62 * SCALE], outline=PAL["cream"], width=2)
    for i in range(BASE_H - 4, BASE_H):
        d.rectangle([0 * SCALE, i * SCALE, BASE_W * SCALE, i * SCALE], fill=PAL["wood2"])
    save(img, "coffee")


def scene_restaurant():
    img, d = new_canvas()
    vgrad(d, 0, 0, BASE_W, 52, (222, 210, 196), (242, 236, 228))
    hline(d, 0, 51, BASE_W, "wood2")
    # 墙画
    picture(d, 12, 10, 22, 18, frame="wood2", art="olive")
    picture(d, 40, 10, 22, 18, frame="wood2", art="red")
    # 吊灯
    for lx in (78, 100, 122):
        vline(d, lx, 0, 8, "dark")
        d.ellipse([(lx - 4) * SCALE, 8 * SCALE, (lx + 4) * SCALE, 13 * SCALE],
                  fill=PAL["amber"])
    # 背景餐厅区
    d.rectangle([0 * SCALE, 52 * SCALE, BASE_W * SCALE, 64 * SCALE], fill=PAL["wood"])
    hline(d, 0, 52, BASE_W, "ink")
    hline(d, 0, 63, BASE_W, "ink")
    # 桌椅
    for tx in (22, 66, 112):
        px(d, tx, 44, "wood2", 18, 4)      # 桌面
        px(d, tx + 8, 48, "wood2", 2, 14)  # 桌腿
        px(d, tx + 2, 36, "dark", 14, 8)   # 椅背
        px(d, tx + 3, 37, "orange", 12, 6)
    # 桌上的餐具
    for tx in (26, 70, 116):
        px(d, tx, 41, "white", 3, 2)
        px(d, tx + 5, 41, "white", 2, 2)
    # 前景大桌
    d.rectangle([0 * SCALE, 64 * SCALE, BASE_W * SCALE, BASE_H * SCALE], fill=PAL["wood"])
    hline(d, 0, 64, BASE_W, "ink")
    for i in range(0, BASE_W, 11):
        d.line([i * SCALE, 66 * SCALE, (i + 6) * SCALE, 66 * SCALE], fill=PAL["wood2"], width=1)
    # 前景餐具
    px(d, 40, 58, "white", 4, 2)
    px(d, 46, 58, "white", 3, 2)
    px(d, 44, 61, "white", 2, 3)
    px(d, 110, 58, "white", 4, 2)
    px(d, 116, 58, "white", 3, 2)
    # 蜡烛
    px(d, 76, 58, "white", 2, 5)
    px(d, 76, 56, "amber", 2, 2)
    for i in range(BASE_H - 4, BASE_H):
        d.rectangle([0 * SCALE, i * SCALE, BASE_W * SCALE, i * SCALE], fill=PAL["wood2"])
    save(img, "restaurant")


def scene_hotel():
    img, d = new_canvas()
    vgrad(d, 0, 0, BASE_W, 50, (214, 212, 206), (238, 236, 230))
    hline(d, 0, 49, BASE_W, "amber")
    # 大理石背景墙
    for i in range(0, BASE_W, 16):
        vline(d, i, 4, 44, (200, 198, 192))
    # 背后的装饰板
    d.rectangle([58 * SCALE, 6 * SCALE, 102 * SCALE, 44 * SCALE], fill=PAL["wood2"])
    d.rectangle([60 * SCALE, 8 * SCALE, 100 * SCALE, 42 * SCALE], fill=PAL["wood"])
    for i in range(0, 40, 8):
        hline(d, 62, 12 + i, 36, "wood2")
    # 前台
    d.rectangle([0 * SCALE, 50 * SCALE, BASE_W * SCALE, 66 * SCALE], fill=PAL["wood"])
    hline(d, 0, 50, BASE_W, "ink")
    hline(d, 0, 65, BASE_W, "ink")
    d.rectangle([0 * SCALE, 50 * SCALE, BASE_W * SCALE, 53 * SCALE], fill=PAL["wood2"])
    # 登记本与铃
    px(d, 30, 46, "red", 8, 4)
    px(d, 30, 46, "ink", 8, 1)
    px(d, 44, 47, "amber", 3, 3)
    # 钥匙格
    for r in range(3):
        for c in range(8):
            x = 108 + c * 6
            y = 8 + r * 11
            d.rectangle([x * SCALE, y * SCALE, (x + 5) * SCALE, (y + 9) * SCALE],
                        fill=PAL["cream"], outline=PAL["dark"], width=1)
            if (r + c) % 3 == 0:
                px(d, x + 2, y + 3, "amber", 2, 2)
    # 地面
    d.rectangle([0, 66 * SCALE, BASE_W * SCALE, BASE_H * SCALE], fill=PAL["floor"])
    for i in range(0, BASE_W, 18):
        d.line([i * SCALE, 67 * SCALE, (i + 9) * SCALE, BASE_H * SCALE],
               fill=(182, 174, 164), width=1)
    hline(d, 0, 66, BASE_W, "ink")
    plant(d, 14, 66)
    save(img, "hotel")


def scene_airport():
    img, d = new_canvas()
    vgrad(d, 0, 0, BASE_W, 46, (206, 216, 226), (236, 240, 244))
    # 大窗户（停机坪）
    d.rectangle([8 * SCALE, 6 * SCALE, 76 * SCALE, 40 * SCALE], fill=PAL["sky"])
    random.seed(3)
    for _ in range(16):
        px(d, random.randint(12, 72), random.randint(8, 20), "white", 3, 1)
    # 远处飞机
    px(d, 46, 26, "white", 14, 3)
    px(d, 52, 23, "white", 3, 3)
    px(d, 44, 29, "white", 18, 1)
    px(d, 58, 22, "white", 1, 5)
    outline(d, 8, 6, 68, 34, "dark", 2)
    for wx in (22, 42, 62):
        vline(d, wx, 6, 34, "dark")
    # 航班信息屏
    d.rectangle([86 * SCALE, 8 * SCALE, 150 * SCALE, 34 * SCALE], fill=PAL["ink"])
    d.rectangle([88 * SCALE, 10 * SCALE, 148 * SCALE, 32 * SCALE], fill=(30, 30, 40))
    for i in range(5):
        hline(d, 92, 13 + i * 4, 44, "amber")
    # 值机柜台
    d.rectangle([0 * SCALE, 46 * SCALE, BASE_W * SCALE, 62 * SCALE], fill=PAL["blue"])
    hline(d, 0, 46, BASE_W, "ink")
    hline(d, 0, 61, BASE_W, "ink")
    for i in range(8):
        px(d, 8 + i * 19, 50, "white", 2, 6)
    # 传送带
    d.rectangle([0 * SCALE, 62 * SCALE, BASE_W * SCALE, 72 * SCALE], fill=PAL["dark"])
    hline(d, 0, 62, BASE_W, "ink")
    for i in range(0, BASE_W, 8):
        px(d, i, 64, (130, 130, 126), 4, 5)
    # 行李箱
    px(d, 22, 56, "red", 7, 6)
    outline(d, 22, 56, 7, 6, "ink", 1)
    px(d, 100, 55, "olive", 8, 7)
    outline(d, 100, 55, 8, 7, "ink", 1)
    # 地面
    d.rectangle([0, 72 * SCALE, BASE_W * SCALE, BASE_H * SCALE], fill=PAL["floor"])
    hline(d, 0, 72, BASE_W, "ink")
    for i in range(0, BASE_W, 22):
        d.line([i * SCALE, 73 * SCALE, (i + 11) * SCALE, BASE_H * SCALE],
               fill=(182, 174, 164), width=1)
    save(img, "airport")


def scene_subway():
    img, d = new_canvas()
    # 站台顶棚
    d.rectangle([0, 0, BASE_W * SCALE, 14 * SCALE], fill=PAL["dark"])
    hline(d, 0, 13, BASE_W, "ink")
    for i in range(0, BASE_W, 10):
        px(d, i, 3, (130, 130, 126), 6, 1)
    # 后墙瓷砖
    d.rectangle([0, 14 * SCALE, BASE_W * SCALE, 50 * SCALE], fill=(208, 214, 212))
    for i in range(0, BASE_W, 8):
        vline(d, i, 14, 36, (192, 198, 196))
    for j in range(14, 50, 8):
        hline(d, 0, j, BASE_W, (192, 198, 196))
    # 站台柱
    for cx in (18, 74, 130):
        d.rectangle([cx * SCALE, 14 * SCALE, (cx + 6) * SCALE, 58 * SCALE], fill=PAL["cream"])
        d.rectangle([cx * SCALE, 14 * SCALE, (cx + 6) * SCALE, 20 * SCALE], fill=PAL["blue"])
        outline(d, cx, 14, 6, 44, "dark", 1)
    # 线路图
    d.rectangle([52 * SCALE, 24 * SCALE, 78 * SCALE, 42 * SCALE], fill=PAL["ink"])
    d.rectangle([54 * SCALE, 26 * SCALE, 76 * SCALE, 40 * SCALE], fill=PAL["cream"])
    for i in range(5):
        hline(d, 56, 28 + i * 3, 16, "red")
    # 座椅
    d.rectangle([0, 56 * SCALE, BASE_W * SCALE, 60 * SCALE], fill=PAL["blue"])
    hline(d, 0, 55, BASE_W, "ink")
    for cx in (28, 58, 96):
        px(d, cx, 60, "dark", 2, 5)
    # 轨道区
    d.rectangle([0, 64 * SCALE, BASE_W * SCALE, 76 * SCALE], fill=(70, 70, 68))
    hline(d, 0, 64, BASE_W, "ink")
    for i in range(0, BASE_W, 6):
        px(d, i, 70, (100, 100, 96), 4, 2)
    # 远处列车
    d.rectangle([0, 16 * SCALE, BASE_W * SCALE, 44 * SCALE], fill=(120, 130, 140))
    for i in range(4, BASE_W, 14):
        d.rectangle([i * SCALE, 20 * SCALE, (i + 10) * SCALE, 30 * SCALE],
                    fill=PAL["sky"], outline=PAL["dark"], width=1)
    # 地面
    d.rectangle([0, 76 * SCALE, BASE_W * SCALE, BASE_H * SCALE], fill=PAL["floor"])
    hline(d, 0, 76, BASE_W, "ink")
    save(img, "subway")


def scene_shop():
    img, d = new_canvas()
    vgrad(d, 0, 0, BASE_W, 48, (232, 226, 216), (246, 242, 234))
    # 货架（左）
    for r in range(3):
        y = 10 + r * 12
        d.rectangle([6 * SCALE, y * SCALE, 46 * SCALE, (y + 9) * SCALE],
                    fill=PAL["cream"], outline=PAL["dark"], width=1)
        for i in range(6):
            c = ["red", "blue", "olive", "amber", "orange", "green"][(r + i) % 6]
            px(d, 8 + i * 6, y + 2, c, 4, 7)
    # 货架（右）
    for r in range(3):
        y = 14 + r * 11
        d.rectangle([116 * SCALE, y * SCALE, 154 * SCALE, (y + 8) * SCALE],
                    fill=PAL["cream"], outline=PAL["dark"], width=1)
        for i in range(5):
            c = ["amber", "green", "red", "blue", "olive"][(r + i) % 5]
            px(d, 118 + i * 7, y + 2, c, 5, 6)
    # 收银台
    d.rectangle([0, 48 * SCALE, BASE_W * SCALE, 62 * SCALE], fill=PAL["wood"])
    hline(d, 0, 48, BASE_W, "ink")
    hline(d, 0, 61, BASE_W, "ink")
    d.rectangle([54 * SCALE, 42 * SCALE, 76 * SCALE, 48 * SCALE], fill=PAL["dark"])
    d.rectangle([57 * SCALE, 44 * SCALE, 73 * SCALE, 47 * SCALE], fill=(90, 140, 200))
    # 前景陈列台
    d.rectangle([0, 62 * SCALE, BASE_W * SCALE, BASE_H * SCALE], fill=(226, 218, 206))
    hline(d, 0, 62, BASE_W, "ink")
    # 前景商品
    px(d, 30, 54, "red", 5, 8)
    outline(d, 30, 54, 5, 8, "ink", 1)
    px(d, 42, 55, "blue", 4, 7)
    outline(d, 42, 55, 4, 7, "ink", 1)
    px(d, 118, 55, "olive", 6, 7)
    outline(d, 118, 55, 6, 7, "ink", 1)
    for i in range(BASE_H - 4, BASE_H):
        d.rectangle([0, i * SCALE, BASE_W * SCALE, i * SCALE], fill=(210, 202, 190))
    save(img, "shop")


def scene_gate():
    """候机厅 / 航班延误柜台"""
    img, d = new_canvas()
    vgrad(d, 0, 0, BASE_W, 44, (216, 222, 230), (240, 242, 246))
    # 大落地窗
    d.rectangle([6 * SCALE, 6 * SCALE, 88 * SCALE, 38 * SCALE], fill=PAL["sky"])
    random.seed(11)
    for _ in range(12):
        px(d, random.randint(10, 84), random.randint(8, 18), "white", 3, 1)
    px(d, 30, 24, "white", 12, 3)
    px(d, 35, 21, "white", 3, 3)
    outline(d, 6, 6, 82, 32, "dark", 2)
    for wx in (28, 50, 72):
        vline(d, wx, 6, 32, "dark")
    # 航班显示屏
    d.rectangle([98 * SCALE, 8 * SCALE, 154 * SCALE, 30 * SCALE], fill=PAL["ink"])
    d.rectangle([100 * SCALE, 10 * SCALE, 152 * SCALE, 28 * SCALE], fill=(28, 28, 38))
    hline(d, 104, 14, 30, "red")
    for i in range(3):
        hline(d, 104, 19 + i * 3, 22, "amber")
    # 柜台
    d.rectangle([0, 44 * SCALE, BASE_W * SCALE, 58 * SCALE], fill=PAL["blue"])
    hline(d, 0, 44, BASE_W, "ink")
    hline(d, 0, 57, BASE_W, "ink")
    for i in range(7):
        px(d, 10 + i * 21, 47, "white", 2, 6)
    # 候机座椅
    for r in range(2):
        y = 60 + r * 12
        for cx in range(6, 150, 20):
            d.rectangle([cx * SCALE, y * SCALE, (cx + 14) * SCALE, (y + 6) * SCALE],
                        fill=PAL["blue"], outline=PAL["ink"], width=1)
            px(d, cx + 6, y + 6, "dark", 2, 4)
    # 地面
    d.rectangle([0, 58 * SCALE, BASE_W * SCALE, BASE_H * SCALE], fill=PAL["floor"])
    hline(d, 0, 58, BASE_W, "ink")
    for i in range(0, BASE_W, 20):
        d.line([i * SCALE, 59 * SCALE, (i + 10) * SCALE, BASE_H * SCALE],
               fill=(182, 174, 164), width=1)
    save(img, "gate")


def scene_interview():
    img, d = new_canvas()
    vgrad(d, 0, 0, BASE_W, 52, (216, 214, 208), (238, 236, 230))
    # 背景书架
    px(d, 104, 6, "wood2", 50, 40)
    for r in range(4):
        hline(d, 104, 12 + r * 9, 50, "dark")
        for i in range(6):
            c = ["red", "blue", "olive", "amber", "orange", "cream"][(r + i) % 6]
            px(d, 107 + i * 8, 4 + r * 9, c, 6, 8)
    # 左侧窗户
    d.rectangle([10 * SCALE, 8 * SCALE, 44 * SCALE, 40 * SCALE], fill=PAL["sky"])
    for i in range(14, 42, 10):
        px(d, i, 12, "white", 5, 2)
    outline(d, 10, 8, 34, 32, "dark", 2)
    vline(d, 27, 8, 32, "dark")
    # 墙上装饰
    picture(d, 54, 10, 18, 16, frame="dark", art="amber")
    # 面试桌（压到中下部，为选项区留空间）
    d.rectangle([20 * SCALE, 40 * SCALE, 140 * SCALE, 50 * SCALE], fill=PAL["wood"])
    hline(d, 20, 40, 120, "ink")
    hline(d, 20, 50, 120, "ink")
    for i in range(20, 140, 16):
        vline(d, i, 41, 8, "wood2")
    # 桌上：简历、笔、水杯
    px(d, 38, 36, "white", 13, 4)
    px(d, 39, 37, "cream", 11, 2)
    px(d, 40, 38, "dark", 5, 1)
    px(d, 60, 37, "blue", 2, 3)
    px(d, 110, 35, "white", 5, 5)
    px(d, 111, 34, "white", 3, 1)
    # 椅子背
    for cx in (26, 96):
        px(d, cx, 34, "dark", 20, 6)
        px(d, cx + 1, 35, "blue", 18, 4)
    # 地面
    d.rectangle([0, 50 * SCALE, BASE_W * SCALE, BASE_H * SCALE], fill=PAL["floor"])
    for i in range(0, BASE_W, 16):
        d.line([i * SCALE, 51 * SCALE, (i + 8) * SCALE, BASE_H * SCALE],
               fill=(180, 172, 162), width=1)
    hline(d, 0, 50, BASE_W, "ink")
    plant(d, 150, 50)
    save(img, "interview")


def scene_meeting():
    img, d = new_canvas()
    vgrad(d, 0, 0, BASE_W, 48, (222, 222, 218), (244, 243, 238))
    # 白板
    d.rectangle([14 * SCALE, 8 * SCALE, 96 * SCALE, 44 * SCALE], fill=PAL["white"])
    outline(d, 14, 8, 82, 36, "dark", 2)
    # 白板内容（图表）
    for i in range(4):
        hline(d, 20, 14 + i * 6, 30, "dark")
    for i, hgt in enumerate([8, 14, 10, 18]):
        px(d, 60 + i * 8, 38 - hgt, ["blue", "orange", "olive", "red"][i], 5, hgt)
    hline(d, 58, 38, 36, "dark")
    # 投影幕布
    d.rectangle([108 * SCALE, 8 * SCALE, 152 * SCALE, 36 * SCALE], fill=(226, 226, 222))
    outline(d, 108, 8, 44, 28, "dark", 1)
    px(d, 112, 12, "blue", 16, 3)
    for i in range(3):
        hline(d, 112, 18 + i * 4, 24, "dark")
    # 会议桌
    d.rectangle([0, 48 * SCALE, BASE_W * SCALE, 62 * SCALE], fill=PAL["wood"])
    hline(d, 0, 48, BASE_W, "ink")
    hline(d, 0, 61, BASE_W, "ink")
    for i in range(0, BASE_W, 14):
        vline(d, i, 49, 11, "wood2")
    # 桌上：笔记本、水杯、文件
    px(d, 30, 43, "blue", 12, 4)
    px(d, 30, 43, "ink", 12, 1)
    px(d, 70, 42, "white", 5, 5)
    px(d, 71, 41, "white", 3, 1)
    px(d, 100, 43, "white", 8, 4)
    px(d, 101, 44, "dark", 5, 1)
    # 前景座椅
    for cx in (12, 44, 76, 108, 136):
        px(d, cx, 62, "dark", 16, 8)
        px(d, cx + 1, 63, "blue", 14, 6)
    # 地面
    d.rectangle([0, 70 * SCALE, BASE_W * SCALE, BASE_H * SCALE], fill=PAL["floor"])
    hline(d, 0, 70, BASE_W, "ink")
    for i in range(0, BASE_W, 18):
        d.line([i * SCALE, 71 * SCALE, (i + 9) * SCALE, BASE_H * SCALE],
               fill=(182, 174, 164), width=1)
    save(img, "meeting")


def scene_office():
    img, d = new_canvas()
    vgrad(d, 0, 0, BASE_W, 46, (220, 222, 220), (240, 240, 236))
    # 格子间隔断
    for i in range(0, BASE_W, 32):
        d.rectangle([i * SCALE, 0, (i + 2) * SCALE, 46 * SCALE], fill=(186, 190, 188))
    # 远处工位
    for cx in (10, 44, 78, 112):
        d.rectangle([cx * SCALE, 30 * SCALE, (cx + 28) * SCALE, 34 * SCALE], fill=PAL["wood"])
        d.rectangle([cx * SCALE, 16 * SCALE, (cx + 22) * SCALE, 28 * SCALE], fill=PAL["dark"])
        d.rectangle([cx + 2 * SCALE, 18 * SCALE, (cx + 20) * SCALE, 26 * SCALE],
                    fill=(110, 160, 210))
        px(d, cx + 4, 26, "amber", 8, 1)
    # 前景办公桌
    d.rectangle([0, 46 * SCALE, BASE_W * SCALE, 64 * SCALE], fill=PAL["cream"])
    hline(d, 0, 46, BASE_W, "ink")
    hline(d, 0, 63, BASE_W, "ink")
    for i in range(0, BASE_W, 16):
        vline(d, i, 47, 15, (222, 222, 216))
    # 桌上的电脑与文件
    d.rectangle([36 * SCALE, 36 * SCALE, 60 * SCALE, 46 * SCALE], fill=PAL["dark"])
    d.rectangle([39 * SCALE, 38 * SCALE, 57 * SCALE, 44 * SCALE], fill=(120, 165, 210))
    px(d, 46, 44, "dark", 5, 2)
    px(d, 80, 40, "white", 10, 5)
    px(d, 81, 41, "dark", 7, 1)
    px(d, 104, 41, "white", 5, 5)
    px(d, 105, 40, "white", 3, 1)
    # 文件柜
    d.rectangle([134 * SCALE, 8 * SCALE, 158 * SCALE, 46 * SCALE], fill=PAL["dark"])
    for r in range(4):
        y = 10 + r * 9
        d.rectangle([136 * SCALE, y * SCALE, 156 * SCALE, (y + 7) * SCALE],
                    fill=PAL["cream"], outline=PAL["ink"], width=1)
        px(d, 145, y + 3, "dark", 3, 1)
    # 地面
    d.rectangle([0, 64 * SCALE, BASE_W * SCALE, BASE_H * SCALE], fill=(200, 200, 196))
    for i in range(0, BASE_W, 20):
        d.line([i * SCALE, 65 * SCALE, (i + 10) * SCALE, BASE_H * SCALE],
               fill=(184, 184, 180), width=1)
    hline(d, 0, 64, BASE_W, "ink")
    save(img, "office")


def scene_street():
    img, d = new_canvas()
    vgrad(d, 0, 0, BASE_W, 40, (176, 204, 230), (226, 238, 246))
    # 远处楼宇
    for bx, bh in [(10, 24), (26, 32), (44, 20), (60, 28), (78, 34), (98, 22), (118, 30), (138, 26)]:
        d.rectangle([bx * SCALE, (40 - bh) * SCALE, (bx + 14) * SCALE, 40 * SCALE],
                    fill=(150, 158, 166))
        for wy in range(42 - bh, 38, 4):
            for wx in range(bx + 2, bx + 12, 4):
                if random.random() < .55:
                    px(d, wx, wy, "amber")
    hline(d, 0, 39, BASE_W, "ink")
    # 路面
    d.rectangle([0, 40 * SCALE, BASE_W * SCALE, BASE_H * SCALE], fill=(120, 122, 120))
    hline(d, 0, 40, BASE_W, "ink")
    for i in range(0, BASE_W, 16):
        px(d, i, 60, "white", 8, 1)
    # 人行道
    d.rectangle([0, 50 * SCALE, BASE_W * SCALE, 58 * SCALE], fill=(186, 182, 176))
    hline(d, 0, 50, BASE_W, "ink")
    hline(d, 0, 57, BASE_W, "ink")
    # 路牌
    px(d, 20, 20, "dark", 2, 30)
    px(d, 12, 16, "blue", 20, 6)
    outline(d, 12, 16, 20, 6, "ink", 1)
    # 路灯
    for lx in (66, 128):
        px(d, lx, 12, "dark", 2, 38)
        px(d, lx - 3, 10, "dark", 8, 3)
        px(d, lx - 2, 13, "amber", 6, 3)
    # 行人道树
    for tx in (96, 146):
        px(d, tx, 30, "wood2", 3, 20)
        px(d, tx - 4, 22, "olive", 11, 9)
    save(img, "street")


SCENES = {
    "coffee": scene_coffee,
    "restaurant": scene_restaurant,
    "hotel": scene_hotel,
    "airport": scene_airport,
    "subway": scene_subway,
    "shop": scene_shop,
    "gate": scene_gate,
    "interview": scene_interview,
    "meeting": scene_meeting,
    "office": scene_office,
    "street": scene_street,
}


def main():
    global OUT_DIR
    palette = "warm"
    only = None
    out = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--palette" and i + 1 < len(args):
            palette = args[i + 1]; i += 2; continue
        if a == "--out" and i + 1 < len(args):
            out = args[i + 1]; i += 2; continue
        if not a.startswith("--"):
            only = a
        i += 1
    apply_palette(palette)
    if out:
        OUT_DIR = out

    names = [only] if only in SCENES else list(SCENES)
    print(f"生成 {len(names)} 张场景图（调色板：{palette}，输出：{OUT_DIR}）")
    for n in names:
        SCENES[n]()
    if OUT_DIR == SRC_DIR:
        print("完成。接着运行 python tools/make_ui_scenes.py 生成 UI 版")
    else:
        print(f"完成。预览目录：{OUT_DIR} —— 对比确认后再覆盖 assets/scenes/")


if __name__ == "__main__":
    main()
