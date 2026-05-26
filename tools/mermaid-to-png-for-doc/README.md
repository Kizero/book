# DOCX Mermaid → PNG 替换工具

把 `docx` 里的 Mermaid 代码块渲染成 `png`，并在原位置插入图片（不再保留 Mermaid 文本）。

## 1) 安装依赖

```bash
python3 -m venv .venv
.venv/bin/pip install python-docx
```

## 2) 执行替换

```bash
.venv/bin/python docx_mermaid_to_png.py "你的文件.docx" -o "输出文件.docx"
```

可选参数：

- `--image-width-in 6.4`：插入图片宽度（英寸）
- `--use-global-mmdc`：使用全局 `mmdc`，默认使用 `npx @mermaid-js/mermaid-cli`

> 默认输出文件名：`原文件名.png-replaced.docx`
