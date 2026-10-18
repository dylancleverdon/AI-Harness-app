const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const api = async (path, opts = {}) => {
  const r = await fetch('/api' + path, { headers: { 'Content-Type': 'application/json', 'X-Harness': '1' }, ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined });
  if (!r.ok) throw new Error((await r.text()) || r.statusText);
  return (r.headers.get('content-type') || '').includes('json') ? r.json() : r.text();
};
const el = (tag, props = {}, ...kids) => { const e = Object.assign(document.createElement(tag), props); kids.forEach(k => e.append(k)); return e; };
const fmtTime = s => { const d = Math.floor(s / 86400), h = Math.floor(s % 86400 / 3600), m = Math.floor(s % 3600 / 60), x = s % 60, p = n => String(n).padStart(2, '0');
  return (d ? d + 'd ' : '') + (d || h ? h + ':' + p(m) : m) + ':' + p(x); };
const LEVEL_COLOR = { green: '#3ecf8e', yellow: '#f2c94c', orange: '#f2994a', red: '#eb5757' };

let state = { script: null, run: null, es: null, settings: {}, status: null, history: [] };

// ---- navigation ----------------------------------------------------------
$$('#rail button').forEach(b => b.onclick = () => {
  $$('#rail button').forEach(x => x.classList.toggle('active', x === b));
  $$('.page').forEach(p => p.classList.toggle('active', p.id === 'page-' + b.dataset.page));
  if (b.dataset.page === 'models') loadModels();
  if (b.dataset.page === 'reports') loadRuns();
  if (b.dataset.page === 'memory') drawChart();
});

// ---- status / telemetry --------------------------------------------------
async function refreshStatus() {
  const s = state.status = await api('/status');
  state.settings = s.settings;
  $('#version').textContent = s.version; setTimeout(updateTermUI, 0);
  $('#s-version').textContent = s.version;
  $('#scripts-dir').textContent = s.scripts_dir; $('#s-python').textContent = s.python; $('#s-pip').textContent = `${s.python} -m pip install <package>`; $('#rs-python').textContent = 'Runs with Python: ' + s.python;
  const lm = $('#lm-pill');
  lm.className = 'pill ' + (s.lmstudio.ok ? 'ok' : 'bad');
  const loaded = s.lmstudio.models.filter(m => m.loaded).length;
  $('#lm-text').textContent = s.lmstudio.ok ? `${loaded} loaded / ${s.lmstudio.models.length} models` : 'offline';
  lm.title = s.lmstudio.error || '';
  showUpdate(s.update);
  $$('[data-setting]').forEach(i => {
    const v = s.settings[i.dataset.setting];
    if (i.type === 'checkbox') i.checked = v; else if (document.activeElement !== i) i.value = v;
  });
}
function showUpdate(u) {
  const b = $('#update-btn'), a = $('#apply-update');
  if (u && u.available) {
    b.textContent = `⬆ Update available (${u.behind})`; b.classList.remove('hidden'); a.classList.remove('hidden');
    $('#s-update-msg').textContent = (u.changes || []).join(' · ');
  } else { b.classList.add('hidden'); a.classList.add('hidden'); $('#s-update-msg').textContent = u && u.error ? u.error : 'Up to date.'; }
}
$('#update-btn').onclick = () => $('#rail button[data-page=settings]').click();

