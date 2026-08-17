"""Render a steadier, slightly faster-feeling Qwen3 podcast performance.

This leaves the previous natural-voice render untouched.  It changes only the
TTS input copy: rhetorical punctuation is made neutral and paragraph joins are
kept explicit, so the model does not mistake the author's written emphasis for
an instruction to switch into a new performance state.
"""

from __future__ import annotations

import re

import render_qwen3_podcast as base


base.OUT_DIR = base.ROOT / "谈判力播客/qwen3_uniform_segments"
base.FULL_WAV = base.ROOT / "谈判力播客/《谈判力》中文播客-Qwen3统一口吻加速前.wav"
base.MANIFEST = base.OUT_DIR / "segments.json"
base.INSTRUCT = (
    "全程保持同一位成年男声平实、沉稳、略微偏快的中文单人播客口吻。"
    "像一个人在长时间连续讲述和思考，语气自然、克制，停顿简短且一致。"
    "感叹、反问、评价和引语都平静叙述，不抬高音调，不放慢，不戏剧化强调。"
    "不要新闻播音腔，不要朗诵腔，不要因段落内容切换情绪状态。"
)
# Voice consistency here comes from the controlled text and instruction.  The
# model's usual sampling range avoids the occasional overlong, low-entropy loop
# that can occur when this is set too low for a long Chinese paragraph.
base.TEMPERATURE = 0.8
base.TOP_K = 40
base.TOP_P = 0.95
base.REPETITION_PENALTY = 1.08


def chunk_text_with_boundaries(
    text: str, max_chars: int = 260, min_chars: int = 90
) -> list[str]:
    """Keep every source paragraph boundary audible, including after headings."""
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


def clean_chunk_for_uniform_speech(text: str) -> str:
    """Retain every word while neutralising written punctuation for TTS only."""
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
base.clean_chunk_for_speech = clean_chunk_for_uniform_speech


if __name__ == "__main__":
    base.main()
