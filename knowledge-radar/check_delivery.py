#!/usr/bin/env python3
"""Read-only artifact gate. Passing proves local readiness, not message delivery or mastery."""
import argparse
import hashlib
import json
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLI = "/Users/houguanqun/dsh/local-reader/scripts/learning"
BOOKS = Path("/Users/houguanqun/Library/Application Support/LocalReader/Books")


def check(root, day, books, books_dir):
    date.fromisoformat(day)
    manifest = root / "state" / "deliveries" / (day + ".json")
    data = json.loads(manifest.read_text())
    if data["date"] != day:
        raise ValueError("交付清单日期不匹配")
    if data["status"] != "ready":
        raise ValueError("尚未完整交付：" + data.get("blocker", "缺少已验证的成品"))
    for name in ("report", "record", "chinese", "import_record"):
        item = data[name]
        path = (root / item["path"]).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("交付路径越界：" + name)
        raw = path.read_bytes()
        if not raw.strip() or hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise ValueError("文件缺失、为空或版本不匹配：" + name)
    report = (root / data["report"]["path"]).read_text()
    record = json.loads((root / data["record"]["path"]).read_text())
    if day not in report or not any(
        e["id"] == data["entity_id"] and e.get("featured")
        for e in record["entities"]
    ):
        raise ValueError("日报日期或主对象不匹配")
    matches = [b for b in books if b["id"] == data["book_id"]]
    if len(matches) != 1 or matches[0]["title"] != data["book_title"]:
        raise ValueError("实际书库没有匹配的中文书籍")
    file_name = matches[0]["fileName"]
    if Path(file_name).name != file_name:
        raise ValueError("书库副本文件名无效")
    if hashlib.sha256((books_dir / file_name).read_bytes()).hexdigest() != data["chinese"]["sha256"]:
        raise ValueError("LocalReader 副本与中文文件不一致")
    if data.get("readback") != ["beginning", "middle", "end"]:
        raise ValueError("缺少首中尾回读记录")
    return "READY：当日日报、中文阅读件及实际书库副本一致；仍须在对话发送成品链接。"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    try:
        # Check manifest before launching even a read-only app query.
        if not (ROOT / "state" / "deliveries" / (args.date + ".json")).exists():
            raise ValueError("缺少当天交付清单；配置启用不等于完成")
        result = subprocess.run([CLI, "books"], check=True, capture_output=True, text=True, timeout=30)
        print(check(ROOT, args.date, json.loads(result.stdout)["books"], BOOKS))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print("NOT_READY：" + str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

