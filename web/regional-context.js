'use strict';
(() => {
  const $=id=>document.getElementById(id);
  let data, version=0;
  const node=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
  function seasons(){
    const unit=data.units[Number($('regional-study').value)];
    $('regional-season').replaceChildren(...unit.calendars.map((c,i)=>{const o=node('option',c.crop_season_label);o.value=i;return o;}));
    render();
  }
  function render(){
    const unit=data.units[Number($('regional-study').value)], calendar=unit.calendars[Number($('regional-season').value)];
    $('regional-zone').textContent=unit.zone_label+' · ASAP zone '+unit.zone_id+' · analyst study box';
    $('regional-windows').replaceChildren(...Object.entries(calendar.windows).map(([phase,w])=>{
      const card=node('div','');card.append(node('h3',phase[0].toUpperCase()+phase.slice(1)),node('p',w.start+' → '+w.end));return card;
    }));
    $('regional-year-note').textContent=calendar.crosses_calendar_year?'This recurring season extends into 2025.':'This recurring season falls within 2024.';
  }
  async function load(){
    const current=++version;
    $('regional-state').textContent='Loading regional context…';$('regional-controls').hidden=true;
    try{
      const response=await fetch('data/regional-context.json',{cache:'no-store'});
      if(!response.ok)throw new Error('HTTP '+response.status);
      const value=await response.json();
      if(value.schema_version!=='vantage-public-regional-context-1'||value.anchor_year!==2024||value.field_priorities_available!==false||value.field_calendars_confirmed!==0||value.units?.length!==3||value.units.some(u=>!u.calendars?.length||u.calendars.some(c=>c.confirmation_kind!=='regional_prior'||c.field_calendar_confirmed!==false||c.crop_identity_confirmed!==false||c.field_priorities_available!==false)))throw new Error('Unsupported context snapshot');
      if(current!==version)return;
      data=value;
      $('regional-study').replaceChildren(...data.units.map((u,i)=>{const o=node('option',u.label);o.value=i;return o;}));
      seasons();$('regional-controls').hidden=false;
      $('regional-state').textContent='Recurring 2024 anchor · sources retrieved '+data.source_observed_on+' · 0 confirmed field calendars';
    }catch(error){if(current===version)$('regional-state').textContent='Regional context unavailable: '+error.message+'. No replacement context is supplied.';}
  }
  $('regional-study').addEventListener('change',seasons);
  $('regional-season').addEventListener('change',render);
  $('regional-retry').addEventListener('click',load);
  load();
})();
