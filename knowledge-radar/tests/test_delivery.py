import importlib.util
import json
import hashlib
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("delivery", Path(__file__).resolve().parents[1] / "check_delivery.py")
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "state/deliveries").mkdir(parents=True)
        self.books_dir = self.root / "books"
        self.books_dir.mkdir()
        self.books = [{"id": "test-book", "title": "中文", "fileName": "test.md"}]
        self.data = {"date": "2026-09-08", "status": "ready", "entity_id": "work:test",
                     "book_id": "test-book", "book_title": "中文",
                     "readback": ["beginning", "middle", "end"]}
        contents = {"report": "# 2026-09-08", "record": json.dumps({"entities": [
            {"id": "work:test", "featured": True}]}), "chinese": "中文正文", "import_record": "回读记录"}
        for name, text in contents.items():
            path = self.root / (name + ".txt")
            path.write_text(text)
            self.data[name] = {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        (self.books_dir / "test.md").write_text("中文正文")
        self.save()

    def save(self):
        (self.root / "state/deliveries/2026-09-08.json").write_text(json.dumps(self.data))

    def run_gate(self):
        return delivery.check(self.root, "2026-09-08", self.books, self.books_dir)

    def test_ready(self):
        self.assertTrue(self.run_gate().startswith("READY"))

    def test_missing_report(self):
        (self.root / "report.txt").unlink()
        with self.assertRaises(FileNotFoundError):
            self.run_gate()

    def test_book_not_imported(self):
        self.books = []
        with self.assertRaisesRegex(ValueError, "实际书库"):
            self.run_gate()

    def test_copy_changed(self):
        (self.books_dir / "test.md").write_text("不完整")
        with self.assertRaisesRegex(ValueError, "副本"):
            self.run_gate()

    def test_blocked_is_not_ready(self):
        self.data.update(status="blocked", blocker="用户正在编辑笔记")
        self.save()
        with self.assertRaisesRegex(ValueError, "尚未完整交付"):
            self.run_gate()

    def test_missing_readback(self):
        self.data["readback"] = []
        self.save()
        with self.assertRaisesRegex(ValueError, "回读"):
            self.run_gate()

    def test_wrong_date(self):
        self.data["date"] = "2026-09-07"
        self.save()
        with self.assertRaisesRegex(ValueError, "日期"):
            self.run_gate()

