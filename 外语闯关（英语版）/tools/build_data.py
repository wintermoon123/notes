# -*- coding: utf-8 -*-
"""
从方案书生成 data/questions.js 与 data/scenes.js

方案书是唯一数据源。解析文本已在方案书中写成「内容指代」格式（不含字母），
因此选项重排不会造成解析错位。
"""
import re, io, json, os, collections

SRC = "英语情境闯关_方案书.md"
OPT_RE = re.compile(r'^- (\*{0,2})([ABCD])\. (.*?)(\*{0,2})( ✅)?\s*$')
SCENE_RE = re.compile(r'^### 情境 (\d+) · (.+)$')
DP_RE = re.compile(r'^#### DP(\d+) · (.+)$')

# 情境 id 与美术资源映射
SCENE_META = {
    1:  dict(id="coffee",     npc="barista",      cat="dining", name="咖啡店点单",     scene="coffee",
            brief="下午三点，街角的咖啡店。你要给自己点一杯饮料。"),
    2:  dict(id="restaurant", npc="waiter",       cat="dining", name="餐厅晚餐",       scene="restaurant",
            brief="晚上七点，餐厅。同事还没到，你得先点。"),
    3:  dict(id="hotel",      npc="receptionist", cat="travel", name="酒店入住",       scene="hotel",
            brief="晚上十点半，你拖着行李箱走进酒店大堂。"),
    4:  dict(id="airport",    npc="checkin",      cat="travel", name="机场值机与转机", scene="airport",
            brief="清晨的机场，你要在中转柜台办完一切。"),
    5:  dict(id="subway",     npc="commuter",     cat="travel", name="问路与地铁",     scene="subway",
            brief="你第一次来这座城市，地铁站的指示牌看不太懂。"),
    6:  dict(id="shop",       npc="clerk",        cat="travel", name="购物与退换货",   scene="shop",
            brief="这件衣服买回去发现尺码不对，你回到店里。"),
    7:  dict(id="gate",       npc="clerk",        cat="travel", name="航班延误改签",   scene="gate",
            brief="你的航班延误三小时，而你今天必须到。"),
    8:  dict(id="interview",  npc="manager",      cat="work",   name="求职面试",       scene="interview",
            brief="终面。面试官合上简历，看着你。"),
    9:  dict(id="meeting",    npc="manager",      cat="work",   name="会议汇报",       scene="meeting",
            brief="季度业务评审。你是今天第一个汇报的人。"),
    10: dict(id="office",     npc="colleague",    cat="work",   name="职场求助与拒绝", scene="office",
            brief="同事在茶水间拦住你，眼里有点着急。"),
}
NPC_NAME = {"barista": "店员", "waiter": "服务员", "receptionist": "前台",
            "checkin": "值机员", "commuter": "路人", "clerk": "店员",
            "manager": "面试官", "colleague": "同事"}


def parse():
    text = io.open(SRC, encoding="utf-8").read()
    lines = text.split("\n")
    scenes, cur_scene, cur_dp = [], None, None
    for ln in lines:
        ms = SCENE_RE.match(ln)
        if ms:
            cur_scene = {"no": int(ms.group(1)), "title": ms.group(2).strip(),
                         "goal": "", "cover": "", "dps": []}
            scenes.append(cur_scene); cur_dp = None; continue
        if cur_scene is None:
            continue
        md = DP_RE.match(ln)
        if md:
            cur_dp = {"no": int(md.group(1)), "focus": md.group(2).strip(),
                      "npc": "", "options": [], "explain": ""}
            cur_scene["dps"].append(cur_dp); continue
        if cur_dp is None:
            if ln.startswith("**目标**"):
                cur_scene["goal"] = ln.replace("**目标**：", "").strip()
            elif ln.startswith("**考点覆盖**"):
                cur_scene["cover"] = ln.replace("**考点覆盖**：", "").strip()
            continue
        if ln.startswith("> NPC："):
            cur_dp["npc"] = re.sub(r'^> NPC：「|」$', '', ln).strip(); continue
        mo = OPT_RE.match(ln)
        if mo:
            cur_dp["options"].append({"L": mo.group(2), "text": mo.group(3).strip(),
                                      "ok": bool(mo.group(5))}); continue
        if ln.startswith("**解析**"):
            cur_dp["explain"] = ln.replace("**解析**：", "").strip()
    return scenes


