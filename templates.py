"""
templates.py — HTML templates inline.
"""

LOGIN_HTML = r"""
<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<title>MedRec — Login</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', Tahoma, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    padding: 20px;
  }
  .card {
    background: white; padding: 40px; border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    max-width: 420px; width: 100%;
  }
  h1 { color: #667eea; text-align: center; font-size: 2em; margin-bottom: 8px; }
  .subtitle { text-align: center; color: #666; margin-bottom: 25px; }
  .tabs { display: flex; margin-bottom: 25px; border-bottom: 2px solid #eee; }
  .tab {
    flex: 1; padding: 12px; text-align: center; cursor: pointer;
    color: #999; font-weight: 600; border-bottom: 3px solid transparent;
    margin-bottom: -2px; transition: all 0.2s;
  }
  .tab.active { color: #667eea; border-bottom-color: #667eea; }
  .form-group { margin-bottom: 18px; }
  label { display: block; font-weight: 600; margin-bottom: 6px; color: #444; font-size: 0.9em; }
  input {
    width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px;
    font-size: 1em;
  }
  input:focus { outline: none; border-color: #667eea; }
  button {
    width: 100%; padding: 14px; background: #764ba2; color: white;
    border: none; border-radius: 8px; font-size: 1.05em; cursor: pointer;
    font-weight: 600; margin-top: 10px;
  }
  button:hover { background: #667eea; }
  button:disabled { background: #ccc; cursor: not-allowed; }
  .error { background: #fee; color: #c33; padding: 10px; border-radius: 6px;
            margin-bottom: 15px; font-size: 0.9em; display: none; }
  .hidden { display: none; }
</style>
</head>
<body>
  <div class="card">
    <h1> MedRec</h1>
    <p class="subtitle">Sistem recomandare specialist medical</p>

    <div class="tabs">
      <div class="tab active" onclick="switchTab('login')">Autentificare</div>
      <div class="tab" onclick="switchTab('register')">Înregistrare medic</div>
      <div class="tab" onclick="switchTab('activate')">Activare pacient</div>
    </div>

    <div id="errorBox" class="error"></div>

    <div id="form-login">
      <div class="form-group">
        <label>Email</label>
        <input type="email" id="login-email" required>
      </div>
      <div class="form-group">
        <label>Parolă</label>
        <input type="password" id="login-password" required>
      </div>
      <button onclick="doLogin()">Intră în cont</button>
    </div>

    <div id="form-register" class="hidden">
      <div class="form-group">
        <label>Nume complet</label>
        <input type="text" id="reg-name" required>
      </div>
      <div class="form-group">
        <label>Email</label>
        <input type="email" id="reg-email" required>
      </div>
      <div class="form-group">
        <label>Parolă (minim 8 caractere)</label>
        <input type="password" id="reg-password" required>
      </div>
      <button onclick="doRegister()">Creează cont medic</button>
    </div>

    <div id="form-activate" class="hidden">
      <p style="color:#666; font-size:0.9em; margin-bottom:15px;">
        Folosește codul de activare primit pe email pentru a activa contul.
      </p>
      <div class="form-group">
        <label>Email</label>
        <input type="email" id="act-email" required>
      </div>
      <div class="form-group">
        <label>Cod activare (6 cifre)</label>
        <input type="text" id="act-code" maxlength="6" pattern="\d{6}" required>
      </div>
      <div class="form-group">
        <label>Setează parola (minim 8 caractere)</label>
        <input type="password" id="act-password" required>
      </div>
      <button onclick="doActivate()">Activează cont</button>
    </div>
  </div>

<script>
  function switchTab(name) {
    ['login','register','activate'].forEach(t => {
      document.getElementById('form-' + t).classList.add('hidden');
    });
    document.getElementById('form-' + name).classList.remove('hidden');
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    hideError();
  }

  function showError(msg) {
    const e = document.getElementById('errorBox');
    e.textContent = msg;
    e.style.display = 'block';
  }
  function hideError() {
    document.getElementById('errorBox').style.display = 'none';
  }

  function saveTokenAndRedirect(data) {
    localStorage.setItem('medrec_token', data.access_token);
    localStorage.setItem('medrec_role', data.role);
    localStorage.setItem('medrec_name', data.full_name);
    if (data.role === 'medic') {
      window.location.href = '/medic';
    } else {
      window.location.href = '/patient';
    }
  }

  async function doLogin() {
    hideError();
    const fd = new FormData();
    fd.append('username', document.getElementById('login-email').value);
    fd.append('password', document.getElementById('login-password').value);
    try {
      const r = await fetch('/auth/login', { method: 'POST', body: fd });
      const data = await r.json();
      if (!r.ok) { showError(data.detail || 'Eroare la login'); return; }
      saveTokenAndRedirect(data);
    } catch (e) { showError('Eroare comunicare: ' + e.message); }
  }

  async function doRegister() {
    hideError();
    const payload = {
      full_name: document.getElementById('reg-name').value,
      email: document.getElementById('reg-email').value,
      password: document.getElementById('reg-password').value,
    };
    try {
      const r = await fetch('/auth/register-medic', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      const data = await r.json();
      if (!r.ok) { showError(data.detail || 'Eroare la înregistrare'); return; }
      saveTokenAndRedirect(data);
    } catch (e) { showError('Eroare comunicare: ' + e.message); }
  }

  async function doActivate() {
    hideError();
    const payload = {
      email: document.getElementById('act-email').value,
      activation_code: document.getElementById('act-code').value,
      new_password: document.getElementById('act-password').value,
    };
    try {
      const r = await fetch('/auth/activate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      const data = await r.json();
      if (!r.ok) { showError(data.detail || 'Eroare la activare'); return; }
      saveTokenAndRedirect(data);
    } catch (e) { showError('Eroare comunicare: ' + e.message); }
  }

  const existing = localStorage.getItem('medrec_token');
  if (existing) {
    const role = localStorage.getItem('medrec_role');
    if (role === 'medic') window.location.href = '/medic';
    else if (role === 'patient') window.location.href = '/patient';
  }
</script>
</body>
</html>
"""