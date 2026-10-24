(function(root){
  'use strict';
  function validate(packet){
    const fail=()=>{throw new Error('This is not a supported field review packet. Rebuild it with build_field_review.py.');};
    if(!packet||packet.schema_version!=='vantage-field-review-1')fail();
    const r=packet.report,p=packet.preview;
    const num=(v,lo,hi)=>typeof v==='number'&&Number.isFinite(v)&&v>=lo&&v<=hi;
    const date=v=>typeof v==='string'&&/(Z|[+-]\d{2}:\d{2})$/.test(v)&&Number.isFinite(Date.parse(v));
    if(!r||r.schema_version!=='vantage-field-change-1'||r.field_priorities_available!==false||!p)fail();
    if(!Array.isArray(r.fields)||r.fields.length<1||r.fields.length>100)fail();
    const ids=new Set();
    for(const f of r.fields){
      if(typeof f.field_id!=='string'||!f.field_id||ids.has(f.field_id)||typeof f.boundary_version!=='string'||typeof f.crop!=='string'||typeof f.season_id!=='string')fail();
      ids.add(f.field_id);
      if(!Array.isArray(f.blockers)||f.blockers.some(b=>typeof b!=='string')||typeof f.eligible_for_research_comparison!=='boolean'||f.field_priority_available!==false)fail();
      if(f.eligible_for_research_comparison!== (f.blockers.length===0))fail();
      if(!num(f.common_valid_pixels,0,4000000)||!Number.isInteger(f.common_valid_pixels)||!num(f.selected_grid_pixels,0,4000000)||!Number.isInteger(f.selected_grid_pixels)||f.common_valid_pixels>f.selected_grid_pixels)fail();
      if(f.common_usable_fraction!==null&&!num(f.common_usable_fraction,0,1))fail();
      if(f.eligible_for_research_comparison){if(!f.common_valid_pixels||f.common_usable_fraction===null||!num(f.median_paired_ndvi_change,-2,2)||!num(f.mean_paired_ndvi_change,-2,2))fail();}
      else if(f.median_paired_ndvi_change!==null||f.mean_paired_ndvi_change!==null)fail();
    }
    if(!r.before||!r.after||!date(r.before.acquired_at)||!date(r.after.acquired_at)||!date(r.decision_cutoff)||Date.parse(r.before.acquired_at)>=Date.parse(r.after.acquired_at)||Date.parse(r.after.acquired_at)>Date.parse(r.decision_cutoff))fail();
    if(typeof packet.report_file_sha256!=='string'||!/^[a-f0-9]{64}$/.test(packet.report_file_sha256))fail();
    if(!Number.isInteger(p.width)||!Number.isInteger(p.height)||p.width<1||p.height<1||p.width>1024||p.height>1024||p.encoding!=='int16-le-ndvi1e4-nodata32767'||typeof p.values_base64!=='string'||p.values_base64.length>2800000)fail();
    const binary=atob(p.values_base64);
    if(binary.length!==p.width*p.height*2)fail();
    const bytes=Uint8Array.from(binary,c=>c.charCodeAt(0)), view=new DataView(bytes.buffer);
    const values=new Int16Array(p.width*p.height);
    let valid=0;
    for(let i=0;i<values.length;i++){const v=view.getInt16(i*2,true);if(v!==32767&&Math.abs(v)>20000)fail();values[i]=v;if(v!==32767)valid++;}
    if(valid&&!r.fields.some(f=>f.eligible_for_research_comparison))fail();
    return {report:r,preview:p,values,reportHash:packet.report_file_sha256};
  }
  function colour(v){
    if(v===32767)return [0,0,0,0];
    const t=Math.min(1,Math.abs(v)/3000), neutral=[242,240,229], edge=v<0?[162,91,46]:[29,111,127];
    return neutral.map((n,i)=>Math.round(n+(edge[i]-n)*t)).concat(255);
  }
  const api={validate,colour};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.VantageFieldReview=api;
})(globalThis);
