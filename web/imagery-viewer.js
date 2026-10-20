'use strict';

// Research imagery stays separate from the adviser-reviewed evidence queue.
(() => {
  const el = id => document.getElementById(id);
  const imageCache = new Map();
  const valuesCache = new Map();
  let catalog = null;
  let modelReport = null;
  let selectedUnit = null;
  let activeProfile = 'uganda';
  let renderVersion = 0;
  let activePair = null;
  let drawScheduled = false;
  let probe = null;

  function node(tag, content, className) {
    const n = document.createElement(tag);
    n.textContent = content;
    if (className) n.className = className;
    return n;
  }

  async function readJSON(path) {
    const r = await fetch(path, { cache: 'no-cache' });
    if (!r.ok) throw new Error(`Evidence asset unavailable (HTTP ${r.status}).`);
    return r.json();
  }

  function image(path) {
    if (!path) return Promise.resolve(null);
    if (!imageCache.has(path)) {
      const promise = new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => { imageCache.delete(path); reject(new Error('An imagery preview is missing. Select another date or rebuild the dataset.')); };
        img.src = path;
      });
      imageCache.set(path, promise);
    }
    return imageCache.get(path);
  }

  async function values(scene) {
    if (!valuesCache.has(scene.id)) {
      const r = await fetch(scene.ndvi_values);
      if (!r.ok) throw new Error('Pixel values are unavailable. No replacement values were generated.');
      const raw = await r.arrayBuffer();
      if (raw.byteLength !== catalog.width * catalog.height * 4) throw new Error('Pixel grid dimensions do not match the catalog.');
      valuesCache.set(scene.id, new Float32Array(raw));
    }
    return valuesCache.get(scene.id);
  }

  function setStatus(message, error = false) {
    el('imagery-state').textContent = message;
    el('imagery-state').className = error ? 'imagery-error' : 'muted';
  }

  function unitWindow() {
    const points = el('image-extent').value === 'unit' && catalog.pixel_polygons[selectedUnit];
    if (!points) return [0, 0, catalog.width, catalog.height];
    const xs = points.map(p => p[0]);
    const ys = points.map(p => p[1]);
    const x = Math.max(0, Math.floor(Math.min(...xs)));
    const y = Math.max(0, Math.floor(Math.min(...ys)));
    return [x, y, Math.min(catalog.width - x, Math.ceil(Math.max(...xs)) - x), Math.min(catalog.height - y, Math.ceil(Math.max(...ys)) - y)];
  }

  function outline(ctx, rectangle, canvas) {
    const points = catalog.pixel_polygons[selectedUnit];
    if (!points) return;
    ctx.beginPath();
    points.forEach((p, i) => {
      const x = (p[0] - rectangle[0]) / rectangle[2] * canvas.width;
      const y = (p[1] - rectangle[1]) / rectangle[3] * canvas.height;
      if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y);
    });
    ctx.closePath();
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
    ctx.strokeStyle = '#213f32'; ctx.lineWidth = .8; ctx.stroke();
  }

  function paint(canvas, sourceImage, overlay) {
    const ctx = canvas.getContext('2d');
    const rectangle = unitWindow();
    canvas.width = rectangle[2]; canvas.height = rectangle[3];
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (sourceImage) ctx.drawImage(sourceImage, ...rectangle, 0, 0, canvas.width, canvas.height);
    if (el('quality-toggle').checked && overlay) {
      ctx.globalAlpha = Number(el('quality-opacity').value) / 100;
      ctx.drawImage(overlay, ...rectangle, 0, 0, canvas.width, canvas.height);
      ctx.globalAlpha = 1;
    }
    outline(ctx, rectangle, canvas);
  }

  function difference(a, b) {
    const canvas = document.createElement('canvas');
    canvas.width = catalog.width; canvas.height = catalog.height;
    const ctx = canvas.getContext('2d');
    const out = ctx.createImageData(canvas.width, canvas.height);
    for (let i = 0; i < a.length; i++) {
      if (!Number.isFinite(a[i]) || !Number.isFinite(b[i])) continue;
      const delta = b[i] - a[i];
      const t = Math.min(1, Math.abs(delta) / .3);
      const color = delta >= 0 ? [43, 111, 69] : [172, 73, 49];
      for (let c = 0; c < 3; c++) out.data[i * 4 + c] = Math.round(247 + (color[c] - 247) * t);
      out.data[i * 4 + 3] = 255;
    }
    ctx.putImageData(out, 0, 0);
    return canvas;
  }

  function paintPair() {
    if (!activePair) return;
    const mode = el('image-layer').value;
    const p = activePair;
    const isRGB = mode === 'rgb';
    const missingRGB = isRGB && (!p.leftRGB || !p.rightRGB);
    if (missingRGB) {
      el('image-panels').hidden = true;
      setStatus('True-color RGB is unavailable for one selected date. Select NDVI or another date. Missing bands are not synthesized.', true);
      return;
    }
    el('image-panels').hidden = false;
    paint(el('image-left'), isRGB ? p.leftRGB : p.leftNDVI, p.leftQuality);
    paint(el('image-right'), isRGB ? p.rightRGB : mode === 'change' ? p.delta : p.rightNDVI, p.rightQuality);
    el('image-right-label').textContent = mode === 'change' ? 'Comparison − reference · NDVI difference' : 'Comparison acquisition';
    el('image-legend').textContent = mode === 'rgb' ? 'RGB: fixed reflectance stretch 0–0.30, gamma 2.2. Checkerboard means rejected/no data.' : mode === 'change' ? 'Difference: brown ≤ −0.30 · near-white 0 · green ≥ +0.30 NDVI. Only pixels valid on both dates are compared.' : 'NDVI: brown −0.20 · light green 0.40 · dark green 1.00. Fixed scale across dates.';
    setStatus('Cached real satellite acquisitions. Selected unit outlined; no cloud filling, crop diagnosis or model-generated imagery.');
    updateProbe();
  }

  function schedulePaint() {
    if (drawScheduled) return;
    drawScheduled = true;
    requestAnimationFrame(() => { drawScheduled = false; paintPair(); });
  }

  function formatPixel(v) { return Number.isFinite(v) ? v.toFixed(3) : 'unavailable'; }

  function updateProbe() {
    if (!probe || !activePair) return;
    const [x, y] = probe;
    const index = y * catalog.width + x;
    const a = activePair.a[index], b = activePair.b[index];
    const t = catalog.transform;
    const east = t[0] * (x + .5) + t[1] * (y + .5) + t[2];
    const north = t[3] * (x + .5) + t[4] * (y + .5) + t[5];
    el('pixel-readout').textContent = `EPSG:32636 · E ${east.toFixed(0)} m, N ${north.toFixed(0)} m · Reference NDVI ${formatPixel(a)} · Comparison ${formatPixel(b)} · Difference ${formatPixel(Number.isFinite(a) && Number.isFinite(b) ? b - a : NaN)}`;
  }

  async function renderPair() {
    if (!catalog || activeProfile !== 'uganda') return;
    const version = ++renderVersion;
    const left = catalog.scenes.find(s => s.id === el('image-reference').value);
    const right = catalog.scenes.find(s => s.id === el('image-comparison').value);
    if (!left || !right) return;
    activePair = null;
    el('image-panels').hidden = true;
    setStatus('Loading georeferenced satellite previews and masked pixel values…');
    el('imagery-retry').hidden = true;
    try {
      const [leftRGB, rightRGB, leftNDVI, rightNDVI, leftQuality, rightQuality, a, b] = await Promise.all([
        image(left.rgb).catch(() => null), image(right.rgb).catch(() => null), image(left.ndvi), image(right.ndvi), image(left.quality), image(right.quality), values(left), values(right)
      ]);
      if (version !== renderVersion || activeProfile !== 'uganda') return;
      activePair = { left, right, leftRGB, rightRGB, leftNDVI, rightNDVI, leftQuality, rightQuality, a, b, delta: difference(a, b) };
      el('image-left-date').textContent = left.acquired_at;
      el('image-right-date').textContent = right.acquired_at;
      el('image-left-source').href = left.source_url;
      el('image-right-source').href = right.source_url;
      el('image-pair-context').textContent = left.year === right.year ? 'Two observations within the same seasonal window. Normal growth, management and residual cloud effects may explain changes.' : 'Same-season observations from different years. This is a seasonal comparison, not an event-damage before/after validation.';
      for (const asset of ['reflectance', 'ndvi', 'quality']) {
        el('download-' + asset).href = '/api/imagery-asset?' + new URLSearchParams({ dataset: catalog.dataset_id, scene: right.id, asset });
      }
      const r = unitWindow(); probe = [Math.floor(r[0] + r[2] / 2), Math.floor(r[1] + r[3] / 2)];
      paintPair();
    } catch (e) {
      if (version !== renderVersion) return;
      activePair = null; el('image-panels').hidden = true;
      setStatus(e.message, true); el('imagery-retry').hidden = false;
    }
  }

  function renderML() {
    const r = modelReport;
    if (!r) return;
    el('ml-summary').textContent = `${r.model} · ${r.training_samples} earlier-year training samples · ${r.training_years.join(', ')} · ${r.target_samples} usable target sample(s).`;
    el('ml-limit').textContent = r.limitation;
    const p = r.predictions.find(p => p.unit_id === selectedUnit);
    el('ml-unit').textContent = p ? `${selectedUnit}: ${p.status.replaceAll('_', ' ')}. ${p.reasons.join(' ')}` : 'No model prediction for the selected unit.';
    el('ml-features').replaceChildren();
    for (const f of p?.feature_context || []) el('ml-features').append(node('li', `${f.feature}: ${f.observed.toFixed(3)}; training median ${f.training_median.toFixed(3)}. Descriptive difference, not cause.`));
  }

  async function loadCatalog() {
    try {
      catalog = await readJSON('data/imagery.json');
      if (catalog.schema_version !== 'imagery-viewer-1' || !catalog.scenes.length) throw new Error('No supported imagery catalog is available.');
      el('imagery-controls').hidden = false;
      for (const id of ['image-reference', 'image-comparison']) {
        el(id).replaceChildren(...catalog.scenes.map(s => {
          const option = node('option', `${s.acquired_at.slice(0, 10)} · ${s.id.slice(0, 3)}`);
          option.value = s.id; return option;
        }));
      }
      const candidates = catalog.scenes.filter(s => s.year < catalog.target_year);
      const reference = [...candidates].sort((a, b) => Number(!!b.rgb) - Number(!!a.rgb) || b.year - a.year || b.accepted_fraction - a.accepted_fraction)[0];
      const target = catalog.scenes.filter(s => s.year === catalog.target_year).sort((a, b) => Number(!!b.rgb) - Number(!!a.rgb) || b.accepted_fraction - a.accepted_fraction)[0];
      el('image-reference').value = reference.id; el('image-comparison').value = target.id;
      el('dataset-id').textContent = catalog.dataset_id;
      await renderPair();
    } catch (e) {
      catalog = null; activePair = null;
      setStatus(e.message + ' Run scripts/prepare_ml_dataset.py to rebuild cached imagery.', true);
      el('imagery-controls').hidden = true; el('image-panels').hidden = true;
      el('imagery-retry').hidden = false;
    }
    try { modelReport = await readJSON('data/ml.json'); renderML(); } catch { el('ml-summary').textContent = 'No ML experiment report available. The original evidence queue is unchanged.'; }
    try {
      const r = await readJSON('data/supervised-status.json');
      el('supervised-state').textContent = r.model_trained ? 'Supervised research model trained; see the research report and validation limits.' : 'Supervised training is gated: independently verified field outcomes and geographically separated cohorts are required. No classifier was trained from demonstration flags.';
    } catch { el('supervised-state').textContent = 'Supervised field-label evaluation has not run.'; }
  }

  window.addEventListener('vantage:profile', event => {
    activeProfile = event.detail.profile;
    ++renderVersion;
    el('imagery-research').hidden = activeProfile !== 'uganda';
    el('imagery-nav').hidden = activeProfile !== 'uganda';
    if (activeProfile === 'uganda') {
      if (catalog) renderPair(); else loadCatalog();
    }
  });
  window.addEventListener('vantage:unit', event => {
    selectedUnit = event.detail.unit_id;
    schedulePaint(); renderML();
  });
  for (const id of ['image-reference', 'image-comparison']) el(id).addEventListener('change', renderPair);
  for (const id of ['image-layer', 'image-extent', 'quality-toggle', 'quality-opacity']) el(id).addEventListener('input', schedulePaint);
  el('imagery-retry').addEventListener('click', () => catalog ? renderPair() : loadCatalog());
  for (const id of ['image-left', 'image-right']) {
    const canvas = el(id);
    canvas.addEventListener('pointerdown', event => {
      if (!catalog || !activePair) return;
      const box = canvas.getBoundingClientRect(), r = unitWindow();
      probe = [Math.min(catalog.width - 1, Math.max(0, Math.floor(r[0] + (event.clientX - box.left) / box.width * r[2]))), Math.min(catalog.height - 1, Math.max(0, Math.floor(r[1] + (event.clientY - box.top) / box.height * r[3])))];
      updateProbe();
    });
    canvas.addEventListener('keydown', event => {
      if (!probe || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
      event.preventDefault();
      const [x, y] = probe;
      probe = [Math.max(0, Math.min(catalog.width - 1, x + (event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0))), Math.max(0, Math.min(catalog.height - 1, y + (event.key === 'ArrowDown' ? 1 : event.key === 'ArrowUp' ? -1 : 0)))];
      updateProbe();
    });
  }
})();
