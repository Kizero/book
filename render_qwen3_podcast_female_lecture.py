"""Render the episode as a clear, steady female lecture.

All text transformations are TTS-only: the source manuscript remains intact.
"""

from __future__ import annotations

import re

import render_qwen3_podcast as base


base.OUT_DIR = base.ROOT / "谈判力播客/qwen3_female_lecture_segments"
base.FULL_WAV = base.ROOT / "谈判力播客/《谈判力》中文播客-Qwen3女声讲课版加速前.wav"
base.MANIFEST = base.OUT_DIR / "segments.json"
base.VOICE = "Vivian"
base.INSTRUCT = (
    "清晰、实声、稳定的普通话女讲师，面对成年听众系统讲解一本书。"
    "全程像课堂知识讲授：发音清楚、声音落在实处、气息饱满，语速中等偏快。"
    "不用气声、耳语、贴耳低语、神秘叙事或悬疑氛围；呼吸声极轻。"
    "反问、感叹、批评和引语都平静讲完，不一惊一乍，不忽然压低音量，"
    "不拉长停顿，不用戏剧化表演。"
)
base.TEMPERATURE = 0.8
base.TOP_K = 40
base.TOP_P = 0.95
base.REPETITION_PENALTY = 1.08


def chunk_text_with_boundaries(
    text: str, max_chars: int = 260, min_chars: int = 90
) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units: list[str] = []
    for paragraph in paragraphs:
        units.extend(base.split_long_paragraph(paragraph, max_chars))

    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n{unit}" if current else unit
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = unit
        else:
            current = candidate
    if current:
        chunks.append(current)

    merged: list[str] = []
    for chunk in chunks:
        if merged and len(chunk) < min_chars and len(merged[-1]) + len(chunk) <= max_chars + 50:
            merged[-1] = f"{merged[-1]}\n{chunk}"
        else:
            merged.append(chunk)
    return merged


_previous_clean = base.clean_chunk_for_speech


def clean_chunk_for_lecture(text: str) -> str:
    """Prevent written emphasis from becoming vocal drama, without deleting words."""
    text = _previous_clean(text)
    text = text.replace("……", "。")
    text = text.replace("…", "。")
    text = text.replace("——", "，")
    text = text.replace("—", "，")
    text = text.replace("！", "。")
    text = text.replace("!", "。")
    text = text.replace("？", "。")
    text = text.replace("?", "。")
    text = re.sub(r"。{2,}", "。", text)
    text = re.sub(r"，{2,}", "，", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


base.chunk_text = chunk_text_with_boundaries
base.clean_chunk_for_speech = clean_chunk_for_lecture


if __name__ == "__main__":
    base.main()
