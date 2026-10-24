"""Build a self-contained local review report from checked public research artifacts."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vantage.evidence_report import summarize,render


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths=dict(recent="outputs/africa/recent/a013b10c8db819241036/pixels/sequence-observations.json",
        samples="outputs/ml/radar-optical/af9b3069cdd50009e367dd96/manifest.json",
        comparison="outputs/africa/lira-comparison/0dbeacd5e45ecbf430b7/report.json",
        model="outputs/ml/cloud-gaps/41353b869729ec810781/protocol-comparison.json")
    inputs={k:json.loads((ROOT/v).read_text()) for k,v in paths.items()}
    for path,expected in inputs["samples"]["source_hashes"].items():
        if digest(ROOT/path)!=expected:raise ValueError("Sample source report differs; rebuild/review first")
    sample_root=(ROOT/paths["samples"]).parent
    for sample in inputs["samples"]["samples"]:
        if digest(sample_root/sample["artifact"])!=sample["artifact_sha256"]:raise ValueError("Research sample differs")
    recent_root=(ROOT/paths["recent"]).parent
    for row in inputs["recent"]["observations"]:
        if row["status"]!="processed" or digest(recent_root/row["metrics"]["artifact"])!=row["metrics"]["artifact_sha256"]:
            raise ValueError("Recent numerical artifact missing or changed")
    comparison=inputs["comparison"]
    for field,path in [("source_radar_report_sha256","outputs/africa/gap-radar-pixels/b9e3ac527f496525a5d7/report.json"),
                       ("source_viewing_report_sha256","outputs/africa/gap-viewing/82fd966dcc318d43362f/report.json"),
                       ("source_visibility_report_sha256","outputs/africa/gap-visibility/727b09efd2cac9dbfae2/report.json")]:
        if digest(ROOT/path)!=comparison[field]:raise ValueError("Comparison source differs")
    model_manifest=ROOT/"outputs/ml/cloud-gaps/41353b869729ec810781/manifest.json"
    if digest(model_manifest)!=inputs["model"]["manifest_sha256"]:raise ValueError("Model dataset manifest differs")
    report=summarize(**inputs)
    report["generated_at"]=datetime.now(timezone.utc).isoformat()
    report["sources"]=[dict(path=path,sha256=digest(ROOT/path)) for path in paths.values()]
    report["builder_sha256"]={p:digest(ROOT/p) for p in ["scripts/build_evidence_review.py","vantage/evidence_report.py","vantage/recent_pixels.py"]}
    output=ROOT/"outputs/evidence-review"
    output.mkdir(parents=True,exist_ok=True)
    html=render(report)
    (output/"evidence.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    (output/"report.html").write_text(html,encoding="utf-8")
    print(f"Local unreviewed evidence report: {output / 'report.html'}")


if __name__=="__main__":main()
