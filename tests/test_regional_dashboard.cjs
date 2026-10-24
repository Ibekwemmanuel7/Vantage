'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const snapshot=JSON.parse(fs.readFileSync('web/data/regional-context.json'));
async function run(value,ok=true){
  class Element{
    constructor(){this.children=[];this.value='0';this.listeners={};this.hidden=false;}
    append(...items){this.children.push(...items);}
    replaceChildren(...items){this.children=items;this.value=String(items[0]?.value??'0');}
    addEventListener(event,fn){this.listeners[event]=fn;}
  }
  const elements={};
  vm.runInNewContext(fs.readFileSync('web/regional-context.js','utf8'),{
    document:{getElementById:id=>elements[id]??=(new Element()),createElement:()=>new Element()},
    fetch:async()=>({ok,status:503,json:async()=>value})
  });
  await new Promise(resolve=>setImmediate(resolve));return elements;
}
test('public snapshot contains only three analyst contexts and no confirmed fields',()=>{
  assert.deepEqual(snapshot.units.map(u=>u.label),['Iganga','Lira','Kasese']);
  assert.equal(snapshot.field_calendars_confirmed,0);
  for(const unit of snapshot.units){assert.equal(unit.calendars.length,5);for(const c of unit.calendars){assert.equal(c.confirmation_kind,'regional_prior');assert.equal(c.field_priorities_available,false);}}
});
test('selection changes study and crop, preserving cross-year ISO dates',async()=>{
  const e=await run(snapshot);assert.equal(e['regional-controls'].hidden,false);
  for(let i=0;i<3;i++){
    e['regional-study'].value=String(i);e['regional-study'].listeners.change();
    assert.match(e['regional-zone'].textContent,new RegExp(snapshot.units[i].zone_label.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
    for(let j=0;j<5;j++){
      e['regional-season'].value=String(j);e['regional-season'].listeners.change();
      const c=snapshot.units[i].calendars[j];assert.equal(e['regional-windows'].children[2].children[1].textContent,c.windows.harvesting.start+' → '+c.windows.harvesting.end);
      assert.match(e['regional-year-note'].textContent,c.crosses_calendar_year?/2025/:/2024/);
    }
  }
});
test('HTTP failure and promoted evidence fail closed',async()=>{
  for(const [value,ok]of [[snapshot,false],[{...snapshot,field_priorities_available:true},true]]){
    const e=await run(value,ok);assert.equal(e['regional-controls'].hidden,true);assert.match(e['regional-state'].textContent,/unavailable/);
  }
});
