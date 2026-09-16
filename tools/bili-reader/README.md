# B 站个人增量阅读器

第一版是本地采集脚本 + 当前 Codex 对话中的个人增量分析。给当前对话一个 BV，按 [READ_VIDEO.md](READ_VIDEO.md) 完成阅读。还不是一个离开 Codex 后自动分析的独立应用。

个人上下文现在可通过 LocalReader 的 `learning evidence --question '具体问题'` 读取：保留原话、旧批注、AI 解释及针对具体回答的理解自报。日常流程会为本次分析保存独立快照，并从中引用依据。它仍是候选检索，不自动推断已知或删除内容；这一步由执行阅读流程的 Agent 调用，采集脚本本身不调用模型。

内容损失与用量的具体边界见 [QUALITY.md](QUALITY.md)。新版增加逐项论点/推导/例子/条件/纠正记录；程序校验引用和去向，不把校验通过解释成语义无损。

已交付的真实视频：

- [malloc 第一种实现的阅读报告](runs/BV1tL4y1Y72y-p1/reading-report.html)；[该轮实际 token 用量](runs/BV1tL4y1Y72y-p1/usage-explained.md)。
- [提示词工程的详细讲义](runs/BV1CQt365EzW-p1/reading-report.html)；[与用户参考报告的内容对照](runs/BV1CQt365EzW-p1/coverage-review.html)。包含 14 章、52 个展开项，区分口述、投影 AI 补注与整理者说明。
- [无符号整数、二进制补码的详细讲义](runs/BV17K4y1N7Q2-p1/reading-report.html)；[整数模型与 C 边界核验](runs/BV17K4y1N7Q2-p1/verification.html)。仅合集默认 P1，包含 10 章、30 个展开项及 24 张精选画面。
- [软件仓库管理的详细讲义](runs/BV1kybV6DE47-p1/reading-report.html)；[Git 与 C 操作核验](runs/BV1kybV6DE47-p1/verification.html)。完整 P1，1:40:13，14 章、51 个展开项、116 张抽样画面，保留原转录及内容去向记录。

采集流程：BV / 指定分 P → 平台字幕（优先）→ 无字幕时本地 Whisper 转录 → 相邻画面变化截图 + 定时补帧 → 完整图文时间轴 → 结合旧笔记的 AI 分析 → 主动回忆。原始材料与分析分别保存，已知内容仅在分析卡片折叠，原始转录始终可见。

## 安装与运行

需要 Python 3.12 与 FFmpeg。本目录已有独立 `.venv` 时直接用它。

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python reader.py collect BV1xx411c7mD
.venv/bin/python reader.py collect 'https://www.bilibili.com/video/BV1xx411c7mD/?p=2'
```

`requirements.lock.txt` 记录本次本机验证的完整依赖版本，可用 `pip install -r requirements.lock.txt` 重建。若默认 PyPI 出现超时/错误地报告包不存在，可在此次安装命令中加 `--index-url https://pypi.tuna.tsinghua.edu.cn/simple` 使用清华镜像；不需要修改全局 pip 设置。

上面的 BV 是命令格式示例，不代表用户选定的视频。首次无字幕转录需要下载 `small` 多语种模型，并在本机 CPU 上运行；可用 `--asr-model` 指定其他模型或本地模型目录。处理长视频所需时间取决于网络、时长、模型和硬件，不能承诺几分钟处理完。

也支持已有视频/音频、SRT、VTT、B 站 JSON 或带 start/end/text 的 JSON 转录：

```sh
.venv/bin/python reader.py collect --media /路径/video.mp4 --subtitle /路径/subtitle.srt --title '视频标题'
.venv/bin/python reader.py collect --media /路径/audio.mp3
```

输出默认在本目录 `runs/BV号-pN/` 或按媒体哈希命名的目录。使用 `--out` 指定目录；重复同一命令复用证据，未完成下载由 yt-dlp 续传，已完成转录可复用。输入/参数变化时必须使用新目录，避免混淆旧分析。失败状态写入 `manifest.json`。异常中断留下 `.lock` 时，先确认进程结束再移除锁目录。

## 产物

- `reading-report.html`、`reading-guide.md`：运行 `render_brief.py` 后生成的阅读讲义，包含提炼后的主线、个人笔记连接、关键帧、原视频时间链接与主动回忆。日常阅读从这里进入。
- `report.html`：本地可打开的阅读报告，带原文、截图和 B 站时间链接。
- `evidence.json`、`transcript.json`、`transcript.md`：结构化证据与保留全部已取得文字的转录。
- 原始字幕或 `asr-original.json`：转录源，ASR 源保留模型分段概率。
- `frames/`、`frames.log`：截图、真实视频时间戳及 FFmpeg 日志。
- `analysis.json` → `review.json`：当前对话生成、经引用和片段覆盖校验的个人增量分析。
- 新版 `content_units`：详细讲义与逐项内容覆盖记录，保留省略原因。
- `usage-audit.json`（显式运行 `usage_audit.py` 后）：指定任务的实际累计 token 计数，不含原始对话正文。

```sh
.venv/bin/python reader.py review runs/某次阅读 runs/某次阅读/analysis.json
.venv/bin/python render_brief.py runs/某次阅读
.venv/bin/python -m unittest -v
```

任务用量示例：

```sh
.venv/bin/python usage_audit.py /绝对路径/rollout.jsonl --turn-id 目标任务轮次ID --out runs/某次阅读/usage-audit.json
```

只统计明确选定的一轮任务，可能包含工具开发和重复上下文；未完成任务会标为 partial。不会因为没有找到用量而填写零。

## 具体边界

仅请求公开可访问的单个分 P，不自动读取浏览器 Cookie。遇到登录限制、风控、失效视频时报告失败，可改用用户已有的本地媒体/字幕。默认下载最高 720p 的可用视频用于读图，截图宽度 960px，可点击展开；细小字需要回到原视频。`--scene 0.18` 为变化阈值，`--min-gap 2` 控制高频截图，`--max-gap 60` 定时补图。这会漏掉部分瞬时/局部变化，不能保证所有关键视觉信息都已捕获。

平台字幕同样可能是机器生成，ASR 也会误识别；报告显示无字幕区间但不把时间覆盖当作语义完整率。增量校验只证明片段有分析归属、旧笔记引用存在，最终判断仍需在当前对话中对照原文。没有匹配笔记不等于用户不知道；有匹配笔记不等于已理解。

实现参考：[yt-dlp](https://github.com/yt-dlp/yt-dlp)、[faster-whisper](https://github.com/SYSTRAN/faster-whisper)、[FFmpeg select](https://ffmpeg.org/ffmpeg-filters.html#select_002c-aselect)。输出材料仅保存在本地 `runs/`，默认被 Git 忽略。