let lastSnap = null, history = [];
function onTelemetry(d) {
  const m = d.memory; if (!m) return;
  lastSnap = m; history.push(m); if (history.length > 600) history.shift();
  const pill = $('#mem-pill');
  pill.className = 'pill lvl-' + m.level;
  $('#mem-text').textContent = `${m.level} · ${m.available_gb} GB free (${m.available_pct}%)`;
  const al = $('#alert');
  if (d.events.length && Date.now() / 1000 - d.events.at(-1).t < 30) {
    al.textContent = '🛑 ' + d.events.at(-1).msg; al.className = d.events.at(-1).level === 'red' ? 'red' : '';
  } else if (m.level === 'orange' || m.level === 'red') {
    al.textContent = `⚠ Memory is ${m.level}: ${m.available_gb} GB free, swap ${m.swap_used_gb} GB.` +
      (state.settings.guard_enabled ? ' Guard is armed.' : ' Guard is OFF.'); al.className = m.level === 'red' ? 'red' : '';
  } else al.className = 'hidden';
  $('#m-avail').textContent = m.available_gb + ' GB'; $('#m-avail-sub').textContent = m.available_pct + '% free';
  $('#m-used').textContent = m.used_gb + ' GB'; $('#m-total').textContent = 'of ' + m.total_gb + ' GB';
  $('#m-swap').textContent = m.swap_used_gb + ' GB'; $('#m-swap-sub').textContent = 'of ' + m.swap_total_gb + ' GB';
  $('#m-lms').textContent = m.lmstudio_gb + ' GB';
  const lv = $('#m-level'); lv.textContent = m.level; lv.style.color = LEVEL_COLOR[m.level];
  $('#m-pressure').textContent = m.pressure ? 'macOS pressure: ' + ({ 1: 'normal', 2: 'warn', 4: 'critical' }[m.pressure] || m.pressure) : '';
  const act = $('#active-runs'); act.replaceChildren();
  if (!d.active.length) act.textContent = 'Nothing running.';
  d.active.forEach(r => act.append(el('div', { textContent: `${r.script} — running ${fmtTime(r.elapsed)} · ${r.rss_mb} MB now, peak ${r.peak_mb} MB` })));
  updateTimers(d);
  $('#guard-state').textContent = state.settings.guard_enabled ? `Armed: stops scripts at ${state.settings.guard_trip_level}.` : 'Guard is disabled.';
  const ev = $('#guard-events'); ev.replaceChildren();
  d.events.slice().reverse().forEach(e => ev.append(el('li', { textContent: new Date(e.t * 1000).toLocaleTimeString() + ' — ' + e.msg })));
  const cur = d.active.find(r => state.run && r.id === state.run.id);
  $('#run-mem').textContent = cur ? `script: ${cur.rss_mb} MB (peak ${cur.peak_mb}) · system: ${m.available_pct}% free` : '';
  if ($('#page-memory').classList.contains('active')) drawChart();
}
function updateTimers(d) {
  const by = Object.fromEntries(d.active.map(r => [r.script, r]));
  $$('#script-list li').forEach(li => {
    const r = by[li.dataset.name]; li.classList.toggle('running', !!r);
    $('.timer', li).textContent = r ? '⏱ ' + fmtTime(r.elapsed) : '';
  });
  const cur = state.run && d.active.find(r => r.id === state.run.id);
  $('#run-timer').textContent = cur ? '⏱ ' + fmtTime(cur.elapsed) : $('#run-timer').textContent;
  $('#awake-switch').classList.toggle('live', !!d.awake);
  $('#awake-switch').title = (d.awake ? 'Mac is being kept awake right now. ' : '') + 'Keep your Mac awake while a script is running (uses macOS caffeinate). Closing the lid on battery power will still sleep it.';
}
function drawChart() {
  const c = $('#chart'), dpr = devicePixelRatio || 1, w = c.clientWidth, h = 220;
  c.width = w * dpr; c.height = h * dpr; const g = c.getContext('2d'); g.scale(dpr, dpr);
  const s = state.settings, bands = [[0, s.red_below_pct, 'red'], [s.red_below_pct, s.orange_below_pct, 'orange'],
    [s.orange_below_pct, s.yellow_below_pct, 'yellow'], [s.yellow_below_pct, 100, 'green']];
  const y = p => h - 18 - (p / 100) * (h - 28);
  bands.forEach(([lo, hi, l]) => { g.fillStyle = LEVEL_COLOR[l] + '1a'; g.fillRect(0, y(hi), w, y(lo) - y(hi)); });
  g.setLineDash([4, 4]); g.strokeStyle = '#555'; g.fillStyle = '#8b8b96'; g.font = '10px sans-serif';
  [s.red_below_pct, s.orange_below_pct, s.yellow_below_pct].forEach(p => { g.beginPath(); g.moveTo(0, y(p)); g.lineTo(w, y(p)); g.stroke(); g.fillText(p + '%', 4, y(p) - 2); });
  g.setLineDash([]);
  if (history.length < 2) return;
  g.lineWidth = 2; const step = w / 599, off = 600 - history.length;
  for (let i = 1; i < history.length; i++) {
    g.strokeStyle = LEVEL_COLOR[history[i].level];
    g.beginPath(); g.moveTo((off + i - 1) * step, y(history[i - 1].available_pct)); g.lineTo((off + i) * step, y(history[i].available_pct)); g.stroke();
  }
}
function connectTelemetry() {
  const es = new EventSource('/api/stream');
  es.onmessage = e => onTelemetry(JSON.parse(e.data));
  es.onerror = () => { es.close(); setTimeout(connectTelemetry, 2000); };
}

