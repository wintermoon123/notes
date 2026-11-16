# 英语情境闯关 · 项目说明与修改指南

> 一个纯静态的英语情境学习小游戏。10 个真实生活情境，86 道决策题，
> 像素风场景图 + NPC 立绘，进度条达到 90% 即通关。
>
> 在线地址：https://wbapp-y65hcs3ot5xf6jxanygot6.app.workbuddy.host/?sharecode=YN7JDSTZT2
>
> **换设备使用**：解压后双击 `index.html` 即可玩（无需装任何东西）。
> 要改内容，先读这份 README；改完跑 `python tools/self_check.py` 验收。

---

## 一、怎么跑起来

### 方式 A：双击即玩（零配置，推荐先试这个）

直接双击 `index.html`，用浏览器打开就能玩。**不需要装任何东西、不需要起服务器。**

已实测：`file://` 协议下 10 张关卡卡片正常显示、场景图与 NPC 正常加载、答题进度正常推进、
localStorage 存档可用、**零 JS 错误**。

> 存档存在浏览器 localStorage 里，换浏览器或清缓存会丢进度（属正常）。

### 方式 B：本地起服务器（改代码时用）

```bash
# 在项目根目录执行，任选一种
python -m http.server 8765
npx serve .
```

然后浏览器打开 `http://localhost:8765/index.html`。

### 方式 C：重新发布为在线链接

本项目由 WorkBuddy 发布。发布后 `index.html` 会在应用管理面板生成一张应用卡，
线上地址保持在上面的 sharecode 链接。改完代码后重新发布即可覆盖更新，链接不变。

---

## 二、目录结构

```
英语情境闯关/
├── index.html                  ← 游戏主程序（界面 + 全部逻辑，31KB，单文件）
│
├── data/                       ← 【自动生成】改题请改方案书，不要直接改这里
│   ├── questions.js            86 道题：选项、答案、解析
│   └── scenes.js               10 个情境配置：场景图、NPC、进度参数
│
├── assets/
│   ├── scenes/                 11 张原版场景图 1280×720
│   ├── scenes_ui/              11 张 UI 版（加半透明白蒙版，供文字叠加）
│   └── npc/                    9 个 NPC 立绘（透明背景，224px 高）
│
├── tools/                      ← 维护工具链
│   ├── build_data.py           方案书 → data/*.js（唯一数据流入口）
│   ├── check_distinctness.py   选项区分度机器验收
│   ├── make_ui_scenes.py       原版场景图 → UI 版（加蒙版）
│   ├── pixel_scenes.py         场景图生成器（⚠️ 参考实现，勿直接覆盖）
│   ├── postprocess.py          AI 图 → 像素立绘后处理管线
│   └── build_npcs.py           NPC 批量构建
│
├── 英语情境闯关_方案书.md        ← 【唯一数据源】题库正文都在这里
├── 选项重写规范.md               干扰项设计规范（v3 决策分岔型）
├── 干扰项验收清单.md             出题质量验收标准
├── 教学点索引.md                 语料库出处与教学点清单
├── 美术资产清单.md               美术资产规格与成本账
├── 视觉风格方案.md               五种画风对比与选型依据
├── 未解决问题清单.md             待办与决策记录
└── 语言学习小游戏_方案书.md       上位方案（含韩语版规划）
```

---

## 三、修改指南

### A. 改题目（最常做的事）

**唯一数据源是 `英语情境闯关_方案书.md`，不要直接改 `data/questions.js`**（它是自动生成的，会被覆盖）。

流程：

```
1. 改 英语情境闯关_方案书.md 里的题库章节（第 4 章）
2. python tools/build_data.py        ← 重新生成 data/questions.js 和 scenes.js
3. python tools/check_distinctness.py  ← 验收选项区分度
4. 浏览器打开确认
```

**题目格式**（方案书里长这样）：

```markdown
#### DP1 · 店员问你要什么 | 考点：点单请求句式
> NPC：「Hi there! What can I get started for you?」

- **A. Could I get a large iced latte, please?** ✅
- B. Actually, do you sell any pastries?
- C. Actually, could I get that hot instead?
- D. Sorry, I need to check my schedule first.

**解析**：正确项用 `Could I get…please` 完成点单，是咖啡店最地道的说法。`sell any pastries`转移到了另一件事上——店员要你说的是「要什么」，不是反问店里有什么甜点。`could I get that hot instead`改了需求（要热的），没有完成点单。`I need to check my schedule first`说的是自己的安排，完全没有点单。
```

**四个选项的构成规则（v3 决策分岔型）**——这是选项质量的硬约束：

| 层次 | 缺陷 | 例子 |
|---|---|---|
| ✅ 正确项 | 完成当前任务 | `Could I get a large iced latte, please?` |
| L1 | 转移话题——问了另一件事 | `Actually, do you sell any pastries?` |
| L2 | 改需求——做了另一件事 | `Actually, could I get that hot instead?` |
| L3 | 无关回应——说的是自己的事 | `Sorry, I need to check my schedule first.` |

四条硬规则：
1. **意图互斥** —— 四个选项表达四种不同的交际动作
2. **场景合法** —— 三个干扰项都是真实对话里说得出口的话，语法正确
3. **唯一最优** —— 只凭「此刻该说什么」就能选出答案
4. **微差异禁用** —— 不用「只差一个词」的干扰项，差异必须体现在语义

