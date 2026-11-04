"""Export an allowlisted static demonstration; never copy private outputs wholesale."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ['index.html', 'dashboard.css', 'dashboard.js', 'platform.css', 'platform.js',
         'workspace-model.js', 'regional-context.js', 'reports.html', 'reports.css',
         'reports.js', 'report-model.js', 'report-images.js', 'field-review.html',
         'field-review.css', 'field-review.js', 'field-review-model.js',
         'data/scouting.json', 'data/regional-context.json']


def build(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ValueError('Destination must be empty; existing releases are never deleted.')
    snapshot = json.loads((ROOT / 'web/data/scouting.json').read_text(encoding='utf-8'))
    for name in FILES:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((ROOT / 'web' / name).read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
    for layer in ('rgb', 'change'):
        source = ROOT / 'outputs/africa/dashboard' / f'kween-{layer}.png'
        if hashlib.sha256(source.read_bytes()).hexdigest() != snapshot['preview']['assets'][layer]['sha256']:
            raise ValueError(f'{layer} imagery differs from the evidence snapshot')
        (destination / 'assets').mkdir(exist_ok=True)
        shutil.copyfile(source, destination / 'assets' / f'kween-{layer}.png')
    replacements = {
        'dashboard.js': ("'/api/scouting-preview?case=kween-2023&layer='+next+'&snapshot='+evidence.snapshot_id", "'assets/kween-'+next+'.png'"),
        'reports.js': ("'/api/scouting-preview?case=kween-2023&layer='+layer+'&snapshot='+encodeURIComponent(snapshot.snapshot_id)", "'assets/kween-'+layer+'.png'"),
    }
    for name, (old, new) in replacements.items():
        target = destination / name
        content = target.read_text(encoding='utf-8')
        if content.count(old) != 1:
            raise ValueError(f'Unexpected source in {name}; review before exporting')
        target.write_text(content.replace(old, new), encoding='utf-8', newline='\n')
    status = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Vantage · Demonstration status</title><link rel="stylesheet" href="field-review.css"><main><p>VANTAGE · AGRICULTURE</p><h1>Evidence before action.</h1><p>This hosted historical demonstration uses public research context from Kween, Uganda, with an evidence cutoff of 5 June 2023. Uganda is the first pilot geography.</p><p>Field boundaries and notes stay in this browser. There is no account, cloud synchronization, live monitoring or independent field validation. Do not enter confidential records on a shared device.</p><p>Imagery highlights differences for investigation. It does not diagnose disease, prescribe irrigation or predict production yields.</p><p>The Python research tools run separately; this static host does not expose their API.</p><p><a href="./">Open scouting workspace</a> · <a href="reports.html">Create an evidence brief</a> · <a href="https://github.com/Ibekwemmanuel7/Vantage">Research and implementation</a> · <a href="https://github.com/Ibekwemmanuel7/Lillie_US">Lillie US</a> · <a href="/">Lillie Earth</a></p><p>Forestry remains with Vepris.</p></main></html>'''
    (destination / 'research.html').write_text(status, encoding='utf-8', newline='\n')
    manifest = {'mode': 'historical_static_demo', 'snapshot_id': snapshot['snapshot_id'],
                'files': {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(destination.rglob('*')) if p.is_file()}}
    (destination / 'release.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8', newline='\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    print(json.dumps(build(parser.parse_args().destination), indent=2))
