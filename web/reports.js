'use strict';
(() => {
  const $=id=>document.getElementById(id);let snapshot=null,pack=null,report=null,version=0;
  const exportsEnabled=value=>{for(const id of ['report-html','report-json'])$(id).disabled=!value;};
  function invalidate(){report=null;exportsEnabled(false);$('report-preview').srcdoc='';$('report-note-count').textContent='Preview not current';$('report-state').textContent='Details changed. Update the preview before exporting.';}
  function build(){
    report=window.VantageReports.build(snapshot,{title:$('report-title').value,author:$('report-author').value,generated_at:new Date().toISOString()},pack);
    $('report-preview').srcdoc=window.VantageReports.html(report);$('report-note-count').textContent=report.draft_note_count+' draft note'+(report.draft_note_count===1?'':'s');
    $('report-state').textContent='Preview ready · evidence cutoff '+report.evidence_as_of.slice(0,10)+' · 0 independent field outcomes';exportsEnabled(true);
  }
  function fail(error){invalidate();$('report-error').textContent=error.message;$('report-error').hidden=false;}
  async function load(){
    snapshot=null;invalidate();$('report-build').disabled=true;$('report-state').textContent='Loading the historical snapshot…';$('report-error').hidden=true;$('report-retry').hidden=true;
    try{const response=await fetch('data/scouting.json',{cache:'no-store'});if(!response.ok)throw new Error('Evidence unavailable (HTTP '+response.status+').');snapshot=window.VantageWorkspace.validateSnapshot(await response.json());$('report-build').disabled=false;build();}
    catch(error){fail(error);$('report-state').textContent='No report available. No replacement evidence is supplied.';$('report-retry').hidden=false;}
  }
  $('report-form').addEventListener('submit',event=>{event.preventDefault();$('report-error').hidden=true;try{build();}catch(error){fail(error);}});
  for(const id of ['report-title','report-author'])$(id).addEventListener('input',invalidate);
  $('report-pack').addEventListener('change',async()=>{
    const current=++version;pack=null;invalidate();$('report-clear').disabled=true;$('report-error').hidden=true;
    try{const file=$('report-pack').files[0];if(!file)return;if(file.size>1_000_000)throw new Error('Choose a review pack no larger than 1 MB.');const candidate=JSON.parse(await file.text());if(current!==version)return;
      if(!snapshot)throw new Error('Load the historical evidence before opening a pack.');
      window.VantageReports.build(snapshot,{title:$('report-title').value,author:$('report-author').value,generated_at:new Date().toISOString()},candidate);
      pack=candidate;$('report-clear').disabled=false;build();
    }catch(error){if(current===version)fail(error);}
  });
  $('report-clear').addEventListener('click',()=>{version++;pack=null;$('report-pack').value='';$('report-clear').disabled=true;invalidate();$('report-error').hidden=true;if(snapshot)build();});
  function download(kind){if(!report)return;const value=kind==='html'?window.VantageReports.html(report):JSON.stringify(report,null,2);const url=URL.createObjectURL(new Blob([value],{type:kind==='html'?'text/html':'application/json'}));const a=document.createElement('a');a.href=url;a.download='vantage-kween-evidence-'+report.generated_at.slice(0,10)+'.'+kind;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
  $('report-html').addEventListener('click',()=>download('html'));$('report-json').addEventListener('click',()=>download('json'));$('report-retry').addEventListener('click',load);load();
})();
