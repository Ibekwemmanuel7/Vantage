"""Train fixed retrospective yield benchmarks on the pinned public Uganda survey."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import importlib.metadata

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.validate_field_evidence import private_output
from vantage.yield_research import load_cohort,experiment


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();out=private_output(args.out)
    config=ROOT/'configs/uganda_yield_research.json';plan=json.loads(config.read_text())
    if args.input.stat().st_size>10_000_000: raise ValueError('Input budget exceeded')
    raw=args.input.read_bytes();cohort=load_cohort(raw,plan)
    # Freeze the exact design before fitting; existing directories are never reused.
    out.mkdir(parents=True,exist_ok=False)
    (out/'frozen-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    report,predictions=experiment(cohort,plan)
    report.update(source_sha256=hashlib.sha256(raw).hexdigest(),plan_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
                  implementation_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('vantage/yield_research.py','scripts/benchmark_uganda_yield.py')},
                  environment=dict(python=platform.python_version(),**{k:importlib.metadata.version(k) for k in ('numpy','scikit-learn')}))
    (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    (out/'held-out-predictions.json').write_text(json.dumps(dict(source_rows=[r['source_row'] for r in cohort],observed_kg_ha=[r['y'] for r in cohort],predictions_kg_ha={k:v.tolist() for k,v in predictions.items()}),allow_nan=False)+'\n')
    print(json.dumps(dict(metrics=report['metrics'],baseline_beaten=report['baseline_beaten'],labels=report['label_audit']),indent=2))


if __name__=='__main__':main()