// ---- scripts -------------------------------------------------------------
async function loadScripts(select) {
  const names = await api('/scripts'); const ul = $('#script-list'); ul.replaceChildren();
  names.forEach(n => {
    const li = el('li', { className: n === state.script ? 'sel' : '' }, el('span', { className: 'name', textContent: n }), el('span', { className: 'timer' }));
    li.dataset.name = n;
    const del = el('small', { textContent: '✕', title: 'Delete' });
    del.onclick = async ev => { ev.stopPropagation(); if (confirm('Delete ' + n + '?')) { await api('/scripts/' + n, { method: 'DELETE' }); if (state.script === n) state.script = null; loadScripts(); } };
    li.append(del); li.onclick = () => openScript(n); ul.append(li);
  });
  if (select) openScript(select); else if (!state.script && names.length) openScript(names[0]);
}
async function openScript(n) {
  state.script = n; $('#script-name').textContent = n;
  $('#editor').value = (await api('/scripts/' + n)).content; loadRunSettings(n);
  $$('#script-list li').forEach(li => li.classList.toggle('sel', li.firstChild.textContent === n));
}
async function saveScript() { if (state.script) { await api('/scripts/' + state.script, { method: 'PUT', body: { content: $('#editor').value } }); loadRunSettings(state.script); } }
$('#save-btn').onclick = saveScript;
$('#editor').addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 's') { e.preventDefault(); saveScript(); }
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); $('#run-btn').click(); }
  if (e.key === 'Tab') { e.preventDefault(); document.execCommand('insertText', false, '    '); }
});
$('#new-script').onclick = async () => {
  let n = prompt('Script name (e.g. my_agent.py)'); if (!n) return; if (!n.endsWith('.py')) n += '.py';
  await api('/scripts/' + n, { method: 'PUT', body: { content: '# New script\nimport os\nfrom openai import OpenAI\n\nclient = OpenAI()  # already pointed at LM Studio\nprint(client.models.list())\n' } });
  loadScripts(n);
};

// ---- import (drag & drop) ----------------------------------------------
const modal = $('#import-modal'), zone = $('#dropzone');
const openImport = () => { $('#import-results').replaceChildren(); modal.classList.remove('hidden'); };
$('#import-script').onclick = openImport;
$('#import-close').onclick = () => modal.classList.add('hidden');
modal.onclick = e => { if (e.target === modal) modal.classList.add('hidden'); };
$('#pick-files').onclick = () => $('#file-input').click();
$('#file-input').onchange = e => { importFiles([...e.target.files]); e.target.value = ''; };
['dragenter', 'dragover'].forEach(t => zone.addEventListener(t, e => { e.preventDefault(); zone.classList.add('over'); }));
['dragleave', 'drop'].forEach(t => zone.addEventListener(t, e => { e.preventDefault(); zone.classList.remove('over'); }));
zone.addEventListener('drop', e => importFiles([...e.dataTransfer.files]));
// Dropping files anywhere on the window opens the importer; the modal handles the drop itself.
window.addEventListener('dragover', e => e.preventDefault());
window.addEventListener('drop', e => { e.preventDefault(); if (!modal.contains(e.target) && e.dataTransfer.files.length) { openImport(); importFiles([...e.dataTransfer.files]); } });
async function importFiles(files) {
  const out = $('#import-results'); let last = null; const existing = await api('/scripts');
  for (const f of files) {
    const li = el('li'); out.append(li);
    if (!f.name.endsWith('.py')) { li.className = 'bad-t'; li.textContent = `✕ ${f.name}: only .py files`; continue; }
    if (existing.includes(f.name) && !confirm(`${f.name} already exists. Overwrite it?`)) { li.textContent = `– ${f.name}: skipped`; continue; }
    try { await api('/scripts/' + f.name, { method: 'PUT', body: { content: await f.text() } }); li.className = 'ok-t'; li.textContent = `✓ ${f.name} imported`; last = f.name; }
    catch (e) { li.className = 'bad-t'; li.textContent = `✕ ${f.name}: ${e.message}`; }
  }
  if (last) { await loadScripts(last); $('#rail button[data-page=run]').click(); }
}

