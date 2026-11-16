# -*- coding: utf-8 -*-
"""
选项区分度检测器 —— 「决策分岔型」范式质检

检测两类缺陷：
  D1 干扰项 vs 正确答案：实义内容词重叠过高（Jaccard ≥ 0.5）或意图标记几乎相同
  D2 干扰项 vs 干扰项：两者实义内容词重叠过高（J ≥ 0.6）或意图标记几乎相同

方法：
  - 去掉礼貌词/虚词，只留【实义词】（词干前 5 字符归一）
  - 意图标记：把同义表达归一到同一 MARK
  - Jaccard = |交集| / |并集|
"""
import re, io, json, sys, collections, subprocess

FILLER = {
    "i", "you", "we", "they", "he", "she", "it", "me", "my", "your", "our", "their",
    "please", "thanks", "thank", "ok", "okay", "yeah", "yes", "no", "not",
    "would", "could", "can", "will", "shall", "may", "might", "should",
    "like", "want", "need", "get", "go", "do", "have", "has", "had", "be", "been",
    "am", "is", "are", "was", "were", "to", "of", "for", "with", "at", "in", "on",
    "and", "or", "but", "so", "if", "that", "this", "there", "here",
    "a", "an", "the", "some", "any", "very", "much", "more", "most", "really",
    "just", "also", "too", "quite", "kind", "sort", "bit", "well",
    "s", "t", "m", "re", "ll", "d", "ve", "one", "thing", "things", "lot",
}

INTENT_GROUPS = [
    (r"\bpay(ing|s)?\b|\bpaid\b", "PAY"),
    (r"\bcard\b", "CARD"), (r"\bcash\b", "CASH"),
    (r"\breceipt\b", "RECEIPT"), (r"\bbag\b|\bbaggage\b|\bluggage\b", "BAG"),
    (r"\bmilk\b", "MILK"), (r"\boat\b", "OAT"),
    (r"\bwhole\b", "WHOLE"), (r"\bskim\b", "SKIM"),
    (r"\biced\b", "ICED"), (r"\bhot\b", "HOT"), (r"\bcold\b", "COLD"),
    (r"\blatte\b", "LATTE"), (r"\bcoffee\b", "COFFEE"),
    (r"\bsize\b|\blarge\b|\bmedium\b|\bsmall\b", "SIZE"),
    (r"\bcheck(ed)?\s+in\b", "CHECKIN"), (r"\bboard(ing)?\b", "BOARD"),
    (r"\bgate\b", "GATE"), (r"\bflight\b|\bflights\b", "FLIGHT"),
    (r"\bticket\b|\btickets\b", "TICKET"), (r"\bhotel\b|\broom\b", "STAY"),
    (r"\bmeeting\b|\bproject\b|\bteam\b|\bwork\b|\bjob\b|\brole\b", "WORK"),
    (r"\bmuseum\b", "MUSEUM"), (r"\bsubway\b|\bmetro\b", "TRANSIT"),
    (r"\binterview(er)?\b", "INTERVIEW"), (r"\bexpense\b|\breimburs\w*\b", "EXPENSE"),
    (r"\bshift\b", "SHIFT"), (r"\breport\b|\bdata\b|\bfigure\b|\bnumber\b", "DATA"),
    (r"\bproposal\b|\bdeck\b|\bdraft\b", "DRAFT"),
    (r"\bprice\b|\bcost\b|\bdollar\b", "PRICE"), (r"\bfee\b", "FEE"),
    (r"\bexchange\b", "EXCHANGE"), (r"\bshop\b|\bstore\b|\bbuy\b", "SHOP"),
    (r"\bappointment\b|\bbook\b|\breserv\w*\b", "BOOK"),
    (r"\bhelp\b|\bassist\b|\bhand\b", "HELP"),
    (r"\bdelay\w*\b|\bwait\w*\b|\blate\b", "DELAY"),
    (r"\btime\b|\bhour\b|\bminute\b|\bmonday\b|\btuesday\b|\bwednesday\b|\bthursday\b|\bfriday\b", "TIME"),
    (r"\bname\b", "NAME"), (r"\bwater\b", "WATER"), (r"\bbread\b", "BREAD"),
    (r"\bsoup\b", "SOUP"), (r"\bsalmon\b|\bfish\b|\bsteak\b|\bchicken\b", "FOOD"),
    (r"\bnapkin\w*\b|\bcutlery\b|\bfork\b|\bknife\b|\bspoon\b", "CUTLERY"),
    (r"\bbill\b|\bcheck\b", "BILL"),
    (r"\bwalk\b|\bwalkway\b|\bcorner\b|\bleft\b|\bright\b|\bstraight\b", "DIRECTION"),
    (r"\btrain\b|\bplatform\b", "TRAIN"),
    (r"\bwear\b|\bfit\b", "WEAR"),
    (r"\bpresident\b|\bceo\b|\bhiring\b|\bcandidate\b", "HIRE"),
    (r"\bweakness\b|\bstrength\b", "TRAIT"),
    (r"\badvice\b|\bsuggest\w*\b|\brecommend\w*\b", "ADVISE"),
    (r"\bslide\w*\b|\bquarter\b|\brevenue\b|\bchurn\b", "MEET"),
]


