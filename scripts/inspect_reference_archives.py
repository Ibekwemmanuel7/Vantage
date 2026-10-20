"""Inspect two pinned small public WorldCereal archives; never import training labels."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
import requests

ROOT=Path(__file__).resolve().parents[1]
FILES={
    "WorldCereal_ReferenceData_2023_Africa_Version_20251008.zip":"df4b29d2a5d92b15e68689625d82233e",
    "WorldCereal_ReferenceData_2024_Africa_Version_20251008.zip":"10ea523428f0c5ba92d506884c99982a",
}


def inspect_zip(raw,prefix="",depth=0):
    if depth>3:raise ValueError("Nested archive depth exceeds bounded inspection")
    records=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if sum(i.file_size for i in archive.infolist())>100_000_000:raise ValueError("Archive expands beyond inspection budget")
        for info in archive.infolist():
            if info.is_dir():continue
            name=prefix+info.filename
            entry=dict(name=name,uncompressed_bytes=info.file_size)
            if info.filename.lower().endswith('.xlsx'):
                with zipfile.ZipFile(io.BytesIO(archive.read(info))) as workbook:
                    if 'xl/sharedStrings.xml' in workbook.namelist():
                        xml=ET.fromstring(workbook.read('xl/sharedStrings.xml'))
                        strings=[''.join(n.itertext()) for n in xml]
                        entry['metadata_country_mentions']=[country for country in ('Uganda','Morocco') if any(country.lower() in s.lower() for s in strings)]
            records.append(entry)
            if info.filename.lower().endswith('.zip'):
                records.extend(inspect_zip(archive.read(info),name+'/',depth+1))
    return records


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--allow-downloads',action='store_true');args=p.parse_args()
    root=ROOT/'outputs/africa/public-references';root.mkdir(parents=True,exist_ok=True)
    results=[]
    for name,md5 in FILES.items():
        path=root/name;url='https://zenodo.org/records/17288873/files/'+name+'?download=1'
        if not path.exists():
            if not args.allow_downloads:raise FileNotFoundError('Pinned reference archive not cached')
            response=requests.get(url,timeout=60);response.raise_for_status()
            if len(response.content)>5_000_000:raise ValueError('Download exceeds inspection budget')
            if hashlib.md5(response.content).hexdigest()!=md5:raise ValueError('Publisher archive checksum mismatch')
            path.write_bytes(response.content)
        raw=path.read_bytes()
        if hashlib.md5(raw).hexdigest()!=md5:raise ValueError('Cached archive checksum mismatch')
        entries=inspect_zip(raw)
        results.append(dict(source_url=url,md5=md5,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),entries=entries,
            uganda_named_entries=[e['name'] for e in entries if 'uganda' in e['name'].lower()],
            content_status='Archive filenames inspected only; per-dataset geography, dates, provenance and licences require review',
            admitted_training_labels=0))
    report=dict(schema_version='public-reference-archive-inspection-1',archives=results,
                limitation='Crop-type reference data are not useful-scouting outcomes. Archive names alone do not prove country coverage or independence.')
    (ROOT/'docs/africa/REFERENCE_ARCHIVES.json').write_text(json.dumps(report,indent=2)+'\n')
    for r in results:print(Path(r['source_url'].split('?')[0]).name,len(r['entries']),'entries; Uganda-named:',len(r['uganda_named_entries']))
