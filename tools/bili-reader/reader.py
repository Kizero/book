#!/usr/bin/env python3
"""Local video evidence collector. The AI review is a separate, validated artifact."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
BV = re.compile(r"BV[1-9A-HJ-NP-Za-km-z]{10}")
LABELS = {"new": "新增", "known": "已有记录", "conflict": "与旧认识冲突", "uncertain": "待确认"}


def save(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical(value, part=None):
    if BV.fullmatch(value):
        bvid, page = value, 1
    else:
        u = urlparse(value)
        if u.scheme not in ("https", "http") or u.hostname not in ("www.bilibili.com", "bilibili.com", "m.bilibili.com"):
            raise ValueError("请输入 BV 号或 bilibili.com/video/BV… 链接；暂不接受短链。")
        m = re.fullmatch(r"/video/(BV[1-9A-HJ-NP-Za-km-z]{10})/?", u.path)
        if not m:
            raise ValueError("不是 B 站视频地址。")
        bvid = m[1]
        page = int(parse_qs(u.query).get("p", ["1"])[0])
    page = part if part is not None else page
    if page < 1:
        raise ValueError("分 P 编号必须大于零。")
    return bvid, page, f"https://www.bilibili.com/video/{bvid}/?p={page}"


def stamp(t):
    t = max(0, int(t))
    return f"{t // 3600:02d}:{t // 60 % 60:02d}:{t % 60:02d}"


def number(value):
    n = float(value)
    if not math.isfinite(n) or n < 0:
        raise ValueError("时间必须是非负有限数字。")
    return n


def timestamp(text):
    parts = text.replace(",", ".").split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"无效字幕时间：{text}")
    total = 0.0
    for part in parts:
        total = total * 60 + number(part)
    return total


def normalize(rows):
    result = []
    for row in rows:
        start = number(row.get("start", row.get("from")))
        end = number(row.get("end", row.get("to")))
        text = str(row.get("text", row.get("content", ""))).strip()
        if end <= start:
            raise ValueError("字幕结束时间必须晚于开始时间。")
        if text:
            result.append({"start": start, "end": end, "text": text})
    result.sort(key=lambda s: (s["start"], s["end"]))
    if not result:
        raise ValueError("未取得有效字幕；不能把空转录标为成功。")
    for i, row in enumerate(result, 1):
        row["id"] = f"s{i:05d}"
    return result


def subtitles(path):
    text = Path(path).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    if Path(path).suffix == ".json":
        obj = json.loads(text)
        return normalize(obj if isinstance(obj, list) else obj.get("body", obj.get("segments", [])))
    rows = []
    for block in re.split(r"\n\s*\n", text):
        lines = block.splitlines()
        for i, line in enumerate(lines):
            if "-->" not in line:
                continue
            left, right = line.split("-->", 1)
            rows.append({"start": timestamp(left.strip()), "end": timestamp(right.strip().split()[0]),
                         "text": html.unescape(re.sub(r"<[^>]*>", "", "\n".join(lines[i + 1:])))})
            break
    return normalize(rows)


def run(command, timeout=3600):
    proc = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    if proc.returncode:
        raise RuntimeError(f"{Path(command[0]).name} 失败：{proc.stderr[-2400:]}")
    return proc.stdout, proc.stderr


def probe(media):
    out, _ = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(media)], 60)
    info = json.loads(out)
    return {"duration": number(info["format"]["duration"]),
            "has_video": any(s["codec_type"] == "video" for s in info["streams"]),
            "has_audio": any(s["codec_type"] == "audio" for s in info["streams"])}


def fetch(url, folder, language):
    from yt_dlp import YoutubeDL
    # Use one requested part only; neither browser cookies nor credentials are read.
    options = {"noplaylist": True, "socket_timeout": 30, "retries": 2,
               "format": "bv[height<=720]+ba/b[height<=720]/b",
               "outtmpl": str(folder / "media.%(ext)s"), "merge_output_format": "mp4",
               "quiet": True, "noprogress": True, "no_warnings": False, "overwrites": False,
               "writesubtitles": True, "writeautomaticsub": True,
               "subtitleslangs": [language + ".*", "ai-" + language + ".*"]}
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info or info.get("_type") in ("playlist", "multi_video"):
            raise ValueError("未解析为单个分 P；请提供带 ?p=N 的精确地址。")
        meta = {k: info.get(k) for k in ("id", "title", "uploader", "duration", "webpage_url", "description")}
        meta["source_url"] = url
        save(folder / "metadata.json", meta)
        warnings, subtitle = [], None
        candidates = []
        for kind in ("subtitles", "automatic_captions"):
            for lang, formats in (info.get(kind) or {}).items():
                if lang == "danmaku":
                    continue
                for fmt in formats:
                    if fmt.get("ext") in ("srt", "vtt", "json"):
                        candidates.append((0 if lang.startswith(language) or lang.startswith("ai-" + language) else 1,
                                           0 if kind == "subtitles" else 1, lang, fmt))
        for _, _, lang, fmt in sorted(candidates, key=lambda c: c[:3]):
            try:
                target = folder / ("original-subtitle." + fmt["ext"])
                if "data" in fmt:
                    data = fmt["data"].encode("utf-8")
                else:
                    with ydl.urlopen(fmt["url"]) as response:
                        data = response.read()
                target.write_bytes(data)
                segments = subtitles(target)
                subtitle = {"segments": segments, "source": "platform-subtitle", "language": lang,
                            "original": target.name, "verified_against_audio": False}
                break
            except Exception as exc:
                warnings.append(f"字幕 {lang} 不可用：{type(exc).__name__}")
        # Only selected media is downloaded, with yt-dlp's partial-download resume.
        ydl.params["writesubtitles"] = False
        ydl.params["writeautomaticsub"] = False
        ydl.process_info(info)
    media = next((p for p in sorted(folder.glob("media.*")) if p.suffix in (".mp4", ".mkv", ".webm", ".flv")), None)
    if media is None:
        raise RuntimeError("视频下载未产出可读媒体文件。")
    return meta, media, subtitle, warnings


def transcribe(media, model_name, language, folder):
    from faster_whisper import WhisperModel
    print(f"本地转录：{model_name}（首次需要下载模型）", file=sys.stderr, flush=True)
    model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=str(ROOT / "runs" / "models"))
    stream, info = model.transcribe(str(media), language=language or None, beam_size=5,
                                    vad_filter=True, condition_on_previous_text=False)
    rows = []
    for segment in stream:
        rows.append({"start": segment.start, "end": segment.end, "text": segment.text,
                     "avg_logprob": segment.avg_logprob, "no_speech_prob": segment.no_speech_prob})
        if len(rows) % 30 == 0:
            print(f"已转录至 {stamp(segment.end)}", file=sys.stderr, flush=True)
    save(folder / "asr-original.json", rows)
    return {"segments": normalize(rows), "source": "local-asr", "model": model_name,
            "language": info.language, "original": "asr-original.json", "verified_against_audio": False}


def frames(media, folder, threshold, min_gap, max_gap):
    target = folder / "frames"
    target.mkdir(exist_ok=True)
    # Decode every frame. `scene` compares adjacent frames; periodic samples cover slow changes.
    expression = f"isnan(prev_selected_t)+gte(t-prev_selected_t,{max_gap})+gt(scene,{threshold})*gte(t-prev_selected_t,{min_gap})"
    vf = f"select='{expression}',scale=960:-2,showinfo"
    _, log = run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", str(media), "-an", "-vf", vf,
                  "-fps_mode", "vfr", "-q:v", "3", str(target / "%06d.jpg")], 7200)
    (folder / "frames.log").write_text(log)
    times = [float(t) for t in re.findall(r"\bn:\s*\d+.*?\bpts_time:([\d.e+\-]+)", log)]
    result, previous = [], None
    for i, t in enumerate(times, 1):
        image = target / f"{i:06d}.jpg"
        if not image.is_file():
            raise ValueError("截图数与时间戳不一致。")
        reason = "first" if previous is None else "periodic" if t - previous >= max_gap - 0.001 else "scene-change"
        result.append({"id": f"f{i:05d}", "time": round(t, 3), "path": str(image.relative_to(folder)), "reason": reason})
        previous = t
    if not result:
        raise ValueError("没有生成任何关键帧。")
    return result


def gaps(segments, duration):
    uncovered, cursor, covered = [], 0.0, 0.0
    for s in segments:
        start, end = min(duration, s["start"]), min(duration, s["end"])
        if start > cursor:
            uncovered.append({"start": cursor, "end": start})
        covered += max(0, end - max(cursor, start))
        cursor = max(cursor, end)
    if cursor < duration:
        uncovered.append({"start": cursor, "end": duration})
    return {"timed_text_seconds": round(covered, 2), "duration_seconds": duration,
            "gaps_over_10s": [g for g in uncovered if g["end"] - g["start"] >= 10],
            "note": "字幕时间占比不等于语音转录完整率；空白可能是停顿、纯画面或漏转录。"}


def validate_review(review, evidence):
    """Reject missing coverage, invented citations, or unsupported hidden material."""
    if review.get("evidence_sha256") != evidence["evidence_sha256"]:
        raise ValueError("分析不属于这份证据快照。")
    segments = {s["id"]: s for s in evidence["transcript"]["segments"]}
    frame_ids = {f["id"] for f in evidence["frames"]}
    seen, ids = set(), set()
    for card in review.get("cards", []):
        if not card.get("id") or card["id"] in ids:
            raise ValueError("分析卡片 ID 缺失或重复。")
        ids.add(card["id"])
        if card.get("label") not in LABELS or not card.get("summary"):
            raise ValueError("分析卡片必须有合法类别与摘要。")
        citations = card.get("segment_ids", [])
        if not citations or not set(citations) <= segments.keys():
            raise ValueError("分析必须引用真实转录片段。")
        if not set(card.get("frame_ids", [])) <= frame_ids:
            raise ValueError("分析引用了不存在的截图。")
        seen.update(citations)
        refs = card.get("memory_refs", [])
        if card["label"] in ("known", "conflict") and not refs:
            raise ValueError("已有记录或冲突判断必须提供旧笔记证据。")
        for ref in refs:
            path = Path(ref["path"]).expanduser().resolve()
            if path.suffix != ".md" or not path.is_file():
                raise ValueError("旧笔记引用必须是可读取的 Markdown 文件。")
            lines = path.read_text().splitlines()
            start, end = ref["start_line"], ref["end_line"]
            if not isinstance(start, int) or not isinstance(end, int) or not 1 <= start <= end <= len(lines):
                raise ValueError("旧笔记行号无效。")
            if not ref.get("quote") or ref["quote"] not in "\n".join(lines[start - 1:end]):
                raise ValueError("旧笔记引用原文不匹配。")
    if seen != segments.keys():
        raise ValueError(f"还有 {len(segments.keys() - seen)} 个转录片段未被分析覆盖。")
    if review.get("schema_version", 1) >= 2 or "content_units" in review:
        units = review.get("content_units")
        if not isinstance(units, list) or not units:
            raise ValueError("新版讲义必须逐项记录论点、推导、例子、条件或纠正。")
        unit_ids, cards_by_id = set(), {c["id"]: c for c in review["cards"]}
        for unit in units:
            if not unit.get("id") or unit["id"] in unit_ids:
                raise ValueError("内容单元 ID 缺失或重复。")
            unit_ids.add(unit["id"])
            if unit.get("kind") not in ("claim", "derivation", "example", "condition", "correction", "aside"):
                raise ValueError("内容单元类型无效。")
            if not unit.get("title") or not unit.get("text"):
                raise ValueError("内容单元必须写明具体内容，不能只登记关键词。")
            source_ids = unit.get("segment_ids", [])
            if not source_ids or not set(source_ids) <= segments.keys():
                raise ValueError("内容单元必须有真实视频证据。")
            if not set(unit.get("frame_ids", [])) <= frame_ids:
                raise ValueError("内容单元的截图不存在。")
            if unit.get("treatment") == "omitted":
                if unit.get("critical") or not unit.get("omission_reason"):
                    raise ValueError("关键单元不能省略；其他省略必须记录原因。")
                if unit.get("card_id") is not None:
                    raise ValueError("省略项不能同时标记为讲义已保留。")
            elif unit.get("treatment") in ("retained", "expanded", "merged"):
                card = cards_by_id.get(unit.get("card_id"))
                if card is None or not set(source_ids) <= set(card["segment_ids"]):
                    raise ValueError("内容单元应落入拥有该证据的真实章节。")
            else:
                raise ValueError("内容单元必须明确保留、展开、合并或省略。")
    if not isinstance(review.get("questions"), list) or not review["questions"]:
        raise ValueError("请提供至少一个主动回忆问题。")
    return review


def jump(meta, t):
    return meta.get("source_url", "") + f"&t={int(t)}" if meta.get("source_url") else ""


def render(folder, evidence, review=None):
    e = html.escape
    meta, transcript = evidence["metadata"], evidence["transcript"]
    segs = transcript["segments"]
    segment_by_id = {s["id"]: s for s in segs}
    frame_by_id = {f["id"]: f for f in evidence["frames"]}
    def time_link(t):
        url = jump(meta, t)
        return f'<a href="{e(url, quote=True)}" target="_blank" rel="noreferrer">{stamp(t)} ↗</a>' if url else stamp(t)
    cards = []
    if review:
        if review.get("overview"):
            cards.append(f'<div class="notice"><strong>阅读主线</strong><p>{e(review["overview"])}</p></div>')
        if review.get("personal_context"):
            cards.append(f'<p class="quality">{e(review["personal_context"])}</p>')
        for card in review["cards"]:
            refs = "".join(f'<li>{e(str(ref["path"]))}:{ref["start_line"]}–{ref["end_line"]}<blockquote>{e(ref["quote"])}</blockquote></li>' for ref in card.get("memory_refs", []))
            sources = " · ".join(f'<a href="#{s}">原文 {stamp(segment_by_id[s]["start"])}</a>' for s in card["segment_ids"])
            if len(card["segment_ids"]) > 6:
                first = min(segment_by_id[s]["start"] for s in card["segment_ids"])
                last = max(segment_by_id[s]["end"] for s in card["segment_ids"])
                sources = f'<details class="citations"><summary>原文 {stamp(first)}–{stamp(last)} · 展开 {len(card["segment_ids"])} 段定位</summary><p>{sources}</p></details>'
            visual = " · ".join(f'<a href="#{f}">画面 {stamp(frame_by_id[f]["time"])}</a>' for f in card.get("frame_ids", []))
            body = f'<p>{e(card["summary"])}</p><div>{sources}</div><p>{visual}</p><ul>{refs}</ul>'
            if card["label"] == "known":
                cards.append(f'<details class="card known"><summary><span>已有记录 · 可展开</span> {e(card.get("title", card["id"]))}</summary>{body}</details>')
            else:
                cards.append(f'<article class="card"><span>{LABELS[card["label"]]}</span><h3>{e(card.get("title", card["id"]))}</h3>{body}</article>')
    else:
        cards.append('<div class="notice">材料已整理，个人增量尚未分析。此时没有内容被认定为“你已掌握”。</div>')
    events = [(s["start"], 1, s) for s in segs] + [(f["time"], 0, f) for f in evidence["frames"]]
    timeline = []
    for t, kind, item in sorted(events, key=lambda row: (row[0], row[1])):
        if kind:
            timeline.append(f'<p class="segment" id="{item["id"]}"><small>{time_link(t)} · {item["id"]}</small>{e(item["text"])}</p>')
        else:
            reason = {"first": "首帧", "periodic": "定时补帧", "scene-change": "画面变化"}[item["reason"]]
            timeline.append(f'<figure id="{item["id"]}"><a href="{e(item["path"])}"><img loading="lazy" src="{e(item["path"])}" alt="{stamp(t)} 的视频截图"></a><figcaption>{time_link(t)} · {reason} · {item["id"]}</figcaption></figure>')
    quality = evidence["coverage"]
    gap_list = "、".join(f'{stamp(g["start"])}–{stamp(g["end"])}' for g in quality["gaps_over_10s"]) or "无超过 10 秒的空白"
    questions = "".join(f'<li>{e(str(q))}</li>' for q in (review or {}).get("questions", []))
    template = (ROOT / "report.html").read_text()
    values = {"TITLE": e(meta.get("title") or "视频阅读材料"), "DURATION": stamp(evidence["media"]["duration"]),
              "SOURCE": e({"platform-subtitle": "平台字幕", "local-asr": "本地语音转录", "imported-subtitle": "导入字幕"}.get(transcript["source"], transcript["source"])), "COUNT": str(len(segs)), "FRAMES": str(len(evidence["frames"])),
              "CARDS": "\n".join(cards), "TIMELINE": "\n".join(timeline), "GAPS": e(gap_list),
              "WARNINGS": e("；".join(evidence.get("warnings", []) + (review or {}).get("limitations", [])) or "无采集错误记录。"),
              "QUESTIONS": f'<ol>{questions}</ol>' if questions else '<p>待个人增量分析后生成。</p>'}
    output = re.sub(r"\{\{([A-Z]+)\}\}", lambda m: values[m[1]], template)
    (folder / "report.html").write_text(output)
    lines = [f'# {meta.get("title", "视频转录")}', '', f'转录来源：{transcript["source"]}；尚未逐字对照音频核验。', '']
    for s in segs:
        lines += [f'[{s["id"]}] {stamp(s["start"])}–{stamp(s["end"])}', s["text"], '']
    (folder / "transcript.md").write_text("\n".join(lines))


def collect(args):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise ValueError("请先安装 ffmpeg（包含 ffprobe）。")
    if args.source:
        bvid, page, url = canonical(args.source, args.part)
        key = f"{bvid}-p{page}"
    elif args.media:
        url, key = "", f"local-{digest(args.media)[:12]}"
    else:
        raise ValueError("请提供 BV 号或 --media 本地媒体。")
    folder = Path(args.out).resolve() if args.out else ROOT / "runs" / key
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / ".lock"
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError(f"该输出目录正在使用；异常退出后请先确认无任务运行，再移除 {lock}") from None
    config = {"source": url, "media_hash": digest(args.media) if args.media else None,
              "subtitle_hash": digest(args.subtitle) if args.subtitle else None,
              "scene": args.scene, "min_gap": args.min_gap, "max_gap": args.max_gap,
              "language": args.language, "model": args.asr_model}
    manifest_path = folder / "manifest.json"
    manifest = {"config": config, "stage": "starting", "updated_at": time.time()}
    try:
        if manifest_path.exists() and read(manifest_path)["config"] != config:
            raise ValueError("该目录已有不同输入或配置。请指定新的 --out 以保留旧证据。")
        if (folder / "evidence.json").exists():
            evidence = read(folder / "evidence.json")
            review = read(folder / "review.json") if (folder / "review.json").exists() else None
            if review:
                validate_review(review, evidence)
            render(folder, evidence, review)
            manifest.update(stage="evidence-ready", updated_at=time.time())
            save(manifest_path, manifest)
            print(folder / "report.html")
            return
        save(manifest_path, manifest)
        if args.media:
            media = Path(args.media).resolve()
            meta = {"title": args.title or media.stem, "source_url": url, "local_media": str(media)}
            transcript, warnings = None, []
        elif (folder / "download.json").exists():
            downloaded = read(folder / "download.json")
            meta, transcript, warnings = downloaded["metadata"], downloaded["transcript"], downloaded["warnings"]
            media = folder / downloaded["media"]
        else:
            print("读取视频与可用字幕…", file=sys.stderr, flush=True)
            meta, media, transcript, warnings = fetch(url, folder, args.language)
            save(folder / "download.json", {"metadata": meta, "media": media.name, "transcript": transcript, "warnings": warnings})
        media_info = probe(media)
        if args.subtitle:
            path = Path(args.subtitle).resolve()
            original = folder / ("imported-subtitle" + path.suffix)
            shutil.copyfile(path, original)
            transcript = {"segments": subtitles(original), "source": "imported-subtitle", "original": original.name, "verified_against_audio": False}
        manifest["stage"] = "transcribing"
        save(manifest_path, manifest)
        if (folder / "transcript.json").exists():
            transcript = read(folder / "transcript.json")
        if transcript is None:
            if not media_info["has_audio"]:
                raise ValueError("媒体没有音轨，且没有可用字幕。")
            transcript = transcribe(media, args.asr_model, args.language, folder)
        if max(s["end"] for s in transcript["segments"]) > media_info["duration"] + 2:
            raise ValueError("字幕超出媒体时长，请检查是否匹配同一个分 P。")
        save(folder / "transcript.json", transcript)
        manifest["stage"] = "frames"
        save(manifest_path, manifest)
        if media_info["has_video"]:
            screenshots = frames(media, folder, args.scene, args.min_gap, args.max_gap)
        else:
            screenshots = []
            warnings.append("输入只有音频，未取得视觉材料。")
        evidence = {"schema_version": 1, "metadata": meta, "media": media_info, "transcript": transcript,
                    "frames": screenshots, "coverage": gaps(transcript["segments"], media_info["duration"]),
                    "warnings": warnings, "config": config}
        payload = json.dumps(evidence, ensure_ascii=False, sort_keys=True).encode()
        evidence["evidence_sha256"] = hashlib.sha256(payload).hexdigest()
        save(folder / "evidence.json", evidence)
        render(folder, evidence)
        manifest.update(stage="evidence-ready", updated_at=time.time())
        save(manifest_path, manifest)
        print(folder / "report.html")
    except Exception as exc:
        # Never overwrite an existing run's configuration when refusing a mismatch.
        if not manifest_path.exists() or read(manifest_path)["config"] == config:
            manifest.update(stage="failed", error=str(exc), updated_at=time.time())
            save(manifest_path, manifest)
        raise
    finally:
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description="BV → 原文、关键帧、图文时间轴；AI 分析由当前阅读对话完成。")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect")
    c.add_argument("source", nargs="?")
    c.add_argument("--part", type=int)
    c.add_argument("--media", type=Path)
    c.add_argument("--subtitle", type=Path)
    c.add_argument("--title")
    c.add_argument("--out")
    c.add_argument("--language", default="zh")
    c.add_argument("--asr-model", default="small")
    c.add_argument("--scene", type=float, default=0.18)
    c.add_argument("--min-gap", type=float, default=2)
    c.add_argument("--max-gap", type=float, default=60)
    a = sub.add_parser("review")
    a.add_argument("folder", type=Path)
    a.add_argument("review_file", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "collect":
            if not 0 < args.scene <= 1 or not 0 < args.min_gap <= args.max_gap or not math.isfinite(args.max_gap):
                raise ValueError("截图参数无效：0 < scene <= 1，0 < min-gap <= max-gap。")
            collect(args)
        else:
            evidence = read(args.folder / "evidence.json")
            review = validate_review(read(args.review_file), evidence)
            render(args.folder, evidence, review)
            save(args.folder / "review.json", review)
            print((args.folder / "report.html").resolve())
    except Exception as exc:
        print(f"未完成：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