def content_words(text):
    t = text.lower().replace("'s", " ").replace("n't", " ")
    t = t.replace("'re", " ").replace("'ll", " ").replace("'m", " ")
    out = set()
    for w in re.findall(r"[a-z]+", t):
        if w in FILLER or len(w) <= 2:
            continue
        out.add(w[:5])
    return out


def jaccard(a, b):
    if not a or not b:
        return 0.0
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def intent_marks(text):
    """交际动作标记 —— 判定「这句在做什么」而非「提到了什么名词」

    关键：名词重叠不代表同义（「我要拿铁」vs「拿铁更浓吗？」动作完全不同）
    真正判同义的是【动作谓词 + 句式框架】都一致
    """
    t = text.lower()
    m = set()

    # --- 句式框架 ---
    # 疑问句：按【问的内容】细分，而不是一律标 QUESTION
    if "?" in text:
        m.add("QUESTION")
        # 问时间/几点
        if re.search(r"\bwhat time\b|\bwhen\b|\bhow long\b|\buntil\b|\bby when\b", t):
            m.add("Q_TIME")
        # 问价格/费用
        elif re.search(r"\bhow much\b|\bprice\b|\bcost\b|\bpay\b|\bfee\b|\bcharge\b", t):
            m.add("Q_PRICE")
        # 问是否可���（can/could + 主语）
        elif re.search(r"\b(is|are|do|does|did|can|could|would|will|has|have)\s+(i|we|you|it|there|you\s+have|you\s+get)", t):
            m.add("Q_YESNO")
        # 问地点/方位
        elif re.search(r"\bwhere\b|\bwhich exit\b|\bwhich gate\b|\bwhich terminal\b", t):
            m.add("Q_PLACE")
        # 问是否可以换/改
        elif re.search(r"\bchange\b|\bexchange\b|\bswap\b|\bmove\b|\bsplit\b|\bdiscount\b", t):
            m.add("Q_CHANGE")
        # 询问对方能否做（请求型）
        elif re.search(r"\bcould you\b|\bcan you\b|\bwould you\b|\bwill you\b", t):
            m.add("Q_REQUEST")
        # 询问信息/内容
        elif re.search(r"\bwhat\b|\bwhich\b|\bwho\b|\bhow\b|\btell me\b", t):
            m.add("Q_INFO")
        else:
            m.add("Q_OTHER")
    # 祈使句（以动词原形开头，无主语）
    if re.match(r"^(use|give|tell|show|write|call|pay|order|check|bring|keep|come|put|wait)\b", t.strip()):
        m.add("IMPERATIVE")

    # --- 动作谓词 ---
    for pat, mk in ACTION_GROUPS:
        if re.search(pat, t):
            m.add(mk)

    # --- 拒绝 / 同意 ---
    if re.search(r"\b(no|not|nope)\b", t):
        m.add("NEG")
    if re.search(r"\b(yes|sure|certainly|of course|absolutely)\b", t):
        m.add("POS")

    return m


# 动作谓词分组（比名词更严格：必须是「做什么」）
ACTION_GROUPS = [
    (r"\bpay(ing|s)?\b|\bpaid\b|\bcharge\b|\bspend\b", "PAY"),
    (r"\border(ing)?\b|\bwant to order\b|\bi'd like\b|\bi would like\b|\bcan i (get|have)\b|\bcould i (get|have)\b", "ORDER"),
    (r"\bbuy(ing)?\b|\bpurchase\b", "BUY"),
    (r"\breceipt\b|\binvoice\b|\bbill\b", "GET_DOC"),
    (r"\bask(ing)?\b|\brequest(ing)?\b|\bwant to ask\b", "REQUEST"),
    (r"\bchange(ing)?\b|\bswitch(ing)?\b|\bswap(ping)?\b|\bmove me\b|\brebook\b", "CHANGE"),
    (r"\bconfirm(ing)?\b|\bcheck\b|\bverify\b|\bdouble-check\b", "CONFIRM"),
    (r"\bapolog(ize|ise|ising|y)\b|\bsorry\b|\bmy mistake\b", "APOLOGIZE"),
    (r"\bthank\b", "THANK"),
    (r"\bdecline(ing)?\b|\bcan'?t\b|\bcan not\b|\bunable\b|\bnot possible\b|\bafraid i\b", "DECLINE"),
    (r"\bexplain(ing)?\b|\bclarify(ing)?\b|\bmean\b|\bjustify\b", "EXPLAIN"),
    (r"\bdiscuss(ing)?\b|\btalk about\b|\bbring up\b", "DISCUSS"),
    (r"\bsuggest(ing)?\b|\brecommend(ing)?\b|\bpropose\b|\badvise\b", "SUGGEST"),
    (r"\bconfirm(ing)?\b", "CONFIRM2"),
    (r"\baccept(ing)?\b|\bgo ahead\b|\bfine\b|\bworks for me\b", "ACCEPT"),
    (r"\bwait(ing)?\b|\bhold on\b", "WAIT"),
    (r"\bcollect(ing)?\b|\bpick up\b|\bget my bag\b", "COLLECT"),
    (r"\bcall(ing)?\b|\bphone\b|\bcontact\b|\breach\b", "CONTACT"),
    (r"\bwalk(ing)?\b|\bgo straight\b|\bturn left\b|\bturn right\b", "DIRECT"),
    (r"\bwear(ing)?\b|\btry(ing)? on\b|\bfit\b|\bexchange for\b", "WEAR"),
    (r"\bhelp(ing)?\b|\bassist\b|\bdo you mind\b", "HELP"),
    (r"\bshare\b|\bpass it\b|\bspread\b", "SHARE"),
    (r"\bintroduce\b|\bintroduc\w+\b|\bhand over\b|\bhandover\b", "INTRO"),
    (r"\bnegotiat\w+\b|\bwork out\b|\bcompromise\b", "NEGOTIATE"),
    (r"\bapolog\w+\b|\bexcuse me\b", "APOLOGIZE2"),
]


