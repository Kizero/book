#!/usr/bin/env python3
"""Render an original reading guide with links back to the source video."""
import html
import sys
from pathlib import Path

from reader import read, stamp, validate_review


def render_brief(folder):
    folder = Path(folder).resolve()
    evidence, review = read(folder / "evidence.json"), read(folder / "review.json")
    validate_review(review, evidence)
    e = html.escape
    meta = evidence["metadata"]
    segments = {s["id"]: s for s in evidence["transcript"]["segments"]}
    frames = {f["id"]: f for f in evidence["frames"]}
    units = review.get("content_units", [])
    by_card = {c["id"]: [u for u in units if u.get("card_id") == c["id"] and u["treatment"] != "omitted"] for c in review["cards"]}
    kinds = {"claim": "论点", "derivation": "推导", "example": "例子", "condition": "边界", "correction": "纠正", "aside": "旁枝"}
    def link(t, label=None):
        return f'<a href="{e(meta["source_url"])}&amp;t={int(t)}" target="_blank" rel="noreferrer">{e(label or stamp(t))} ↗</a>'
    def picture(fid):
        f = frames[fid]
        return f'<figure><a href="{e(f["path"])}"><img loading="lazy" src="{e(f["path"])}" alt="{stamp(f["time"])} 的视频画面"></a><figcaption>{link(f["time"])} · {e({"first":"首帧","periodic":"定时补帧","scene-change":"画面变化"}[f["reason"]])}</figcaption></figure>'
    cards, route = [], []
    for card in review["cards"]:
        start = min(segments[s]["start"] for s in card["segment_ids"])
        end = max(segments[s]["end"] for s in card["segment_ids"])
        route.append(f'<li><a href="#{e(card["id"])}">{stamp(start)}　{e(card["title"])}</a></li>')
        refs = ''.join(f'<blockquote>{e(r["quote"])}<cite>{e(Path(r["path"]).name)} · 第 {r["start_line"]}–{r["end_line"]} 行</cite></blockquote>' for r in card.get("memory_refs", []))
        code_refs = ''
        for source in card.get("source_refs", []):
            if not source["url"].startswith("https://"):
                raise ValueError("补充来源只接受 HTTPS 地址。")
            code_refs += f'<a href="{e(source["url"])}" target="_blank" rel="noreferrer">{e(source["title"])}</a>　'
        visual = ''.join(picture(fid) for fid in card.get("frame_ids", [])[:2])
        paragraphs = ''.join(f'<p>{e(p)}</p>' for p in card["summary"].split("\n\n"))
        detail = ''
        for unit in by_card[card["id"]]:
            t = min(segments[s]["start"] for s in unit["segment_ids"])
            prose = ''.join(f'<p>{e(p)}</p>' for p in unit["text"].split('\n\n'))
            illustrations = ''.join(picture(fid) for fid in unit.get("frame_ids", []))
            ordered = sorted(unit["segment_ids"], key=lambda s: segments[s]["start"])
            raw = f'<a href="report.html#{e(ordered[0])}">对应转录起点</a>–<a href="report.html#{e(ordered[-1])}">终点</a>（未逐句听校）'
            provenance = f'<p class="sources">来源：{e(unit["source_note"])}</p>' if unit.get("source_note") else ''
            detail += f'<section class="unit" id="{e(unit["id"])}"><div class="range">{e(kinds[unit["kind"]])} · {link(t)} · {raw}</div><h4>{e(unit["title"])}</h4>{provenance}{prose}{illustrations}</section>'
        if detail:
            detail = f'<details open class="lecture-detail"><summary>讲解、例子与边界 · {len(by_card[card["id"]])} 项（可折叠）</summary>{detail}</details>'
        content = f'<div class="range">{link(start)}–{stamp(end)}</div><h3>{e(card["title"])}</h3>{paragraphs}{refs}<div class="sources">{code_refs}</div>{visual}{detail}'
        if card["label"] == "known":
            content = f'<details><summary>已有记录 · {e(card["title"])}</summary>{content}</details>'
        cards.append(f'<article id="{e(card["id"])}">{content}</article>')
    questions = ''.join(f'<li>{e(q)}</li>' for q in review["questions"])
    answers = ''.join(f'<li>{e(a)}</li>' for a in review.get("recall_answers", []))
    highlights = ''.join(f'<li>{e(h)}</li>' for h in review.get("highlights", []))
    limits = ''.join(f'<li>{e(l)}</li>' for l in review.get("limitations", []))
    timeline = ''.join(picture(fid) for fid in frames)
    audit = ''
    if units:
        rows = []
        for unit in units:
            t = min(segments[s]["start"] for s in unit["segment_ids"])
            target = f'<a href="#{e(unit["id"])}">讲义位置</a>' if unit["treatment"] != "omitted" else e(unit["omission_reason"])
            rows.append(f'<tr><td>{e(kinds[unit["kind"]])}</td><td>{e(unit["title"])}</td><td>{link(t)}</td><td>{target}</td></tr>')
        audit = '<details><summary>逐项内容记录 · 不等于绝对无损证明</summary><p>下面记录本次识别出的内容及其去向。它能帮助发现遗漏，不能证明内容清单本身没有遗漏，也不能证明转录完全准确。</p><div class="table-wrap"><table><thead><tr><th>类型</th><th>具体内容</th><th>原视频</th><th>去向或省略原因</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div></details>'
    text = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(meta["title"])} · 个人阅读报告</title>
