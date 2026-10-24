from io import BytesIO
import tarfile
import unittest
from vantage.cdse_exports import export_files,access_token,process_export,ExportError


def archive(entries):
    stream=BytesIO()
    with tarfile.open(fileobj=stream,mode="w") as tar:
        for name,raw in entries:
            info=tarfile.TarInfo(name)
            info.size=len(raw)
            tar.addfile(info,BytesIO(raw))
    return stream.getvalue()


class Response:
    status_code=200
    headers={"Content-Type":"application/tar"}
    def json(self):return dict(access_token="test-secret",token_type="Bearer")
    def iter_content(self,size):yield archive([("default.tif",b"fixture"),("userdata.json",b"{}")])
    def close(self):pass


class Session:
    def __init__(self,response):self.response=response;self.calls=[]
    def post(self,*args,**kwargs):self.calls.append((args,kwargs));return self.response


class CDSEExportTests(unittest.TestCase):
    def test_only_fixed_outputs_not_paths_or_duplicates(self):
        self.assertEqual(set(export_files(archive([("default.tif",b"fixture"),("userdata.json",b"{}")]))),{"default.tif","userdata.json"})
        for entries in [[("../secret",b"x")],[("default.tif",b"a"),("default.tif",b"b")],[("default.tif",b"a")]]:
            with self.assertRaises(ExportError):export_files(archive(entries))

    def test_auth_no_redirects_and_secret_not_in_errors(self):
        session=Session(Response())
        self.assertEqual(access_token(session,"client","secret"),"test-secret")
        self.assertFalse(session.calls[0][1]["allow_redirects"])
        session.response.status_code=401
        with self.assertRaises(ExportError) as error:access_token(session,"client","secret")
        self.assertNotIn("secret",str(error.exception))

    def test_process_bounded_contract_and_no_post_retry(self):
        session=Session(Response())
        self.assertIn("default.tif",process_export(session,"test-secret",{}))
        self.assertFalse(session.calls[0][1]["allow_redirects"])
        session.response.status_code=429
        session.calls=[]
        with self.assertRaises(ExportError):process_export(session,"test-secret",{})
        self.assertEqual(len(session.calls),1)
