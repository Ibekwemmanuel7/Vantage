'use strict';
(() => {
  const focus=document.getElementById('map-focus'), explorer=document.querySelector('.focus-grid');
  focus.addEventListener('click',()=>{
    const expanded=explorer.classList.toggle('map-expanded');
    focus.setAttribute('aria-pressed',String(expanded));
    focus.setAttribute('aria-label',expanded?'Restore split imagery view':'Expand imagery view');
    focus.title=expanded?'Restore split imagery view':'Expand imagery view';
  });
  const tabs=[...document.querySelectorAll('.workspace-tabs a')];
  function update(){
    const hash=location.hash||'#overview';
    tabs.forEach(tab=>{const selected=tab.hash===hash;tab.classList.toggle('selected',selected);
      if(selected)tab.setAttribute('aria-current','location');else tab.removeAttribute('aria-current');});
  }
  window.addEventListener('hashchange',update);update();
})();