<style>
*{{box-sizing:border-box}}:root{{color-scheme:light;--ink:#223c34;--muted:#61746b;--line:#d6ddd3;--accent:#1c6855}}html{{scroll-behavior:smooth}}body{{margin:0;background:#f7f5ed;color:var(--ink);font:17px/1.85 system-ui,-apple-system,"PingFang SC",sans-serif}}main{{max-width:1040px;margin:auto;padding:54px 32px 90px}}header{{border-bottom:1px solid var(--line);padding-bottom:24px}}.eyebrow{{font-size:12px;letter-spacing:3px;color:var(--accent)}}h1{{font:500 clamp(30px,4vw,43px)/1.45 Georgia,"Songti SC",serif;margin:15px 0}}h2{{font-size:26px;margin:42px 0 18px}}h3{{font-size:22px;margin:6px 0 14px;line-height:1.5}}p{{margin:14px 0}}a{{color:var(--accent);text-underline-offset:4px}}.meta,.range,.sources,figcaption{{font-size:13px;color:var(--muted)}}.meta{{display:flex;gap:22px;flex-wrap:wrap}}nav{{display:flex;gap:22px;flex-wrap:wrap;margin:22px 0;font-size:15px}}.intro{{font-size:20px;line-height:1.9}}.baseline{{padding:18px 22px;border-left:3px solid #8aa38e;background:#eeeee4;font-size:15px}}article{{scroll-margin-top:24px;border-top:1px solid var(--line);padding:28px 0 18px}}.route{{columns:2;column-gap:24px;list-style:none;padding:0;font-size:14px}}.route li{{break-inside:avoid;padding:6px 0}}figure{{margin:22px 0}}figure img{{width:100%;max-width:960px;display:block;border:1px solid var(--line);border-radius:8px}}figcaption{{padding-top:6px}}details{{margin:20px 0}}summary{{cursor:pointer;color:var(--accent)}}blockquote{{margin:20px 0;padding:12px 20px;border-left:2px solid #9bb39c;background:#eeeee4;font-size:15px}}cite{{display:block;font-size:12px;font-style:normal;color:var(--muted);margin-top:10px}}li{{padding:5px 0}}.limitations{{font-size:14px;color:var(--muted)}}footer{{margin-top:42px;border-top:1px solid var(--line);padding-top:20px;font-size:13px;color:var(--muted)}}:target{{background:#f0ebce}}@media(max-width:640px){{main{{padding:28px 19px 65px}}.route{{columns:1}}.intro{{font-size:18px}}h2{{font-size:24px}}}}
</style><main><header><div class="eyebrow">READ WITH EVIDENCE / 个人阅读报告</div><h1>{e(meta["title"])}</h1><div class="meta"><span>视频 {stamp(evidence["media"]["duration"])}</span><span>{len(segments)} 段转录用于分析</span><span>{len(frames)} 张时间定位截图</span><span>来源：{e(meta.get("uploader") or "B 站")}</span></div></header>
<nav><a href="#main">先读主线</a><a href="#route">章节与证据</a><a href="#recall">主动回忆</a><a href="#limits">核验范围</a></nav>
<section id="main"><p class="intro">{e(review.get("overview", ""))}</p><ul>{highlights}</ul><p class="baseline">{e(review.get("personal_context", ""))}</p></section>
<section id="route"><h2>沿着问题回到视频</h2><ol class="route">{''.join(route)}</ol>{''.join(cards)}</section>
<section id="recall"><h2>合上材料，检验能否重建</h2><ol>{questions}</ol><details><summary>回答后展开核对要点</summary><ol>{answers}</ol></details></section>
<section id="limits"><h2>核验范围与缺口</h2><ul class="limitations">{limits}</ul>{audit}</section>
<details><summary>展开完整截图时间轴 · {len(frames)} 张</summary>{timeline}</details>
<footer>这份讲义是 AI 对视频的整理与分析。时间链接回到原视频，配套代码核验单独标注。没有将材料准备或笔记匹配记作“已理解”。</footer></main></html>'''
    output = folder / "reading-report.html"
    if review.get("source_notice"):
        notice = f'<p class="baseline">{e(review["source_notice"])}</p>'
        text = text.replace('<section id="route">', notice + '<section id="route">')
    text = text.replace('</nav>', '<a href="report.html">完整转录与画面</a></nav>')
    if (folder / "coverage-review.html").is_file():
        text = text.replace('</nav>', '<a href="coverage-review.html">与参考讲义对照</a></nav>')
    if (folder / "verification.html").is_file():
        text = text.replace('</nav>', '<a href="verification.html">公式与边界核验</a></nav>')
    text = text.replace('</style>', '.unit{padding:20px 0 10px}.unit h4{font-size:19px;margin:8px 0 12px}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}.lecture-detail>summary{font-size:14px}.lecture-detail[open]>summary{margin-bottom:12px}</style>')
    output.write_text(text, encoding="utf-8")
    print(output)
    markdown = [f'# {meta["title"]}',
                f'[原视频]({meta["source_url"]}) · {stamp(evidence["media"]["duration"])}',
                review.get("overview", ""),
                '\n'.join(f'- {h}' for h in review.get("highlights", [])),
                review.get("personal_context", "")]
    if review.get("source_notice"):
        markdown.append(review["source_notice"])
    if (folder / "verification.html").is_file():
        markdown.append('[公式与边界核验](verification.html)')
    for card in review["cards"]:
        start = min(segments[s]["start"] for s in card["segment_ids"])
        markdown.extend([f'## {stamp(start)} · {card["title"]}',
                         f'[回到这一段]({meta["source_url"]}&t={int(start)})', card["summary"]])
        for ref in card.get("memory_refs", []):
            markdown.extend([f'> {ref["quote"]}',
                             f'旧笔记：[原文第 {ref["start_line"]} 行](<{ref["path"]}:{ref["start_line"]}>)'])
        for source in card.get("source_refs", []):
            markdown.append(f'[{source["title"]}]({source["url"]})')
        for fid in card.get("frame_ids", [])[:2]:
            frame = frames[fid]
            markdown.append(f'![{stamp(frame["time"])} 的关键画面]({folder / frame["path"]})')
        for unit in by_card[card["id"]]:
            t = min(segments[s]["start"] for s in unit["segment_ids"])
            ordered = sorted(unit["segment_ids"], key=lambda s: segments[s]["start"])
            markdown.extend([f'<a id="{unit["id"]}"></a>', f'### {unit["title"]}', f'{kinds[unit["kind"]]} · [视频 {stamp(t)}]({meta["source_url"]}&t={int(t)}) · [对应转录](report.html#{ordered[0]})'])
            if unit.get("source_note"):
                markdown.append(f'来源：{unit["source_note"]}')
            markdown.append(unit["text"])
            for fid in unit.get("frame_ids", []):
                frame = frames[fid]
                markdown.append(f'![{stamp(frame["time"])} 的关键画面]({folder / frame["path"]})')
    markdown.extend(['## 主动回忆',
                     '\n'.join(f'{i}. {q}' for i, q in enumerate(review["questions"], 1)),
                     '<details>\n<summary>回答后展开核对要点</summary>\n\n' +
                     '\n\n'.join(f'{i}. {a}' for i, a in enumerate(review.get("recall_answers", []), 1)) +
                     '\n\n</details>',
                     '## 核验范围与缺口',
                     '\n'.join(f'- {l}' for l in review.get("limitations", []))])
    if units:
        markdown.extend(['## 逐项内容记录', '此清单记录已识别内容的去向，不能证明清单本身无遗漏。'])
        ledger = ['| 内容 | 去向 |', '| --- | --- |']
        for unit in units:
            target = f'[详细讲解](#{unit["id"]})' if unit['treatment'] != 'omitted' else unit['omission_reason']
            ledger.append(f'| {unit["title"].replace("|", "／")} | {target.replace("|", "／")} |')
        markdown.append('\n'.join(ledger))
    markdown_output = folder / "reading-guide.md"
    markdown_output.write_text('\n\n'.join(markdown) + '\n', encoding="utf-8")
    print(markdown_output)


if __name__ == "__main__":
    render_brief(sys.argv[1])
