import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qdrant_upload import BM25SparseEncoder, get_sparse_encoder, extract_text, make_payload, parse_text_to_articles


class TestBM25SparseEncoder(unittest.TestCase):

    def setUp(self):
        self.encoder = BM25SparseEncoder()

    def test_tokenization_arabic(self):
        text = "المادةُ الأُولَى: تُعَدُّ الْمُعَامَلَاتُ الْمَدَنِيَّةُ أساساً للالتزامات."
        tokens = self.encoder.tokenize(text)
        self.assertIn("المادة", tokens)
        self.assertIn("المعاملات", tokens)
        self.assertIn("المدنية", tokens)

    def test_encode_text_structure(self):
        text = "نظام المعاملات المدنية في المملكة العربية السعودية"
        encoded = self.encoder.encode_text(text)
        self.assertIn("indices", encoded)
        self.assertIn("values", encoded)
        self.assertEqual(len(encoded["indices"]), len(encoded["values"]))
        self.assertTrue(len(encoded["indices"]) > 0)
        
        # Verify indices are positive 32-bit integers
        for idx in encoded["indices"]:
            self.assertIsInstance(idx, int)
            self.assertGreaterEqual(idx, 0)
            self.assertLessEqual(idx, 2147483647)

        # Verify sorted indices
        self.assertEqual(encoded["indices"], sorted(encoded["indices"]))

    def test_encode_batch(self):
        texts = [
            "المادة الأولى ينفذ هذا النظام بعد تسعين يوما من تاريخ نشره",
            "المادة الثانية تحسب المدد المذكورة في هذا النظام بالتقويم الهجري"
        ]
        batch = self.encoder.encode_batch(texts)
        self.assertEqual(len(batch), 2)
        self.assertTrue(len(batch[0]["indices"]) > 0)
        self.assertTrue(len(batch[1]["indices"]) > 0)

    def test_factory_native(self):
        enc = get_sparse_encoder("native")
        self.assertIsInstance(enc, BM25SparseEncoder)

    def test_extract_text(self):
        self.assertEqual(extract_text({"content": "محتوى التجربة"}), "محتوى التجربة")
        self.assertEqual(extract_text({"نص المادة": "نص المادة"}), "نص المادة")
        self.assertEqual(extract_text("نص مباشر"), "نص مباشر")

    def test_make_payload_handles_strings_and_dicts(self):
        p1 = make_payload("نص تجريبي مفرد", pid=1)
        self.assertEqual(p1["content"], "نص تجريبي مفرد")
        self.assertEqual(p1["metadata"]["رقم المادة رقما"], 1)

        p2 = make_payload({"content": "محتوى كتاب", "id": 42, "part": "1", "page": "100"}, source_type='csv')
        self.assertEqual(p2["content"], "محتوى كتاب")
        self.assertEqual(p2["metadata"]["رقم المادة رقما"], 42)
        self.assertEqual(p2["metadata"]["رقم الجزء"], "1")

    def test_parse_text_fallback(self):
        plain_text = "الفقرة الأولى من الكتاب بدون كلمة مادة.\n\nالفقرة الثانية من الكتاب تفصيلية."
        articles = parse_text_to_articles(plain_text, "كتاب فقهي")
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]["رقم المادة كتابة"], "فقرة 1")


if __name__ == '__main__':
    unittest.main()

