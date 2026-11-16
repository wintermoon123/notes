# -*- coding: utf-8 -*-
"""
AI 生成图的像素化后处理管线

为什么需要这一步：
    ImageGen 出的「像素风」图有两个问题：
      1. 透明背景参数经常不生效，实际是白底
      2. 像素格不是整数倍、边缘有半透明羽化，缩小后糊成一团

    本管线做四件事：
      1. 去白底     —— 按角落采样推断背景色，去掉接近背景的像素
      2. 对齐网格   —— 缩放到 SCALE 的整数倍，强制像素格对齐
      3. 量化调色板 —— 统一到有限色数，与程序化场景图共用一套观感
      4. 最近邻缩放 —— 保持像素锐利，不做插值

用法：
    python tools/postprocess.py <源图.png> <目标.png> [目标高度]
    python tools/postprocess.py <源图.png> <目标.png> 224 --grid 8 --colors 32
"""
import sys
import os
from PIL import Image


def remove_background(im, bg_color=None, tol=42):
    """去掉背景，返回 RGBA 图。bg_color 为 None 时按四角投票推断。"""
    im = im.convert("RGBA")
    w, h = im.size

    if bg_color is None:
        samples = [
            im.getpixel((0, 0)), im.getpixel((w - 1, 0)),
            im.getpixel((0, h - 1)), im.getpixel((w - 1, h - 1)),
            im.getpixel((w // 2, 0)), im.getpixel((w // 2, h - 1)),
        ]
        # 取出现次数最多的（忽略 alpha 通道）
        from collections import Counter
        bg_color = Counter([s[:3] for s in samples]).most_common(1)[0][0]

    r, g, b = bg_color
    px = im.load()
    for y in range(h):
        for x in range(w):
            cr, cg, cb, ca = px[x, y]
            if abs(cr - r) + abs(cg - g) + abs(cb - b) <= tol:
                px[x, y] = (cr, cg, cb, 0)
    return im, bg_color


def snap_to_grid(im, grid=8):
    """缩放到 grid 的整数倍（最近邻），让像素格对齐"""
    w, h = im.size
    tw = max(grid, (w // grid) * grid)
    th = max(grid, (h // grid) * grid)
    if (tw, th) != (w, h):
        im = im.resize((tw, th), Image.NEAREST)
    return im


def quantize(im, colors=32):
    """统一到有限调色板，保证与程序化场景图观感一致"""
    rgb = im.convert("RGB")
    q = rgb.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE)
    out = q.convert("RGBA")
    # 把 alpha 通道拷回去
    out.putalpha(im.getchannel("A"))
    return out


def process(src, dst, target_h=224, grid=8, colors=32, tol=42):
    im = Image.open(src)
    im, bg = remove_background(im, tol=tol)
    im = snap_to_grid(im, grid)
    im = quantize(im, colors)

    # 缩放到目标高度（最近邻，保持像素锐利）
    w, h = im.size
    if h > target_h:
        ratio = target_h / h
        im = im.resize((max(1, int(w * ratio)), target_h), Image.NEAREST)
    elif h < target_h:
        ratio = target_h / h
        im = im.resize((int(w * ratio), target_h), Image.NEAREST)

    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    im.save(dst, "PNG")
    print(f"  {os.path.basename(src)} -> {dst}  {im.size[0]}x{im.size[1]}  bg={bg}")
    return im.size


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    src = sys.argv[1]
    dst = sys.argv[2]
    th = int(sys.argv[3]) if len(sys.argv) > 3 else 224
    grid = 8
    colors = 32
    if "--grid" in sys.argv:
        grid = int(sys.argv[sys.argv.index("--grid") + 1])
    if "--colors" in sys.argv:
        colors = int(sys.argv[sys.argv.index("--colors") + 1])
    process(src, dst, target_h=th, grid=grid, colors=colors)
