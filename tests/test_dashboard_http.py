import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts import serve_demo as server


class DashboardHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        (cls.root / "web/data").mkdir(parents=True)
        cls.path = cls.root / "outputs/africa/dashboard/kween-rgb.png"
        cls.path.parent.mkdir(parents=True)
        cls.raw = b"\x89PNG\r\n\x1a\nsynthetic-http-test"
        (cls.root / "web/data/scouting.json").write_text(
            json.dumps(
                dict(
                    snapshot_id="qa",
                    preview=dict(
                        assets=dict(
                            rgb=dict(sha256=hashlib.sha256(cls.raw).hexdigest())
                        )
                    ),
                )
            )
        )
        original = server.scouting_preview
        cls.preview_patch = patch.object(
            server, "scouting_preview", lambda query: original(query, cls.root)
        )
        cls.preview_patch.start()

        class Quiet(server.Handler):
            def log_message(self, *args):
                pass

        cls.http = server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
        cls.thread = threading.Thread(
            target=lambda: cls.http.serve_forever(poll_interval=0.01), daemon=True
        )
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.http.server_port}/api/scouting-preview?case=kween-2023&layer=rgb&snapshot=qa"

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join(timeout=3)
        cls.preview_patch.stop()
        cls.temporary.cleanup()

    def setUp(self):
        self.path.write_bytes(self.raw)

    def test_verified_preview_get_and_head(self):
        with urlopen(self.url) as response:
            self.assertEqual(response.read(), self.raw)
            self.assertEqual(response.headers["Content-Type"], "image/png")
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        with urlopen(Request(self.url, method="HEAD")) as response:
            self.assertEqual(int(response.headers["Content-Length"]), len(self.raw))
            self.assertEqual(response.read(), b"")

    def test_tampered_preview_is_unavailable_not_silently_substituted(self):
        self.path.write_bytes(b"different-bytes")
        with self.assertRaises(HTTPError) as error:
            urlopen(self.url)
        self.assertEqual(error.exception.code, 404)

    def test_unknown_layer_and_remote_host_rejected(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.url.replace("layer=rgb", "layer=../../private"))
        self.assertEqual(error.exception.code, 404)
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(self.url, headers={"Host": "outside.example"}))
        self.assertEqual(error.exception.code, 403)
