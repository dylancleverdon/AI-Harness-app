// The console of one script's run in its own window (a second monitor, or a phone).
// It follows the script: when a run ends and a new one of the same script starts,
// it switches to that one. Refresh reloads everything if it got out of sync.
const $ = s => document.querySelector(s);
const q = new URLSearchParams(location.search);
const script = q.get('script') || '';
let runId = q.get('run'), es = null, poll = null, started = 0, tick = null;
const api = async (path, opts = {}) => {
  const r = await fetch('/api' + path, { headers: { 'Content-Type': 'application/json', 'X-Harness': '1' }, ...opts });
  if (!r.ok) throw new Error((await r.text()) || r.statusText);
  return (r.headers.get('content-type') || '').includes('json') ? r.json() : r.text();
};
const fmt = s => { s = Math.max(0, Math.round(s)); const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60;
  return (h ? h + ':' + String(m).padStart(2, '0') : m) + ':' + String(x).padStart(2, '0'); };
function add(line) {
  const out = $('#pc-out'), stick = $('#pc-follow').checked;
  const d = document.createElement('div'); d.className = line.s; d.textContent = line.x; out.append(d);
  while (out.childElementCount > 20000) out.firstChild.remove();
  if (stick) window.scrollTo(0, document.body.scrollHeight);
}
function setStatus(st) {
  $('#pc-status').textContent = st; $('#pc-status').className = 'badge ' + st;
  $('#pc-stop').classList.toggle('hidden', st !== 'running');
  clearInterval(tick);
  if (st === 'running') tick = setInterval(() => $('#pc-timer').textContent = '⏱ ' + fmt(Date.now() / 1000 - started), 1000);
}
async function latestRun() {
  const list = await api('/runs');
  const mine = list.filter(r => r.script === script).sort((a, b) => b.started - a.started);
  return mine.length ? mine[0].id : null;
}
async function connect() {
  es && es.close(); clearInterval(poll);
  $('#pc-out').replaceChildren(); $('#pc-live').classList.add('hidden');
  if (!runId && script) { try { runId = await latestRun(); } catch { } }
  $('#pc-title').textContent = script || 'Console';
  document.title = (script || 'Console') + ' — console';
  if (!runId) { setStatus('no run yet'); followNext(); return; }
  let d; try { d = await api('/runs/' + runId); } catch { setStatus('not found'); followNext(); return; }
  started = d.started;
  if (d.status !== 'running') {
    (d.output || '').split('\n').forEach(x => add({ s: 'out', x }));
    setStatus(d.status); $('#pc-timer').textContent = '⏱ ' + fmt(d.duration) + ' total'; followNext(); return;
  }
  setStatus('running');
  es = new EventSource(`/api/runs/${runId}/stream`);
  es.onmessage = e => add(JSON.parse(e.data));
  es.addEventListener('live', e => { const x = JSON.parse(e.data).x; $('#pc-live').textContent = x; $('#pc-live').classList.toggle('hidden', !x); });
  es.addEventListener('done', e => { es.close(); const s = JSON.parse(e.data); $('#pc-live').classList.add('hidden');
    setStatus(s.status); $('#pc-timer').textContent = '⏱ ' + fmt(s.duration) + ' total'; followNext(); });
  es.onerror = () => { es.close(); setTimeout(connect, 3000); };   // dropped (phone asleep, restart): reconnect
}
function followNext() {   // a new run of the same script: switch to it
  if (!script) return;
  clearInterval(poll);
  poll = setInterval(async () => { try { const id = await latestRun(); if (id && id !== runId) { runId = id; connect(); } } catch { } }, 5000);
}
$('#pc-refresh').onclick = () => connect();
$('#pc-stop').onclick = () => runId && api(`/runs/${runId}/stop`, { method: 'POST' });
document.addEventListener('visibilitychange', () => { if (!document.hidden) connect(); });
connect();
