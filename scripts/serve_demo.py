"""Loopback-only local demonstration server. No production authentication."""
import argparse
from contextlib import closing
from datetime import date, datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import sys
import re
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DB = ROOT / "outputs/uganda/feedback.sqlite"


def imagery_asset(query):
    dataset=query.get("dataset",[""])[0]
    scene=query.get("scene",[""])[0]
    asset=query.get("asset",[""])[0]
    if not re.fullmatch(r"[0-9a-f]{20}",dataset) or not re.fullmatch(r"S2[ABC]_MSIL2A_[A-Za-z0-9_]+",scene) or asset not in ("reflectance","ndvi","quality"):
        raise ValueError("Invalid imagery asset identifier")
    dataset_root=(ROOT/"outputs/ml/datasets").resolve()
    directory=(dataset_root/dataset).resolve()
    if not directory.is_relative_to(dataset_root):
        raise ValueError("Dataset escapes the artifact directory")
    manifest=json.loads((directory/"manifest.json").read_text(encoding="utf-8"))
    if manifest["dataset_id"]!=dataset or scene not in manifest["scene_ids"]:
        raise ValueError("Unknown dataset or scene")
    path=(directory/"assets"/(scene+"-"+asset+".tif")).resolve()
    if not path.is_relative_to(directory/"assets") or not path.is_file():
        raise ValueError("Unknown imagery asset")
    return path


def store_feedback(body, db=DB):
    if not isinstance(body, dict):
        raise ValueError("Feedback must be a JSON object")
    if body.get("profile") not in ("uganda", "texas") or body.get("demo") is not True:
        raise ValueError("Only labeled demonstration feedback is accepted")
    brief = json.loads((WEB/"data"/(body["profile"]+".json")).read_text(encoding="utf-8"))
    expected = brief.get("brief_id") or "texas-synthetic-"+brief["as_of"]
    ids = {u.get("id") or u.get("zone_id") for u in brief.get("units", brief.get("zones", []))}
    if body.get("brief_id") != expected or body.get("unit_id") not in ids:
        raise ValueError("Brief or monitoring unit mismatch; reload the evidence")
    if body.get("kind") not in ("expert_review", "field_feedback") or body.get("outcome") not in ("uncertain", "confirmed_observation", "misleading_flag", "no_unusual_finding"):
        raise ValueError("Unsupported feedback type or outcome")
    observed = date.fromisoformat(body["observed_at"])
    if observed > datetime.now(timezone.utc).date():
        raise ValueError("Feedback date cannot be in the future")
    for key, limit in (("finding", 1500), ("next_step", 500)):
        if not isinstance(body.get(key), str) or not body[key].strip() or len(body[key]) > limit:
            raise ValueError("Finding and follow-up are required within length limits")
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE IF NOT EXISTS area_feedback (id INTEGER PRIMARY KEY, brief_id TEXT, payload TEXT, brief_snapshot TEXT, received_at TEXT)")
        cur = conn.execute("INSERT INTO area_feedback (brief_id,payload,brief_snapshot,received_at) VALUES (?,?,?,?)", (expected,json.dumps(body),json.dumps(brief),datetime.now(timezone.utc).isoformat()))
        return cur.lastrowid


def feedback_records(brief_id, db=DB):
    if not Path(db).exists():
        return []
    with closing(sqlite3.connect(db)) as conn:
        return [dict(json.loads(payload), id=record_id, received_at=stamp) for record_id,payload,stamp in conn.execute("SELECT id,payload,received_at FROM area_feedback WHERE brief_id=? ORDER BY id", (brief_id,))]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def valid_host(self):
        return self.headers.get("Host") in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}")

    def send_json(self, status, data):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if not self.valid_host():
            return self.send_json(403, dict(error="Loopback host required"))
        parsed = urlparse(self.path)
        if parsed.path=="/api/imagery-asset":
            return self.send_imagery(parse_qs(parsed.query))
        if parsed.path == "/api/feedback":
            brief_id = parse_qs(parsed.query).get("brief_id", [""])[0]
            if len(brief_id) > 100:
                return self.send_json(400, dict(error="Invalid brief ID"))
            return self.send_json(200, feedback_records(brief_id))
        return super().do_GET()

    def do_HEAD(self):
        parsed=urlparse(self.path)
        if not self.valid_host():
            return self.send_json(403,dict(error="Loopback host required"))
        if parsed.path=="/api/imagery-asset":
            return self.send_imagery(parse_qs(parsed.query),head=True)
        return super().do_HEAD()

    def send_imagery(self,query,head=False):
        try:
            path=imagery_asset(query)
            size=path.stat().st_size
            start,end=0,size-1
            range_header=self.headers.get("Range")
            if range_header:
                match=re.fullmatch(r"bytes=(\d*)-(\d*)",range_header)
                if not match or not any(match.groups()):
                    raise ValueError("Unsupported byte range")
                a,b=match.groups()
                if not a:
                    start=max(0,size-int(b))
                else:
                    start=int(a)
                    end=min(size-1,int(b)) if b else size-1
                if start>=size or start>end:
                    self.send_response(416)
                    self.send_header("Content-Range",f"bytes */{size}")
                    self.send_header("Content-Length","0")
                    self.end_headers()
                    return
            self.send_response(206 if range_header else 200)
            self.send_header("Content-Type","image/tiff")
            self.send_header("Content-Disposition",f'attachment; filename="{path.name}"')
            self.send_header("Accept-Ranges","bytes")
            self.send_header("Content-Length",str(end-start+1))
            self.send_header("X-Content-Type-Options","nosniff")
            if range_header:self.send_header("Content-Range",f"bytes {start}-{end}/{size}")
            self.end_headers()
            if not head:
                with path.open("rb") as stream:
                    stream.seek(start)
                    remaining=end-start+1
                    while remaining:
                        block=stream.read(min(65536,remaining))
                        if not block:break
                        self.wfile.write(block);remaining-=len(block)
        except (ValueError,KeyError,OSError):
            return self.send_json(404,dict(error="Requested imagery asset is unavailable"))

    def do_POST(self):
        origin = self.headers.get("Origin")
        allowed = (f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}")
        if not self.valid_host() or (origin and origin not in allowed):
            return self.send_json(403, dict(error="Same-origin local request required"))
        if self.path != "/api/feedback":
            return self.send_json(404, dict(error="Unknown endpoint"))
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 12000 or self.headers.get("Content-Type") != "application/json":
                raise ValueError("Bounded JSON body required")
            body = json.loads(self.rfile.read(length))
            record_id = store_feedback(body)
            return self.send_json(201, dict(id=record_id))
        except (ValueError, TypeError, KeyError) as exc:
            return self.send_json(400, dict(error=str(exc)))
        except (OSError, sqlite3.Error):
            return self.send_json(503, dict(error="Local feedback storage unavailable; retry later"))

    def list_directory(self, path):
        return self.send_error(403, "Directory listing disabled")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Vantage local preview: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
