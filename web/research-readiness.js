'use strict';
(() => {
  const el = id => document.getElementById(id);
  let report = null;
  const percent = value => typeof value === 'number' && Number.isFinite(value) ? (value * 100).toFixed(1) + '%' : 'Unavailable';
  function cell(row, value) {
    const td = document.createElement('td');
    td.textContent = value;
    row.append(td);
  }
  function render() {
    const location = el('research-location').value;
    const rows = report.observations.filter(r => r.location_id === location);
    el('research-rows').replaceChildren();
    for (const r of rows) {
      const tr = document.createElement('tr');
      cell(tr, r.acquired_at.slice(0, 10));
      cell(tr, percent(r.whole_box_usable_fraction));
      cell(tr, percent(r.crop_usable_fraction));
      cell(tr, r.evidence_status === 'sufficient_coverage_for_research' ? 'Coverage sufficient for research' : 'Insufficient coverage');
      const ndvi = r.features?.ndvi_b8a_median;
      cell(tr, typeof ndvi === 'number' && Number.isFinite(ndvi) ? ndvi.toFixed(3) : 'Unavailable');
      el('research-rows').append(tr);
    }
    const first = rows[0];
    el('research-context').textContent = first ? first.historical_cropland_pixels.toLocaleString() + ' analysis pixels mapped as cropland in 2021. Current crop and field boundaries are unconfirmed.' : 'No dated observations for this study box.';
  }
  async function load() {
    el('research-retry').hidden = true;
    el('research-body').hidden = true;
    el('research-state').textContent = 'Loading archive coverage…';
    try {
      const response = await fetch('data/research-readiness.json', {cache: 'no-store'});
      if (!response.ok) throw new Error('Archive response HTTP ' + response.status);
      const data = await response.json();
      if (data.schema_version !== 'crop-context-1' || !Array.isArray(data.observations) || !data.contexts) throw new Error('Unsupported archive format');
      report = data;
      el('research-location').replaceChildren();
      for (const id of Object.keys(report.contexts).sort()) {
        const option = document.createElement('option'); option.value = id; option.textContent = id.replace('-study', '') + ' study box';
        el('research-location').append(option);
      }
      el('research-state').textContent = report.observations.length + ' dated observations · ' + Object.keys(report.contexts).length + ' study boxes · ' + (report.dataset_complete ? 'Requested six-band archive complete' : 'Partial six-band archive');
      el('research-provenance').textContent = 'Dataset ' + report.dataset_id + ' · Context run ' + report.context_run_id + ' · Source: ESA WorldCover 2021 v200 and Copernicus Sentinel-2 L2A.';
      render(); el('research-body').hidden = false;
    } catch (error) {
      report = null;
      el('research-rows').replaceChildren();
      el('research-state').textContent = 'Research archive unavailable. ' + error.message + '. No previous or live data are substituted.';
      el('research-retry').hidden = false;
    }
  }
  el('research-location').addEventListener('change', () => { if (report) render(); });
  el('research-retry').addEventListener('click', load);
  window.addEventListener('vantage:profile', event => { el('research-readiness').hidden = event.detail.profile !== 'uganda'; });
  load();
})();
