"""Offline review gates for a manually researched public-source evidence registry."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vantage.public_evidence import assess_registry
from vantage.imagery import atomic_json,sha256_file


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry",type=Path,default=ROOT/"examples/uganda-public-evidence.json")
    p.add_argument("--out",type=Path,default=ROOT/"docs/africa/PUBLIC_EVIDENCE_REVIEW.json")
    args=p.parse_args()
    registry=json.loads(args.registry.read_text())
    report=assess_registry(registry["records"])
    report["registry_sha256"]=sha256_file(args.registry)
    atomic_json(args.out,report)
    print(f"Reviewed {report['records']} references; {report['admissible_supervised_references']} admissible supervised references")
