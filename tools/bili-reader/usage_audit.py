#!/usr/bin/env python3
"""Export one explicitly selected Codex turn's usage, without copying conversations."""
import argparse
import json
from datetime import datetime
from pathlib import Path

FIELDS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens",
          "output_tokens", "reasoning_output_tokens", "total_tokens")


def audit(path, turn_id):
    records, started, completed, last_cumulative = {}, None, None, None
    with Path(path).open() as stream:
        for line in stream:
            item = json.loads(line)
            payload = item.get("payload", {})
            if payload.get("turn_id") != turn_id:
                continue
            if item["type"] == "event_msg":
                if payload.get("type") == "task_started":
                    started = item.get("timestamp")
                elif payload.get("type") == "task_complete":
                    completed = item.get("timestamp")
            if item["type"] != "token_usage_record":
                continue
            usage = payload["usage"]
            if not all(isinstance(usage.get(k), int) and usage[k] >= 0 for k in FIELDS):
                raise ValueError("用量字段不完整，不能把缺失值记成零。")
            if usage["input_tokens"] + usage["output_tokens"] != usage["total_tokens"]:
                raise ValueError("输入加输出与总量不一致。")
            if usage["cached_input_tokens"] + usage["cache_write_input_tokens"] > usage["input_tokens"]:
                raise ValueError("缓存输入超出总输入。")
            if usage["reasoning_output_tokens"] > usage["output_tokens"]:
                raise ValueError("推理 token 应是输出的子集。")
            key = payload["response_id"]
            if key in records and records[key] != usage:
                raise ValueError("同一响应出现相互冲突的用量。")
            records[key] = usage
            last_cumulative = payload.get("turn_token_usage")
    if not records:
        raise ValueError("没有找到该轮任务的逐响应 token 用量；不能推算为零。")
    totals = {k: sum(r[k] for r in records.values()) for k in FIELDS}
    if last_cumulative is not None and totals != last_cumulative:
        raise ValueError("逐响应求和与任务累计量不符，可能日志不完整。")
    seconds = (datetime.fromisoformat(completed) - datetime.fromisoformat(started)).total_seconds() if completed and started else None
    return {"schema_version": 1, "scope": "selected Codex task turn, including tool orchestration and implementation work",
            "turn_id": turn_id, "status": "complete" if completed else "partial",
            "started_at": started, "completed_at": completed, "wall_seconds": seconds,
            "response_count": len(records), "usage": totals,
            "ordinary_input_tokens": totals["input_tokens"] - totals["cached_input_tokens"] - totals["cache_write_input_tokens"],
            "noncached_input_tokens": totals["input_tokens"] - totals["cached_input_tokens"],
            "notes": ["缓存输入是输入的子集，推理输出是输出的子集，不额外相加。",
                      "这是多次调用累计量，不是材料本身的 token 数，也不等于一次上下文窗口大小。",
                      "不能用一个研发任务的用量推出每条视频的固定成本或账户扣费。",
                      "本地 Whisper、FFmpeg 和下载本身不调用文字模型；调度这些工具的对话会产生模型用量。"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_log", type=Path)
    parser.add_argument("--turn-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.session_log, args.turn_id)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