// ---- console input: type into a running script, or run a shell command --------
const term = { hist: [], i: 0 };
try { term.hist = JSON.parse(localStorage.getItem('termHist') || '[]'); } catch { }
const isRunning = () => $('#run-state').classList.contains('running');
function updateTermUI() {
  $('#eof-btn').classList.toggle('hidden', !isRunning());
  $('#term-input').placeholder = isRunning() ? 'Type here to answer the running script (Enter to send)…' : 'Type a shell command (cd, ls, python, pip…)';
  $('#term-prompt').textContent = isRunning() ? '›' : ((state.status?.term_cwd || '~').replace(/^.*\/AIHarness/, '~/AIHarness') + ' $');
}
$('#term-form').onsubmit = async e => {
  e.preventDefault(); const t = $('#term-input').value; if (!t.trim() && !isRunning()) return;
  $('#term-input').value = '';
  if (t.trim()) { term.hist = [...term.hist.filter(x => x !== t), t].slice(-100); term.i = term.hist.length; try { localStorage.setItem('termHist', JSON.stringify(term.hist)); } catch { } }
  try {
    if (isRunning()) { await api(`/runs/${state.run.id}/input`, { method: 'POST', body: { text: t } }); return; }
    const r = await api('/terminal', { method: 'POST', body: { command: t } });
    if (r.run) {
      state.run = r.run; $('#files').classList.add('hidden'); $('#diagnosis').replaceChildren();
      appendLine({ s: 'sys', x: '' }); setRunState('running'); watchRun(r.run.id); $('#run-timer').textContent = '⏱ 0:00';
    } else {
      appendLine({ s: r.cd ? 'sys' : 'err', x: r.cd ? '$ ' + t + '\n' + r.message : r.message }); if (state.status) state.status.term_cwd = r.cwd; updateTermUI();
    }
  } catch (err) { appendLine({ s: 'err', x: err.message }); }
};
$('#term-input').onkeydown = e => {
  if (e.key === 'ArrowUp' && term.i > 0) { e.preventDefault(); $('#term-input').value = term.hist[--term.i]; }
  if (e.key === 'ArrowDown') { e.preventDefault(); term.i = Math.min(term.i + 1, term.hist.length); $('#term-input').value = term.hist[term.i] || ''; }
  if (e.key === 'd' && e.ctrlKey && isRunning() && !$('#term-input').value) { e.preventDefault(); $('#eof-btn').click(); }
};
$('#eof-btn').onclick = () => state.run && api(`/runs/${state.run.id}/input`, { method: 'POST', body: { eof: true } });

// ---- run settings (discovered options, remembered between runs) -----------
let rs = { params: [], values: {} }, rsTimer;
const flagName = p => p.flags.find(f => f.startsWith('--')) || p.flags[0];
async function loadRunSettings(name) {
  const box = $('#run-settings'); let d;
  try { d = await api('/script-settings/' + name); } catch { box.classList.add('hidden'); return; }
  rs = { params: d.params, values: { ...d.values } };
  $('#rs-extra').value = d.extra || ''; $('#rs-env').value = d.env || '';
  const form = $('#rs-form'); form.replaceChildren();
  d.params.forEach(p => {
    const cur = p.dest in rs.values ? rs.values[p.dest] : p.default;
    const label = el('label', { className: p.kind === 'bool' ? 'check' : '' });
    let input;
    if (p.kind === 'bool') { input = el('input', { type: 'checkbox', checked: !!cur }); label.append(input, p.dest.replace(/_/g, ' ')); }
    else {
      if (p.kind === 'append') input = el('textarea', { rows: 2, value: Array.isArray(cur) ? cur.join('\n') : (cur ?? ''), placeholder: 'one value per line' });
      else if (p.choices) input = el('select', {}, ...p.choices.map(c => el('option', { value: c, textContent: c, selected: String(c) === String(cur) })));
      else input = el('input', { type: p.kind === 'int' || p.kind === 'float' || p.kind === 'count' ? 'number' : 'text', value: cur ?? '', placeholder: p.default == null ? (p.required ? 'required' : '') : '', step: p.kind === 'float' ? 'any' : undefined });
      label.append(p.dest.replace(/_/g, ' ') + (p.required ? ' *' : ''), input);
    }
    if (p.path && p.kind === 'str' && !p.choices) {  // Browse… buttons for file/folder options
      const row = el('div', { className: 'pathrow' }); input.after && null; label.removeChild(input); row.append(input);
      [['📁', 'folder', 'Choose a folder'], ['📄', 'file', 'Choose a file']].forEach(([icon, kind, tip]) => {
        const b = el('button', { type: 'button', textContent: icon, title: tip, className: 'ghost' });
        b.onclick = async () => {
          try { const r = await api('/pick', { method: 'POST', body: { kind, start: input.value } });
            if (r.path) { input.value = r.path; input.dispatchEvent(new Event('change')); } }
          catch (e) { alert(e.message.includes('macOS') ? 'The picker only works on macOS. Type the path instead.' : e.message); }
        }; row.append(b);
      }); label.append(row);
    }
    if (p.help) label.append(el('small', { textContent: p.help }));
    input.onchange = () => { rs.values[p.dest] = p.kind === 'bool' ? input.checked : (p.kind === 'int' || p.kind === 'count') && input.value !== '' ? parseInt(input.value) : p.kind === 'float' && input.value !== '' ? parseFloat(input.value) : input.value; persistRunSettings(); };
    form.append(label);
  });
  box.classList.remove('hidden'); box.open = box.open || d.params.length > 0 && !box.dataset.touched;
  $('#rs-summary').textContent = d.params.length ? `· ${d.params.length} option(s) found, last values remembered` : '· no options detected in this script';
}
$('#run-settings').addEventListener('toggle', e => e.target.dataset.touched = 1);
function persistRunSettings() { clearTimeout(rsTimer); rsTimer = setTimeout(() => state.script && api('/script-settings/' + state.script, { method: 'PUT', body: { values: rs.values, extra: $('#rs-extra').value, env: $('#rs-env').value } }), 300); }
$('#pkg-btn').onclick = async () => {
  const pkg = $('#pkg-input').value.trim(), log = $('#pkg-log'); if (!pkg) return;
  $('#pkg-btn').disabled = true; $('#pkg-btn').textContent = 'Installing…'; log.classList.remove('hidden'); log.textContent = 'pip install ' + pkg + ' …';
  try { const r = await api('/pip', { method: 'POST', body: { package: pkg } }); log.textContent = (r.ok ? '✓ Installed into ' : '✕ Failed for ') + r.python + '\n\n' + r.log; if (r.ok) $('#pkg-input').value = ''; }
  catch (e) { log.textContent = '✕ ' + e.message; }
  $('#pkg-btn').disabled = false; $('#pkg-btn').textContent = 'Install';
};
$('#pkg-input').onkeydown = e => { if (e.key === 'Enter') $('#pkg-btn').click(); };
$('#rs-extra').oninput = $('#rs-env').oninput = persistRunSettings;
$('#rs-reset').onclick = () => { rs.values = {}; persistRunSettings(); setTimeout(() => loadRunSettings(state.script), 500); };
const runBody = () => ({ script: state.script, values: rs.values, extra: $('#rs-extra').value, env: $('#rs-env').value });

