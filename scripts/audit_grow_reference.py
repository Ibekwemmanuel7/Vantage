"""Audit pinned GROW-Africa workbooks read-only; write private aggregate JSON."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vantage.grow_reference import audit_archive
from scripts.validate_field_evidence import private_output


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();out=private_output(args.out)
    if out.exists():raise ValueError('Report already exists; choose a new path')
    config=ROOT/'configs/grow_africa_reference.json';plan=json.loads(config.read_text())
    readme=args.archive.parent/'readme.txt'
    if readme.stat().st_size>20_000 or hashlib.sha256(readme.read_bytes()).hexdigest()!=plan['readme_sha256']:
        raise ValueError('Pinned adjacent readme required')
    implementations={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('vantage/grow_reference.py','scripts/audit_grow_reference.py')}
    report=audit_archive(args.archive,plan['archive_sha256'])
    if report['total_source_rows']!=plan['expected_total_rows']:raise ValueError('Source row count differs')
    if implementations!={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in implementations}:
        raise ValueError('Implementation changed during audit; rerun in a new output path')
    report.update(source=plan,implementation_sha256=implementations)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    print('Source rows:',report['total_source_rows'],'Uganda rows:',report['uganda_rows'])


if __name__=='__main__':main()
