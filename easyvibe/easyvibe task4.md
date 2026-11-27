# task4：为原型接入 AI 能力

## 教程规定的作业要求

参考本节课的提示词和内容，为原型接入一种真实 AI 能力：

- 从页面里选一个真正需要 AI 的按钮，第一版只接一种能力，不必把文本、图片、语音和视频全部做完；
- 在官方文档中找到当前 Model ID 和最小示例；
- 把示例交给 AI IDE，接到页面中的按钮上；
- 把 API Key 放在服务端环境变量中，并为等待和失败加上提示；
- 实际调用一次，再到日志中确认请求已经到达平台；
- 保存一张运行截图，并用一句话说明 AI 在这个页面里帮用户做了什么。

预期产出：能够调用真实 AI 服务的 Web 原型。

## 我选的功能：把「生成知识卡片」接到真实大模型

上次作业思考题里列了五个可嵌入点，最值得先做的是第（1）项：把模拟解析 `mockParse()` 换成大模型调用。它直接替换原型里最“假”的环节，输出结构正好就是已经设计好的卡片字段，不用改数据结构。

| 项目 | 内容 |
| --- | --- |
| 用户动作 | 粘贴网址 / 上传 TXT、Markdown / 直接粘贴文本，点击「生成知识卡片」 |
| AI 做的事 | 阅读资料，直接输出标题、一句话核心、3–5 条要点、领域、标签的 JSON |
| 输入类型 | 文字（网址会先在服务端抓取正文，再作为文字送给模型） |
| 能力判断 | 文本生成；网页抓取是普通程序，不是 AI 能力 |
| 一句话说明 | AI 帮用户把零散资料整理成结构一致、可继续编辑的知识卡片草稿 |

教程提醒“一个功能有时会分成几步”。这里就是两步：网址 → 服务端抓正文（普通程序）→ 大模型整理成卡片（AI）。登录、保存、页面跳转仍然用普通程序实现。

## 先把生成结果试出来

在写接口代码前，先按教程的方法把任务描述清楚。程序自动附加的固定要求放在 system prompt 里，用户只需要自然输入：

```text
你是一个知识卡片整理助手。请把用户提供的资料整理成一张结构化知识卡片。
只返回 JSON，不要 Markdown 代码块，不要任何解释文字。
JSON 格式：
{"title": "string", "domain": "string", "core": "string", "points": ["string"], "tags": ["string"]}
要求：
- title 不超过 20 个字；
- domain 从 产品设计、商业、写作、自助成长、理财、科技、其他 里选一个；
- core 用一句话说清核心内容；
- points 给 3 到 5 条，每条不超过 40 个字；
- tags 给 2 到 4 个；
- 不要编造资料里没有的事实；资料不足时如实写“资料中未提及”。
```

这样设计的原因和教程里的商品文案例子一样：页面要分别显示标题、核心、要点、标签，就必须让模型稳定返回这些字段；规则应该由程序固定附加，而不是要求每位用户学会写提示词。我另外用两组不同资料试了，确认输出会跟着输入变化，而不是返回一套通用套话。

## 服务平台与模型 ID

教程反复强调：服务平台名称、Model ID 和 API 地址不是一回事，要从当前官方文档复制，不要照抄教程里的版本号。我最初照旧平台的示例填写，踩了两个坑：

| 项目 | 值 | 说明 |
| --- | --- | --- |
| 平台 | 腾讯云 TokenHub | 国内直连，OpenAI 兼容接口 |
| Base URL | `https://tokenhub.tencentmaas.com/v1` | 老地址 `api.hunyuan.cloud.tencent.com/v1` 对新 Key 返回 401 |
| 完整路径 | `https://tokenhub.tencentmaas.com/v1/chat/completions` | 从官方文档的最小示例复制 |
| Model ID | `hy4-flash` | 从 `/v1/models` 查当前账号可用值；`hunyuan-lite` 在 TokenHub 报“服务 ID 不存在” |
| 环境变量 | `HUNYUAN_API_KEY` / `HUNYUAN_BASE_URL` / `HUNYUAN_MODEL` | 写在服务端 `.env.local`，不提交 Git |

这两个坑正好印证教程说的：401 先查 Key 和请求头，404 /“服务不存在”先查 Base URL、Endpoint 和 Model ID。确认一次终端请求能返回后，才把示例交给 AI IDE。

## 接入架构：Key 不进浏览器

```text
浏览器页面
  │ 只发送资料文本和模板信息
  ▼
自己的 /api/generate-cards（本地 Vite 中间件 / 云函数）
  │ 读取服务端环境变量中的 API Key
  ▼
TokenHub /v1/chat/completions
  │ 返回 JSON
  ▼
页面显示卡片；失败时降级为模拟数据并提示
```

给 AI IDE 的接入提示词（核心）：

