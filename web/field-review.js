'use strict';
(()=>{
  const $=id=>document.getElementById(id);let current=null,loadVersion=0;
  const text=(id,value)=>{$(id).textContent=value;};
  const date=v=>new Date(v).toISOString().replace('T',' ').replace('.000Z',' UTC');
  const percent=v=>v===null?'Unavailable':`${(v*100).toFixed(1)}%`;
  function fact(parent,name,value){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=name;dd.textContent=String(value);parent.append(dt,dd);}
  function reset(){loadVersion++;current=null;$('packet').value='';$('review').hidden=true;$('empty').hidden=false;$('clear').disabled=true;$('error').hidden=true;$('fields').replaceChildren();$('field-detail').replaceChildren();$('lineage').replaceChildren();$('limitations').replaceChildren();$('map').width=1;$('map').height=1;}
  function field(){const f=current.report.fields[Number($('fields').value)],target=$('field-detail');target.replaceChildren();
    const status=document.createElement('span');status.className='status'+(f.eligible_for_research_comparison?'':' withheld');status.textContent=f.eligible_for_research_comparison?'Supported research comparison':'Comparison withheld';target.append(status);
    const value=document.createElement('p');value.className='change-value';value.textContent=f.median_paired_ndvi_change===null?'—':`${f.median_paired_ndvi_change>0?'+':''}${f.median_paired_ndvi_change.toFixed(3)}`;target.append(value);
    const label=document.createElement('p');label.className='help';label.textContent='Median paired NDVI change · later minus earlier';target.append(label);
    const dl=document.createElement('dl');for(const [k,v] of [['Field ID',f.field_id],['Declared crop / season',`${f.crop} / ${f.season_id}`],['Boundary version',f.boundary_version],['Common usable coverage',percent(f.common_usable_fraction)],['Common valid / selected pixels',`${f.common_valid_pixels} / ${f.selected_grid_pixels}`],['Mean paired NDVI change',f.mean_paired_ndvi_change===null?'Withheld':f.mean_paired_ndvi_change.toFixed(3)]])fact(dl,k,v);target.append(dl);
    if(f.blockers.length){const list=document.createElement('ul');list.className='blockers';for(const b of f.blockers){const li=document.createElement('li');li.textContent=b.replaceAll('_',' ');list.append(li);}target.append(list);}
    const note=document.createElement('p');note.className='help';note.textContent='Field selection changes these details. The map continues to show the union of supported fields; no selected-field boundary is inferred.';target.append(note);
  }
  function render(){const r=current.report,p=current.preview; text('before-date',date(r.before.acquired_at));text('after-date',date(r.after.acquired_at));text('cutoff',date(r.decision_cutoff));
    text('count',`${r.fields.length} ${r.fields.length===1?'field':'fields'}`);$('fields').replaceChildren();r.fields.forEach((f,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${f.field_id} · ${f.eligible_for_research_comparison?'supported':'withheld'}`;$('fields').append(o);});
    const canvas=$('map');canvas.width=p.width;canvas.height=p.height;const ctx=canvas.getContext('2d'),image=ctx.createImageData(p.width,p.height);current.values.forEach((v,i)=>image.data.set(VantageFieldReview.colour(v),i*4));ctx.putImageData(image,0,0);
    text('overview-note',p.note||'Nearest sampled overview; full-resolution statistics are retained.');text('grid',`${p.crs} · ${p.width} × ${p.height} overview cells · north-up local raster, no basemap`);text('pixel','Move over the map to inspect an overview pixel.');
    $('lineage').replaceChildren();for(const [k,v] of [['Report file SHA-256',current.reportHash],['Earlier source',r.before.source_ref],['Later source',r.after.source_ref],['Processing recipe',r.recipe_ref],['Raster SHA-256',r.change_raster?.sha256||'Not supplied']])fact($('lineage'),k,v);
    $('limitations').replaceChildren();for(const message of r.limitations||[]){const li=document.createElement('li');li.textContent=String(message);$('limitations').append(li);}
    field();$('empty').hidden=true;$('review').hidden=false;$('clear').disabled=false;
  }
  $('packet').addEventListener('change',async()=>{const file=$('packet').files[0];reset();if(!file)return;const version=loadVersion;try{if(file.size>12*1024*1024)throw new Error('The packet exceeds the 12 MiB review limit.');const raw=await file.text();if(version!==loadVersion)return;current=VantageFieldReview.validate(JSON.parse(raw));render();}catch(error){if(version!==loadVersion)return;reset();text('error',error.message||'Unable to open this review packet.');$('error').hidden=false;}});
  $('clear').addEventListener('click',reset);$('fields').addEventListener('change',field);$('print').addEventListener('click',()=>window.print());
  $('map').addEventListener('pointermove',event=>{if(!current)return;const box=$('map').getBoundingClientRect(),p=current.preview,scale=Math.min(box.width/p.width,box.height/p.height),x=Math.floor((event.clientX-box.left-(box.width-p.width*scale)/2)/scale),y=Math.floor((event.clientY-box.top-(box.height-p.height*scale)/2)/scale);if(x<0||y<0||x>=p.width||y>=p.height){text('pixel','Outside the raster overview.');return;}const v=current.values[y*p.width+x];text('pixel',v===32767?'No supported comparison at this overview pixel.':`Overview pixel · NDVI change ${(v/10000).toFixed(4)} · not a diagnosis`);});
})();
