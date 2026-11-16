# -*- coding: utf-8 -*-
"""
从 assets/scenes/ 生成 assets/scenes_ui/（UI 版场景图）

为什么需要这一步：
    场景图要作为文字的衬底，必须压低对比度。做法是在原图上叠一层
    半透明白色（alpha=46/255，约 18%），既保留像素画面的质感，
    又让叠加的英文台词和选项文字有足够可读性。

用法：
    python tools/make_ui_scenes.py
    python tools/make_ui_scenes.py --alpha 60     # 自定义蒙版强度
"""
import os
import sys
from PIL import Image, ImageDraw

SRC_DIR = "assets/scenes"
DST_DIR = "assets/scenes_ui"
DEFAULT_ALPHA = 46      # 0-255，约 18% 白


def make_ui(src_dir=SRC_DIR, dst_dir=DST_DIR, alpha=DEFAULT_ALPHA):
    if not os.path.isdir(src_dir):
        raise SystemExit(f"找不到源目录：{src_dir}")
    os.makedirs(dst_dir, exist_ok=True)

    names = sorted(f for f in os.listdir(src_dir) if f.lower().endswith(".png"))
    if not names:
        raise SystemExit(f"{src_dir} 里没有 PNG 文件")

    for name in names:
        im = Image.open(os.path.join(src_dir, name)).convert("RGBA")
        overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        d.rectangle([0, 0, im.size[0], im.size[1]], fill=(255, 255, 255, alpha))
        out = Image.alpha_composite(im, overlay)
        dst = os.path.join(dst_dir, name)
        out.save(dst, "PNG")
        print(f"  {name:26s} {im.size[0]}x{im.size[1]}  alpha={alpha}")

    print(f"完成：{len(names)} 张 UI 场景图 -> {dst_dir}")
    return len(names)


if __name__ == "__main__":
    a = DEFAULT_ALPHA
    if "--alpha" in sys.argv:
        i = sys.argv.index("--alpha")
        a = int(sys.argv[i + 1])
    make_ui(alpha=a)