// ---- files a run produced -------------------------------------------------
function showFiles(runId, files, box, total) {
  box.replaceChildren(); box.classList.toggle('hidden', !files || !files.length); if (!files || !files.length) return;
  box.append(el('b', { textContent: `Files created or changed (${total || files.length})` + ((total || files.length) > 50 ? ` — showing the first 50` : '') }));
  files.slice(0, 50).forEach(f => {
    const row = el('div', { className: 'file' }, el('span', { className: 'tag' + (f.status === 'new' ? '' : ' off'), textContent: f.status }), el('code', { textContent: f.path, title: f.path }), el('small', { className: 'muted', textContent: (f.size / 1024).toFixed(1) + ' KB' }));
    const view = el('button', { textContent: 'Preview' }); view.onclick = async () => { const t = await api(`/run-file?run=${runId}&path=${encodeURIComponent(f.path)}`); const w = el('pre', { className: 'report', textContent: t }); row.after(w); view.disabled = true; };
    const rev = el('button', { textContent: 'Show in Finder' }); rev.onclick = () => api('/reveal', { method: 'POST', body: { run: runId, path: f.path } });
    row.append(view, rev); box.append(row);
  });
}

// ---- AI edit -------------------------------------------------------------
const aim = $('#ai-modal'); let aiResult = null, aiAbort = null, aiReview = null;
$('#ai-btn').onclick = async () => {
  if (!state.script) return;
  $('#ai-name').textContent = state.script; $('#ai-diff').classList.add('hidden'); $('#ai-apply').classList.add('hidden'); $('#ai-status').textContent = '';
  const ms = (await api('/status')).lmstudio; const sel = $('#ai-model'); sel.replaceChildren(el('option', { value: '', textContent: 'Whatever is loaded' }));
  ms.models.filter(m => m.type !== 'embeddings').forEach(m => sel.append(el('option', { value: m.id, textContent: m.id + (m.loaded ? ' (loaded)' : '') })));
  if (!ms.ok) $('#ai-status').textContent = '⚠ LM Studio server not reachable. Start it in the Developer tab.';
  aim.classList.remove('hidden'); $('#ai-instr').focus();
};
$('#ai-close').onclick = () => { aiAbort && aiAbort.abort(); aim.classList.add('hidden'); };
$('#ai-cancel').onclick = () => aiAbort && aiAbort.abort();
function renderDiff(text) {
  const box = $('#ai-diff'); box.replaceChildren();
  text.split('\n').forEach(l => { if (l === '') return; const c = l.startsWith('+++') || l.startsWith('---') ? 'hunk' : l.startsWith('@@') ? 'hunk' : l[0] === '+' ? 'add' : l[0] === '-' ? 'del' : ''; box.append(el('span', { className: c, textContent: l + '\n' })); });
  box.classList.remove('hidden');
}
$('#ai-go').onclick = async () => {
  const instruction = $('#ai-instr').value.trim(); if (!instruction) { $('#ai-instr').focus(); return; }
  const original = $('#editor').value; aiResult = null; aiReview = null; $('#ai-review-btns').classList.add('hidden'); aiAbort = new AbortController();
  $('#ai-go').classList.add('hidden'); $('#ai-cancel').classList.remove('hidden'); $('#ai-apply').classList.add('hidden'); $('#ai-diff').classList.add('hidden'); $('#ai-status').textContent = 'Starting…';
  try {
    const r = await fetch('/api/ai-edit', { method: 'POST', signal: aiAbort.signal, headers: { 'Content-Type': 'application/json', 'X-Harness': '1' },
      body: JSON.stringify({ name: state.script, content: original, instruction, model: $('#ai-model').value, mode: $('#ai-mode').value }) });
    const rd = r.body.getReader(), dec = new TextDecoder(); let buf = '';
    for (;;) {
      const { done, value } = await rd.read(); if (done) break; buf += dec.decode(value, { stream: true });
      const parts = buf.split('\n\n'); buf = parts.pop();
      for (const p of parts) {
        if (!p.startsWith('data: ')) continue; const ev = JSON.parse(p.slice(6));
        if (ev.type === 'info') $('#ai-status').textContent = `${ev.model} · context ${ev.context} · ${ev.chunks} section(s)`;
        else if (ev.type === 'progress') $('#ai-status').textContent = `Section ${ev.chunk}/${ev.chunks}…` + (ev.stats ? ` ${ev.stats.applied} edit(s) applied so far` : '');
        else if (ev.type === 'error') $('#ai-status').textContent = '✕ ' + ev.message;
        else if (ev.type === 'done') {
          aiResult = ev.edited; aiReview = ev.review; $('#ai-review-btns').classList.remove('hidden');
          const st = ev.stats ? ` Applied ${ev.stats.applied}, skipped ${ev.stats.not_found} (text not found), rejected ${ev.stats.broke} (would break the file).` : '';
          $('#ai-status').textContent = (ev.changed ? 'Review the changes below.' : 'The model made no changes.') + st + (ev.notes.length ? ' Notes: ' + [...new Set(ev.notes)].join('; ') : '') + (ev.review_path ? ' Review saved to ' + ev.review_path : '');
          if (ev.changed) { renderDiff(ev.diff); $('#ai-apply').classList.remove('hidden'); }
        }
      }
    }
  } catch (e) { $('#ai-status').textContent = e.name === 'AbortError' ? 'Cancelled.' : '✕ ' + e.message; }
  $('#ai-go').classList.remove('hidden'); $('#ai-cancel').classList.add('hidden'); aiAbort = null;
};
$('#ai-copy-review').onclick = async () => {
  try { await navigator.clipboard.writeText(aiReview); $('#ai-copy-review').textContent = 'Copied ✓ — paste into Claude'; } catch { prompt('Copy this review:', aiReview); }
  setTimeout(() => $('#ai-copy-review').textContent = 'Copy review', 3000);
};
$('#ai-dl-review').onclick = () => {
  const a = el('a', { href: URL.createObjectURL(new Blob([aiReview], { type: 'text/markdown' })), download: `ai-edit-review-${state.script.replace(/\.py$/, '')}.md` });
  document.body.append(a); a.click(); a.remove();
};
$('#ai-apply').onclick = async () => {
  if (aiResult == null) return;
  const r = await api('/ai-edit/apply', { method: 'POST', body: { name: state.script, content: aiResult } });
  $('#editor').value = aiResult; aim.classList.add('hidden');
  const c = $('#console'); c.replaceChildren(el('div', { className: 'sys', textContent: 'AI edit applied.' + (r.backup ? ' Previous version backed up to ' + r.backup : '') }));
};

