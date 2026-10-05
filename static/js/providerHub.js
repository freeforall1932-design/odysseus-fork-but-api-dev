// static/js/providerHub.js
// Providers · Auto pool · Council, in one modal with three tabs.
//
//   Connect  pick a provider, paste a key, the model list is fetched, tick the ones you want.
//            Saving goes through the EXISTING POST /api/model-endpoints (key encryption and the model
//            picker are unchanged) and, optionally, adds the models to the Auto pool.
//   Auto     the saved pool + the router model. Exposes window.odysseusAuto for chat.js.
//   Council  several models (or several personas of one model) work a question and a chair merges.
//
// Everything is built with createElement/textContent, never innerHTML, so model names, provider
// messages and model output cannot inject markup. Pure helpers are exported for tests.

// --------------------------------------------------------------------------- pure helpers
export function h(tag, attrs = {}, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v == null) continue;
    if (k === 'class') node.className = v;
    else if (k === 'dataset') Object.assign(node.dataset, v);
    else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
    else if (k === 'value') node.value = v;
    else if (k === 'checked') node.checked = !!v;
    else if (k === 'disabled') node.disabled = !!v;
    else node.setAttribute(k, v === true ? '' : String(v));
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    node.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return node;
}

export function formatCtx(n) {
  if (!n || n <= 0) return '';
  if (n >= 1e6) return `${+(n / 1e6).toFixed(1)}M ctx`;
  if (n >= 1000) return `${Math.round(n / 1000)}k ctx`;
  return `${n} ctx`;
}

export function filterModels(models, { query = '', freeOnly = false } = {}) {
  const q = String(query || '').trim().toLowerCase();
  return (models || []).filter((m) => (!freeOnly || m.free === true) && (!q || `${m.id} ${m.name || ''}`.toLowerCase().includes(q)));
}

export function toPoolEntries(endpointId, models, selectedIds) {
  const want = new Set(selectedIds);
  return (models || []).filter((m) => want.has(m.id)).map((m) => ({
    endpoint_id: endpointId, model: m.id, label: m.name || m.id, tags: [],
    free: m.free ?? null, context_length: m.context_length ?? null, vision: m.vision ?? null, tools: m.tools ?? null,
  }));
}

export function mergePool(existing, additions, max = 60) {
  const base = Array.isArray(existing) ? existing : [];
  const seen = new Set(base.map((e) => `${e.endpoint_id}::${e.model}`));
  const pool = [...base];
  let skipped = 0;
  for (const a of additions || []) {
    const key = `${a.endpoint_id}::${a.model}`;
    if (seen.has(key)) continue;
    if (pool.length >= max) { skipped += 1; continue; }
    seen.add(key);
    pool.push(a);
  }
  return { pool, added: pool.length - base.length, skipped };
}

export const refOf = (e) => `${e.endpoint_id}::${e.model}`;

// Incremental parser for text/event-stream. Returns the parsed events and the unfinished remainder.
export function parseSseChunk(buffer, chunk) {
  const parts = (buffer + chunk).split('\n\n');
  const rest = parts.pop();
  const events = [];
  for (const part of parts) {
    for (const line of part.split('\n')) {
      if (!line.startsWith('data:')) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      if (payload === '[DONE]') { events.push({ type: '__done__' }); continue; }
      try { events.push(JSON.parse(payload)); } catch (_) { /* ignore a malformed frame */ }
    }
  }
  return { events, rest };
}

