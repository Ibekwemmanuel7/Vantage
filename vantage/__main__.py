import argparse
import html
import json
from pathlib import Path
import sqlite3
from contextlib import closing

from .core import brief, instant


def render(result):
    rows = result["zones"]
    coords = [p for r in rows for p in r["geometry"]["coordinates"][0]]
    if not coords:
        return "<h1>Vantage: no zones supplied</h1>"
    xmin, xmax = min(p[0] for p in coords), max(p[0] for p in coords)
    ymin, ymax = min(p[1] for p in coords), max(p[1] for p in coords)
    colors = {"inspect": "#d65c35", "no_relative_flag": "#7c9aaa"}
    polygons, details = [], []
    for r in rows:
        points = " ".join(f"{20+760*(x-xmin)/(xmax-xmin):.2f},{380-360*(y-ymin)/(ymax-ymin):.2f}" for x, y in r["geometry"]["coordinates"][0])
        label = html.escape(f'{r["field_id"]}/{r["zone_id"]}: {r["status"]}')
        polygons.append(f'<polygon points="{points}" fill="{colors.get(r["status"], "#bbb")}" stroke="white"><title>{label}</title></polygon>')
        evidence = {k: v for k, v in r.items() if k != "geometry"}
        details.append(f'<details open><summary>{label}</summary><pre>{html.escape(json.dumps(evidence, indent=2))}</pre></details>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>Vantage scouting brief</title><style>body{font:16px system-ui;max-width:900px;margin:auto;padding:1rem}svg{width:100%;height:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:1rem 0}</style>'
            f'<h1>Vantage scouting brief</h1><p>As of {html.escape(result["as_of"])}</p><p>{html.escape(result["limitations"])}</p>'
            '<p>Orange: inspect first. Blue: no relative flag. Grey: evidence unavailable or excluded. Schematic WGS84 zone map, not for navigation.</p>'
            '<svg viewBox="0 0 800 400" role="img" aria-label="Zone scouting evidence map">'+''.join(polygons)+'</svg>'+''.join(details)+
            '<p>Record a field check using <code>python -m vantage feedback</code>; see README for required fields.</p></html>')


def save_feedback(db, result, tenant, zone, visited_at, outcome, finding, action):
    if tenant != result["tenant_id"] or zone not in {r["zone_id"] for r in result["zones"]}:
        raise ValueError("tenant or zone mismatch")
    if instant(visited_at) < instant(result["as_of"]):
        raise ValueError("visit must follow brief")
    if outcome not in ("useful_finding", "no_finding", "uncertain") or not finding.strip() or not action.strip():
        raise ValueError("outcome, finding and action required")
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, tenant TEXT, zone TEXT, visited_at TEXT, outcome TEXT, finding TEXT, action TEXT, brief_json TEXT)")
        cursor = conn.execute("INSERT INTO feedback (tenant,zone,visited_at,outcome,finding,action,brief_json) VALUES (?,?,?,?,?,?,?)",
                              (tenant, zone, visited_at, outcome, finding, action, json.dumps(result)))
        return cursor.lastrowid


def main():
    p = argparse.ArgumentParser(description="Vantage offline scouting prototype")
    commands = p.add_subparsers(dest="command", required=True)
    b = commands.add_parser("brief")
    b.add_argument("input", type=Path)
    b.add_argument("--as-of", required=True)
    b.add_argument("--out", type=Path, required=True)
    f = commands.add_parser("feedback")
    f.add_argument("brief", type=Path)
    f.add_argument("--db", required=True)
    for name in ("tenant", "zone", "visited-at", "outcome", "finding", "action"):
        f.add_argument("--"+name, required=True)
    args = p.parse_args()
    try:
        if args.command == "brief":
            result = brief(json.loads(args.input.read_text(encoding="utf-8")), args.as_of)
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out/"brief.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            features = [dict(type="Feature", geometry=r["geometry"], properties={k:v for k,v in r.items() if k != "geometry"}) for r in result["zones"]]
            (args.out/"zones.geojson").write_text(json.dumps(dict(type="FeatureCollection", features=features)), encoding="utf-8")
            boundaries = [dict(type="Feature", geometry=f["geometry"], properties={k:v for k,v in f.items() if k != "geometry"}) for f in result["fields"]]
            (args.out/"fields.geojson").write_text(json.dumps(dict(type="FeatureCollection", features=boundaries)), encoding="utf-8")
            (args.out/"brief.html").write_text(render(result), encoding="utf-8")
            print(f"Wrote {len(features)} zone assessments to {args.out}")
        else:
            result = json.loads(args.brief.read_text(encoding="utf-8"))
            print("Feedback ID:", save_feedback(args.db, result, args.tenant, args.zone, args.visited_at, args.outcome, args.finding, args.action))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        p.error(str(exc))


if __name__ == "__main__":
    main()