function appendLine(l) {
  const c = $('#console'), stick = c.scrollTop + c.clientHeight > c.scrollHeight - 40;
  c.append(el('div', { className: l.s, textContent: l.x })); if (stick) c.scrollTop = c.scrollHeight;
}
function setRunState(s) {
  const b = $('#run-state'); b.textContent = s; b.className = 'badge ' + s;
  const running = s === 'running';
  $('#run-btn').classList.toggle('hidden', running); $('#stop-btn').classList.toggle('hidden', !running);
  $('#report-btn').classList.toggle('hidden', running || !state.run);
  setTimeout(() => { updateTermUI(); if (running === false) $('#term-input').focus(); }, 0);
}
$('#run-btn').onclick = async () => {
  if (!state.script) return; await saveScript();
  $('#console').replaceChildren(); $('#live').classList.add('hidden'); $('#diagnosis').replaceChildren(); $('#files').classList.add('hidden');
  state.run = await api('/runs', { method: 'POST', body: runBody() }); $('#run-timer').textContent = '⏱ 0:00';
  setRunState('running'); watchRun(state.run.id);
};
$('#stop-btn').onclick = () => state.run && api(`/runs/${state.run.id}/stop`, { method: 'POST' });
function watchRun(id) {
  state.es && state.es.close();
  const es = state.es = new EventSource(`/api/runs/${id}/stream`);
  es.onmessage = e => appendLine(JSON.parse(e.data));
  es.addEventListener('live', e => { const x = JSON.parse(e.data).x; $('#live').textContent = x; $('#live').classList.toggle('hidden', !x); });
  es.addEventListener('done', async e => {
    es.close(); $('#live').classList.add('hidden'); const s = JSON.parse(e.data); setRunState(s.status); $('#run-timer').textContent = '⏱ ' + fmtTime(Math.round(s.duration)) + ' total';
    const d = await api('/runs/' + id); showDiagnosis(d.hints, $('#diagnosis')); showFiles(id, d.files, $('#files'), d.files_total);
  });
  es.onerror = () => es.close();
}
function showDiagnosis(hints, box) {
  box.replaceChildren();
  (hints || []).forEach(h => {
    const row = el('div', { className: 'hint' }, el('b', { textContent: h.title + ': ' }), h.detail);
    if (h.action && h.action.pip) {
      const b = el('button', { textContent: 'pip install ' + h.action.pip });
      b.onclick = async () => { b.disabled = true; b.textContent = 'Installing…'; const r = await api('/pip', { method: 'POST', body: { package: h.action.pip } }); b.textContent = r.ok ? 'Installed ✓ — run again' : 'Failed (see log)'; if (!r.ok) alert(r.log); };
      row.append(b);
    }
    box.append(row);
  });
}
$('#report-btn').onclick = async () => {
  const md = await api(`/runs/${state.run.id}/report`);
  try { await navigator.clipboard.writeText(md); $('#report-btn').textContent = 'Copied ✓'; } catch { prompt('Copy report:', md); }
  setTimeout(() => $('#report-btn').textContent = 'Copy failure report', 2000);
};

