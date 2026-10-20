import importlib.util
import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("imagery_http_server",ROOT/"scripts/serve_demo.py")
server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)


class ImageryHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            c=json.loads((ROOT/"web/data/imagery.json").read_text())
            p=server.imagery_asset(dict(dataset=[c["dataset_id"]],scene=[c["scenes"][0]["id"]],asset=["ndvi"]))
        except (OSError,ValueError):
            raise unittest.SkipTest("Generate local imagery artifacts for HTTP integration tests")
        class Quiet(server.Handler):
            def log_message(self,*args):pass
        cls.server=server.ThreadingHTTPServer(("127.0.0.1",0),Quiet)
        cls.thread=threading.Thread(target=lambda:cls.server.serve_forever(poll_interval=.01),daemon=True)
        cls.thread.start()
        cls.url=f"http://127.0.0.1:{cls.server.server_port}"
        cls.query=urlencode(dict(dataset=c["dataset_id"],scene=c["scenes"][0]["id"],asset="ndvi"))
        cls.path=p

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=3)

    def test_cog_byte_range_matches_original_and_head(self):
        with urlopen(Request(self.url+"/api/imagery-asset?"+self.query,headers={"Range":"bytes=0-99"})) as response:
            self.assertEqual(response.status,206)
            self.assertEqual(response.headers["Accept-Ranges"],"bytes")
            self.assertEqual(response.read(),self.path.read_bytes()[:100])
        with urlopen(Request(self.url+"/api/imagery-asset?"+self.query,method="HEAD")) as response:
            self.assertEqual(response.status,200)
            self.assertEqual(int(response.headers["Content-Length"]),self.path.stat().st_size)
            self.assertEqual(response.read(),b"")

    def test_unknown_assets_and_out_of_range_do_not_expose_files(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.url+"/api/imagery-asset?"+urlencode(dict(dataset="../",scene="x",asset="../../.env")))
        self.assertEqual(error.exception.code,404)
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(self.url+"/api/imagery-asset?"+self.query,headers={"Range":"bytes=999999999-"}))
        self.assertEqual(error.exception.code,416)

    def test_cross_origin_feedback_is_denied(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(self.url+"/api/feedback",data=b"{}",headers={"Origin":"https://unrelated.example","Content-Type":"application/json"}))
        self.assertEqual(error.exception.code,403)


if __name__=="__main__":unittest.main()