def main():
    scenes = parse()
    questions, scene_meta = [], []
    for sc in scenes:
        meta = SCENE_META[sc["no"]]
        sid = meta["id"]
        steps = len(sc["dps"])
        complex_scene = steps > 8
        questions.extend(sc["dps"])
        scene_meta.append({
            "id": sid, "order": sc["no"], "name": meta["name"],
            "nameEn": sc["title"].split("（")[0].split("(")[0].strip(),
            "category": meta["cat"],
            "cefr": sc["title"].split("（")[-1].rstrip("）") if "（" in sc["title"] else "B1",
            "goal": sc["goal"], "brief": meta["brief"], "focus": sc["cover"],
            "steps": steps, "startProgress": 20,
            "stepGain": 8 if complex_scene else 10, "passAt": 90,
            "scene": f"assets/scenes_ui/scene_{meta['scene']}.png",
            "npc": f"assets/npc/{meta['npc']}.png",
            "npcName": NPC_NAME[meta["npc"]],
        })

    # ---- 答案位置重排：每情境内按 ACBD 循环 ----
    # 解析已是「内容指代」格式（不含字母），重排不会造成解析错位
    CYCL = ["A", "C", "B", "D"]
    scene_ctr = collections.Counter()
    for sc in scenes:
        sid = SCENE_META[sc["no"]]["id"]
        for dp in sc["dps"]:
            opts = dp["options"]
            ans_idx = [i for i, o in enumerate(opts) if o["ok"]][0]
            correct_text = opts[ans_idx]["text"]
            distract = [o["text"] for i, o in enumerate(opts) if i != ans_idx]
            target = CYCL[scene_ctr[sid] % 4]
            scene_ctr[sid] += 1
            letters = ["A", "B", "C", "D"]
            di = 0
            new_opts = []
            for L in letters:
                if L == target:
                    new_opts.append({"L": L, "text": correct_text, "ok": True})
                else:
                    new_opts.append({"L": L, "text": distract[di], "ok": False}); di += 1
            dp["options"] = new_opts

    os.makedirs("data", exist_ok=True)
    qjs = ["/* 英语情境闯关 · 题库（自动生成，勿手改） */", "window.QUESTIONS = ["]
    for sc in scenes:
        sid = SCENE_META[sc["no"]]["id"]
        for dp in sc["dps"]:
            qjs.append("  {")
            qjs.append(f'    id: "{sid}_dp{dp["no"]}",')
            qjs.append(f'    scene: "{sid}",')
            qjs.append(f'    step: {dp["no"]},')
            qjs.append(f'    focus: {json.dumps(dp["focus"], ensure_ascii=False)},')
            qjs.append(f'    npc: {json.dumps(dp["npc"], ensure_ascii=False)},')
            opts = ", ".join(json.dumps(o["text"], ensure_ascii=False) for o in dp["options"])
            qjs.append(f'    options: [{opts}],')
            ans = [i for i, o in enumerate(dp["options"]) if o["ok"]][0]
            qjs.append(f'    answer: {ans},')
            qjs.append(f'    explain: {json.dumps(dp["explain"], ensure_ascii=False)}')
            qjs.append("  },")
    qjs.append("];")
    io.open("data/questions.js", "w", encoding="utf-8").write("\n".join(qjs))

    sjs = ["/* 英语情境闯关 · 情境配置（自动生成，勿手改） */", "window.SCENES = " +
           json.dumps(scene_meta, ensure_ascii=False, indent=2) + ";"]
    io.open("data/scenes.js", "w", encoding="utf-8").write("\n".join(sjs))

    dist = collections.Counter()
    for sc in scenes:
        for dp in sc["dps"]:
            dist[[i for i, o in enumerate(dp["options"]) if o["ok"]][0]] += 1
    print(f"题目 {len(questions)} 道 -> data/questions.js")
    print(f"情境 {len(scene_meta)} 个 -> data/scenes.js")
    print(f"答案分布: {dict(dist)}")
    for m in scene_meta:
        print(f'  {m["order"]:>2} {m["name"]:<12} {m["steps"]}题 '
              f'起始{m["startProgress"]}% 每题+{m["stepGain"]}% 达标{m["passAt"]}%')


if __name__ == "__main__":
    main()