// ---- models / chat -------------------------------------------------------
async function loadModels() {
  await refreshStatus(); const ms = state.status.lmstudio.models;
  const ul = $('#model-list'); ul.replaceChildren();
  if (!state.status.lmstudio.ok) ul.append(el('li', { textContent: 'LM Studio server not reachable. Start it in the Developer tab.' }));
  ms.forEach(m => ul.append(el('li', {}, el('span', { textContent: m.id }), el('span', { className: 'tag' + (m.loaded ? '' : ' off'), textContent: m.loaded ? 'loaded' : 'on disk' }))));
  const sel = $('#chat-model'); sel.replaceChildren(); ms.filter(m => m.type !== 'embeddings').forEach(m => sel.append(el('option', { value: m.id, textContent: m.id, selected: m.loaded })));
}
$('#refresh-models').onclick = loadModels;
$('#unload-btn').onclick = async () => { const r = await api('/models/unload', { method: 'POST' }); alert(r.ok ? 'Unloaded.' : 'Failed: ' + r.log); loadModels(); };
let chatHistory = [];
$('#chat-form').onsubmit = async e => {
  e.preventDefault(); const t = $('#chat-input').value.trim(); if (!t) return; $('#chat-input').value = '';
  chatHistory.push({ role: 'user', content: t }); $('#chat-log').append(el('div', { className: 'msg user', textContent: t }));
  const out = el('div', { className: 'msg' }); $('#chat-log').append(out); let text = '';
  const r = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Harness': '1' }, body: JSON.stringify({ model: $('#chat-model').value, messages: chatHistory }) });
  const rd = r.body.getReader(), dec = new TextDecoder(); let buf = '';
  for (;;) {
    const { done, value } = await rd.read(); if (done) break; buf += dec.decode(value, { stream: true });
    const parts = buf.split('\n\n'); buf = parts.pop();
    for (const p of parts) {
      if (!p.startsWith('data: ') || p.includes('[DONE]')) continue;
      try { const j = JSON.parse(p.slice(6)); text += j.error ? '⚠ ' + j.error : (j.choices?.[0]?.delta?.content || ''); out.textContent = text; } catch { }
    }
    $('#chat-log').scrollTop = 1e9;
  }
  chatHistory.push({ role: 'assistant', content: text });
};

