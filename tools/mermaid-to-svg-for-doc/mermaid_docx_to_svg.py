#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
DOC_XML_PATH = "word/document.xml"

MERMAID_BLOCK_START = re.compile(
    r"^(graph\s+(TD|LR|RL|BT)|flowchart\s+(TD|LR|RL|BT)|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie\b|mindmap|timeline)\b",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract Mermaid diagrams from a DOCX file and render them to SVG.",
    )
    parser.add_argument("input", type=Path, help="Path to input .docx file")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("svg-output"),
        help="Directory to write SVG files (default: ./svg-output)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds for each Mermaid render operation (default: 60)",
    )
    parser.add_argument(
        "--renderer",
        choices=["local", "kroki"],
        default="local",
        help="Renderer engine: local (mermaid-cli) or kroki API (default: local)",
    )
    return parser.parse_args()


def extract_paragraph_texts(docx_path: Path) -> list[str]:
    with zipfile.ZipFile(docx_path) as docx:
        document_xml = docx.read(DOC_XML_PATH)

    root = ET.fromstring(document_xml)
    paragraphs: list[str] = []

    for paragraph in root.findall(".//w:p", WORD_NS):
        text_parts = [t.text or "" for t in paragraph.findall(".//w:t", WORD_NS)]
        text = "".join(text_parts).strip()
        if text:
            paragraphs.append(text)

    return paragraphs


def extract_mermaid_blocks(paragraphs: list[str]) -> list[str]:
    blocks: list[str] = []
    in_fenced_block = False
    fenced_lines: list[str] = []

    for paragraph in paragraphs:
        text = paragraph.strip()

        if not in_fenced_block and text.lower() == "```mermaid":
            in_fenced_block = True
            fenced_lines = []
            continue

        if in_fenced_block:
            if text == "```":
                candidate = "\n".join(fenced_lines).strip()
                if candidate:
                    blocks.append(candidate)
                in_fenced_block = False
                fenced_lines = []
            else:
                fenced_lines.append(text)
            continue

        if MERMAID_BLOCK_START.match(text):
            blocks.append(text)

    if in_fenced_block and fenced_lines:
        candidate = "\n".join(fenced_lines).strip()
        if candidate:
            blocks.append(candidate)

    return blocks


def normalize_mermaid_block(block: str) -> str:
    text = block.strip()

    if "\n" not in text and "\r" not in text:
        # DOCX often collapses a full Mermaid diagram into one paragraph with wide spacing.
        text = re.sub(r"[ \t]{2,}", "\n", text)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def render_mermaid_svg(diagram: str, timeout: int) -> str:
    return render_mermaid_svg_via_kroki(diagram, timeout)


def render_mermaid_svg_local(diagram: str, timeout: int) -> str:
    with tempfile.TemporaryDirectory(prefix="mermaid-docx-") as tmpdir:
        tmp_path = Path(tmpdir)
        src_path = tmp_path / "diagram.mmd"
        svg_path = tmp_path / "diagram.svg"

        src_path.write_text(diagram, encoding="utf-8")

        command = [
            "npx",
            "-y",
            "@mermaid-js/mermaid-cli",
            "-i",
            str(src_path),
            "-o",
            str(svg_path),
            "--outputFormat",
            "svg",
            "--quiet",
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
            raise RuntimeError(f"mermaid-cli failed: {stderr}")

        if not svg_path.exists():
            raise RuntimeError("mermaid-cli completed but SVG file was not produced")

        payload = svg_path.read_text(encoding="utf-8")
        if "<svg" not in payload:
            raise RuntimeError("mermaid-cli output does not look like SVG")

        return payload


def render_mermaid_svg_via_kroki(diagram: str, timeout: int) -> str:
    url = "https://kroki.io/mermaid/svg"
    request = urllib.request.Request(
        url=url,
        method="POST",
        data=diagram.encode("utf-8"),
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Kroki HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Cannot reach Kroki service: {error.reason}") from error

    if "<svg" not in payload:
        raise RuntimeError("Kroki response does not look like SVG output")

    return payload


def convert_docx(input_path: Path, output_dir: Path, timeout: int, renderer: str) -> int:
    paragraphs = extract_paragraph_texts(input_path)
    blocks = extract_mermaid_blocks(paragraphs)

    if not blocks:
        print("No Mermaid blocks found in DOCX.")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = input_path.stem

    success_count = 0
    for index, block in enumerate(blocks, start=1):
        output_file = output_dir / f"{base_name}-mermaid-{index:02d}.svg"
        try:
            normalized_block = normalize_mermaid_block(block)
            if renderer == "local":
                svg = render_mermaid_svg_local(normalized_block, timeout=timeout)
            else:
                svg = render_mermaid_svg(normalized_block, timeout=timeout)
            output_file.write_text(svg, encoding="utf-8")
            success_count += 1
            print(f"[{index}/{len(blocks)}] wrote {output_file}")
        except Exception as error:  # keep converting other blocks
            print(f"[{index}/{len(blocks)}] failed: {error}", file=sys.stderr)

    print(f"Done. {success_count}/{len(blocks)} Mermaid blocks rendered to SVG.")
    return 0 if success_count == len(blocks) else 2


def main() -> int:
    args = parse_args()
    input_path: Path = args.input

    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1

    if input_path.suffix.lower() != ".docx":
        print("Only .docx files are supported.", file=sys.stderr)
        return 1

    try:
        return convert_docx(
            input_path,
            args.output_dir,
            timeout=args.timeout,
            renderer=args.renderer,
        )
    except zipfile.BadZipFile:
        print(f"Invalid DOCX file (not a valid zip archive): {input_path}", file=sys.stderr)
        return 1
    except KeyError:
        print(f"DOCX missing expected {DOC_XML_PATH}: {input_path}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Unexpected error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
