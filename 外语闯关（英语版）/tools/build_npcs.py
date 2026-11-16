# -*- coding: utf-8 -*-
"""
NPC 立绘批量构建 —— AI 原始图 → 统一规格立绘

【当前状态说明】
    开发时的 AI 原始输出目录（assets/npc_ai/）已在发布清理阶段删除，
    只保留了处理好的成品 assets/npc/*.png（9 张，224px 高，透明背景）。

    因此本脚本现在【无法直接跑通】——它需要你重新用 AI 生成原始图。
    保留它的意义是：一旦你要新增/替换 NPC 角色，这套管线能保证
    新角色和现有 9 张的风格一致（同样的像素网格、同样的调色板量化、同样的尺寸）。

【新增 NPC 的完整流程】
    1. 用 AI 图像生成，提示词模板（照抄，改职业描述即可）：

       Pixel art character sprite, 32x32 pixel art style, upper body bust portrait
       of a <职业描述>, front facing, <发型>, <肤色>, <服装>,
       neutral calm expression, clean flat colors, limited 10 color palette,
       bold dark outline, centered, solid plain white background,
       crisp pixel edges, no anti-aliasing, 1990s game sprite aesthetic

    2. 把生成结果存成 PNG（背景是纯白，不是透明）

    3. 跑本脚本：
           python tools/build_npcs.py

    4. 在 data/scenes.js 里把对应情境的 npc 字段改成新文件名

【为什么需要后处理】
    AI 出的「像素风」有两个问题：透明背景参数常不生效（实际是白底）、
    像素格不是整数倍且边缘有半透明羽化（缩小后糊成一团）。
    postprocess.py 做四件事：去白底 → 对齐像素网格 → 量化 32 色 → 最近邻缩放。
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from postprocess import process  # noqa: E402

SRC_DIR = "assets/npc_ai"
DST_DIR = "assets/npc"

# 角色清单：文件名 -> 中文描述
ROLES = [
    ("barista",      "咖啡店 · 店员"),
    ("waiter",       "餐厅 · 服务员"),
    ("receptionist", "酒店 · 前台"),
    ("checkin",      "机场 · 值机员"),
    ("commuter",     "地铁/街头 · 路人"),
    ("clerk",        "商店 · 店员"),
    ("shopper",      "商店 · 顾客"),
    ("manager",      "面试/会议 · 面试官"),
    ("colleague",    "办公室 · 同事"),
]


def main():
    if not os.path.isdir(SRC_DIR):
        raise SystemExit(
            f"找不到 AI 原始输出目录：{SRC_DIR}\n"
            f"当前成品在 {DST_DIR}/（已保留）。\n"
            f"若要新增角色，先按本文件头部的提示词模板生成 PNG 存到 {SRC_DIR}/ 再运行。"
        )

    files = sorted(glob.glob(os.path.join(SRC_DIR, "*.png")))
    if not files:
        raise SystemExit(f"{SRC_DIR} 里没有 PNG 文件。")

    if len(files) != len(ROLES):
        print(f"⚠️  源图 {len(files)} 张，角色清单 {len(ROLES)} 个 —— 请按顺序核对映射关系")

    os.makedirs(DST_DIR, exist_ok=True)
    for (role, desc), f in zip(ROLES, files):
        dst = os.path.join(DST_DIR, f"{role}.png")
        size = process(f, dst, target_h=224, grid=8, colors=32)
        print(f"  {role:14s} {desc:20s} {size[0]}x{size[1]}")

    print(f"\n完成 {min(len(files), len(ROLES))} 个角色。")
    print("下一步：在 data/scenes.js 里更新对应情境的 npc 字段")


if __name__ == "__main__":
    main()