// ---- reports -------------------------------------------------------------
async function loadRuns() {
  const runs = await api('/runs'); const ul = $('#run-list'); ul.replaceChildren();
  runs.forEach(r => {
    const li = el('li', {}, el('span', { textContent: r.script }), el('span', { className: 'badge ' + r.status, textContent: r.status }));
    li.title = new Date(r.started * 1000).toLocaleString(); li.onclick = () => { $$('#run-list li').forEach(x => x.classList.remove('sel')); li.classList.add('sel'); showReport(r.id); };
    ul.append(li);
  });
}
async function showReport(id) {
  const d = await api('/runs/' + id), v = $('#report-view'); v.replaceChildren();
  const copy = el('button', { className: 'primary', textContent: 'Copy report for debugging' });
  copy.onclick = async () => { await navigator.clipboard.writeText(await api(`/runs/${id}/report`)); copy.textContent = 'Copied ✓'; };
  const rerun = el('button', { className: 'ghost', textContent: 'Open script' });
  rerun.onclick = () => { $('#rail button[data-page=run]').click(); openScript(d.script); };
  v.append(el('h2', { textContent: `${d.script} — ${d.status}` }),
    el('div', { className: 'muted', textContent: `${new Date(d.started * 1000).toLocaleString()} · ${d.duration}s · exit ${d.exit_code} · peak ${d.peak_rss_mb} MB${d.kill_reason ? ' · ' + d.kill_reason : ''}` }),
    el('div', {}, copy, ' ', rerun));
  const dg = el('div', { className: 'panel' }); showDiagnosis(d.hints, dg); if (d.hints?.length) v.append(dg);
  if (d.files && d.files.length) { const fb = el('div', { className: 'panel' }); showFiles(id, d.files, fb, d.files_total); fb.classList.remove('hidden'); v.append(fb); }
  if (d.traceback) v.append(el('h3', { textContent: `Traceback — ${d.traceback.file}:${d.traceback.line}` }), el('pre', { className: 'report', textContent: d.traceback.text }));
  v.append(el('h3', { textContent: 'Output' }), el('pre', { className: 'report', textContent: d.output || '(no output)' }));
  if (d.mem && d.mem.length) { const cv = el('canvas', { height: 120 }); v.append(el('h3', { textContent: 'Script memory over time (MB)' }), cv); drawRunMem(cv, d.mem); }
}
function drawRunMem(c, mem) {
  const w = c.clientWidth, h = 120, dpr = devicePixelRatio || 1; c.width = w * dpr; c.height = h * dpr; const g = c.getContext('2d'); g.scale(dpr, dpr);
  const max = Math.max(...mem.map(m => m.rss_mb), 1), tmax = mem.at(-1).t || 1;
  g.lineWidth = 2; for (let i = 1; i < mem.length; i++) { g.strokeStyle = LEVEL_COLOR[mem[i].level]; g.beginPath(); g.moveTo(mem[i - 1].t / tmax * w, h - 14 - mem[i - 1].rss_mb / max * (h - 24)); g.lineTo(mem[i].t / tmax * w, h - 14 - mem[i].rss_mb / max * (h - 24)); g.stroke(); }
  g.fillStyle = '#8b8b96'; g.font = '10px sans-serif'; g.fillText(max + ' MB peak', 4, 10);
}
$('#refresh-runs').onclick = loadRuns;

// ---- settings / updates --------------------------------------------------
$$('[data-setting]').forEach(i => i.onchange = async () => {
  const v = i.type === 'checkbox' ? i.checked : i.type === 'number' ? Number(i.value) : i.value;
  state.settings = await api('/settings', { method: 'PUT', body: { [i.dataset.setting]: v } }); refreshStatus();
});
$('#check-update').onclick = async () => { $('#s-update-msg').textContent = 'Checking…'; showUpdate(await api('/update/check')); };
$('#apply-update').onclick = async () => {
  $('#apply-update').disabled = true; $('#s-update-msg').textContent = 'Updating…';
  const r = await api('/update/apply', { method: 'POST' });
  if (!r.ok) { $('#s-update-msg').textContent = 'Update failed: ' + r.log; $('#apply-update').disabled = false; return; }
  $('#s-update-msg').textContent = 'Restarting…';
  try { await api('/restart', { method: 'POST' }); } catch (e) { if (confirm('Scripts are running. Restart anyway?')) await api('/restart?force=true', { method: 'POST' }); }
  const t = setInterval(async () => { try { await api('/ping'); clearInterval(t); location.reload(); } catch { } }, 800);
};

// ---- boot ----------------------------------------------------------------
(async () => {
  await refreshStatus(); history = await api('/memory/history'); loadScripts(); connectTelemetry(); setInterval(refreshStatus, 10000);
})();
