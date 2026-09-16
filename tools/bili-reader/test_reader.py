import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import reader
import usage_audit
import render_brief


class EvidenceTests(unittest.TestCase):
    def test_detailed_report_renders_evidence_unit_not_only_chapter_summary(self):
        evidence = {"evidence_sha256": "abc", "metadata": {"title": "测试讲义", "source_url": "https://www.bilibili.com/video/BV1xx411c7mD/?p=1"},
                    "media": {"duration": 10}, "transcript": {"segments": [{"id": "s1", "start": 0, "end": 10}]}, "frames": []}
        review = {"schema_version": 2, "evidence_sha256": "abc", "cards": [{"id": "c1", "label": "uncertain", "title": "约束", "summary": "短摘要", "segment_ids": ["s1"]}],
                  "questions": ["为什么？"], "content_units": [{"id": "u1", "kind": "condition", "title": "必须保留的条件", "text": "声调是否计入同音，需要明确。<不是 HTML>",
                  "segment_ids": ["s1"], "card_id": "c1", "treatment": "retained", "critical": True}]}
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d); reader.save(folder / "evidence.json", evidence); reader.save(folder / "review.json", review)
            render_brief.render_brief(folder)
            html = (folder / "reading-report.html").read_text()
            md = (folder / "reading-guide.md").read_text()
            self.assertIn('id="u1"', html)
            self.assertIn('声调是否计入同音，需要明确。&lt;不是 HTML&gt;', html)
            self.assertIn('声调是否计入同音，需要明确。', md)
            self.assertIn('逐项内容记录', html)

    def test_content_units_reject_missing_critical_evidence_and_hidden_omission(self):
        evidence = {"evidence_sha256": "abc", "transcript": {"segments": [{"id": "s1"}, {"id": "s2"}]}, "frames": []}
        review = {"schema_version": 2, "evidence_sha256": "abc", "cards": [
            {"id": "c1", "label": "uncertain", "summary": "论点", "segment_ids": ["s1"]},
            {"id": "c2", "label": "uncertain", "summary": "例子", "segment_ids": ["s2"]}],
            "questions": ["这个例子限定了什么？"], "content_units": [
                {"id": "u1", "kind": "condition", "title": "成立条件", "text": "只在条件成立时适用。",
                 "segment_ids": ["s2"], "card_id": "c2", "treatment": "retained", "critical": True}]}
        reader.validate_review(review, evidence)
        for mutation in (lambda r: r.update(content_units=[]),
                         lambda r: r["content_units"][0].update(card_id="c1"),
                         lambda r: r["content_units"][0].update(segment_ids=["fake"]),
                         lambda r: r["content_units"][0].update(treatment="omitted", card_id=None, omission_reason="缩短")):
            invalid = copy.deepcopy(review); mutation(invalid)
            with self.assertRaises(ValueError): reader.validate_review(invalid, evidence)
        omitted = copy.deepcopy(review)
        omitted["content_units"][0].update(critical=False, treatment="omitted", card_id=None)
        with self.assertRaises(ValueError): reader.validate_review(omitted, evidence)
        omitted["content_units"][0]["omission_reason"] = "只省略重复问候，留存源时间。"
        reader.validate_review(omitted, evidence)

    def test_usage_counts_each_response_once_and_does_not_add_subsets(self):
        usage = {"input_tokens": 100, "cached_input_tokens": 80, "cache_write_input_tokens": 0,
                 "output_tokens": 10, "reasoning_output_tokens": 6, "total_tokens": 110}
        row = {"type": "token_usage_record", "payload": {"turn_id": "t", "response_id": "r", "usage": usage, "turn_token_usage": usage}}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "log.jsonl"
            path.write_text(json.dumps(row) + '\n' + json.dumps(row) + '\n')
            result = usage_audit.audit(path, "t")
            self.assertEqual(result["usage"]["total_tokens"], 110)
            self.assertEqual(result["noncached_input_tokens"], 20)
            self.assertEqual(result["response_count"], 1)
            self.assertEqual(result["status"], "partial")
            with self.assertRaises(ValueError): usage_audit.audit(path, "missing")
            bad = copy.deepcopy(row); bad["payload"]["turn_token_usage"] = dict(usage, total_tokens=999)
            path.write_text(json.dumps(bad) + '\n')
            with self.assertRaises(ValueError): usage_audit.audit(path, "t")

    def test_bv_and_parts_never_expand_to_playlist(self):
        self.assertEqual(reader.canonical("https://www.bilibili.com/video/BV1xx411c7mD/?p=3&t=25")[1:],
                         (3, "https://www.bilibili.com/video/BV1xx411c7mD/?p=3"))
        for value in ("https://evil.example/BV1xx411c7mD", "https://bilibili.com.evil/video/BV1xx411c7mD", "BV1xx411c7mD; touch /tmp/x"):
            with self.assertRaises(ValueError):
                reader.canonical(value)

    def test_subtitle_formats_and_invalid_timing(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.srt"
            path.write_text("1\n00:00:01,200 --> 00:00:03,400\n你好\n世界\n\n2\n00:00:04,000 --> 00:00:05,000\n<b>保留文字</b>\n")
            result = reader.subtitles(path)
            self.assertEqual(result[0]["text"], "你好\n世界")
            self.assertEqual(result[1]["text"], "保留文字")
            path = Path(d) / "test.vtt"
            path.write_text("WEBVTT\n\n00:01.200 --> 00:03.400 align:start\n测试 &amp; 保留\n")
            self.assertEqual(reader.subtitles(path)[0]["text"], "测试 & 保留")
            path = Path(d) / "test.json"
            path.write_text(json.dumps({"body": [{"from": 1, "to": 2, "content": "测试"}]}))
            self.assertEqual(reader.subtitles(path)[0]["id"], "s00001")
        for rows in ([], [{"start": 4, "end": 2, "text": "错位"}], [{"start": 0, "end": float("nan"), "text": "坏数据"}]):
            with self.assertRaises(ValueError):
                reader.normalize(rows)

    def test_coverage_is_union_and_retains_long_gaps(self):
        rows = reader.normalize([{"start": 0, "end": 5, "text": "a"}, {"start": 3, "end": 8, "text": "b"}, {"start": 20, "end": 22, "text": "c"}])
        result = reader.gaps(rows, 40)
        self.assertEqual(result["timed_text_seconds"], 10)
        self.assertEqual(result["gaps_over_10s"], [{"start": 8, "end": 20}, {"start": 22, "end": 40}])

    def test_review_rejects_omissions_fake_memory_and_wrong_snapshot(self):
        evidence = {"evidence_sha256": "abc", "transcript": {"segments": [{"id": "s00001"}, {"id": "s00002"}]}, "frames": []}
        review = {"evidence_sha256": "abc", "cards": [{"id": "a", "label": "new", "summary": "新增内容", "segment_ids": ["s00001", "s00002"]}], "questions": ["如何验证？"]}
        reader.validate_review(review, evidence)
        for mutate in (lambda r: r.update(evidence_sha256="wrong"),
                       lambda r: r["cards"][0].update(segment_ids=["s00001"]),
                       lambda r: r["cards"][0].update(label="known"),
                       lambda r: r["cards"][0].update(frame_ids=["f99999"])):
            invalid = copy.deepcopy(review)
            mutate(invalid)
            with self.assertRaises(ValueError):
                reader.validate_review(invalid, evidence)
        with tempfile.TemporaryDirectory() as d:
            note = Path(d) / "memory.md"
            note.write_text("# 旧笔记\n真实的旧判断\n")
            review["cards"][0].update(label="known", memory_refs=[{"path": str(note), "start_line": 2, "end_line": 2, "quote": "真实的旧判断"}])
            reader.validate_review(review, evidence)
            note.write_text("# 旧笔记\n改过的内容\n")
            with self.assertRaises(ValueError):
                reader.validate_review(review, evidence)

    @unittest.skipUnless(shutil.which("ffmpeg"), "requires ffmpeg")
    def test_real_ffmpeg_scene_detection_and_periodic_capture(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            video = folder / "fixture.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:s=320x180:r=10:d=3",
                            "-f", "lavfi", "-i", "color=white:s=320x180:r=10:d=3",
                            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-c:v", "libx264", str(video)], check=True)
            result = reader.frames(video, folder, 0.18, 0.5, 2)
            self.assertTrue(any(abs(f["time"] - 3) < 0.11 and f["reason"] == "scene-change" for f in result), result)
            self.assertTrue(any(f["reason"] == "periodic" for f in result), result)
            self.assertEqual(len(result), len(list((folder / "frames").glob("*.jpg"))))


if __name__ == "__main__":
    unittest.main()
