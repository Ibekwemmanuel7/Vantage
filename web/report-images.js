(function(root,factory){const model=factory();if(typeof module==='object'&&module.exports)module.exports=model;else root.VantageReportImages=model;})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  async function verify(bytes,expected,grid){
    if(!(bytes instanceof Uint8Array)||bytes.length<24||bytes.length>2_000_000||!/^[a-f0-9]{64}$/.test(expected))throw new Error('Bounded PNG and expected SHA-256 required.');
    const signature=[137,80,78,71,13,10,26,10];if(signature.some((v,i)=>bytes[i]!==v)||String.fromCharCode(...bytes.slice(12,16))!=='IHDR')throw new Error('PNG header required.');
    const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),width=view.getUint32(16),height=view.getUint32(20);
    if(width!==grid.width||height!==grid.height||width*height>4_000_000||width<1||height<1)throw new Error('Preview dimensions differ from the snapshot grid.');
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
    if(digest!==expected)throw new Error('Preview checksum differs from the snapshot.');
    let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
    return {sha256:digest,width,height,data_url:'data:image/png;base64,'+btoa(binary)};
  }
  return {verify};
});
