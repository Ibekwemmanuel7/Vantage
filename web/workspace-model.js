/* Pure workspace contracts; imported boundaries and notes never become validated evidence. */
(function (root, factory) {
  const model = factory();
  if (typeof module === 'object' && module.exports) module.exports = model;
  else root.VantageWorkspace = model;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const fail = message => { throw new Error(message); };
  function validDate(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const d = new Date(value + 'T00:00:00Z');
    return Number.isFinite(d.getTime()) && d.toISOString().slice(0, 10) === value;
  }
  function validateSnapshot(s) {
    if (!s || s.schema_version !== 'scouting-workspace-1' || s.mode !== 'historical_research' ||
        s.case_id !== 'kween-2023' || s.field_recommendations_available !== false ||
        s.independent_field_outcomes !== 0 || !Array.isArray(s.optical?.observations) ||
        !Array.isArray(s.sources) || !s.sources.length || !s.radar || !s.benchmark || !s.preview) fail('Unsupported or incomplete historical evidence snapshot.');
    const cutoff = Date.parse(s.as_of), latest = Date.parse(s.optical.latest_usable);
    const age = (cutoff - latest) / 86400000;
    if (!Number.isFinite(age) || age < 0 || Math.abs(age - s.optical.age_at_cutoff_days) > .001 ||
        age <= s.optical.freshness_policy_days || s.optical.status !== 'stale_research_context' ||
        s.preview.acquired_at !== s.optical.latest_usable || s.radar.illumination_confirmed !== false) fail('Evidence dates or eligibility differ from the supported research case.');
    let previous = -Infinity;
    for (const o of s.optical.observations) {
      const t = Date.parse(o.acquired_at);
      if (!Number.isFinite(t) || t > cutoff || t <= previous ||
          typeof o.coverage_qualified !== 'boolean' ||
          (o.usable_crop_fraction !== null && (!Number.isFinite(o.usable_crop_fraction) || o.usable_crop_fraction < 0 || o.usable_crop_fraction > 1))) fail('Invalid dated observation or coverage.');
      previous = t;
    }
    return s;
  }
  const cross = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
  const onSegment = (a, b, p) => Math.abs(cross(a, b, p)) < 1e-12 &&
    p[0] >= Math.min(a[0], b[0]) - 1e-12 && p[0] <= Math.max(a[0], b[0]) + 1e-12 &&
    p[1] >= Math.min(a[1], b[1]) - 1e-12 && p[1] <= Math.max(a[1], b[1]) + 1e-12;
  function intersects(a, b, c, d) {
    const x = cross(a,b,c), y = cross(a,b,d), z = cross(c,d,a), w = cross(c,d,b);
    return (x * y < 0 && z * w < 0) || onSegment(a,b,c) || onSegment(a,b,d) || onSegment(c,d,a) || onSegment(c,d,b);
  }
  function ringsIntersect(a, b) {
    for (let i=0;i<a.length-1;i++) for (let j=0;j<b.length-1;j++) if (intersects(a[i],a[i+1],b[j],b[j+1])) return true;
    return false;
  }
  function inside(point, ring) {
    let result=false;
    for (let i=0,j=ring.length-2;i<ring.length-1;j=i++) {
      const a=ring[i],b=ring[j];
      if ((a[1]>point[1]) !== (b[1]>point[1]) && point[0] < (b[0]-a[0])*(point[1]-a[1])/(b[1]-a[1])+a[0]) result=!result;
    }
    return result;
  }
  function validateGeometry(g, budget) {
    if (g?.crs != null) fail('Reproject to RFC 7946 WGS84 GeoJSON without a custom CRS declaration.');
    if (!g || !['Polygon','MultiPolygon'].includes(g.type) || !Array.isArray(g.coordinates)) fail('Each field must have Polygon or MultiPolygon geometry.');
    const polygons = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
    if (!polygons.length || polygons.length > 50) fail('Empty or overly complex geometry.');
    for (const polygon of polygons) {
      if (!Array.isArray(polygon) || !polygon.length || polygon.length > 20) fail('A polygon needs an exterior ring and at most 19 holes.');
      for (const ring of polygon) {
        if (!Array.isArray(ring) || ring.length < 4 || ring.length > 500) fail('Rings need 4–500 coordinates, including the closing point.');
        budget.count += ring.length;
        if (budget.count > 10000) fail('The file exceeds the 10,000-coordinate limit.');
        for (const p of ring) if (!Array.isArray(p) || p.length !== 2 || !p.every(Number.isFinite) ||
            p[0] < 29 || p[0] > 35.5 || p[1] < -2 || p[1] > 5) fail('Use WGS84 longitude/latitude within the Uganda workspace extent (29–35.5 E, 2 S–5 N).');
        if (ring[0][0] !== ring.at(-1)[0] || ring[0][1] !== ring.at(-1)[1]) fail('Polygon rings must close exactly.');
        let area = 0;
        for (let i=0;i<ring.length-1;i++) {
          if (ring[i][0] === ring[i+1][0] && ring[i][1] === ring[i+1][1]) fail('Consecutive duplicate vertices are not supported.');
          area += ring[i][0]*ring[i+1][1] - ring[i+1][0]*ring[i][1];
          for (let j=i+2;j<ring.length-1;j++) {
            if (i===0 && j===ring.length-2) continue;
            if (intersects(ring[i],ring[i+1],ring[j],ring[j+1])) fail('Self-intersecting field boundaries are not supported.');
          }
        }
        if (Math.abs(area) < 1e-12) fail('Zero-area rings are not supported.');
      }
      for (let i=1;i<polygon.length;i++) {
        if (!inside(polygon[i][0],polygon[0]) || ringsIntersect(polygon[0],polygon[i])) fail('Holes must lie strictly inside their exterior ring.');
        for (let j=1;j<i;j++) if (ringsIntersect(polygon[i],polygon[j]) || inside(polygon[i][0],polygon[j]) || inside(polygon[j][0],polygon[i])) fail('Overlapping or touching holes are not supported.');
      }
    }
    for (let i=0;i<polygons.length;i++) for (let j=0;j<i;j++) if (ringsIntersect(polygons[i][0],polygons[j][0]) || inside(polygons[i][0][0],polygons[j][0]) || inside(polygons[j][0][0],polygons[i][0])) fail('Overlapping or touching MultiPolygon components are not supported.');
    return JSON.parse(JSON.stringify(g));
  }
  function importFields(collection, existing=[]) {
    if (collection?.type !== 'FeatureCollection' || !Array.isArray(collection.features) || !collection.features.length) fail('Choose a nonempty GeoJSON FeatureCollection.');
    if (collection.crs != null) fail('Reproject to RFC 7946 WGS84 GeoJSON without a custom CRS declaration.');
    if (existing.length + collection.features.length > 50) fail('This local pilot supports up to 50 fields in total.');
    const budget={count:0}, ids=new Set(existing.map(f=>f.id)), shapes=new Set(existing.map(f=>JSON.stringify(f.geometry)));
    return collection.features.map((f,index)=>{
      if (f?.type !== 'Feature') fail('Every imported entry must be a GeoJSON Feature.');
      if (f.crs != null || (f.properties != null && (typeof f.properties !== 'object' || Array.isArray(f.properties)))) fail('Feature properties must be an object or null, with no custom CRS declaration.');
      const geometry=validateGeometry(f.geometry,budget), shape=JSON.stringify(geometry), p=f.properties || {};
      const id=String(f.id ?? p.id ?? ('local-' + (existing.length+index+1)));
      if (!id.trim() || id.length > 100 || ids.has(id) || shapes.has(shape)) fail('Field IDs and boundaries must be unique. No existing field is replaced.');
      ids.add(id);shapes.add(shape);
      const name=typeof p.name==='string' && p.name.trim() ? p.name.trim().slice(0,100) : 'Imported field ' + (existing.length+index+1);
      const crop=typeof p.crop==='string' && p.crop.trim() ? p.crop.trim().slice(0,100) : null;
      const planting=p.planting_date ?? null;
      if (planting !== null && !validDate(planting)) fail('planting_date must be a valid YYYY-MM-DD date or omitted.');
      return {id,name,crop,planting_date:planting,geometry,source:'user_import_unverified',status:'awaiting_observations'};
    });
  }
  function validateNote(note, today) {
    if (!validDate(note.observed_at) || note.observed_at > today || !['desk_review','field_observation_draft'].includes(note.kind) ||
        typeof note.finding!=='string' || !note.finding.trim() || note.finding.length>1500 ||
        typeof note.next_step!=='string' || !note.next_step.trim() || note.next_step.length>500) fail('Enter a valid date (not in the future), factual finding and next step.');
    return {...note,finding:note.finding.trim(),next_step:note.next_step.trim(),validation_status:'unverified_local_draft'};
  }
  return {validateSnapshot,importFields,validateNote,validDate};
});
