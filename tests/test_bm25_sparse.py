import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qdrant_upload import BM25SparseEncoder, get_sparse_encoder


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


if __name__ == '__main__':
    unittest.main()
