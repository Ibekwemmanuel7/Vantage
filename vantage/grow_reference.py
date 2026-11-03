"""Read-only aggregate audit of GROW-Africa; no field records or labels exported."""
from collections import Counter
from datetime import date,datetime
import hashlib
import io
import math
import zipfile

TABLES={
    'LSMS_cropcut':dict(country='Country',crop='Crop',source='Source',year='Year',yield_column='Yield_ton_ha_',lat='GPS_lat',lon='GPS_lon',precision=None),
    'LSMS_survey':dict(country='Country',crop='Crop',source='Source',year='AgYearEnd',yield_column='Yield_ton_ha_',lat='GPS_lat',lon='GPS_lon',precision='SpatialPrecision_km_'),
    'Point':dict(country='Country',crop='Crop',source='Source',year='HarvestYear',yield_column='Yield_ton_ha_',lat='Latitude',lon='Longitude',precision='SpatialPrecision_km_'),
    'Regional':dict(country='country',crop='crop',source='Source',year='harvest_year',yield_column='yieldTonHa',lat=None,lon=None,precision=None)}


def finite(value):
    if value is None or isinstance(value,bool):return None
    try: result=float(value)
    except (ValueError,TypeError):return None
    return result if math.isfinite(result) else None


def dated(value):
    if isinstance(value,datetime):return value.date().isoformat()
    if isinstance(value,date):return value.isoformat()
    if isinstance(value,str):
        try:return date.fromisoformat(value).isoformat()
        except ValueError:return None
    return None


class TableAudit:
    def __init__(self,kind,headers):
        self.kind=kind;self.spec=TABLES[kind];self.headers=list(headers)
        required={v for v in self.spec.values() if v is not None}
        if len(set(headers))!=len(headers) or not required.issubset(headers):raise ValueError('Unexpected table schema')
        self.counts=Counter();self.sources=Counter();self.crops=Counter();self.years=Counter();self.precisions=Counter();self.maize_sources=Counter();self.maize_years=Counter()
        self.crop_years={};self.identities=Counter();self.source_checks={}
    def add(self,row):
        self.counts['all_rows']+=1
        if self.counts['all_rows']>300_000:raise ValueError('Table row budget exceeded')
        if str(row[self.spec['country']] or '').strip().casefold()!='uganda':return
        self.counts['uganda_rows']+=1
        crop=str(row[self.spec['crop']] or '(missing)').strip();source=str(row[self.spec['source']] or '(missing)').strip()
        self.crops[crop]+=1;self.sources[source]+=1
        checks=self.source_checks.setdefault(source,Counter());checks['rows']+=1
        year=finite(row[self.spec['year']]);year=str(int(year)) if year is not None and year.is_integer() and 1900<=year<=2100 else '(missing or invalid)'
        self.years[year]+=1;self.crop_years.setdefault(crop,Counter())[year]+=1
        maize=crop.casefold()=='maize'
        if maize:self.counts['maize_rows']+=1;self.maize_sources[source]+=1;self.maize_years[year]+=1
        y=finite(row[self.spec['yield_column']])
        valid_y=y is not None and y>=0
        self.counts['yield_nonnegative_finite' if valid_y else 'yield_missing_or_invalid']+=1
        if maize and valid_y:self.counts['maize_yield_nonnegative_finite']+=1
        for key in ('YieldUsingGPS_ton_ha_','YieldEst2_ton_ha_','YieldEst2UsingGPS_ton_ha_'):
            if key in row:
                value=finite(row[key]);self.counts[key+'_nonnegative_finite']+=int(value is not None and value>=0)
        lon=finite(row.get(self.spec['lon'])) if self.spec['lon'] else None
        lat=finite(row.get(self.spec['lat'])) if self.spec['lat'] else None
        if lon is not None and lat is not None and -180<=lon<=180 and -90<=lat<=90:
            self.counts['valid_coordinate_rows']+=1;self.identities[(source,year,crop,lon,lat)]+=1
        for key in ('PlantDate','HarvestDate'):
            if key in row and dated(row[key]):self.counts[key+'_parseable']+=1
        precision=finite(row.get(self.spec['precision'])) if self.spec['precision'] else None
        bucket='missing_or_nonpositive' if precision is None or precision<=0 else '<=30m' if precision<=.03 else '<=100m' if precision<=.1 else '<=1km' if precision<=1 else '>1km'
        self.precisions[bucket]+=1
        if maize and bucket=='<=30m':self.counts['maize_reported_precision_le_30m']+=1
        planting=dated(row.get('PlantDate'));harvest=dated(row.get('HarvestDate'))
        checks['maize_rows']+=int(maize);checks['yield_nonnegative_finite']+=int(valid_y)
        checks['reported_precision_le_30m']+=int(bucket=='<=30m')
        checks['both_dates_parseable']+=int(bool(planting and harvest))
        checks['calendar_boundary_date_patterns']+=int(bool((planting and planting.endswith('-01-01')) or (harvest and harvest.endswith('-12-31'))))
    def result(self):
        return dict(table=self.kind,counts=dict(self.counts),sources=dict(sorted(self.sources.items())),crops=dict(sorted(self.crops.items())),years=dict(sorted(self.years.items())),
                    maize_sources=dict(sorted(self.maize_sources.items())),maize_years=dict(sorted(self.maize_years.items())),
                    source_checks={k:dict(v) for k,v in sorted(self.source_checks.items())},
                    crop_years={k:dict(sorted(v.items())) for k,v in sorted(self.crop_years.items())},reported_precision_buckets=dict(self.precisions),
                    repeated_source_year_crop_coordinate_extra_rows=sum(v-1 for v in self.identities.values()),
                    repeated_coordinates_interpretation='Not duplicate-farm identification; survey clusters, rounded coordinates and repeated crop/plot observations may share points.',
                    date_columns_present=[k for k in ('PlantDate','HarvestDate','cropCutDay','cropCutMonth') if k in self.headers],
                    primary_yield_header=self.spec['yield_column'],units_confirmed_for_training=False,field_satellite_join_allowed=False,training_labels_admitted=0)