```text
请在现有项目基础上接入腾讯混元的文本生成能力，替代 mockParse()。

要求：
1. API Key 放在服务端 .env.local，前端不接触 Key；
2. 用 Vite dev middleware 提供 /api/generate-cards 接口；
3. 服务端调用 https://tokenhub.tencentmaas.com/v1/chat/completions，
   model 用从 /v1/models 查到的 hy4-flash；
4. system prompt 要求模型只返回 JSON：title、domain、core、points、tags，
   不要编造资料里没有的事实；
5. 服务端解析 JSON 并补上 source、note、relations 字段；
6. 前端按钮调用自己的 /api 接口，加入等待、成功、失败状态；
7. Key 未配置或调用失败时降级为原来的模拟数据，并明确提示用户。
```

代码分工：

| 文件 | 作用 |
| --- | --- |
| `cloudfunctions/generateCards/index.js` | 本地与线上共用的 AI 调用核心：提示词、抓正文、JSON 解析、脱敏日志、云函数入口 |
| `plugins/hunyuanApi.js` | Vite dev middleware，挂载 `/api/generate-cards` |
| `src/App.jsx` | 按钮、等待状态、成功/失败提示、降级标记 |
| `.env.example` | 说明需要配置哪些变量，避免把真实 Key 提交 |

## 关键修复：看似成功，其实一直走的是模拟数据

教程说“页面显示了文字，并不一定代表它真的来自 API”。这次我正好遇到了。

上一次作业后，项目为了 GitHub Pages 静态部署把 Vite 的 `base` 改成了 `/knowledgecard/`。前端原本用 `${import.meta.env.BASE_URL}api/generate-cards` 拼接口地址，于是实际请求变成 `/knowledgecard/api/generate-cards`；而中间件挂载的是 `/api/generate-cards`，返回 404。前端捕获错误后按设计降级为模拟数据，页面照样出现卡片，肉眼很难发现。

修复方式：前端统一用

```js
const AI_API_URL = import.meta.env.VITE_AI_API_URL || '/api/generate-cards'
```

本地开发走 Vite 中间件；部署后填云函数的 HTTP 地址。修复后在浏览器里重新点击按钮，卡片没有「模拟数据」标记，服务端日志出现 `status: 200`，这才算真正接通。

## 补上 Serverless：让线上也能真实调用

Vite dev middleware 只在本机开发时存在，`npm run build` 产出的静态文件里没有后端。按教程第 5 节的思路，我把接口补成了腾讯云 CloudBase 云函数，并且让本地和线上共用同一份核心代码，避免两边行为不一致。

云函数入口 `cloudfunctions/generateCards/index.js` 导出 `main(event, context)`，兼容 HTTP 触发的 `event`（含 `httpMethod`、`body`、`isBase64Encoded`）和直接调用；处理 OPTIONS 预检并返回 CORS 头；从 `context.requestId` 取请求 ID 写进日志。日志只记录时间、模型、来源数量、状态码、耗时和 requestId，不记录 Key 或用户原文：

```text
[generate-cards] {"time":"2026-11-27T12:11:19.691Z","model":"hy4-flash","sourceCount":1,"requestId":"","status":200,"durationMs":4035}
```

部署步骤（需要有自己的 CloudBase 环境 ID，Key 在云函数控制台配置，不写进仓库）：

```bash
npm install -g @cloudbase/cli
tcb login

# 部署云函数（Node.js 18.15，入口 index.js 的 main）
tcb fn deploy generateCards --path cloudfunctions/generateCards -e <你的环境ID>

# 在控制台：云函数 → generateCards → 函数配置 → 环境变量
# 添加 HUNYUAN_API_KEY、HUNYUAN_BASE_URL、HUNYUAN_MODEL

# 创建 HTTP 访问路由
tcb service create -f generateCards -p /generate-cards -e <你的环境ID>
```

得到形如 `https://<环境ID>.<区域>.app.tcloudbase.com/generate-cards` 的地址后，写进本地 `.env.local`：

```text
VITE_AI_API_URL=https://<环境ID>.<区域>.app.tcloudbase.com/generate-cards
```

再重新 `npm run build`。`VITE_` 前缀的变量会出现在浏览器里，所以这里只放公开 URL；API Key 始终只放在服务端环境变量。`VITE_AI_API_URL` 留空时，静态站点仍会降级为模拟数据，并在页面上说明原因。

## 验证过程

| 场景 | 结果 |
| --- | --- |
| 未配置 Key | 服务端返回 503 `NO_API_KEY`，卡片带「模拟数据」标记，前端提示去填 Key |
| 填错 Key | 服务端返回 401，detail 里有 TokenHub 的 `401002` 鉴权错误，前端降级并提示 |
| 正确 Key，粘贴文本 | 返回 200，生成「先收敛再生成草稿」等 4 条要点、4 个标签 |
| 正确 Key，文本 + 文件两组资料 | 返回 200 / 2 张卡片，分别识别为「产品设计」「商业」，各 4 条要点 |
| 云函数 HTTP 触发模拟 | 返回 200，requestId `local-test-001` 出现在日志里；OPTIONS 预检返回 204 |
| 浏览器实际点击按钮 | 卡片无「模拟数据」标记，日志 `status: 200`，耗时约 4 秒 |
| `npm run build` | 构建通过，0 错误 0 警告 |

