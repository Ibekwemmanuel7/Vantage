'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const model=require('../web/workspace-model.js');
const ring=[[34.5,1.5],[34.501,1.5],[34.501,1.501],[34.5,1.501],[34.5,1.5]];
const collection=(coords=ring,properties={name:'Synthetic QA field',crop:'Maize'})=>({type:'FeatureCollection',features:[{type:'Feature',id:'qa-field',properties,geometry:{type:'Polygon',coordinates:[coords]}}]});
test('snapshot requires historical, stale, unvalidated evidence',()=>{
  const snapshot=JSON.parse(fs.readFileSync('web/data/scouting.json','utf8'));
  assert.equal(model.validateSnapshot(snapshot).field_recommendations_available,false);
  assert.throws(()=>model.validateSnapshot({...snapshot,field_recommendations_available:true}));
  assert.throws(()=>model.validateSnapshot({...snapshot,optical:{...snapshot.optical,latest_usable:'2023-06-06T00:00:00Z'}}));
});
test('import preserves geometry and unverified metadata without granting priority',()=>{
  const fields=model.importFields(collection());
  assert.equal(fields[0].name,'Synthetic QA field');
  assert.equal(fields[0].status,'awaiting_observations');
  assert.equal(fields[0].source,'user_import_unverified');
  assert.equal(fields[0].planting_date,null);
  assert.deepEqual(fields[0].geometry.coordinates[0],ring);
});
test('duplicates cannot overwrite existing fields',()=>{
  const fields=model.importFields(collection());
  assert.throws(()=>model.importFields(collection(),fields),/unique/);
  const other=collection();other.features[0].id='different';
  assert.throws(()=>model.importFields(other,fields),/unique/);
});
test('open, zero-area and crossing rings rejected',()=>{
  assert.throws(()=>model.importFields(collection(ring.slice(0,-1))),/close/);
  assert.throws(()=>model.importFields(collection([[34.5,1.5],[34.6,1.6],[34.7,1.7],[34.5,1.5]])));
  assert.throws(()=>model.importFields(collection([[34.5,1.5],[34.6,1.6],[34.5,1.6],[34.6,1.5],[34.5,1.5]])),/intersect/);
});
test('out-of-workspace coordinates, invalid crops dates, and nonfinite values rejected',()=>{
  assert.throws(()=>model.importFields(collection([[0,0],[1,0],[1,1],[0,0]])),/extent/);
  assert.throws(()=>model.importFields(collection(undefined,{planting_date:'2023-02-30'})),/planting_date/);
  const invalid=structuredClone(ring);invalid[1][0]=NaN;
  assert.throws(()=>model.importFields(collection(invalid)),/WGS84/);
});
test('holes must be contained and not overlap',()=>{
  const c=collection();c.features[0].geometry.coordinates.push([[34.502,1.502],[34.503,1.502],[34.503,1.503],[34.502,1.502]]);
  assert.throws(()=>model.importFields(c),/inside/);
});
test('finite import budget is enforced',()=>{
  const c=collection();c.features=Array(51).fill(c.features[0]);
  assert.throws(()=>model.importFields(c),/50 fields/);
  assert.throws(()=>model.importFields({type:'FeatureCollection',features:[]}),/nonempty/);
});
test('custom CRS and malformed properties never silently change geometry meaning',()=>{
  assert.throws(()=>model.importFields({...collection(),crs:{type:'name',properties:{name:'EPSG:32636'}}}),/Reproject/);
  const c=collection();c.features[0].properties='not an object';
  assert.throws(()=>model.importFields(c),/properties/);
});
test('notes remain unverified, preserve uncertainty, reject future and invalid dates',()=>{
  const note={kind:'field_observation_draft',observed_at:'2026-10-20',finding:' Synthetic test; cause uncertain ',next_step:'Confirm date'};
  const checked=model.validateNote(note,'2026-10-20');
  assert.equal(checked.validation_status,'unverified_local_draft');
  assert.equal(checked.finding,'Synthetic test; cause uncertain');
  assert.throws(()=>model.validateNote({...note,observed_at:'2026-10-21'},'2026-10-20'));
  assert.throws(()=>model.validateNote({...note,observed_at:'2026-02-30'},'2026-10-20'));
  assert.throws(()=>model.validateNote({...note,kind:'confirmed_label'},'2026-10-20'));
});
