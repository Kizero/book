# 网页正文读取器

一个最小、本地、零第三方 Python 依赖的网页正文读取工具。

普通网页依次尝试：

1. 默认通过 Jina Reader 远程读取公开页面并返回 Markdown；
2. 远程正文通道失败时，再从当前电脑直连目标网页并提取可见文本。

Reddit 帖子会先通过 Arctic Shift 公开归档读取结构化的主帖与已归档评论；失败后再依次尝试 Jina Reader 和本机直连。Jina Reader 使用可信 DNS 查询结果建立连接，并继续执行正常的 TLS 域名校验，避免本机 DNS 错误解析导致无意义的超时。

Reddit 社区地址（例如 `https://www.reddit.com/r/example/`）会显示公开归档中的帖子。每页 25 条，并用归档数据的发帖时间游标提供“上一页 / 下一页”，不是只截取固定的 25 条。

直接读取 `https://www.reddit.com/` 会进入只读 Reddit 首页。网页上方的 Reddit 搜索框支持：

- 全站搜索公开 Reddit 帖子；
- 指定 `DeepSeek` 或 `r/DeepSeek` 之类的社区后搜索；
- 搜索结果翻页、点击帖子、返回上一层；
- 在同一个工具内继续读取帖子正文和归档评论。

全站搜索通过 Brave 的公开网页结果完成；直连搜索被限流或网络解析异常时，会自动改走远程正文备用通道。明确填写社区时，优先用 Arctic Shift 做社区内的归档搜索，不依赖 Brave。若全站通道全部失败，`milf ruined` 这种“社区名 + 关键词”还会被明确标注地降级为“在 r/milf 中搜索 ruined”；它不会把社区结果冒充成全站结果。页面会把正文里的 Markdown 链接整理成“继续阅读”列表。媒体不会自动加载。

每次尝试的成败、错误和耗时都会显示出来。工具不会绕过登录、付费墙或验证码，也拒绝读取本机和局域网地址。

Scriptbin 脚本使用站点自己的年龄确认流程。首次读取只显示确认提示；只有读者本人点击“我符合条件，确认并读取正文”后，工具才会在一次内存中的临时 Cookie 会话里提交站点表单及防伪令牌，再提取脚本的正文区域。Cookie 不会写入磁盘。

## 启动网页界面

```bash
cd /Users/houguanqun/Downloads/book/book/tools/web-reader
python3 app.py
```

浏览器会自动打开 <http://127.0.0.1:8765>。按 `Ctrl+C` 停止服务。

如果读取器已经在运行，重复执行命令会直接打开现有页面并正常退出。若端口被其他程序占用，程序会提示使用 `--port 8766` 等其他端口。

## 命令行读取

```bash
python3 app.py --url 'https://example.com/article' > article.md
```

正文写到标准输出，实际采用的读取链路和耗时写到标准错误，不会混进文章文件。

## 验证

```bash
python3 -m unittest -v
```

边界：Jina Reader、Arctic Shift 和 Brave Search 都是外部服务。敏感、私有或带临时密钥的网址不要提交给它们。这个工具提供的是只读搜索与归档内容，不包含 Reddit 登录态、个性化首页，也不等同于 Reddit 的 Hot/Best 排序。Reddit 归档内容、分数和评论可能比当前页面稍有延迟。
