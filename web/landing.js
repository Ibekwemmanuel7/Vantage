'use strict';
(() => {
  // Preserve bookmarks from when the root URL was the scouting workspace.
  const workspaceSections = new Set(['overview','fields','review-plan','observations','regional-context','data-status']);
  function routeWorkspaceBookmark() {
    if (workspaceSections.has(location.hash.slice(1)) && !location.pathname.endsWith('landing.html')) {
      location.replace('workspace.html' + location.hash);
      return true;
    }
    return false;
  }
  window.addEventListener('hashchange', routeWorkspaceBookmark);
  if (routeWorkspaceBookmark()) return;
  const range = document.getElementById('compare-range');
  range.addEventListener('input', () => {
    document.getElementById('comparison').style.setProperty('--split', (100 - Number(range.value)) + '%');
    range.setAttribute('aria-valuetext', range.value + '% vegetation difference revealed');
  });
  range.setAttribute('aria-valuetext', '50% vegetation difference revealed');
  for (const image of document.querySelectorAll('.comparison img')) {
    const fail = () => { document.getElementById('image-failure').hidden = false; };
    image.addEventListener('error', fail);
    if (image.complete && !image.naturalWidth) fail();
  }
})();
