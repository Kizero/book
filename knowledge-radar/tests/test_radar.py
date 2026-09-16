import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import radar


class RadarTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "inbox").mkdir()
        (self.root / "records").mkdir()
        raw = self.root / "inbox" / "sample.md"
        raw.write_text("# Sample\n\nA useful claim with evidence.\n", encoding="utf-8")
        digest = hashlib.sha256(raw.read_bytes()).hexdigest()
        self.record_path = self.root / "records" / "sample.json"
        self.record = {
            "schema_version": 1,
            "id": "2026-09-04-sample",
            "captured_at": "2026-09-04T08:00:00+08:00",
            "artifact": {
                "title": "Sample",
                "kind": "article",
                "author": "Tester",
                "raw_path": "inbox/sample.md",
                "source_url": "https://example.com/sample",
                "sha256": digest,
            },
            "entities": [
                {
                    "id": "work:sample",
                    "name": "Sample Work",
                    "type": "book",
                    "aliases": [],
                    "status": "candidate",
                    "priority": 5,
                    "locator": "L3",
                    "context": "new work",
                    "confidence": "verified",
                }
            ],
            "claims": [
                {
                    "id": "claim:sample",
                    "text": "The claim is useful.",
                    "kind": "source_claim",
                    "locator": "L3",
                    "evidence": "useful claim",
                    "confidence": "verified",
                    "priority": 5,
                }
            ],
            "methods": [],
            "context_cards": [],
            "resources": [],
            "relations": [],
            "questions": [],
            "actions": [],
        }
        self.write_record()

    def tearDown(self):
        self.temporary.cleanup()

    def write_record(self):
        self.record_path.write_text(
            json.dumps(self.record, ensure_ascii=False), encoding="utf-8"
        )

    def test_valid_record_builds_index_and_report(self):
        self.assertEqual([], radar.validate_all(self.root))
        index = radar.build_index(self.root)
        self.assertEqual(1, index["stats"]["candidate_entities"])
        report = radar.render_report(self.root, "2026-09-04")
        self.assertIn("Sample Work", report)
        self.assertIn("今天先看什么", report)

    def test_report_only_shows_methods_scoped_to_featured_work(self):
        self.record["entities"][0]["featured"] = True
        self.record["context_cards"] = [
            {
                "id": "context:sample",
                "about_entity": "work:sample",
                "title": "Why it was written",
                "summary": "Useful context.",
                "kind": "origin",
                "locator": "L3",
                "evidence": "useful claim",
                "confidence": "verified",
                "priority": 5,
            }
        ]
        self.record["methods"] = [
            {
                "id": "method:sample",
                "about_entity": "work:sample",
                "title": "Method from the work",
                "summary": "A scoped method.",
                "locator": "L3",
                "evidence": "useful claim",
                "confidence": "verified",
                "priority": 5,
                "acceptance": [],
            },
            {
                "id": "method:unrelated",
                "about_entity": "work:other",
                "title": "Unrelated method",
                "summary": "Should stay hidden.",
                "locator": "L3",
                "evidence": "useful claim",
                "confidence": "verified",
                "priority": 5,
                "acceptance": [],
            },
        ]
        self.write_record()
        report = radar.render_report(self.root, "2026-09-04")
        self.assertIn("Why it was written", report)
        self.assertIn("Method from the work", report)
        self.assertNotIn("Unrelated method", report)

    def test_evidence_must_exist_at_locator(self):
        self.record["claims"][0]["evidence"] = "not in the source"
        self.write_record()
        errors = radar.validate_all(self.root)
        self.assertTrue(any("evidence is not present" in error for error in errors))

    def test_feedback_removes_known_entity_from_new_discoveries(self):
        radar.add_feedback(self.root, "work:sample", "known", "already knew it")
        index = radar.build_index(self.root)
        self.assertEqual(0, index["stats"]["candidate_entities"])
        report = radar.render_report(self.root, "2026-09-04")
        self.assertNotIn("**Sample Work**", report)

    def test_hash_change_is_detected(self):
        raw = self.root / "inbox" / "sample.md"
        raw.write_text("changed\n", encoding="utf-8")
        errors = radar.validate_all(self.root)
        self.assertTrue(any("hash mismatch" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
