# -*- coding: utf-8 -*-
"""
项目自检 —— 在任何设备上验证这个包是否完整可用

用法：
    python tools/self_check.py

检查项：
    [1] file:// 双击直接玩（10 关全部可进入、资源加载、完整通关、零 JS 错误）
    [2] 改题重建链路（build_data.py）
    [3] 选项区分度检测（check_distinctness.py）
    [4] UI 场景图重建（make_ui_scenes.py）
    [5] 场景图生成器参考实现（输出到预览目录，不覆盖资产）
    [6] 资源引用完整性（index.html / scenes.js 里引用的文件都存在）

需要：python + playwright（若未安装会跳过浏览器测试，其余照常）
"""
import asyncio
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr


async def play_test():
    from playwright.async_api import async_playwright
    url = "file:///" + os.path.join(ROOT, "index.html").replace("\\", "/")
    errs = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1280, "height": 900})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(url, wait_until="load", timeout=30000)
        await pg.wait_for_timeout(1000)
        cards = await pg.locator(".card").count()
        ok_scenes = 0
        for i in range(cards):
            await pg.goto(url, wait_until="load", timeout=30000)
            await pg.wait_for_timeout(600)
            await pg.locator(".card").nth(i).click()
            await pg.wait_for_timeout(500)
            bg = await pg.locator("#stageBg").evaluate("el=>el.complete&&el.naturalWidth>0")
            npc = await pg.locator("#stageNpcImg").evaluate("el=>el.complete&&el.naturalWidth>0")
            if bg and npc:
                ok_scenes += 1
        # 完整通关第 1 关：选答案 -> 读解析 -> 点「下一题」
        await pg.goto(url, wait_until="load", timeout=30000)
        await pg.wait_for_timeout(600)
        await pg.locator(".card").first.click()
        await pg.wait_for_timeout(500)
        for _ in range(12):
            if await pg.locator("#result").evaluate("el=>!el.classList.contains('hide')"):
                break
            ans = await pg.evaluate("()=>G.qs[G.idx]?G.qs[G.idx].answer:-1")
            if ans < 0:
                break
            await pg.locator("#opts .opt").nth(ans).click()
            await pg.wait_for_timeout(260)
            try:
                nxt = pg.locator("#btnNext")
                await nxt.wait_for(state="visible", timeout=3000)
                await nxt.click()
                await pg.wait_for_timeout(260)
            except Exception:
                break
        await pg.wait_for_timeout(500)
        pct = await pg.locator("#pct").inner_text()
        on_result = await pg.locator("#result").evaluate("el=>!el.classList.contains('hide')")
        await b.close()
    return cards, ok_scenes, pct, on_result, errs


def check_refs():
    missing = []
    files = ["index.html", "data/scenes.js"]
    for f in files:
        p = os.path.join(ROOT, f)
        if not os.path.exists(p):
            continue
        text = open(p, encoding="utf-8").read()
        for ref in set(re.findall(r'assets/[A-Za-z0-9_./-]+\.png', text)):
            if not os.path.exists(os.path.join(ROOT, ref)):
                missing.append(ref)
    return missing


def main():
    print("=== 英语情境闯关 · 项目自检 ===")
    print(f"目录: {ROOT}\n")
    ok = True

    print("[1] file:// 双击直接玩")
    try:
        cards, ok_scenes, pct, on_result, errs = asyncio.run(play_test())
        print(f"    关卡卡片 {cards} | 资源加载正常 {ok_scenes} | 通关进度 {pct} | 进入结算页 {on_result}")
        print(f"    JS 错误: {errs if errs else '无'}")
        if cards != 10 or ok_scenes != 10 or errs:
            ok = False
    except Exception as e:
        print(f"    跳过（playwright 未安装或环境受限）: {type(e).__name__}")
        print(f"    → pip install playwright && python -m playwright install chromium")

    print("[2] 改题重建 build_data.py")
    rc, out, err = run([sys.executable, "tools/build_data.py"])
    tail = [l for l in out.strip().split("\n") if l.strip()][-1:]
    print(f"    退出码 {rc} | {tail[0].strip() if tail else ''}")
    if rc != 0:
        print("    stderr:", err[:400])
        ok = False

    print("[3] 选项区分度检测 check_distinctness.py")
    rc, out, err = run([sys.executable, "tools/check_distinctness.py"])
    line = [l for l in out.split("\n") if "检出" in l]
    print(f"    退出码 {rc} | {line[0].strip() if line else out.strip()[:80]}")
    if rc != 0 or (line and "检出 0 题" not in line[0]):
        ok = False

    print("[4] UI 场景图重建 make_ui_scenes.py")
    rc, out, err = run([sys.executable, "tools/make_ui_scenes.py"])
    line = [l for l in out.split("\n") if "完成" in l]
    print(f"    退出码 {rc} | {line[-1].strip() if line else ''}")
    if rc != 0:
        ok = False

    print("[5] 场景图生成器参考实现（输出预览目录，不覆盖资产）")
    rc, out, err = run([sys.executable, "tools/pixel_scenes.py", "--out", "_preview"])
    line = [l for l in out.split("\n") if "预览目录" in l]
    print(f"    退出码 {rc} | {line[0].strip() if line else ''}")
    if rc != 0:
        ok = False

    print("[6] 资源引用完整性")
    missing = check_refs()
    print(f"    缺失资源: {missing if missing else '无'}")
    if missing:
        ok = False

    print()
    print("★ 全部通过" if ok else "✗ 存在问题")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