// --------------------------------------------------------------------------- api
async function api(path, { method = 'GET', json, form } = {}) {
  const init = { method, credentials: 'same-origin', headers: {} };
  if (json !== undefined) { init.headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(json); }
  if (form) init.body = form;
  const res = await fetch(path, init);
  let data = null;
  try { data = await res.json(); } catch (_) { /* not JSON */ }
  if (!res.ok) {
    const detail = data && (data.detail || data.error || data.message);
    const err = new Error(typeof detail === 'string' ? detail : `Request failed (HTTP ${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}

function notify(msg) {
  try { if (window.showToast) window.showToast(msg); } catch (_) { /* toast is optional */ }
}

// --------------------------------------------------------------------------- Auto state (used by chat.js)
const LS = { enabled: 'odysseus.auto.enabled', keepLocal: 'odysseus.auto.keepLocal' };
const lsGet = (k) => { try { return localStorage.getItem(k) === '1'; } catch (_) { return false; } };
const lsSet = (k, v) => { try { localStorage.setItem(k, v ? '1' : '0'); } catch (_) { /* private mode */ } };

export const auto = {
  enabled: () => lsGet(LS.enabled),
  keepLocal: () => lsGet(LS.keepLocal),
  setEnabled: (v) => {
    const value = !!v; lsSet(LS.enabled, value);
    if (typeof document !== 'undefined') document.querySelectorAll('[data-auto-setting="enabled"]').forEach((el) => { el.checked = value; });
  },
  setKeepLocal: (v) => {
    const value = !!v; lsSet(LS.keepLocal, value);
    if (typeof document !== 'undefined') document.querySelectorAll('[data-auto-setting="keepLocal"]').forEach((el) => { el.checked = value; });
  },
  last: null,
  // Never throws. Returns { route } to use for this send, { blocked, message } to stop it, or {} to carry on
  // with the model the user picked. With keep-local on, a failure BLOCKS the send instead of falling through.
  async pick(message, { hasImage = false, needsTools = false } = {}) {
    try {
      const d = await api('/api/auto/route', { method: 'POST', json: {
        message: String(message || '').slice(0, 20000), keep_local: auto.keepLocal(),
        has_image: !!hasImage, needs_tools: !!needsTools,
      } });
      auto.last = d;
      window.dispatchEvent(new CustomEvent('odysseus:auto-picked', { detail: d }));
      notify(`Auto → ${d.label}${d.reason ? ` · ${d.reason}` : ''}`);
      return { route: { model: d.model, endpoint_id: d.endpoint_id, endpoint_url: '' } };
    } catch (err) {
      if (auto.keepLocal()) return { blocked: true, message: `Keep-local is on, so this message was not sent. ${err.message}` };
      notify(`Auto could not pick a model (${err.message}). Using the selected model.`);
      return {};
    }
  },
  // Keep chat.js' send path small and centralized: approval replies bypass Auto, while a failed
  // keep-local decision stops the send instead of silently using the currently selected cloud model.
  async beforeSend(message, route, isApproval = false, taskFlags = {}) {
    if (isApproval || !route || !auto.enabled()) return false;
    const result = await auto.pick(message, taskFlags);
    if (result.blocked) {
      try {
        if (window.showToast) window.showToast(result.message);
        else if (typeof window.alert === 'function') window.alert(result.message);
      } catch (_) { /* a notification failure must not fall through to a cloud send */ }
      return true;
    }
    if (result.route) Object.assign(route, result.route, { source: 'auto' });
    return false;
  },
};

// shared pool store
const poolStore = {
  data: null,
  async load() { this.data = await api('/api/auto/pool'); return this.data; },
  async save(pool, settings) { const r = await api('/api/auto/pool', { method: 'PUT', json: { pool, settings } }); await this.load(); return r; },
};
const labelFor = (e) => `${e.label || e.model}  [${e.local ? 'offline' : 'cloud'}${e.free ? ', free' : ''}]`;

// --------------------------------------------------------------------------- styles
function injectCss() {
  if (document.getElementById('odysseus-hub-css')) return;
  const css = `
.hub-content{width:min(860px,94vw);max-height:88vh;display:flex;flex-direction:column;color:var(--fg)}
.hub-content .hidden{display:none !important}
.hub-tabs{display:flex;gap:4px;padding:0 14px;border-bottom:1px solid var(--border)}
.hub-tab{background:none;border:0;border-bottom:2px solid transparent;color:var(--fg-muted);padding:8px 12px;cursor:pointer;font:inherit}
.hub-tab.active{color:var(--fg);border-bottom-color:var(--accent)}
.hub-body{overflow:auto;padding:14px 16px;flex:1}
.hub-row{display:flex;flex-direction:column;gap:4px;margin-bottom:10px}
.hub-row>label,.hub-label{font-size:.85em;color:var(--fg-muted)}
.hub-inline{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px}
.hub-input{width:100%;box-sizing:border-box;padding:7px 9px;border-radius:6px;border:1px solid var(--border);background:var(--panel);color:var(--fg);font:inherit}
select.hub-input{width:auto;min-width:160px;max-width:100%}
textarea.hub-input{min-height:84px;resize:vertical}
.hub-btn{padding:7px 12px;border-radius:6px;border:1px solid var(--border);background:var(--panel);color:var(--fg);cursor:pointer;font:inherit}
.hub-btn.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
.hub-btn:disabled{opacity:.5;cursor:default}
.hub-note,.hub-status{font-size:.85em;color:var(--fg-muted);margin:4px 0}
.hub-status.err{color:var(--color-error,var(--red))}
.hub-status.ok{color:var(--fg)}
.hub-link{font-size:.85em;color:var(--accent)}
.hub-list{border:1px solid var(--border);border-radius:6px;max-height:300px;overflow:auto;margin:8px 0}
.hub-model{display:flex;gap:8px;align-items:center;padding:5px 8px;border-bottom:1px solid var(--border);cursor:pointer;flex-wrap:wrap}
.hub-model:last-child{border-bottom:0}
.hub-model-name{font-weight:500}
.hub-model-id{font-size:.8em;color:var(--fg-muted)}
.hub-badge{font-size:.72em;padding:1px 6px;border-radius:9px;border:1px solid var(--border);color:var(--fg-muted)}
.hub-badge.free{color:var(--accent);border-color:var(--accent)}
.hub-badge.local{color:var(--fg);background:var(--panel)}
.hub-card{border:1px solid var(--border);border-radius:8px;padding:8px 10px;margin:8px 0;background:var(--panel)}
.hub-card summary{cursor:pointer;font-weight:500}
.hub-card.final{border-color:var(--accent)}
.hub-pre{white-space:pre-wrap;word-break:break-word;margin:6px 0 0;font:inherit}
.hub-members .hub-inline select{flex:1}
`;
  document.head.append(h('style', { id: 'odysseus-hub-css' }, css));
}

// --------------------------------------------------------------------------- Connect tab
function connectPane() {
  const st = { presets: [], preset: null, discovery: null, selected: new Set(), userPickedProvider: false, keyUsedForProvider: '' };
  const provSel = h('select', { class: 'hub-input', 'aria-label': 'Provider' });
  const keyInput = h('input', { class: 'hub-input', type: 'password', autocomplete: 'off', spellcheck: 'false', placeholder: 'Paste your API key', 'aria-label': 'API key' });
  const urlInput = h('input', { class: 'hub-input', type: 'text', placeholder: 'http://host:port/v1', 'aria-label': 'Base URL' });
  const urlRow = h('div', { class: 'hub-row hidden' }, h('label', {}, 'Base URL (OpenAI-compatible)'), urlInput);
  const keyRow = h('div', { class: 'hub-row' }, h('label', {}, 'API key'), keyInput);
  const keyLink = h('a', { href: '#', target: '_blank', rel: 'noopener noreferrer', class: 'hub-link hidden' }, 'Get a key');
  const note = h('div', { class: 'hub-note' });
  const fetchBtn = h('button', { class: 'hub-btn primary', type: 'button' }, 'Fetch models');
  const status = h('div', { class: 'hub-status', role: 'status' });
  const search = h('input', { class: 'hub-input', type: 'search', placeholder: 'Search models', 'aria-label': 'Search models' });
  const freeOnly = h('input', { type: 'checkbox', 'aria-label': 'Free only' });
  const freeLabel = h('label', { class: 'hidden' }, freeOnly, ' Free only');
  const listBox = h('div', { class: 'hub-list' });
  const count = h('span', { class: 'hub-note' });
  const selShown = h('button', { class: 'hub-btn', type: 'button' }, 'Select shown');
  const selFree = h('button', { class: 'hub-btn hidden', type: 'button' }, 'Select all free');
  const selNone = h('button', { class: 'hub-btn', type: 'button' }, 'Clear');
  const addPool = h('input', { type: 'checkbox', checked: true, 'aria-label': 'Add to Auto pool' });
  const connectBtn = h('button', { class: 'hub-btn primary', type: 'button', disabled: true }, 'Connect');
  const result = h('div', { class: 'hub-status', role: 'status' });
  const modelsBox = h('div', { class: 'hidden' },
    h('div', { class: 'hub-inline' }, search, freeLabel, selShown, selFree, selNone, count), listBox,
    h('div', { class: 'hub-inline' }, h('label', {}, addPool, ' Also add to the Auto pool'), connectBtn));

  const say = (el, text, cls = '') => { el.textContent = text; el.className = `hub-status ${cls}`.trim(); };
  let fetchGeneration = 0;

  function applyPreset() {
    fetchGeneration += 1; // discard any in-flight response for the previous provider
    fetchBtn.disabled = false;
    const p = st.presets.find((x) => x.id === provSel.value) || null;
    st.preset = p;
    st.discovery = null; st.selected = new Set();
    modelsBox.classList.add('hidden');
    say(result, '');
    updateCount();
    if (!p) return;
    const showUrl = p.id === 'custom' || p.local;
    urlRow.classList.toggle('hidden', !showUrl);
    urlInput.value = p.local ? p.base_url : '';
    keyRow.classList.toggle('hidden', !p.needs_key && p.local);
    keyInput.placeholder = p.needs_key ? 'Paste your API key' : 'API key (optional)';
    keyLink.classList.toggle('hidden', !p.key_url);
    if (p.key_url) keyLink.href = p.key_url;
    note.textContent = p.note || '';
    say(status, '');
  }

  function updateCount() {
    const total = st.discovery ? st.discovery.models.length : 0;
    count.textContent = `${st.selected.size} selected of ${total}`;
    connectBtn.disabled = st.selected.size === 0;
    connectBtn.textContent = st.selected.size ? `Connect ${st.selected.size} model${st.selected.size === 1 ? '' : 's'}` : 'Connect';
  }

  function invalidateDiscovery() {
    fetchGeneration += 1;
    st.discovery = null;
    st.selected = new Set();
    modelsBox.classList.add('hidden');
    updateCount();
  }

  const badge = (text, cls = '') => h('span', { class: `hub-badge ${cls}`.trim() }, text);
  function renderList() {
    listBox.textContent = '';
    const all = st.discovery ? st.discovery.models : [];
    const shown = filterModels(all, { query: search.value, freeOnly: freeOnly.checked });
    for (const m of shown.slice(0, 200)) {
      const cb = h('input', { type: 'checkbox', checked: st.selected.has(m.id), 'aria-label': `Select ${m.id}` });
      cb.addEventListener('change', () => { if (cb.checked) st.selected.add(m.id); else st.selected.delete(m.id); updateCount(); });
      listBox.append(h('label', { class: 'hub-model', title: m.id }, cb, h('span', { class: 'hub-model-name' }, m.name || m.id),
        m.name && m.name !== m.id ? h('span', { class: 'hub-model-id' }, m.id) : null,
        m.free === true ? badge('free', 'free') : null, m.local ? badge('offline', 'local') : null,
        m.vision ? badge('vision') : null, m.tools ? badge('tools') : null, m.reasoning ? badge('reasoning') : null,
        m.context_length ? badge(formatCtx(m.context_length)) : null));
    }
    if (shown.length > 200) listBox.append(h('div', { class: 'hub-note' }, `Showing the first 200 of ${shown.length}. Type in the search box to narrow it down.`));
    if (!shown.length) listBox.append(h('div', { class: 'hub-note' }, 'No models match.'));
    updateCount();
  }

  async function fetchModels() {
    const preset = st.preset;
    if (!preset) return;
    const apiKey = keyInput.value.trim();
    const baseUrl = urlInput.value.trim();
    if (apiKey) st.keyUsedForProvider = preset.id;
    const generation = ++fetchGeneration;
    fetchBtn.disabled = true; say(status, 'Fetching models…'); modelsBox.classList.add('hidden'); say(result, '');
    st.discovery = null; st.selected = new Set(); updateCount();
    try {
      const d = await api('/api/providers/models', { method: 'POST', json: { provider: preset.id, api_key: apiKey, base_url: baseUrl } });
      // Provider/key/URL can change while the request is in flight. Never show stale models
      // or allow them to be connected with a different provider's credentials.
      if (generation !== fetchGeneration || st.preset?.id !== preset.id || keyInput.value.trim() !== apiKey || urlInput.value.trim() !== baseUrl) return;
      st.discovery = d; st.selected = new Set();
      // Small catalogs: tick everything. Big ones (OpenRouter): the user chooses.
      if (d.models.length <= 15) d.models.forEach((m) => st.selected.add(m.id));
      freeLabel.classList.toggle('hidden', !d.free_count); selFree.classList.toggle('hidden', !d.free_count);
      freeOnly.checked = false; search.value = '';
      const extra = [];
      if (d.key_info && d.key_info.is_free_tier === true) extra.push('free-tier key');
      if (d.free_count) extra.push(`${d.free_count} free`);
      say(status, `${d.label}: ${d.count} model${d.count === 1 ? '' : 's'}${extra.length ? ` (${extra.join(', ')})` : ''}.`, 'ok');
      modelsBox.classList.remove('hidden'); renderList();
    } catch (err) {
      if (generation === fetchGeneration) say(status, err.message, 'err');
    } finally {
      if (generation === fetchGeneration) fetchBtn.disabled = false;
    }
  }

  async function connect() {
    const p = st.preset; const d = st.discovery; const ids = [...st.selected];
    if (!p || !d || !ids.length) return;
    const generation = fetchGeneration;
    const apiKey = keyInput.value.trim();
    const addToPool = addPool.checked;
    connectBtn.disabled = true; say(result, 'Connecting…');
    try {
      const form = new FormData();
      form.append('name', p.label.replace(/\s*\(local\)$/, ''));
      form.append('base_url', d.base_url);
      form.append('api_key', apiKey);
      form.append('endpoint_kind', d.local ? 'local' : (p.id === 'custom' ? 'auto' : 'api'));
      form.append('pinned_models', JSON.stringify(ids));
      form.append('require_models', 'false');
      const ep = await api('/api/model-endpoints', { method: 'POST', form });
      let msg = `Connected ${p.label}: ${ids.length} model${ids.length === 1 ? '' : 's'} added to the model picker.`;
      if (addToPool) {
        const cur = await poolStore.load();
        const merged = mergePool(cur.pool, toPoolEntries(ep.id, d.models, ids), cur.max_pool || 60);
        await poolStore.save(merged.pool, cur.settings);
        msg += ` ${merged.added} added to the Auto pool${merged.skipped ? ` (${merged.skipped} skipped: pool is full)` : ''}.`;
      }
      if (generation === fetchGeneration && st.preset?.id === p.id && keyInput.value.trim() === apiKey) {
        keyInput.value = '';   // the key now lives, encrypted, on the server only
        st.keyUsedForProvider = '';
        st.selected.clear();
        st.discovery = null;
        modelsBox.classList.add('hidden');
        updateCount(); // require a fresh discovery before any subsequent save
      }
      try { if (window.modelsModule && window.modelsModule.refreshModels) await window.modelsModule.refreshModels(true); } catch (_) { /* picker refresh is best effort */ }
      say(result, msg, 'ok'); notify(`Connected ${p.label}`);
    } catch (err) { say(result, err.message, 'err'); } finally { updateCount(); }
  }

  let guessTimer = null;
  keyInput.addEventListener('input', () => {
    st.keyUsedForProvider = '';
    invalidateDiscovery();
    clearTimeout(guessTimer);
    const v = keyInput.value.trim();
    if (st.userPickedProvider || v.length < 6) return;
    guessTimer = setTimeout(async () => {
      try {
        const { candidates } = await api('/api/providers/guess', { method: 'POST', json: { api_key: v } });
        if (st.userPickedProvider || keyInput.value.trim() !== v) return;
        if (candidates.length === 1 && provSel.value !== candidates[0] && st.presets.some((p) => p.id === candidates[0])) { provSel.value = candidates[0]; applyPreset(); }
        else if (candidates.length > 1) note.textContent = `This key looks like one from: ${candidates.join(' or ')}. Pick the provider above.`;
      } catch (_) { /* guessing is a convenience only */ }
    }, 250);
  });
  urlInput.addEventListener('input', invalidateDiscovery);
  provSel.addEventListener('change', () => {
    st.userPickedProvider = true;
    clearTimeout(guessTimer);
    if (st.keyUsedForProvider && st.keyUsedForProvider !== provSel.value) keyInput.value = '';
    st.keyUsedForProvider = '';
    applyPreset();
  });
  fetchBtn.addEventListener('click', fetchModels);
  keyInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') fetchModels(); });
  search.addEventListener('input', renderList);
  freeOnly.addEventListener('change', renderList);
  selShown.addEventListener('click', () => { filterModels(st.discovery?.models, { query: search.value, freeOnly: freeOnly.checked }).slice(0, 200).forEach((m) => st.selected.add(m.id)); renderList(); });
  selFree.addEventListener('click', () => { (st.discovery?.models || []).filter((m) => m.free === true).forEach((m) => st.selected.add(m.id)); renderList(); });
  selNone.addEventListener('click', () => { st.selected.clear(); renderList(); });
  connectBtn.addEventListener('click', connect);

  const el = h('section', { class: 'hub-pane', dataset: { pane: 'connect' } },
    h('div', { class: 'hub-note' }, 'Pick a provider, paste its API key, and the available models are fetched for you. No URLs to copy.'),
    h('div', { class: 'hub-row' }, h('label', {}, 'Provider'), provSel), keyRow, urlRow,
    h('div', { class: 'hub-inline' }, fetchBtn, keyLink), note, status, modelsBox, result);

  return {
    el,
    async onShow() {
      if (st.presets.length) return;
      try {
        st.presets = (await api('/api/providers/presets')).presets;
        provSel.textContent = '';
        for (const p of st.presets) provSel.append(h('option', { value: p.id }, p.label));
        applyPreset();
      } catch (err) { say(status, `Could not load providers: ${err.message}`, 'err'); }
    },
  };
}

// --------------------------------------------------------------------------- Auto tab
function autoPane() {
  const enabled = h('input', { type: 'checkbox', checked: auto.enabled(), 'aria-label': 'Use Auto for new messages', dataset: { autoSetting: 'enabled' } });
  const keepLocal = h('input', { type: 'checkbox', checked: auto.keepLocal(), 'aria-label': 'Keep this machine only', dataset: { autoSetting: 'keepLocal' } });
  const routerSel = h('select', { class: 'hub-input', 'aria-label': 'Router model' });
  const defaultSel = h('select', { class: 'hub-input', 'aria-label': 'Default model' });
  const keepDefault = h('input', { type: 'checkbox', 'aria-label': 'Keep local by default' });
  const listBox = h('div', { class: 'hub-list' });
  const saveBtn = h('button', { class: 'hub-btn primary', type: 'button' }, 'Save pool');
  const status = h('div', { class: 'hub-status', role: 'status' });
  let pool = [];
  const say = (text, cls = '') => { status.textContent = text; status.className = `hub-status ${cls}`.trim(); };

  function fillSelect(sel, current, blank) {
    sel.textContent = '';
    sel.append(h('option', { value: '' }, blank));
    for (const e of pool) sel.append(h('option', { value: refOf(e) }, labelFor(e)));
    sel.value = pool.some((e) => refOf(e) === current) ? current : '';
  }

  function renderPool() {
    listBox.textContent = '';
    if (!pool.length) listBox.append(h('div', { class: 'hub-note' }, 'The pool is empty. Use the Connect tab and keep “Also add to the Auto pool” ticked.'));
    pool.forEach((e, i) => {
      const tags = h('input', { class: 'hub-input', type: 'text', value: (e.tags || []).join(', '), placeholder: 'tags: code, fast, reasoning', 'aria-label': `Tags for ${e.model}` });
      tags.addEventListener('change', () => { e.tags = tags.value.split(',').map((t) => t.trim()).filter(Boolean); });
      const rm = h('button', { class: 'hub-btn', type: 'button', 'aria-label': `Remove ${e.model}` }, 'Remove');
      rm.addEventListener('click', () => { pool.splice(i, 1); renderPool(); fillSelect(routerSel, routerSel.value, '(none: use pool order)'); fillSelect(defaultSel, defaultSel.value, '(first in pool)'); });
      listBox.append(h('div', { class: 'hub-model' }, h('span', { class: 'hub-model-name' }, e.label || e.model),
        h('span', { class: 'hub-model-id' }, e.endpoint_name || ''), h('span', { class: `hub-badge ${e.local ? 'local' : ''}` }, e.local ? 'offline' : 'cloud'),
        e.free ? h('span', { class: 'hub-badge free' }, 'free') : null, e.available === false ? h('span', { class: 'hub-badge' }, 'endpoint removed') : null, tags, rm));
    });
  }

  enabled.addEventListener('change', () => auto.setEnabled(enabled.checked));
  keepLocal.addEventListener('change', () => auto.setKeepLocal(keepLocal.checked));
  saveBtn.addEventListener('click', async () => {
    saveBtn.disabled = true;
    try {
      const r = await poolStore.save(pool, { router_ref: routerSel.value, default_ref: defaultSel.value, keep_local_default: keepDefault.checked });
      say(`Saved ${r.saved} model${r.saved === 1 ? '' : 's'}${r.dropped ? ` (${r.dropped} dropped)` : ''}.`, 'ok');
      await load();
    } catch (err) { say(err.message, 'err'); } finally { saveBtn.disabled = false; }
  });

  async function load() {
    try {
      const d = await poolStore.load();
      pool = d.pool.map((e) => ({ ...e }));
      fillSelect(routerSel, d.settings.router_ref, '(none: use pool order)');
      fillSelect(defaultSel, d.settings.default_ref, '(first in pool)');
      keepDefault.checked = !!d.settings.keep_local_default;
      enabled.checked = auto.enabled(); keepLocal.checked = auto.keepLocal();
      renderPool();
    } catch (err) { say(err.message, 'err'); }
  }

  const el = h('section', { class: 'hub-pane hidden', dataset: { pane: 'auto' } },
    h('div', { class: 'hub-note' }, 'Auto sends each message to the best model in your pool. A small router model (cloud or offline) makes the pick; if it is down, the default model is used.'),
    h('div', { class: 'hub-inline' }, h('label', {}, enabled, ' Use Auto for new messages'), h('label', {}, keepLocal, ' Keep-local: only offline models, and the router must be offline too')),
    h('div', { class: 'hub-row' }, h('label', {}, 'Router model'), routerSel),
    h('div', { class: 'hub-row' }, h('label', {}, 'Default model (when the router is unavailable)'), defaultSel),
    h('div', { class: 'hub-inline' }, h('label', {}, keepDefault, ' Keep-local by default for council runs')),
    listBox, h('div', { class: 'hub-inline' }, saveBtn), status);
  return { el, onShow: load };
}

// --------------------------------------------------------------------------- Council tab
const PERSONAS = [['', 'No persona'], ['researcher', 'Researcher'], ['logician', 'Logician'], ['contrarian', 'Contrarian'], ['builder', 'Builder']];
const MODES = [['debate', 'Debate: members revise after reading each other'], ['fanout', 'Fan-out: independent answers, chair merges'], ['verify', 'Verify: a worker drafts, the council reviews it']];

function councilPane() {
  let pool = [];
  let members = [];
  let abort = null;
  const modeSel = h('select', { class: 'hub-input', 'aria-label': 'Council mode' }, MODES.map(([v, t]) => h('option', { value: v }, t)));
  const rounds = h('select', { class: 'hub-input', 'aria-label': 'Rounds' }, [1, 2, 3].map((n) => h('option', { value: n, ...(n === 2 ? { selected: true } : {}) }, `${n} round${n > 1 ? 's' : ''}`)));
  const chairSel = h('select', { class: 'hub-input', 'aria-label': 'Chair model' });
  const workerSel = h('select', { class: 'hub-input', 'aria-label': 'Worker model' });
  const workerRow = h('div', { class: 'hub-row hidden' }, h('label', {}, 'Worker (drafts the answer the council will verify; an offline model is typical)'), workerSel);
  const skillSel = h('select', { class: 'hub-input', 'aria-label': 'Skill' }, h('option', { value: '' }, 'No skill'));
  const scopeSel = h('select', { class: 'hub-input', 'aria-label': 'Skill scope' }, h('option', { value: 'chair' }, 'Skill: chair only (final voice)'), h('option', { value: 'all' }, 'Skill: every member'));
  const keepLocal = h('input', { type: 'checkbox', 'aria-label': 'Keep local' });
  const question = h('textarea', { class: 'hub-input', placeholder: 'What should the council work on?', 'aria-label': 'Question' });
  const membersBox = h('div', { class: 'hub-members' });
  const addMember = h('button', { class: 'hub-btn', type: 'button' }, 'Add member');
  const estimate = h('div', { class: 'hub-note' });
  const runBtn = h('button', { class: 'hub-btn primary', type: 'button' }, 'Run council');
  const status = h('div', { class: 'hub-status', role: 'status' });
  const out = h('div', { class: 'hub-out' });
  const say = (text, cls = '') => { status.textContent = text; status.className = `hub-status ${cls}`.trim(); };
  const nameOf = (ref) => { const e = pool.find((x) => refOf(x) === ref); return e ? (e.label || e.model) : ref.split('::')[1] || ref; };

  function fill(sel, keep, blank) {
    sel.textContent = '';
    if (blank) sel.append(h('option', { value: '' }, blank));
    for (const e of pool) sel.append(h('option', { value: refOf(e) }, labelFor(e)));
    if (keep && pool.some((e) => refOf(e) === keep)) sel.value = keep;
  }

  function renderMembers() {
    membersBox.textContent = '';
    members.forEach((m, i) => {
      const ms = h('select', { class: 'hub-input', 'aria-label': `Member ${i + 1} model` });
      for (const e of pool) ms.append(h('option', { value: refOf(e) }, labelFor(e)));
      ms.value = m.ref; ms.addEventListener('change', () => { m.ref = ms.value; });
      const ps = h('select', { class: 'hub-input', 'aria-label': `Member ${i + 1} persona` }, PERSONAS.map(([v, t]) => h('option', { value: v }, t)));
      ps.value = m.persona; ps.addEventListener('change', () => { m.persona = ps.value; });
      const rm = h('button', { class: 'hub-btn', type: 'button', 'aria-label': `Remove member ${i + 1}` }, 'Remove');
      rm.addEventListener('click', () => { members.splice(i, 1); renderMembers(); refreshEstimate(); });
      membersBox.append(h('div', { class: 'hub-inline' }, ms, ps, rm));
    });
    addMember.disabled = members.length >= 8 || !pool.length;
  }

  let estTimer = null;
  function refreshEstimate() {
    clearTimeout(estTimer);
    estTimer = setTimeout(async () => {
      if (!members.length) { estimate.textContent = ''; return; }
      try {
        const p = await api('/api/council/plan', { method: 'POST', json: { mode: modeSel.value, members: members.length, rounds: Number(rounds.value) } });
        estimate.textContent = `About ${p.calls} model calls, roughly ${p.x_single_call}× the tokens of one answer (rough estimate).`;
      } catch (_) { estimate.textContent = ''; }
    }, 150);
  }

  function addCard(title, text, { open = false, cls = '', tag = '' } = {}) {
    const card = h('details', { class: `hub-card ${cls}`.trim(), ...(open ? { open: true } : {}) }, h('summary', {}, title, tag ? h('span', { class: 'hub-badge' }, tag) : null), h('pre', { class: 'hub-pre' }, text || ''));
    out.append(card); return card;
  }

  function onEvent(ev) {
    if (ev.type === 'start') {
      say(`${ev.mode} · ${ev.members.length} members · about ${ev.estimate.calls} calls`);
    } else if (ev.type === 'draft') {
      addCard(`Worker draft · ${nameOf(ev.ref)}`, ev.text, { open: true, tag: ev.ok ? '' : 'no draft' });
    } else if (ev.type === 'member') {
      const tag = ev.refused ? 'declined' : (!ev.ok ? `failed${ev.error ? ` (${ev.error})` : ''}` : '');
      addCard(`${ev.name} · round ${ev.round}`, ev.text || '(no answer)', { open: ev.round === 1 && ev.ok, tag });
    } else if (ev.type === 'chair') {
      const card = addCard('Final answer (chair)', ev.text, { open: true, cls: 'final', tag: ev.refused ? 'declined' : '' });
      const copy = h('button', { class: 'hub-btn', type: 'button' }, 'Copy');
      copy.addEventListener('click', async () => { try { await navigator.clipboard.writeText(ev.text); copy.textContent = 'Copied'; } catch (_) { copy.textContent = 'Copy failed'; } });
      card.append(copy);
    } else if (ev.type === 'error') {
      say(ev.message, 'err');
    } else if (ev.type === 'done') {
      say(`Done: ${ev.calls} calls, ${ev.answered} answered${ev.declined ? `, ${ev.declined} declined` : ''}${ev.failed ? `, ${ev.failed} failed` : ''}.`, 'ok');
    }
  }

  async function run() {
    if (abort) { abort.abort(); return; }                       // second click = Stop
    const q = question.value.trim();
    if (!q) { say('Type a question first.', 'err'); return; }
    if (!chairSel.value) { say('Pick a chair model.', 'err'); return; }
    if (!members.length) { say('Add at least one member.', 'err'); return; }
    if (modeSel.value === 'verify' && !workerSel.value) { say('Verify mode needs a worker model.', 'err'); return; }
    out.textContent = ''; say('Running…');
    abort = new AbortController(); runBtn.textContent = 'Stop';
    const body = { question: q, mode: modeSel.value, members: members.map((m) => ({ ref: m.ref, persona: m.persona || undefined })), chair: chairSel.value,
      rounds: Number(rounds.value), worker: modeSel.value === 'verify' ? workerSel.value : '', skill: skillSel.value, skill_scope: scopeSel.value, keep_local: keepLocal.checked };
    try {
      const res = await fetch('/api/council/run', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: abort.signal });
      if (!res.ok) { let d = null; try { d = await res.json(); } catch (_) { /* no body */ } throw new Error(typeof (d && d.detail) === 'string' ? d.detail : `HTTP ${res.status}`); }
      const reader = res.body.getReader(); const dec = new TextDecoder(); let buf = '';
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        const parsed = parseSseChunk(buf, dec.decode(value, { stream: true }));
        buf = parsed.rest; parsed.events.forEach(onEvent);
      }
    } catch (err) { if (err.name === 'AbortError') say('Stopped.'); else say(err.message, 'err'); }
    finally { abort = null; runBtn.textContent = 'Run council'; }
  }

  modeSel.addEventListener('change', () => { workerRow.classList.toggle('hidden', modeSel.value !== 'verify'); rounds.classList.toggle('hidden', modeSel.value !== 'debate'); refreshEstimate(); });
  rounds.addEventListener('change', refreshEstimate);
  addMember.addEventListener('click', () => { if (pool.length) { members.push({ ref: refOf(pool[members.length % pool.length]), persona: '' }); renderMembers(); refreshEstimate(); } });
  runBtn.addEventListener('click', run);

  const el = h('section', { class: 'hub-pane hidden', dataset: { pane: 'council' } },
    h('div', { class: 'hub-note' }, 'A council is separate calls, not one mind: each member is its own request, and the app pastes their answers into each other’s next prompt. The same model can sit in several seats, each with a different persona.'),
    h('div', { class: 'hub-label' }, 'Members'), membersBox, h('div', { class: 'hub-inline' }, addMember),
    h('div', { class: 'hub-inline' }, modeSel, rounds), workerRow,
    h('div', { class: 'hub-row' }, h('label', {}, 'Chair (writes the final answer; does not vote)'), chairSel),
    h('div', { class: 'hub-inline' }, skillSel, scopeSel, h('label', {}, keepLocal, ' Keep-local: offline models only')),
    question, estimate, h('div', { class: 'hub-inline' }, runBtn), status, out);

  return {
    el,
    onHide() { if (abort) abort.abort(); },
    async onShow() {
      try {
        const d = await poolStore.load();
        pool = d.pool.filter((e) => e.available !== false);
        fill(chairSel, chairSel.value, ''); fill(workerSel, workerSel.value, '(pick a worker)');
        if (!chairSel.value && pool.length) chairSel.value = refOf(pool[0]);
        const local = pool.find((e) => e.local); if (local && !workerSel.value) workerSel.value = refOf(local);
        keepLocal.checked = auto.keepLocal() || !!d.settings.keep_local_default;
        if (!members.length && pool.length) {
          const base = pool.slice(0, 3); const personas = ['researcher', 'logician', 'contrarian'];
          members = Array.from({ length: Math.max(3, base.length) }, (_, i) => ({ ref: refOf(base[i % base.length]), persona: personas[i] }));
        }
        members = members.filter((m) => pool.some((e) => refOf(e) === m.ref));
        renderMembers(); refreshEstimate();
        if (!pool.length) say('The pool is empty. Connect a provider first and keep “Also add to the Auto pool” ticked.', 'err');
        else if (status.className.includes('err')) say('');
      } catch (err) { say(err.message, 'err'); }
      try {
        const s = await api('/api/skills');
        const names = (s.skills || []).map((x) => x && x.name).filter(Boolean);
        const keep = skillSel.value;
        skillSel.textContent = ''; skillSel.append(h('option', { value: '' }, 'No skill'));
        for (const n of names) skillSel.append(h('option', { value: n }, n));
        skillSel.value = names.includes(keep) ? keep : '';
      } catch (_) { /* skills are optional */ }
    },
  };
}

// --------------------------------------------------------------------------- hub shell
let hub = null;
function ensureHub() {
  if (hub) return hub;
  injectCss();
  const panes = { connect: connectPane(), auto: autoPane(), council: councilPane() };
  const titles = { connect: 'Connect', auto: 'Auto pool', council: 'Council' };
  const btns = {};
  const root = h('div', { id: 'hub-modal', class: 'modal hidden' });
  const close = () => {
    for (const pane of Object.values(panes)) { try { if (pane.onHide) pane.onHide(); } catch (_) { /* closing must always work */ } }
    root.classList.add('hidden');
  };
  function show(id) {
    for (const [k, p] of Object.entries(panes)) { p.el.classList.toggle('hidden', k !== id); btns[k].classList.toggle('active', k === id); btns[k].setAttribute('aria-selected', String(k === id)); }
    panes[id].onShow();
  }
  for (const id of Object.keys(panes)) btns[id] = h('button', { class: 'hub-tab', type: 'button', role: 'tab', dataset: { tab: id }, onclick: () => show(id) }, titles[id]);
  root.append(h('div', { class: 'modal-content hub-content', role: 'dialog', 'aria-label': 'Providers, Auto and Council', style: 'background:var(--bg)' },
    h('div', { class: 'modal-header' }, h('h4', {}, 'Providers · Auto · Council'), h('button', { class: 'close-btn', type: 'button', 'aria-label': 'Close', onclick: close }, '✖')),
    h('div', { class: 'hub-tabs', role: 'tablist' }, Object.values(btns)),
    h('div', { class: 'modal-body hub-body' }, Object.values(panes).map((p) => p.el))));
  root.addEventListener('click', (e) => { if (e.target === root) close(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !root.classList.contains('hidden')) close(); });
  document.body.append(root);
  hub = { root, show, close, open(tab = 'connect') { root.classList.remove('hidden'); show(tab); } };
  return hub;
}

// --------------------------------------------------------------------------- entry points
function mountPickerControls() {
  const menu = document.getElementById('model-picker-menu');
  if (!menu || menu.querySelector('[data-hub-mounted]')) return;
  const addBtn = document.getElementById('model-picker-add-models-btn');
  if (addBtn) {
    const keyBtn = h('button', { type: 'button', class: 'model-picker-action-btn', id: 'model-picker-connect-btn', title: 'Connect a provider with an API key', 'aria-label': 'Connect a provider with an API key', dataset: { hubMounted: '1' } }, 'API key');
    keyBtn.addEventListener('click', (e) => { e.stopPropagation(); ensureHub().open('connect'); });
    addBtn.insertAdjacentElement('afterend', keyBtn);
  }
  const list = document.getElementById('model-picker-list');
  const enabled = h('input', { type: 'checkbox', checked: auto.enabled(), 'aria-label': 'Auto mode', dataset: { autoSetting: 'enabled' } });
  const keep = h('input', { type: 'checkbox', checked: auto.keepLocal(), 'aria-label': 'Keep local', dataset: { autoSetting: 'keepLocal' } });
  enabled.addEventListener('change', () => auto.setEnabled(enabled.checked));
  keep.addEventListener('change', () => auto.setKeepLocal(keep.checked));
  const poolBtn = h('button', { type: 'button', class: 'hub-btn', title: 'Edit the Auto pool' }, 'Pool');
  poolBtn.addEventListener('click', (e) => { e.stopPropagation(); ensureHub().open('auto'); });
  const councilBtn = h('button', { type: 'button', class: 'hub-btn', title: 'Open the council' }, 'Council');
  councilBtn.addEventListener('click', (e) => { e.stopPropagation(); ensureHub().open('council'); });
  const row = h('div', { class: 'hub-inline', style: 'padding:6px 10px;border-bottom:1px solid var(--border);font-size:.85em', dataset: { hubMounted: '1' } },
    h('label', { title: 'Let the router pick a model for each message' }, enabled, ' Auto'), h('label', { title: 'Offline models only' }, keep, ' Keep local'), poolBtn, councilBtn);
  if (list) list.insertAdjacentElement('beforebegin', row); else menu.append(row);
}

export function init() {
  injectCss();
  mountPickerControls();
}

if (typeof window !== 'undefined') {
  window.odysseusAuto = auto;
  window.odysseusHub = { open: (tab) => ensureHub().open(tab), close: () => hub && hub.close() };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
}
