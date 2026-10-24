'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const model=require('../web/report-model.js');
const snapshot=JSON.parse(fs.readFileSync('web/data/scouting.json','utf8'));
const options={title:'Evidence brief',author:'Test team',generated_at:'2026-10-24T12:00:00Z'};
const pack=()=>({schema_version:'local-review-pack-1',validation_status:'unverified_local_drafts',field_recommendations_available:false,evidence_snapshot_id:snapshot.snapshot_id,evidence_as_of:snapshot.as_of,fields:[{id:'qa',name:'Synthetic field',geometry:{private:'omit me'}}],notes:[{target:'field:qa',observed_at:'2026-10-23',kind:'desk_review',finding:'Synthetic draft',next_step:'Confirm calendar'}]});
test('historical evidence and generation date remain separate',()=>{
  const r=model.build(snapshot,options);assert.equal(r.evidence_as_of,snapshot.as_of);assert.equal(r.generated_at,new Date(options.generated_at).toISOString());assert.equal(r.independent_field_outcomes,0);assert.equal(r.field_recommendations_available,false);assert.equal(r.draft_note_count,0);
});
test('notes remain unverified and omit geometry and raw fields',()=>{
  const r=model.build(snapshot,options,pack());assert.equal(r.draft_note_count,1);assert.equal(r.draft_notes[0].validation_status,'unverified_local_draft');assert.equal(r.fields,undefined);assert.doesNotMatch(JSON.stringify(r),/omit me/);assert.equal(r.independent_field_outcomes,0);
});
test('stale packs, promoted records and unknown note targets reject',()=>{
  for(const change of [{evidence_snapshot_id:'wrong'},{evidence_as_of:'2024-01-01'},{field_recommendations_available:true},{validation_status:'verified'},{notes:[{...pack().notes[0],target:'field:unknown'}]}])assert.throws(()=>model.build(snapshot,options,{...pack(),...change}));
});
test('future notes, duplicate IDs and oversized arrays reject',()=>{
  assert.throws(()=>model.build(snapshot,options,{...pack(),notes:[{...pack().notes[0],observed_at:'2027-01-01'}]}));
  assert.throws(()=>model.build(snapshot,options,{...pack(),fields:[...pack().fields,...pack().fields]}));
  assert.throws(()=>model.build(snapshot,options,{...pack(),notes:Array(101).fill(pack().notes[0])}));
});
test('text is escaped in standalone export, which loads no scripts or images',()=>{
  const attack='</h1><img src=x onerror=alert(1)><script>alert(2)</script>';
  const p=pack();p.notes[0].finding=attack;
  const html=model.html(model.build(snapshot,{...options,title:attack,author:attack},p));
  assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script|<img|<iframe|<link|<form/i);assert.match(html,/default-src/);assert.match(html,/Local draft appendix/);
});
test('empty title and impossible creation times reject',()=>{
  for(const change of [{title:''},{generated_at:'invalid'},{generated_at:'2020-01-01T00:00:00Z'},{generated_at:'2026-10-24T12:00:00'}])assert.throws(()=>model.build(snapshot,{...options,...change}));
});
