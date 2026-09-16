# Knowledge Radar v0.1

这是一套本地、可检查、可修改、可重放的个人信息雷达。它不以“抓到最多内容”为目标，而是把新材料转换为带证据位置的知识增量、引用关系、方法卡和开放问题。

当前版本已经用一条真实发现链跑通：

- 知乎评论中的 Hardy 线索 → 标题致敬关系 → 完整电子版 → 作者生平与成书背景 → 作品论证、可迁移方法和历史反例；
- 蒋炎岩 AI 实践统一总纲继续作为系统设计输入，但不会冒充 Hardy 这本书“带来的方法”。

## 核心数据流

```text
inbox/ 原始凭证
   ↓
records/ 可审查的 JSON 中间表示
   ↓ radar.py validate
证据片段、行号、哈希、关系端点校验
   ↓ radar.py rebuild
state/index.json 个人状态与去重索引
   ↓ radar.py report
reports/YYYY-MM-DD.md 增量日报
   ↓ radar.py feedback
state/feedback.jsonl 人工反馈事件
   └───────────────→ 下一次 rebuild/report
```

`inbox/` 和 `records/` 是事实来源；`state/index.json` 与 `reports/` 是可重新生成的派生结果。`feedback.jsonl` 是追加式的人类判断历史，不应被生成器覆盖。

执行 `DAILY_TASK.md` 的 Agent 还会按本期具体问题调用 LocalReader 的只读 `learning evidence` 接口，取得最新的个人原话、相关笔记和对具体回答的理解自报，保存为本轮可引用的独立快照。这用于校正阅读价值与个人增量；不会把“我觉得这点懂了”自动写成整本作品 `known/read`，`radar.py` 的作品反馈逻辑保持独立。

## 立即运行

只需要 Python 3，不依赖第三方包：

```bash
cd /Users/houguanqun/Downloads/book/book/knowledge-radar
python3 radar.py validate
python3 radar.py rebuild
python3 radar.py report --date 2026-09-04
```

查看候选对象后，可以反馈：

```bash
python3 radar.py feedback work:a-mathematicians-apology \
  --status reading \
  --note "开始阅读"
python3 radar.py rebuild
python3 radar.py report --date 2026-09-04
```

实体状态：

- `candidate`：相对于当前个人基线仍是新候选；
- `known`：已经知道，无需继续作为新发现报告；
- `reading`：正在处理；
- `read`：已经读过或完成处理；
- `ignored`：明确不值得继续投入。

## 新材料怎样入库

1. 把网页摘录、视频转写、PDF 阅读笔记或用户输入原样放入 `inbox/`。不要用摘要覆盖原文。
2. 计算文件 SHA-256，并参照 `templates/record.json` 创建一条 `records/*.json`。
3. 至少提取四层：作品内容、来龙去脉、从作品本身导出的方法、反例或批评。
4. 每个重要 claim/method 填写 `locator` 和原文中确实存在的 `evidence` 短语。
5. 运行 `validate`。行号漂移、原文被改、证据不存在或关系端点错误都会失败。
6. `rebuild` 后生成日报；不要手工修改 `state/index.json`。

## 记录的事实边界

- `artifact.verification` 描述整份材料的来源边界。
- `claim.kind` 区分原作者观点、评论者解释、用户转述和出版社书目。
- `confidence` 只允许 `verified`、`likely`、`unverified`、`disputed`。
- “作者回复确认标题致敬”与“评论者对两位作者心境的类比”必须是两条不同 claim。
- 评论可用于发现引用，书目事实仍应回到出版社、论文、大学或图书馆核验。

## 第一版的完成条件

- 原始文件经过哈希保护；
- 重要判断能跳回原文行号；
- 中英文别名归并到同一实体；
- 同一实体跨记录合并，置信度和语境仍分别保留；
- 人的反馈通过事件回放覆盖默认状态；
- `known/read/ignored` 不再作为新发现出现；
- 没有当天记录时，日报明确显示没有新增；
- 所有上述规则均可用标准库测试重放。

## 当前有意不做的事情

- 不做全网或全量评论爬虫；
- 不在没有个人状态前堆向量数据库；
- 不让模型在没有原始定位时生成“事实”；
- 不自动登录、绕过访问限制或镜像受版权保护的全文；
- 每日调度已于 2026-09-05 创建：北京时间 09:00，在本对话执行，名称“每日知识雷达”，自动化 ID 为 `automation-2`。此前只有提示词和本地生成器，没有实际调度。

后续最自然的增量是：网页/视频/PDF 采集适配器、基于个人历史的已知判定、主动回忆题、跨材料矛盾检测，以及真正的每日只读采集任务。

## 为什么明天不会只剩 Hardy

`config/discovery.json` 把发现与研究分成两阶段。发现阶段轮换主题和通道，从引用图、课程与领域史、历史反例和相邻领域寻找候选，并过滤最近展示过的对象；只有选出当天主对象后，才围绕它补作品、生平、背景、方法与批评。

`radar.py` 本身不联网，它负责验证、去重和呈现；真正的全网发现由每次执行 `DAILY_TASK.md` 的联网 Agent 完成。也就是说，明天再次执行时会重新搜索，不会把今天这份 Hardy 档案换个说法再发一次。