def analyze_items(items):
    problems = []
    for q in items:
        opts = q["options"]
        if len(opts) != 4:
            problems.append({"id": q.get("id", ""), "type": "structure",
                             "msg": f"选项数={len(opts)}"})
            continue
        ai = q["answer"]
        correct = opts[ai]
        c_cw = content_words(correct)
        c_int = intent_marks(correct)

        for i, o in enumerate(opts):
            if i == ai:
                continue
            ow = content_words(o)
            oi = intent_marks(o)
            j = jaccard(c_cw, ow)
            ji = (len(c_int & oi) / len(c_int | oi)) if (c_int | oi) else 0.0
            # 主判据：实义词高度重叠 = 玩家读不出区别
            # 辅助判据：动作谓词完全一致 且 实义词也高重叠（双重确认，避免误报）
            same_action = (ji >= 0.8) and len(c_int & oi) >= 1
            if j >= 0.7 or (same_action and j >= 0.5 and len(c_cw) >= 2 and len(ow) >= 2):
                problems.append({"id": q.get("id", ""), "type": "vs_correct",
                                 "i": i, "j": round(j, 2), "ji": round(ji, 2), "t": o})
            for k in range(i + 1, len(opts)):
                if k == ai:
                    continue
                j2 = jaccard(ow, content_words(opts[k]))
                oi2 = intent_marks(opts[k])
                j2i = (len(oi & oi2) / len(oi | oi2)) if (oi | oi2) else 0.0
                same_action = (j2i >= 0.85) and len(oi & oi2) >= 1
                if j2 >= 0.7 or (same_action and j2 >= 0.5):
                    problems.append({"id": q.get("id", ""), "type": "pair", "a": i, "b": k,
                                     "j": round(j2, 2), "ji": round(j2i, 2),
                                     "ta": o, "tb": opts[k]})
    return problems


def load(path):
    if path.endswith(".json"):
        raw = json.loads(io.open(path, encoding="utf-8").read())
        if isinstance(raw, dict):
            out = []
            for k, v in raw.items():
                q = dict(v)
                q["id"] = k
                q.setdefault("focus", "")
                out.append(q)
            return out
        return raw
    subprocess.run(["node", "-e",
        "global.window={};require('./data/questions.js');"
        "require('fs').writeFileSync('_q.json',JSON.stringify(window.QUESTIONS))"], check=True)
    return json.loads(io.open("_q.json", encoding="utf-8").read())


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/questions.js"
    Q = load(path)
    problems = analyze_items(Q)
    by_q = collections.defaultdict(list)
    for p in problems:
        by_q[p["id"]].append(p)

    print(f"共 {len(Q)} 题，检出 {len(by_q)} 题存在区分度问题\n")
    for qid, ps in by_q.items():
        q = next((x for x in Q if x.get("id") == qid), None)
        print(f"=== {qid}" + (f" | {q.get('focus','')}" if q else "") + " ===")
        if q:
            for i, o in enumerate(q["options"]):
                print(f"  {'*' if i == q['answer'] else ' '}{'ABCD'[i]}. {o}")
        for p in ps:
            if p["type"] == "vs_correct":
                kind = "同义" if p["ji"] >= 0.8 else "近似"
                print(f'    ⚠ {kind}: {p["t"][:58]}  (J={p["j"]} 意图重合={p["ji"]})')
            elif p["type"] == "pair":
                print(f'    ⚠ 两干扰项撞车: {p["ta"][:36]} || {p["tb"][:36]} (J={p["j"]} 意图重合={p["ji"]})')
            else:
                print(f'    ⚠ {p["msg"]}')
        print()
