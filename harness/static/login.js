document.getElementById('login').onsubmit = async (e) => {
  e.preventDefault();
  const msg = document.getElementById('msg');
  msg.textContent = 'Signing in…';
  const r = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Harness': '1' },
    body: JSON.stringify({ password: document.getElementById('pw').value }) });
  if (r.ok) { location.href = '/'; return; }
  let t = await r.text(); try { t = JSON.parse(t).detail || t; } catch {} msg.textContent = t || 'Wrong password.';
};
