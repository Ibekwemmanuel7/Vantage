"""Audit the pinned One Acre Fund public survey; output aggregates privately."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vantage.survey_audit import SOURCE_SHA256, audit
from scripts.validate_field_evidence import private_output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        output = private_output(args.out)
        if args.input.stat().st_size > 10_000_000: raise ValueError('Input exceeds budget')
        raw = args.input.read_bytes()
        if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256: raise ValueError('Pinned survey hash mismatch')
        result = audit(raw)
        result['source_url'] = 'https://zenodo.org/records/11122388'
        result['implementation_sha256'] = hashlib.sha256((ROOT/'vantage/survey_audit.py').read_bytes()).hexdigest()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
        print(json.dumps(result['counts'], sort_keys=True))
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Survey audit failed: {exc}\n')


if __name__ == '__main__': main()
