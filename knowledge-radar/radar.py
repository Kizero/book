#!/usr/bin/env python3
"""Local, inspectable knowledge-radar harness.

The JSON records are the intermediate representation.  This program validates
their evidence links, rebuilds derived state, replays human feedback, and emits
a compact daily report.  It intentionally uses only Python's standard library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


SCHEMA_VERSION = 1
ENTITY_STATUSES = {"candidate", "known", "reading", "read", "ignored"}
CONFIDENCE_LEVELS = {"verified", "likely", "unverified", "disputed"}
CONTEXT_KINDS = {"biography", "origin", "bridge", "counterpoint"}
LOCATOR_RE = re.compile(r"^L([1-9][0-9]*)(?:-L?([1-9][0-9]*))?$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9:._-]*$")


class ValidationFailure(Exception):
    pass


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"{path}: invalid JSON: {exc}") from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def locate(lines: list[str], locator: str) -> tuple[int, int, str]:
    match = LOCATOR_RE.match(locator)
    if not match:
        raise ValidationFailure(f"invalid locator {locator!r}; expected L12 or L12-L15")
    start = int(match.group(1))
    end = int(match.group(2) or start)
    if start > end:
        raise ValidationFailure(f"invalid backwards locator {locator!r}")
    if end > len(lines):
        raise ValidationFailure(
            f"locator {locator!r} exceeds artifact length ({len(lines)} lines)"
        )
    return start, end, "\n".join(lines[start - 1 : end])


def record_paths(root: Path) -> list[Path]:
    return sorted((root / "records").glob("*.json"))


def feedback_events(root: Path) -> list[dict[str, Any]]:
    path = root / "state" / "feedback.jsonl"
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationFailure(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if event.get("entity_id") is None or event.get("status") not in ENTITY_STATUSES:
            raise ValidationFailure(
                f"{path}:{line_number}: feedback needs entity_id and a valid status"
            )
        events.append(event)
    return events


def ensure_list(record: dict[str, Any], field: str, path: Path, errors: list[str]) -> list[Any]:
    value = record.get(field, [])
    if not isinstance(value, list):
        errors.append(f"{path}: {field} must be a list")
        return []
    return value


def validate_record(root: Path, path: Path, global_ids: set[str]) -> list[str]:
    errors: list[str] = []
    try:
        record = read_json(path)
    except ValidationFailure as exc:
        return [str(exc)]
    if not isinstance(record, dict):
        return [f"{path}: top level must be an object"]
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{path}: schema_version must be {SCHEMA_VERSION}")
    record_id = record.get("id")
    if not isinstance(record_id, str) or not ID_RE.match(record_id):
        errors.append(f"{path}: invalid record id {record_id!r}")
    elif record_id in global_ids:
        errors.append(f"{path}: duplicate record id {record_id!r}")
    else:
        global_ids.add(record_id)

    captured_at = record.get("captured_at")
    try:
        datetime.fromisoformat(captured_at)
    except (TypeError, ValueError):
        errors.append(f"{path}: captured_at must be an ISO-8601 timestamp")

    artifact = record.get("artifact")
    if not isinstance(artifact, dict):
        return errors + [f"{path}: artifact must be an object"]
    raw_path = artifact.get("raw_path")
    if not isinstance(raw_path, str):
        return errors + [f"{path}: artifact.raw_path must be a string"]
    raw_file = (root / raw_path).resolve()
    try:
        raw_file.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{path}: artifact.raw_path escapes the radar root")
        return errors
    if not raw_file.is_file():
        return errors + [f"{path}: missing artifact {raw_path}"]
    lines = raw_file.read_text(encoding="utf-8").splitlines()
    expected_hash = artifact.get("sha256")
    actual_hash = sha256(raw_file)
    if expected_hash and expected_hash != actual_hash:
        errors.append(
            f"{path}: artifact hash mismatch for {raw_path}; expected {expected_hash}, got {actual_hash}"
        )
    source_url = artifact.get("source_url")
    if source_url is not None and (not isinstance(source_url, str) or not valid_url(source_url)):
        errors.append(f"{path}: artifact.source_url must be an http(s) URL or null")

    entity_ids: set[str] = set()
    for entity in ensure_list(record, "entities", path, errors):
        if not isinstance(entity, dict):
            errors.append(f"{path}: every entity must be an object")
            continue
        entity_id = entity.get("id")
        if not isinstance(entity_id, str) or not ID_RE.match(entity_id):
            errors.append(f"{path}: invalid entity id {entity_id!r}")
        elif entity_id in entity_ids:
            errors.append(f"{path}: duplicate local entity id {entity_id!r}")
        else:
            entity_ids.add(entity_id)
        if entity.get("status", "candidate") not in ENTITY_STATUSES:
            errors.append(f"{path}: entity {entity_id!r} has invalid status")
        priority = entity.get("priority", 3)
        if not isinstance(priority, int) or not 1 <= priority <= 5:
            errors.append(f"{path}: entity {entity_id!r} priority must be 1..5")

    evidence_groups: Iterable[tuple[str, list[Any]]] = (
        ("claims", ensure_list(record, "claims", path, errors)),
        ("methods", ensure_list(record, "methods", path, errors)),
        ("context_cards", ensure_list(record, "context_cards", path, errors)),
        ("resources", ensure_list(record, "resources", path, errors)),
    )
    for group_name, items in evidence_groups:
        for item in items:
            if not isinstance(item, dict):
                errors.append(f"{path}: every {group_name} item must be an object")
                continue
            item_id = item.get("id")
            if not isinstance(item_id, str) or not ID_RE.match(item_id):
                errors.append(f"{path}: invalid {group_name} id {item_id!r}")
            locator = item.get("locator")
            evidence = item.get("evidence")
            try:
                _, _, selected = locate(lines, locator)
            except (TypeError, ValidationFailure) as exc:
                errors.append(f"{path}: {group_name} {item_id!r}: {exc}")
                continue
            if not isinstance(evidence, str) or evidence not in selected:
                errors.append(
                    f"{path}: {group_name} {item_id!r} evidence is not present at {locator}"
                )
            confidence = item.get("confidence", "unverified")
            if confidence not in CONFIDENCE_LEVELS:
                errors.append(f"{path}: {group_name} {item_id!r} has invalid confidence")
            about_entity = item.get("about_entity")
            if about_entity is not None and (
                not isinstance(about_entity, str) or not ID_RE.match(about_entity)
            ):
                errors.append(
                    f"{path}: {group_name} {item_id!r} has invalid about_entity"
                )
            if group_name == "context_cards" and item.get("kind") not in CONTEXT_KINDS:
                errors.append(
                    f"{path}: context_cards {item_id!r} kind must be one of "
                    f"{sorted(CONTEXT_KINDS)}"
                )

    for resource in ensure_list(record, "resources", path, errors):
        if not isinstance(resource, dict):
            continue
        url = resource.get("url")
        local_path = resource.get("local_path")
        if url is not None and (not isinstance(url, str) or not valid_url(url)):
            errors.append(f"{path}: resource {resource.get('id')!r} has invalid URL")
        if local_path is not None:
            if not isinstance(local_path, str):
                errors.append(
                    f"{path}: resource {resource.get('id')!r} local_path must be a string"
                )
            else:
                resource_path = (root / local_path).resolve()
                try:
                    resource_path.relative_to(root.resolve())
                except ValueError:
                    errors.append(
                        f"{path}: resource {resource.get('id')!r} local_path escapes the radar root"
                    )
                else:
                    if not resource_path.is_file():
                        errors.append(
                            f"{path}: resource {resource.get('id')!r} local_path is missing"
                        )

    for relation in ensure_list(record, "relations", path, errors):
        if not isinstance(relation, dict):
            errors.append(f"{path}: every relation must be an object")
            continue
        relation_id = relation.get("id", "<unknown>")
        for endpoint in ("from", "to"):
            if relation.get(endpoint) not in entity_ids:
                errors.append(
                    f"{path}: relation {relation_id!r} {endpoint} must name a local entity"
                )
        locator = relation.get("locator")
        if locator:
            try:
                locate(lines, locator)
            except ValidationFailure as exc:
                errors.append(f"{path}: relation {relation_id!r}: {exc}")
    return errors


def validate_all(root: Path) -> list[str]:
    errors: list[str] = []
    paths = record_paths(root)
    if not paths:
        errors.append(f"{root / 'records'}: no records found")
    ids: set[str] = set()
    for path in paths:
        errors.extend(validate_record(root, path, ids))
    try:
        feedback_events(root)
    except ValidationFailure as exc:
        errors.append(str(exc))
    return errors


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def loaded_records(root: Path) -> list[dict[str, Any]]:
    return [read_json(path) for path in record_paths(root)]


def build_index(root: Path) -> dict[str, Any]:
    errors = validate_all(root)
    if errors:
        raise ValidationFailure("\n".join(errors))
    records = loaded_records(root)
    entities: dict[str, dict[str, Any]] = {}
    methods: dict[str, dict[str, Any]] = {}
    context_cards: dict[str, dict[str, Any]] = {}
    resources: dict[str, dict[str, Any]] = {}
    relations: list[dict[str, Any]] = []

    for record in records:
        record_id = record["id"]
        day = record["captured_at"][:10]
        for entity in record.get("entities", []):
            entity_id = entity["id"]
            current = entities.setdefault(
                entity_id,
                {
                    "id": entity_id,
                    "name": entity["name"],
                    "type": entity["type"],
                    "aliases": [],
                    "status": entity.get("status", "candidate"),
                    "max_priority": entity.get("priority", 3),
                    "first_seen": day,
                    "last_seen": day,
                    "mentions": [],
                    "featured": False,
                    "blurb": "",
                    "why_it_matters": "",
                    "recommended_action": "",
                    "report_note": "",
                },
            )
            current["aliases"] = sorted(
                set(current["aliases"]) | set(entity.get("aliases", []))
            )
            current["max_priority"] = max(current["max_priority"], entity.get("priority", 3))
            current["first_seen"] = min(current["first_seen"], day)
            current["last_seen"] = max(current["last_seen"], day)
            if current["status"] == "candidate" and entity.get("status") != "candidate":
                current["status"] = entity.get("status", current["status"])
            current["featured"] = current["featured"] or bool(entity.get("featured"))
            for field in ("blurb", "why_it_matters", "recommended_action"):
                if entity.get(field):
                    current[field] = entity[field]
            if record.get("report_note"):
                current["report_note"] = record["report_note"]
            current["mentions"].append(
                {
                    "record_id": record_id,
                    "locator": entity.get("locator"),
                    "context": entity.get("context", ""),
                    "confidence": entity.get("confidence", "unverified"),
                }
            )

        for method in record.get("methods", []):
            method_id = method["id"]
            current_method = methods.setdefault(
                method_id,
                {
                    "id": method_id,
                    "title": method["title"],
                    "summary": method["summary"],
                    "max_priority": method.get("priority", 3),
                    "appearances": [],
                    "acceptance": [],
                    "about_entities": [],
                },
            )
            current_method["max_priority"] = max(
                current_method["max_priority"], method.get("priority", 3)
            )
            current_method["acceptance"] = sorted(
                set(current_method["acceptance"]) | set(method.get("acceptance", []))
            )
            if method.get("about_entity"):
                current_method["about_entities"] = sorted(
                    set(current_method["about_entities"]) | {method["about_entity"]}
                )
            current_method["appearances"].append(
                {
                    "record_id": record_id,
                    "locator": method["locator"],
                    "confidence": method.get("confidence", "unverified"),
                    "about_entity": method.get("about_entity"),
                }
            )

        for card in record.get("context_cards", []):
            card_id = card["id"]
            current_card = context_cards.setdefault(
                card_id,
                {
                    "id": card_id,
                    "title": card["title"],
                    "summary": card["summary"],
                    "kind": card["kind"],
                    "about_entity": card.get("about_entity"),
                    "max_priority": card.get("priority", 3),
                    "appearances": [],
                },
            )
            current_card["max_priority"] = max(
                current_card["max_priority"], card.get("priority", 3)
            )
            current_card["appearances"].append(
                {
                    "record_id": record_id,
                    "locator": card["locator"],
                    "confidence": card.get("confidence", "unverified"),
                }
            )

        for resource in record.get("resources", []):
            resource_id = resource["id"]
            current_resource = resources.setdefault(
                resource_id,
                {
                    "id": resource_id,
                    "label": resource["label"],
                    "note": resource.get("note", ""),
                    "url": resource.get("url"),
                    "local_path": resource.get("local_path"),
                    "about_entity": resource.get("about_entity"),
                    "max_priority": resource.get("priority", 3),
                    "appearances": [],
                },
            )
            current_resource["max_priority"] = max(
                current_resource["max_priority"], resource.get("priority", 3)
            )
            current_resource["appearances"].append(
                {
                    "record_id": record_id,
                    "locator": resource["locator"],
                    "confidence": resource.get("confidence", "unverified"),
                }
            )

        for relation in record.get("relations", []):
            relations.append({**relation, "record_id": record_id})

    for event in feedback_events(root):
        entity = entities.get(event["entity_id"])
        if entity is None:
            raise ValidationFailure(
                f"feedback references missing entity {event['entity_id']!r}"
            )
        entity["status"] = event["status"]
        entity["last_feedback"] = {
            "at": event.get("at"),
            "note": event.get("note", ""),
        }

    entity_list = sorted(
        entities.values(), key=lambda value: (-value["max_priority"], value["name"])
    )
    method_list = sorted(
        methods.values(), key=lambda value: (-value["max_priority"], value["title"])
    )
    context_card_list = sorted(
        context_cards.values(),
        key=lambda value: (-value["max_priority"], value["title"]),
    )
    resource_list = sorted(
        resources.values(), key=lambda value: (-value["max_priority"], value["label"])
    )
    days = sorted(record["captured_at"][:10] for record in records)
    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": days[-1] if days else None,
        "stats": {
            "records": len(records),
            "entities": len(entity_list),
            "candidate_entities": sum(item["status"] == "candidate" for item in entity_list),
            "methods": len(method_list),
            "context_cards": len(context_card_list),
            "resources": len(resource_list),
            "relations": len(relations),
        },
        "records": [
            {
                "id": record["id"],
                "captured_at": record["captured_at"],
                "artifact": record["artifact"],
            }
            for record in records
        ],
        "entities": entity_list,
        "methods": method_list,
        "context_cards": context_card_list,
        "resources": resource_list,
        "relations": sorted(relations, key=lambda value: value["id"]),
    }


def rebuild(root: Path) -> dict[str, Any]:
    index = build_index(root)
    destination = root / "state" / "index.json"
    atomic_write(destination, json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    return index


def record_link(record: dict[str, Any], locator: str | None = None) -> str:
    raw_path = record["artifact"]["raw_path"]
    suffix = f"#{locator.lower()}" if locator else ""
    return f"../{raw_path}{suffix}"


def local_resource_link(local_path: str) -> str:
    return f"../{local_path}"


def evidence_label(record: dict[str, Any], confidence: str) -> str:
    if confidence == "verified":
        return "已由原始来源核实"
    provenance = record.get("artifact", {}).get("provenance")
    if provenance == "user_supplied_excerpt":
        return "用户提供的摘录，尚未独立复核"
    if provenance == "user_supplied":
        return "用户现场转述，尚未对照原始材料"
    if confidence == "disputed":
        return "存在争议"
    if confidence == "likely":
        return "较可信，尚未完成原始来源核验"
    return "尚未完成原始来源核验"


def artifact_boundary(record: dict[str, Any]) -> str:
    verification = record.get("artifact", {}).get("verification")
    return {
        "comment_text_not_independently_archived": "评论文字来自用户摘录，尚未保存可独立复核的评论页面。",
        "unverified_against_original_video": "内容来自用户现场转述，尚未对照原视频或讲义。",
        "verified_primary": "关键书目信息已经由原始出版来源核验。",
    }.get(verification, "该材料尚未完成原始来源核验。")


def render_report(root: Path, day: str, limit: int = 3) -> str:
    index = build_index(root)
    records = {
        record["id"]: record
        for record in loaded_records(root)
        if record["captured_at"].startswith(day)
    }
    lines = [f"# 今日信息简报 · {day}", ""]
    if not records:
        lines.extend(["今天没有发现值得打扰你的可信增量。", ""])
        return "\n".join(lines)

    candidates = []
    for entity in index["entities"]:
        if entity["status"] != "candidate":
            continue
        mentions = [m for m in entity["mentions"] if m["record_id"] in records]
        if mentions:
            candidates.append((entity, mentions))
    featured = [item for item in candidates if item[0].get("featured")]
    primary = featured[:limit] if featured else candidates[:limit]
    lines.extend(["## 今天先看什么", ""])
    if not candidates:
        lines.extend(["今天没有需要进入阅读队列的新对象。", ""])
    for number, (entity, mentions) in enumerate(primary, 1):
        lines.append(f"### {number}. {entity['name']}")
        lines.append("")
        if entity.get("aliases"):
            lines.append(f"也可以用这些名字找到它：{'、'.join(entity['aliases'])}。")
            lines.append("")
        if entity.get("blurb"):
            lines.append(entity["blurb"])
            lines.append("")
        if entity.get("why_it_matters"):
            lines.append(f"**为什么值得你关注：** {entity['why_it_matters']}")
            lines.append("")
        entity_resources = [
            resource
            for resource in index.get("resources", [])
            if resource.get("about_entity") == entity["id"]
            and any(a["record_id"] in records for a in resource["appearances"])
        ]
        for resource in entity_resources[:2]:
            target = (
                local_resource_link(resource["local_path"])
                if resource.get("local_path")
                else resource["url"]
            )
            label = "**免费全文：**" if resource.get("local_path") else "**在线版本：**"
            note = f"。{resource['note']}" if resource.get("note") else ""
            lines.append(f"{label} [{resource['label']}]({target}){note}")
            lines.append("")
        if entity.get("recommended_action"):
            lines.append(f"**怎么读：** {entity['recommended_action']}")
        lines.append("")

    for entity, _ in primary:
        cards = [
            card
            for card in index.get("context_cards", [])
            if card.get("about_entity") == entity["id"]
            and any(a["record_id"] in records for a in card["appearances"])
        ]
        background = [card for card in cards if card["kind"] in {"biography", "origin", "bridge"}]
        counterpoints = [card for card in cards if card["kind"] == "counterpoint"]
        if background:
            lines.extend(["## 来龙去脉", ""])
            for card in background:
                appearance = next(
                    a for a in card["appearances"] if a["record_id"] in records
                )
                record = records[appearance["record_id"]]
                lines.append(f"### {card['title']}")
                lines.append("")
                lines.append(
                    f"{card['summary']} [展开]({record_link(record, appearance['locator'])})"
                )
                lines.append("")

        methods = []
        for method in index["methods"]:
            appearances = [
                a
                for a in method["appearances"]
                if a["record_id"] in records and a.get("about_entity") == entity["id"]
            ]
            if appearances:
                methods.append((method, appearances))
        if methods:
            heading = "从这本书可以带走什么" if entity["type"] == "book" else "从这篇材料可以带走什么"
            lines.extend([f"## {heading}", ""])
            for method, appearances in methods[:4]:
                appearance = appearances[0]
                record = records[appearance["record_id"]]
                lines.append(
                    f"- **{method['title']}**：{method['summary']} "
                    f"[展开]({record_link(record, appearance['locator'])})"
                )
            lines.append("")

        if counterpoints:
            lines.extend(["## 不要照单全收", ""])
            for card in counterpoints:
                appearance = next(
                    a for a in card["appearances"] if a["record_id"] in records
                )
                record = records[appearance["record_id"]]
                lines.append(
                    f"- **{card['title']}**：{card['summary']} "
                    f"[展开]({record_link(record, appearance['locator'])})"
                )
            lines.append("")

        if entity.get("report_note"):
            lines.append(f"> 资料说明：{entity['report_note']}")
            lines.append("")

    for record in records.values():
        for section in record.get("report_sections", []):
            lines.extend([f"## {section['title']}", "", section["body"], ""])

    lines.extend(["## 你只需要告诉我", ""])
    lines.append("对最上面的对象回复“准备读”“已经知道”或“暂时忽略”即可；后续日报会据此去重和调整优先级。")
    lines.append("")
    return "\n".join(lines)


def add_feedback(root: Path, entity_id: str, status: str, note: str) -> None:
    index = build_index(root)
    if entity_id not in {entity["id"] for entity in index["entities"]}:
        raise ValidationFailure(f"unknown entity {entity_id!r}")
    event = {
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "entity_id": entity_id,
        "status": status,
        "note": note,
    }
    path = root / "state" / "feedback.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="可检查、可重放的个人信息雷达")
    result.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="radar data root (defaults to the directory containing radar.py)",
    )
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="validate records, evidence locators, hashes and feedback")
    commands.add_parser("rebuild", help="rebuild derived state/index.json")
    report = commands.add_parser("report", help="render a daily Markdown report")
    report.add_argument("--date", required=True, help="YYYY-MM-DD")
    report.add_argument("--limit", type=int, default=3)
    report.add_argument("--stdout", action="store_true")
    feedback = commands.add_parser("feedback", help="append human feedback for an entity")
    feedback.add_argument("entity_id")
    feedback.add_argument("--status", required=True, choices=sorted(ENTITY_STATUSES))
    feedback.add_argument("--note", default="")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "validate":
            errors = validate_all(root)
            if errors:
                print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
                return 1
            print(f"OK: {len(record_paths(root))} records validated")
            return 0
        if args.command == "rebuild":
            index = rebuild(root)
            print(json.dumps(index["stats"], ensure_ascii=False))
            return 0
        if args.command == "report":
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", args.date):
                raise ValidationFailure("--date must be YYYY-MM-DD")
            report_text = render_report(root, args.date, args.limit)
            if args.stdout:
                print(report_text)
            else:
                destination = root / "reports" / f"{args.date}.md"
                atomic_write(destination, report_text + "\n")
                print(destination)
            return 0
        if args.command == "feedback":
            add_feedback(root, args.entity_id, args.status, args.note)
            print(f"feedback recorded: {args.entity_id} -> {args.status}")
            return 0
    except ValidationFailure as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