**解析格式约束**：**不要用字母指代选项**（写「B 转移了话题」）。
用字母的话，`build_data.py` 重排答案位置后解析必然错位。
正确写法是用选项原文的短句指代：

```
`sell any pastries`转移到了另一件事上
```

> `build_data.py` 会自动把答案位置按 `A→C→B→D` 循环重排（每情境内），
> 保证全局分布均匀（A/C 各 23、B/D 各 20）。解析不受影响，因为不含字母。

### B. 改情境配置

进度机制在方案书里定义，改完同样跑 `build_data.py`：

```python
# tools/build_data.py 里的 SCENE_META
SCENE_META = {
    1: {"id": "coffee", "name": "咖啡店点单", "category": "dining",
        "scene": "assets/scenes_ui/scene_coffee.png",
        "npc": "assets/npc/barista.png",
        "npcName": "店员", "steps": 8, "stepGain": 10, ...},
    ...
}
```

**进度数学约束**（改题数时务必保持）：

| 情境类型 | 起始 | 每题增量 | 题数 | 满进度 | 达标线 | 容错 |
|---|---|---|---|---|---|---|
| 普通情境 | 20% | +10% | 8 | 100% | 90% | 1 题 |
| 复杂情境 | 20% | +8% | 10 | 100% | 90% | 1 题 |

复杂情境（10 题）用 +8% 而不是 +10%，是为了让满进度恰好 100% 不溢出，
同时保持容错统一为 1 题。

### C. 改界面

全部在 `index.html` 里，纯 HTML + CSS + 原生 JS，零依赖、零 CDN。

主要结构：
- `#topbar` 顶栏 · `#home` 关卡网格 · `#play` 情境页 · `#result` 结算页 · `#vocab` 生词本
- 配色变量在 `:root`（`--ink` `--cream` `--orange` `--blue` `--olive` `--red` 等）
- 存档用 `localStorage`，key 前缀 `lexiquest_`

改完直接刷新浏览器即可（`file://` 也能刷新）。

### D. 改美术

**场景图**：

```bash
# UI 版可随时从原版重新生成（改蒙版强度用 --alpha）
python tools/make_ui_scenes.py
python tools/make_ui_scenes.py --alpha 60
```

⚠️ `tools/pixel_scenes.py` 是**参考实现**，不是现资产的权威生成器——
现存 11 张图在开发中经过多轮手工调整，直接用它覆盖会丢失那些调整。
想换风格请先输出到别处对比：

```bash
python tools/pixel_scenes.py --out _preview      # 生成全部到预览目录
python tools/pixel_scenes.py coffee --out _preview  # 只生成一张
# 确认更好后再：
python tools/pixel_scenes.py --out assets/scenes
python tools/make_ui_scenes.py
```

**NPC 立绘**：需要先用 AI 生成（提示词模板见 `tools/build_npcs.py` 文件头），
再跑 `python tools/build_npcs.py` 过一遍后处理管线，保证风格统一。

---

## 四、校验清单

### 一键自检（推荐）

```bash
python tools/self_check.py
```

检查 6 项：file:// 直接玩（10 关全部可进入 + 完整通关 + 零 JS 错误）· 改题重建链路 ·
选项区分度 · UI 场景图重建 · 场景图生成器 · 资源引用完整性。

输出 `★ 全部通过` 即可发布。首次运行若提示缺 playwright：

```bash
pip install playwright && python -m playwright install chromium
```

### 分项校验

```bash
python tools/build_data.py          # 方案书 -> data/*.js（校验结构、答案位置、进度数学）
python tools/check_distinctness.py  # 选项区分度（期望：0 题不通过）
python tools/make_ui_scenes.py      # 原版场景图 -> UI 版
```

### 浏览器手动实测

双击 `index.html`，逐关走一遍，重点确认：进度条递增正确、结算页错题清单与生词本生成正常、
移动端（390px 宽）布局无重叠。

`check_distinctness.py` 的判据是**实义词 Jaccard 重叠度 ≥ 0.7** 即判为
「玩家读不出区别」。开发时这个问题在 86 题里有 46 题（53%）命中，
全部按 v3 范式重写后归零。

---

## 五、已知限制

| 项 | 说明 |
|---|---|
| AI 点评未接真实云服务 | 代码与降级逻辑已写好，需在 WorkBuddy 激活云服务后填 `window.CLOUD_CONFIG`；未配置时走本地点评，功能不断 |
| NPC 分配有复用 | 9 个角色覆盖 10 个情境（地铁/街头共用路人，商店/候机共用店员），当前可接受 |
| 解析未做母语者审校 | 脚本能保证「解析引用与选项对得上」，但母语者的语感判断更准——建议找英语老师过一遍 |
| 场景图无原始生成记录 | `tools/pixel_scenes.py` 为事后复现版，非像素级一致 |

---

## 六、下一步可做什么

- 接真实云服务的 AI 教练点评（代码已就位）
- 韩语版（题库结构已为双语预留，见 `语言学习小游戏_方案书.md`）
- NPC 表情变体（当前用界面角标代替，理由见 `美术资产清单.md`）
- 加生活场景（看医生、租房看房）平衡当前 2/5/3 的配比
