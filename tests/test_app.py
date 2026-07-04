import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mcp_server


class AppStartupTests(unittest.TestCase):
    def test_health_endpoint(self):
        client = TestClient(mcp_server.app)
        response = client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_root_page_serves(self):
        client = TestClient(mcp_server.app)
        response = client.get('/')
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
