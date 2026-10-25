'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const images=require('../web/report-images.js'),reports=require('../web/report-model.js');
const png=Uint8Array.from(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jJ1kAAAAASUVORK5CYII=','base64'));
const sha=async bytes=>Buffer.from(await crypto.subtle.digest('SHA-256',bytes)).toString('hex');
test('PNG verification checks bytes, hash and exact grid before embedding',async()=>{
  const expected=await sha(png);const image=await images.verify(png,expected,{width:1,height:1});
  assert.equal(image.sha256,expected);assert.equal(image.width,1);assert.match(image.data_url,/^data:image\/png;base64,/);
});
test('changed bytes, non-PNG data, wrong dimensions and oversized images reject',async()=>{
  const expected=await sha(png),grid={width:1,height:1};
  const changed=png.slice();changed[30]^=1;
  await assert.rejects(images.verify(changed,expected,grid),/checksum/);
  await assert.rejects(images.verify(png,expected,{width:2,height:1}),/dimensions/);
  await assert.rejects(images.verify(new Uint8Array(40),expected,grid),/PNG/);
  await assert.rejects(images.verify(new Uint8Array(2_000_001),expected,grid),/Bounded/);
});
test('report records image lineage without copying binary data into JSON',()=>{
  const s=JSON.parse(fs.readFileSync('web/data/scouting.json','utf8'));
  const image={...s.preview.grid,sha256:s.preview.assets.rgb.sha256,data_url:'data:image/png;base64,AA=='};
  const report=reports.build(s,{title:'Test',author:'',generated_at:'2026-10-24T00:00:00Z',images:{rgb:image}});
  assert.equal(report.imagery.status,'partial');assert.equal(report.imagery.assets.rgb.data_url,undefined);
  const html=reports.html(report,{rgb:image});assert.match(html,/<img /);assert.match(html,/Vegetation-change preview unavailable/);assert.match(html,/img-src data:/);assert.doesNotMatch(html,/<script|src="https?:/);
  assert.throws(()=>reports.html(report),/Verified/);
  assert.throws(()=>reports.html(report,{rgb:{...image,data_url:'https://example.test/tracker.png'}}),/Verified/);
  assert.throws(()=>reports.build(s,{title:'Test',author:'',generated_at:'2026-10-24T00:00:00Z',images:{rgb:{...image,sha256:'0'.repeat(64)}}}),/identity/);
});