def audit_archive(path,expected_sha):
    import openpyxl
    if path.stat().st_size>70_000_000:raise ValueError('Archive exceeds budget')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha:raise ValueError('Pinned archive hash mismatch')
    results=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        selected=[i for i in archive.infolist() if i.filename.startswith('GROW-Africa-Database/') and i.filename.endswith('.xlsx')]
        expected={f'GROW-Africa-Database/GROW-Africa_{kind}.xlsx' for kind in TABLES}
        if len(selected)!=4 or {i.filename for i in selected}!=expected or sum(i.file_size for i in selected)>80_000_000:
            raise ValueError('Four bounded expected workbooks required')
        for info in selected:
            content=archive.read(info)
            with zipfile.ZipFile(io.BytesIO(content)) as workbook_zip:
                if sum(i.file_size for i in workbook_zip.infolist())>250_000_000:raise ValueError('Workbook expansion budget exceeded')
            book=openpyxl.load_workbook(io.BytesIO(content),read_only=True,data_only=True)
            try:
                if len(book.worksheets)!=1:raise ValueError('Single-sheet source workbook required')
                sheet=book.worksheets[0];rows=sheet.iter_rows(values_only=True);headers=next(rows)
                kind=info.filename.rsplit('GROW-Africa_',1)[1][:-5];audit=TableAudit(kind,headers)
                for values in rows:
                    if not any(v is not None for v in values):continue
                    audit.add(dict(zip(headers,values)))
                report=audit.result();report.update(workbook_sha256=hashlib.sha256(content).hexdigest(),sheet=sheet.title)
                results.append(report)
                print(kind,report['counts'],flush=True)
            finally:book.close()
    return dict(schema_version='vantage-grow-reference-audit-1',archive_sha256=expected_sha,tables=results,
                total_source_rows=sum(t['counts']['all_rows'] for t in results),uganda_rows=sum(t['counts'].get('uganda_rows',0) for t in results),
                original_source_overlap_review_required=True,field_satellite_join_allowed=False,training_labels_admitted=0,
                interpretation='Aggregate inventory only. Spatial scales, source families, year definitions and yield variants remain separate. No field labels, coordinates or raw yields exported.')