失败时前端会展示服务端返回的 `error`，卡片照常生成但标为模拟数据，用户可以继续使用原型——这符合教程“为等待和失败加上提示”的要求。

## 成果截图

| 截图 | 说明 |
| --- | --- |
| `screenshots/05-ai-fallback.png` | 未配置 Key：降级为模拟数据，卡片带「模拟数据」标记 |
| `screenshots/06-ai-generated.png` | 真实 AI 生成：调用成功后的卡片结果 |
| `screenshots/07-url-fetch.png` | 网址解析：粘贴文章链接后，基于抓取正文生成的卡片 |
| `screenshots/08-builtin-cases.png` | 内置案例集扩充后：9 张卡片 |
| `screenshots/09-domain-filter.png` | 领域分类：按「商业」筛选 |
| `screenshots/10-export-preview.png` | 导出图片：卡片转为 2 倍分辨率 PNG |

截图文件在项目的 `screenshots/` 目录下。

## 遇到的问题与排查

| 现象 | 优先检查项 | 本次结论 |
| --- | --- | --- |
| 老接口 401 | Key 是否正确、请求头是否正确 | 地址过期，TokenHub 用新域名 |
| `hunyuan-lite` 报服务不存在 | Base URL、Endpoint、Model ID 是否变化 | 老平台模型名，TokenHub 用新服务 ID |
| 页面有卡片但其实是模拟数据 | 请求有没有真正到达平台 | `base` 改动导致 API 路径 404 |
| 线上没有 AI | 环境变量、跨域、Serverless 超时 | 补 CloudBase 云函数 + CORS 预检 |

调试时保存了时间、请求类型、HTTP 状态码和 requestId；没有把 API Key 或资料原文写进日志，也没有贴进截图。

## 学习心得

这一章最关键的认知是：接入 AI 不只是“复制一段 API 代码”。教程把它拆成三件事——怎样描述任务、怎样读懂官方文档、怎样把调用安全地放进产品流程，这三件事在实践里都躲不过去。

提示词方面，把固定规则写在 system prompt、让用户只管输入自然内容，比要求用户学会写提示词更合理。文档方面，`hunyuan-lite` 的报错让我真正理解了“Model ID 要从当前文档复制”不是一句套话。安全方面，Key 只留在服务端，浏览器里的 `VITE_AI_API_URL` 只是公开地址。

印象最深的是那个 404：从截图上看，AI 好像已经工作了，实际上前端一直在降级。教程说“页面成功但没有内容”时要检查响应字段，我这里则是“页面成功、内容也有，但来源是模拟数据”。后来靠服务端日志和浏览器里的「模拟数据」标记才确认问题。这也说明为什么作业要求实际调用一次并到日志确认，而不是只看页面效果。

本次还补了 CloudBase 云函数，让本地和线上共用同一份核心逻辑。原型阶段先接一种能力就够了；上次思考题里剩下的文生图、综述生成、向量关联和自动归类，留到下一节继续。

这次还学会从页面功能倒推 AI 能力。教程的商品案例是“照片 → 图片理解 → 文本生成”，我的工作台是“网址 → 服务端抓正文 → 文本生成”。看起来都是一键生成卡片，但中间哪些环节该交给普通程序、哪些交给模型，要先拆清楚；如果把抓取也硬塞给模型，既不稳定也浪费额度。

提示词上有个小体会：约束越具体，页面越好接。我要求只返回 JSON、给定 domain 枚举、限制要点数量和字数，解析代码就很简单；第一次试的时候还故意少填一个字段，确认模型会写“资料中未提及”而不是编造。这正好对应教程说的：规则由程序固定附加，用户只管自然输入。

发布到 GitHub Pages 后又补了一课：静态站没有后端，线上依旧走模拟数据。看到页面上线很开心，但点生成才发现提示语告诉我降级了。这把教程里“本地能用、上线失败”“API Key 不要放前端”从条文变成了亲历的坑；后面接云函数时，我也会先确认环境变量和 HTTP 路由，再重新发布。

回头看，这一章真正练的是验证习惯：先让终端里的一次请求跑通，再接进页面；用日志和状态码确认请求到达平台，而不是只看页面上出现了文字。以后接图片、语音或视频，我会沿用同样的顺序，尤其异步任务还要盯住 task_id 和轮询状态。

## 学习资料

https://datawhalechina.github.io/easy-vibe/zh-cn/stage-1/integrating-ai-capabilities/

https://cloud.tencent.com/document/product/876/41812

https://docs.cloudbase.net/cloud-function/quick-start
