from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

import mlx.core as mx
import numpy as np
from mlx_audio.audio_io import read as audio_read
from mlx_audio.audio_io import write as audio_write
from mlx_audio.tts.utils import load_model


ROOT = Path("/Users/houguanqun/Downloads/book/book")
MODEL = ROOT / ".models/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit"
SOURCE = ROOT / "谈判力播客/《谈判力》中文播客纯文本.txt"
OUT_DIR = ROOT / "谈判力播客/qwen3_segments"
FULL_WAV = ROOT / "谈判力播客/《谈判力》中文播客-Qwen3.wav"
MANIFEST = OUT_DIR / "segments.json"

VOICE = "Uncle_Fu"
INSTRUCT = (
    "自然、克制、松弛的中文单人播客口吻，像坐在桌边与听众认真聊天。"
    "语速中等，重音准确，停顿自然；带一点思考感和个人锋芒。"
    "不要新闻播音腔，不要字正腔圆地逐字朗诵，也不要夸张表演。"
)
TEMPERATURE = 0.8
TOP_K = 40
TOP_P = 0.95
REPETITION_PENALTY = 1.08


def normalize_for_model(text: str) -> str:
    replacements = {
        "TPP": "T P P",
        "GDP": "G D P",
        "BBC": "B B C",
        "T一": "T一",
        "T二": "T二",
        "1920s": "二十世纪二十年代",
        "08年": "二零零八年",
        "79年的": "一九七九年的",
        "3个": "三个",
        "2个": "两个",
        "1个": "一个",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_chunk_for_speech(text: str) -> str:
    """Remove citation labels and repair a title boundary without reflowing chunks."""
    citation_labels = [
        "Demonstrations, Hostility Greet Waldheim in Iran - The Washington Post",
        "Waldheim's Mission To Iran Ends With No Sign of Progress - The Washington Post",
        "Iran hostage rescue mission ends in disaster | April 24, 1980 | HISTORY",
        "Iran hostage crisis - Wikipedia",
    ]
    for label in citation_labels:
        text = text.replace(label, "")
    text = text.replace(
        "第十四章：原则不是立场原则谈判",
        "第十四章：原则不是立场。\n原则谈判",
    )
    text = re.sub(r" +([。；，])", r"\1", text)
    return text.strip()


def split_long_paragraph(paragraph: str, max_chars: int) -> list[str]:
    if len(paragraph) <= max_chars:
        return [paragraph]

    sentences = [
        item.strip()
        for item in re.split(r"(?<=[。！？；!?])", paragraph)
        if item.strip()
    ]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            # Commas are the next safest speech boundary for unusually long prose.
            clauses = [
                item.strip()
                for item in re.split(r"(?<=[，、：])", sentence)
                if item.strip()
            ]
            clause_buf = ""
            for clause in clauses:
                if clause_buf and len(clause_buf) + len(clause) > max_chars:
                    chunks.append(clause_buf)
                    clause_buf = clause
                else:
                    clause_buf += clause
            if clause_buf:
                chunks.append(clause_buf)
            continue

        if current and len(current) + len(sentence) > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current += sentence
    if current:
        chunks.append(current)
    return chunks


def chunk_text(text: str, max_chars: int = 260, min_chars: int = 90) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units: list[str] = []
    for paragraph in paragraphs:
        units.extend(split_long_paragraph(paragraph, max_chars))

    chunks: list[str] = []
    current = ""
    for unit in units:
        separator = "\n" if re.match(r"^(第[一二三四五六七八九十]+章|开场|收束)", unit) else ""
        candidate = f"{current}{separator}{unit}" if current else unit
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = unit
        else:
            current = candidate
    if current:
        chunks.append(current)

    # Avoid tiny trailing chunks, which tend to sound performative or unstable.
    merged: list[str] = []
    for chunk in chunks:
        if merged and len(chunk) < min_chars and len(merged[-1]) + len(chunk) <= max_chars + 50:
            merged[-1] = f"{merged[-1]}\n{chunk}"
        else:
            merged.append(chunk)
    return merged


def segment_path(index: int) -> Path:
    return OUT_DIR / f"segment_{index:03d}.wav"


def fade_edges(audio: np.ndarray, sample_rate: int, milliseconds: int = 12) -> np.ndarray:
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    fade_samples = min(int(sample_rate * milliseconds / 1000), len(audio) // 2)
    if fade_samples > 0:
        ramp = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
        audio[:fade_samples] *= ramp
        audio[-fade_samples:] *= ramp[::-1]
    return audio


def write_manifest(chunks: list[str], metadata: dict[int, dict[str, object]]) -> None:
    payload = {
        "model": str(MODEL),
        "voice": VOICE,
        "instruct": INSTRUCT,
        "segments": [
            {
                "index": index,
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "chars": len(text),
                "text": text,
                **metadata.get(index, {}),
            }
            for index, text in enumerate(chunks)
        ],
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def assemble(chunks: list[str]) -> None:
    combined: list[np.ndarray] = []
    expected_sample_rate: int | None = None
    for index, text in enumerate(chunks):
        audio, sample_rate = audio_read(str(segment_path(index)))
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        if expected_sample_rate is None:
            expected_sample_rate = int(sample_rate)
        elif int(sample_rate) != expected_sample_rate:
            raise RuntimeError(f"Sample rate mismatch in segment {index}: {sample_rate}")
        combined.append(audio)
        gap_seconds = 0.8 if re.search(r"第[一二三四五六七八九十]+章", text) else 0.36
        combined.append(np.zeros(int(expected_sample_rate * gap_seconds), dtype=np.float32))

    if expected_sample_rate is None:
        raise RuntimeError("No audio segments were generated")
    joined = np.concatenate(combined)
    audio_write(str(FULL_WAV), joined, expected_sample_rate, format="wav")
    print(f"Assembled {FULL_WAV} ({len(joined) / expected_sample_rate:.1f}s)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-chars", type=int, default=260)
    args = parser.parse_args()

    if not MODEL.joinpath("config.json").exists():
        raise FileNotFoundError(f"Model is not available at {MODEL}")

    text = normalize_for_model(SOURCE.read_text(encoding="utf-8"))
    if args.preview:
        text = (
            "今天想聊的是《谈判力》。这不是一期内容提要，也不是把书里的方法重新复述一遍。"
            "我更想沿着书中的案例往外走：去看双赢背后的权力，去看客观事实背后的解释器，"
            "也去看谈判者身后的国家、组织、阶级、观众和历史。"
        )

    # Clean after chunking so repair runs retain exactly the same segment indices.
    chunks = [
        clean_chunk_for_speech(chunk)
        for chunk in chunk_text(text, max_chars=args.max_chars)
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata: dict[int, dict[str, object]] = {}
    write_manifest(chunks, metadata)

    mx.random.seed(20260715)
    print(f"Loading {MODEL}")
    model = load_model(str(MODEL))
    print(f"Loaded model; {len(chunks)} segments, batch size {args.batch_size}")

    missing = [i for i in range(len(chunks)) if not segment_path(i).exists()]
    started = time.time()
    for offset in range(0, len(missing), args.batch_size):
        batch_indices = missing[offset : offset + args.batch_size]
        texts = [chunks[i] for i in batch_indices]
        results = list(
            model.batch_generate(
                texts=texts,
                voices=[VOICE] * len(texts),
                instructs=[INSTRUCT] * len(texts),
                lang_code="Chinese",
                temperature=TEMPERATURE,
                top_k=TOP_K,
                top_p=TOP_P,
                repetition_penalty=REPETITION_PENALTY,
                max_tokens=1800,
                stream=False,
                verbose=False,
            )
        )
        if len(results) != len(batch_indices):
            raise RuntimeError(
                f"Expected {len(batch_indices)} results, received {len(results)}"
            )
        for result in results:
            source_index = batch_indices[result.sequence_idx]
            audio = fade_edges(np.array(result.audio), result.sample_rate)
            audio_write(
                str(segment_path(source_index)),
                audio,
                result.sample_rate,
                format="wav",
            )
            seconds = len(audio) / result.sample_rate
            metadata[source_index] = {
                "duration_seconds": round(seconds, 3),
                "peak": round(float(np.max(np.abs(audio))), 6),
                "rms": round(float(np.sqrt(np.mean(audio**2))), 6),
            }
            print(
                f"[{source_index + 1:02d}/{len(chunks)}] "
                f"{len(chunks[source_index])} chars -> {seconds:.1f}s"
            )
        write_manifest(chunks, metadata)
        mx.clear_cache()

    # Restore metadata from existing files during resume runs.
    for index in range(len(chunks)):
        if index in metadata:
            continue
        audio, sample_rate = audio_read(str(segment_path(index)))
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        metadata[index] = {
            "duration_seconds": round(len(audio) / sample_rate, 3),
            "peak": round(float(np.max(np.abs(audio))), 6),
            "rms": round(float(np.sqrt(np.mean(audio**2))), 6),
        }
    write_manifest(chunks, metadata)
    assemble(chunks)
    print(f"Done in {(time.time() - started) / 60:.1f} minutes")


if __name__ == "__main__":
    main()
