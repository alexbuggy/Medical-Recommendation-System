"""
templates_medic.py — HTML pentru dashboard-ul medicului.

ACTUALIZAT pentru modelul neuronal cu 23 feature-uri si 6 specialisti.
Campurile sunt grupate pe categorii clinice (metabolic, lipidic, renal, etc.)
ca sa fie usor de scanat. Cele 4 user-only (height/weight/BMI/SpO2) sunt
marcate explicit ca "necesara introducere manuala".
"""

MEDIC_DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MedRec — Medic</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', Tahoma, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh; padding: 20px;
  }
  .container {
    background: white; padding: 35px; border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    max-width: 1100px; width: 100%; margin: 0 auto;
  }
  .topbar {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 25px; padding-bottom: 20px; border-bottom: 2px solid #eee;
  }
  h1 { color: #667eea; font-size: 1.8em; }
  .user-info { color: #666; }
  .logout {
    color: #c33; cursor: pointer; text-decoration: underline; margin-left: 15px;
  }
  .tabs { display: flex; gap: 10px; margin-bottom: 25px; }
  .tab {
    padding: 10px 22px; border-radius: 8px; background: #eee; color: #777;
    cursor: pointer; font-weight: 600;
  }
  .tab.active { background: #667eea; color: white; }

  .upload-box {
    border: 3px dashed #667eea; border-radius: 15px; padding: 35px;
    text-align: center; background: #f8f9ff;
  }
  .file-label {
    display: inline-block; padding: 13px 35px; background: #667eea;
    color: white; border-radius: 10px; cursor: pointer; margin: 10px;
  }
  input[type="file"] { display: none; }
  .toggle-row {
    display: flex; align-items: center; justify-content: center;
    gap: 10px; margin: 18px 0; color: #555;
  }
  .switch { position: relative; width: 50px; height: 26px; }
  .switch input { display: none; }
  .slider {
    position: absolute; cursor: pointer; inset: 0; background: #ccc;
    border-radius: 26px; transition: 0.3s;
  }
  .slider:before {
    content: ""; position: absolute; height: 20px; width: 20px;
    left: 3px; bottom: 3px; background: white; border-radius: 50%;
    transition: 0.3s;
  }
  .switch input:checked + .slider { background: #667eea; }
  .switch input:checked + .slider:before { transform: translateX(24px); }

  .btn {
    background: #764ba2; color: white; padding: 13px 40px; border: none;
    border-radius: 10px; cursor: pointer; font-size: 1em; font-weight: 600;
    margin-top: 15px;
  }
  .btn:hover { background: #667eea; }
  .btn:disabled { background: #ccc; cursor: not-allowed; }
  .btn-sm { padding: 8px 18px; font-size: 0.85em; margin: 0; }
  .btn-secondary { background: #aaa; }

  .group {
    margin: 22px 0 10px;
  }
  .group-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 14px; background: #f0f4ff; border-radius: 8px;
    color: #667eea; font-weight: 700; margin-bottom: 10px;
  }
  .group-header .count { font-size: 0.85em; color: #888; font-weight: 500; }
  .field-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
  }
  .field {
    padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px;
    background: white;
  }
  .field.missing { border-color: #ff9800; background: #fff8e1; }
  .field.user-only { border-color: #9c27b0; background: #faf5ff; }
  .field label {
    font-weight: 600; font-size: 0.85em; color: #444;
    display: block; margin-bottom: 5px;
  }
  .field input, .field select {
    width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 6px;
    font-size: 0.95em;
  }
  .field .unit { font-size: 0.75em; color: #999; }
  .field .badge {
    display: inline-block; font-size: 0.65em; padding: 1px 6px;
    border-radius: 8px; margin-left: 5px; vertical-align: middle;
  }
  .badge-user { background: #9c27b0; color: white; }
  .badge-auto { background: #4caf50; color: white; }

  .identity-box {
    background: #f0f4ff; border-radius: 12px; padding: 20px; margin: 20px 0;
  }
  .identity-box h3 { color: #667eea; margin-bottom: 12px; }
  .identity-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 15px;
  }
  .identity-box input {
    width: 100%; padding: 9px; border: 1px solid #ddd; border-radius: 6px;
  }
  .identity-box label { font-weight: 600; font-size: 0.9em; }
  .cnp-warn { color: #e65100; font-size: 0.85em; margin-top: 5px; }

  .banner { padding: 14px; border-radius: 8px; margin: 15px 0; }
  .banner-info { background: #e3f2fd; border-left: 4px solid #2196f3; color: #1565c0; }
  .banner-warn { background: #fff3e0; border-left: 4px solid #ff9800; color: #e65100; }
  .banner-ok   { background: #e8f5e9; border-left: 4px solid #4caf50; color: #2e7d32; }
  .banner-err  { background: #fee; border-left: 4px solid #c33; color: #c33; }

  .specialist-result {
    font-size: 1.6em; font-weight: bold; color: #667eea; text-align: center;
    padding: 20px; background: #f8f9ff; border-radius: 10px; margin: 15px 0;
  }
  .confidence {
    font-size: 0.55em; color: #666; font-weight: 500; display: block;
    margin-top: 8px;
  }
  .probs-row {
    display: flex; flex-wrap: wrap; gap: 8px; justify-content: center;
    margin-top: 15px;
  }
  .prob-pill {
    padding: 5px 12px; border-radius: 14px; font-size: 0.85em;
    background: #eee; color: #555;
  }
  .prob-pill.top { background: #667eea; color: white; font-weight: 600; }

  .shap-box {
    background: #f8f9ff; border-radius: 10px; padding: 18px; margin: 15px 0;
  }
  .shap-box h4 { color: #764ba2; margin-bottom: 12px; }
  .shap-factor {
    padding: 10px; border-left: 4px solid #ccc; background: white;
    margin-bottom: 8px; border-radius: 4px; font-size: 0.92em;
  }
  .shap-factor.supports { border-left-color: #4caf50; }
  .shap-factor.against  { border-left-color: #f44336; }
  .shap-factor .meta {
    display: flex; justify-content: space-between; font-size: 0.8em;
    color: #888; margin-top: 4px;
  }

  .report-text {
    background: #f8f9ff; padding: 20px; border-radius: 10px; line-height: 1.7;
    margin: 15px 0;
  }
  select {
    padding: 9px; border: 1px solid #ddd; border-radius: 6px; font-size: 1em;
  }
  table { width: 100%; border-collapse: collapse; margin-top: 15px; }
  th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
  th { background: #f8f9ff; color: #667eea; }
  tr:hover { background: #f8f9ff; }
  .pill {
    padding: 3px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600;
  }
  .pill-active { background: #e8f5e9; color: #2e7d32; }
  .pill-inactive { background: #fff3e0; color: #e65100; }
  .loading { text-align: center; padding: 30px; color: #667eea; }
  .hidden { display: none; }
</style>
</head>
<body>
  <div class="container">
    <div class="topbar">
      <h1> MedRec — Medic</h1>
      <div class="user-info">
        <span id="medicName"></span>
        <span class="logout" onclick="logout()">Logout</span>
      </div>
    </div>

    <div class="tabs">
      <div class="tab active" id="tab-upload" onclick="switchTab('upload')">📄 Analiză nouă</div>
      <div class="tab" id="tab-patients" onclick="switchTab('patients')">👥 Pacienții mei</div>
    </div>

    <!-- ===== TAB: UPLOAD ===== -->
    <div id="view-upload">
      <!-- Stage 1: file pick -->
      <div id="stage-pick">
        <div class="upload-box">
          <p style="color:#764ba2; font-size:1.1em; margin-bottom:15px;">
            Încarcă analizele de laborator ale pacientului
          </p>
          <label class="file-label" for="fileInput">📁 Alege fișier (PDF/imagine)</label>
          <input type="file" id="fileInput" accept=".pdf,.png,.jpg,.jpeg">
          <div id="fileName" style="margin-top:10px; color:#667eea; font-weight:600;"></div>

          <div class="toggle-row">
            <span>Interpretare AI (GPT)</span>
            <label class="switch">
              <input type="checkbox" id="gptToggle" checked>
              <span class="slider"></span>
            </label>
            <span id="gptLabel" style="font-size:0.85em; color:#888;">Activat</span>
          </div>
          <p style="font-size:0.8em; color:#999;">
            Dezactivat = extragere doar prin OCR local (fără internet),
            raport standard fără AI.
          </p>

          <br>
          <button class="btn" id="extractBtn" disabled onclick="doExtract()">
            🔍 Extrage valori
          </button>
        </div>
      </div>

      <!-- Stage 2: confirm -->
      <div id="stage-confirm" class="hidden">
        <div class="banner banner-info">
          ℹ️ Verifică valorile extrase. Câmpurile galbene = lipsesc din PDF (completează manual sau lasă goale).
          Câmpurile violete (înălțime, greutate, IMC, SpO₂) = nu sunt în analize, se introduc manual.
        </div>
        <div id="confirmBanner"></div>

        <div class="identity-box">
          <h3>👤 Date pacient</h3>
          <div class="identity-grid">
            <div>
              <label>Nume complet</label>
              <input type="text" id="patientName">
            </div>
            <div>
              <label>CNP (13 cifre)</label>
              <input type="text" id="patientCnp" maxlength="13">
              <div id="cnpWarn" class="cnp-warn"></div>
            </div>
          </div>
          <div style="margin-top:15px;">
            <label>Email pacient (pentru activare cont)</label>
            <input type="email" id="patientEmail" placeholder="email@exemplu.ro">
          </div>
        </div>

        <div id="groupsContainer"></div>

        <div style="text-align:center; margin-top:20px;">
          <button class="btn btn-secondary" onclick="backToPick()">↺ Reîncepe</button>
          <button class="btn" onclick="doPredict()"> Recomandă specialist</button>
        </div>
      </div>

      <!-- Stage 3: result -->
      <div id="stage-result" class="hidden">
        <div id="resultContent"></div>
        <div style="text-align:center;">
          <button class="btn" onclick="backToPick()">📄 Analiză nouă</button>
        </div>
      </div>

      <div id="loadingBox" class="loading hidden">⏳ Se procesează...</div>
    </div>

    <!-- ===== TAB: PATIENTS ===== -->
    <div id="view-patients" class="hidden">
      <div id="patientsContent"><div class="loading">Se încarcă...</div></div>
    </div>
  </div>

<script>
  // ============================================================
  // Definitii feature-uri — sincron cu model_service.MODEL_FEATURES
  // ============================================================
  const FIELD_META = {
    age:               { label: 'Vârstă', unit: 'ani', step: '1' },
    sex:               { label: 'Sex', unit: '', type: 'select',
                         options: [{v:0,t:'Masculin'},{v:1,t:'Feminin'}] },
    glucose:           { label: 'Glicemie', unit: 'mg/dL' },
    hba1c:             { label: 'HbA1c', unit: '%' },
    cholesterol_total: { label: 'Colesterol total', unit: 'mg/dL' },
    hdl:               { label: 'HDL', unit: 'mg/dL' },
    ldl:               { label: 'LDL', unit: 'mg/dL' },
    triglycerides:     { label: 'Trigliceride', unit: 'mg/dL' },
    hemoglobin:        { label: 'Hemoglobină', unit: 'g/dL' },
    hematocrit:        { label: 'Hematocrit', unit: '%' },
    wbc:               { label: 'Leucocite', unit: '10³/µL' },
    creatinine:        { label: 'Creatinină', unit: 'mg/dL' },
    egfr:              { label: 'eGFR', unit: 'mL/min/1.73m²' },
    bun:               { label: 'BUN', unit: 'mg/dL' },
    alt:               { label: 'ALT (TGP)', unit: 'U/L' },
    ast:               { label: 'AST (TGO)', unit: 'U/L' },
    bilirubin_total:   { label: 'Bilirubină totală', unit: 'mg/dL' },
    systolic_bp:       { label: 'TA Sistolică', unit: 'mmHg' },
    diastolic_bp:      { label: 'TA Diastolică', unit: 'mmHg' },
    height_cm:         { label: 'Înălțime', unit: 'cm', userOnly: true },
    weight_kg:         { label: 'Greutate', unit: 'kg', userOnly: true },
    bmi:               { label: 'IMC', unit: 'kg/m²', userOnly: true, autoCalc: true },
    oxygen_saturation: { label: 'Saturație O₂ (SpO₂)', unit: '%', userOnly: true },
  };

  const FIELD_GROUPS = [
    { title: '👤 Date pacient',         fields: ['age','sex'] },
    { title: '🍬 Metabolic glucidic',   fields: ['glucose','hba1c'] },
    { title: '🫀 Profil lipidic',       fields: ['cholesterol_total','hdl','ldl','triglycerides'] },
    { title: '🩸 Hematologie',          fields: ['hemoglobin','hematocrit','wbc'] },
    { title: '🫘 Funcție renală',       fields: ['creatinine','egfr','bun'] },
    { title: '🫁 Funcție hepatică',     fields: ['alt','ast','bilirubin_total'] },
    { title: '💓 Tensiune arterială',   fields: ['systolic_bp','diastolic_bp'] },
    { title: '📏 Antropometrie & vitale', fields: ['height_cm','weight_kg','bmi','oxygen_saturation'],
      note: 'Aceste valori nu apar în buletinul de analize — introducere manuală.' },
  ];

  // Cele 6 clase ale modelului
  const SPECIALISTS = ['Cardiolog','Diabetolog','Hematolog','Medicina interna','Nefrolog','Pneumolog'];

  let extractData = null;
  const token = localStorage.getItem('medrec_token');

  if (!token || localStorage.getItem('medrec_role') !== 'medic') {
    window.location.href = '/';
  }
  document.getElementById('medicName').textContent =
    'Dr. ' + (localStorage.getItem('medrec_name') || '');

  function logout() { localStorage.clear(); window.location.href = '/'; }

  function authHeaders(extra) {
    return Object.assign({ 'Authorization': 'Bearer ' + token }, extra || {});
  }

  function switchTab(name) {
    document.getElementById('view-upload').classList.toggle('hidden', name !== 'upload');
    document.getElementById('view-patients').classList.toggle('hidden', name !== 'patients');
    document.getElementById('tab-upload').classList.toggle('active', name === 'upload');
    document.getElementById('tab-patients').classList.toggle('active', name === 'patients');
    if (name === 'patients') loadPatients();
  }

  document.getElementById('gptToggle').addEventListener('change', e => {
    document.getElementById('gptLabel').textContent = e.target.checked ? 'Activat' : 'Dezactivat (offline)';
  });

  document.getElementById('fileInput').addEventListener('change', e => {
    const f = e.target.files[0];
    if (f) {
      document.getElementById('fileName').textContent = '📎 ' + f.name;
      document.getElementById('extractBtn').disabled = false;
    }
  });

  function showStage(s) {
    ['pick','confirm','result'].forEach(x =>
      document.getElementById('stage-' + x).classList.add('hidden'));
    document.getElementById('stage-' + s).classList.remove('hidden');
  }
  function showLoading(v) {
    document.getElementById('loadingBox').classList.toggle('hidden', !v);
  }
  function backToPick() {
    extractData = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('fileName').textContent = '';
    document.getElementById('extractBtn').disabled = true;
    showStage('pick');
  }

  // ============================================================
  // EXTRACT
  // ============================================================
  async function doExtract() {
    const file = document.getElementById('fileInput').files[0];
    if (!file) return;
    const useGpt = document.getElementById('gptToggle').checked;

    const fd = new FormData();
    fd.append('file', file);
    fd.append('use_gpt', useGpt);

    document.getElementById('stage-pick').classList.add('hidden');
    showLoading(true);

    try {
      const r = await fetch('/medic/extract', {
        method: 'POST', headers: authHeaders(), body: fd
      });
      const data = await r.json();
      showLoading(false);
      if (!r.ok) { alert('Eroare: ' + (data.error || data.detail)); showStage('pick'); return; }
      extractData = data;
      renderConfirm(data);
      showStage('confirm');
    } catch (e) {
      showLoading(false); alert('Eroare comunicare: ' + e.message); showStage('pick');
    }
  }

  function renderConfirm(data) {
    // Identity
    document.getElementById('patientName').value = data.patient_name || '';
    document.getElementById('patientCnp').value = data.patient_cnp || '';
    document.getElementById('patientEmail').value = '';

    const cnpWarn = document.getElementById('cnpWarn');
    if (!data.patient_cnp) {
      cnpWarn.textContent = '⚠️ CNP negăsit în PDF — introdu-l manual';
      cnpWarn.style.color = '#e65100';
    } else if (!data.cnp_valid) {
      cnpWarn.textContent = '⚠️ CNP-ul extras pare invalid — verifică';
      cnpWarn.style.color = '#e65100';
    } else {
      cnpWarn.textContent = '✓ CNP valid';
      cnpWarn.style.color = '#2e7d32';
    }

    // Banner: cate valori lipsesc din cele extractabile
    const banner = document.getElementById('confirmBanner');
    const userOnlySet = new Set(data.user_only_fields || []);
    const missingExtractable = (data.missing_fields || [])
      .filter(f => !userOnlySet.has(f));
    if (missingExtractable.length) {
      banner.className = 'banner banner-warn';
      banner.innerHTML = '⚠️ <b>' + missingExtractable.length +
        '</b> valori din laborator nu au putut fi extrase. Completează manual sau lasă goale (modelul va folosi valori implicite).';
    } else {
      banner.className = 'banner banner-ok';
      banner.textContent = '✓ Toate valorile extractabile au fost găsite în PDF.';
    }

    // Build grouped form
    const container = document.getElementById('groupsContainer');
    container.innerHTML = '';
    const extracted = data.extracted_values || {};

    for (const group of FIELD_GROUPS) {
      const groupEl = document.createElement('div');
      groupEl.className = 'group';

      let header = `<div class="group-header">
        <span>${group.title}</span>
        <span class="count">${group.fields.length} câmpuri</span>
      </div>`;
      if (group.note) {
        header += `<div style="font-size:0.85em; color:#888; padding:0 4px 8px;">${group.note}</div>`;
      }
      groupEl.innerHTML = header;

      const grid = document.createElement('div');
      grid.className = 'field-grid';
      for (const field of group.fields) {
        grid.appendChild(buildField(field, extracted));
      }
      groupEl.appendChild(grid);
      container.appendChild(groupEl);
    }

    // BMI auto-calc on height/weight change
    const hEl = document.getElementById('f-height_cm');
    const wEl = document.getElementById('f-weight_kg');
    const bEl = document.getElementById('f-bmi');
    function recalcBMI() {
      const h = parseFloat(hEl.value);
      const w = parseFloat(wEl.value);
      if (h > 0 && w > 0) {
        const bmi = w / Math.pow(h / 100, 2);
        bEl.value = bmi.toFixed(1);
      }
    }
    if (hEl && wEl && bEl) {
      hEl.addEventListener('input', recalcBMI);
      wEl.addEventListener('input', recalcBMI);
    }
  }

  function buildField(field, extracted) {
    const meta = FIELD_META[field];
    const v = extracted[field];
    const hasValue = v !== null && v !== undefined;
    const isUserOnly = !!meta.userOnly;

    const card = document.createElement('div');
    card.className = 'field';
    if (isUserOnly) card.classList.add('user-only');
    else if (!hasValue) card.classList.add('missing');

    let labelHtml = `${meta.label}`;
    if (isUserOnly) labelHtml += ' <span class="badge badge-user">manual</span>';
    else if (hasValue) labelHtml += ' <span class="badge badge-auto">auto</span>';

    let inputHtml;
    if (meta.type === 'select') {
      const opts = meta.options.map(o =>
        `<option value="${o.v}" ${hasValue && Number(v)===o.v ? 'selected' : ''}>${o.t}</option>`
      ).join('');
      inputHtml = `<select id="f-${field}"><option value="">— Necunoscut —</option>${opts}</select>`;
    } else {
      const step = meta.step || '0.01';
      inputHtml = `<input type="number" step="${step}" id="f-${field}"
        value="${hasValue ? v : ''}" placeholder="${isUserOnly ? 'introdu manual' : (hasValue ? '' : 'lipsă')}">`;
    }

    card.innerHTML = `
      <label>${labelHtml}</label>
      ${inputHtml}
      <span class="unit">${meta.unit}</span>
    `;
    return card;
  }

  // ============================================================
  // PREDICT
  // ============================================================
  async function doPredict() {
    const name = document.getElementById('patientName').value.trim();
    const cnp = document.getElementById('patientCnp').value.trim();
    const email = document.getElementById('patientEmail').value.trim();

    if (!name) { alert('Introdu numele pacientului'); return; }
    if (cnp.replace(/\D/g,'').length !== 13) { alert('CNP-ul trebuie să aibă 13 cifre'); return; }
    if (!email) { alert('Introdu email-ul pacientului'); return; }

    const payload = {
      patient_name: name,
      patient_cnp: cnp,
      patient_email: email,
      use_gpt: extractData.used_gpt,
      pdf_temp_path: extractData.pdf_temp_path,
      override_specialist: null,
    };
    // Cele 23 feature-uri
    for (const field of Object.keys(FIELD_META)) {
      const el = document.getElementById('f-' + field);
      const val = el ? el.value : '';
      payload[field] = val === '' ? null : parseFloat(val);
    }

    document.getElementById('stage-confirm').classList.add('hidden');
    showLoading(true);

    try {
      const r = await fetch('/medic/predict', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload)
      });
      const data = await r.json();
      showLoading(false);
      if (!r.ok) { alert('Eroare: ' + (data.detail || data.error)); showStage('confirm'); return; }
      renderResult(data);
      showStage('result');
    } catch (e) {
      showLoading(false); alert('Eroare comunicare: ' + e.message); showStage('confirm');
    }
  }

  function renderResult(data) {
    const c = document.getElementById('resultContent');
    let html = '';

    if (data.is_new_patient) {
      html += `<div class="banner banner-ok">
        ✓ Cont pacient nou creat. ${data.activation_email_sent
          ? 'Email de activare trimis.' : '⚠️ Email-ul nu a putut fi trimis.'}
      </div>`;
    }

    const conf = data.confidence ? Math.round(data.confidence * 100) : null;
    html += `<div class="specialist-result">
      🎯 Specialist recomandat:<br>${data.recommended_specialist}
      ${conf !== null ? `<span class="confidence">Încredere model: ${conf}%</span>` : ''}
    </div>`;

    // Probabilitatile pentru toate cele 6 clase
    if (data.probabilities) {
      const entries = Object.entries(data.probabilities).sort((a,b) => b[1]-a[1]);
      let pills = '';
      for (const [name, p] of entries) {
        const pct = Math.round(p * 100);
        const isTop = name === data.recommended_specialist;
        pills += `<span class="prob-pill ${isTop?'top':''}">${name}: ${pct}%</span>`;
      }
      html += `<div class="probs-row">${pills}</div>`;
    }

    // Override dropdown
    html += `<div style="text-align:center; margin:20px 0;">
      <label style="font-weight:600;">Suprascrie recomandarea (opțional): </label>
      <select id="overrideSelect">
        <option value="">— Păstrează recomandarea sistemului —</option>
        ${SPECIALISTS.map(s => `<option value="${s}" ${s===data.recommended_specialist?'disabled':''}>${s}</option>`).join('')}
      </select>
      <button class="btn btn-sm" onclick="applyOverride('${data.report_id}')">Aplică</button>
      <div id="overrideMsg" style="margin-top:8px; font-size:0.9em;"></div>
    </div>`;

    // SHAP factors — de ce a decis modelul asa
    if (data.explanation && data.explanation.top_factors && data.explanation.top_factors.length) {
      html += `<div class="shap-box">
        <h4>🔍 Factori care au contat (analiză SHAP)</h4>`;
      for (const f of data.explanation.top_factors) {
        const cls = f.direction === 'supports' ? 'supports' : 'against';
        const arrow = f.direction === 'supports' ? '↑' : '↓';
        html += `<div class="shap-factor ${cls}">
          <div>${f.sentence}</div>
          <div class="meta">
            <span>${f.label}${f.value !== null ? ': '+f.value+' '+(f.unit||'') : ' (necunoscut)'}</span>
            <span>${arrow} impact: ${Math.abs(f.shap).toFixed(2)}</span>
          </div>
        </div>`;
      }
      html += `</div>`;
    }

    if (data.campuri_completate_automat && data.campuri_completate_automat.length) {
      const labels = data.campuri_completate_automat
        .map(f => (FIELD_META[f] || {}).label || f).join(', ');
      html += `<div class="banner banner-info">
        ℹ️ Câmpuri completate automat cu valori implicite (lipseau): <b>${labels}</b>
      </div>`;
    }
    if (!data.used_gpt) {
      html += `<div class="banner banner-info">🔌 Mod offline — raport generat fără AI.</div>`;
    }

    html += `<div class="report-text"><b>📋 Raport:</b><br>${data.report_text.replace(/\n/g,'<br>')}</div>`;
    c.innerHTML = html;
  }

  async function applyOverride(reportId) {
    const sel = document.getElementById('overrideSelect').value;
    if (!sel) { document.getElementById('overrideMsg').textContent = 'Selectează un specialist.'; return; }
    try {
      const r = await fetch('/medic/report/' + reportId + '/override', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ specialist: sel })
      });
      const data = await r.json();
      const msg = document.getElementById('overrideMsg');
      if (r.ok) {
        msg.style.color = '#2e7d32';
        msg.textContent = '✓ Specialist actualizat la: ' + sel;
      } else {
        msg.style.color = '#c33';
        msg.textContent = 'Eroare: ' + (data.detail || data.error);
      }
    } catch (e) {
      document.getElementById('overrideMsg').textContent = 'Eroare: ' + e.message;
    }
  }

  // ============================================================
  // PATIENTS LIST
  // ============================================================
  async function loadPatients() {
    const c = document.getElementById('patientsContent');
    c.innerHTML = '<div class="loading">Se încarcă...</div>';
    try {
      const r = await fetch('/medic/patients', { headers: authHeaders() });
      const data = await r.json();
      if (!r.ok) { c.innerHTML = '<div class="banner banner-err">Eroare la încărcare</div>'; return; }
      if (!data.patients.length) {
        c.innerHTML = '<div class="banner banner-info">Nu ai încă pacienți. Încarcă o analiză.</div>';
        return;
      }
      let html = '<table><tr><th>Nume</th><th>Email</th><th>Cont</th><th>Rapoarte</th><th></th></tr>';
      for (const p of data.patients) {
        html += `<tr>
          <td><b>${p.name}</b></td>
          <td>${p.email}</td>
          <td><span class="pill ${p.is_active?'pill-active':'pill-inactive'}">
            ${p.is_active?'Activ':'Neactivat'}</span></td>
          <td>${p.report_count}</td>
          <td><button class="btn btn-sm" onclick="viewPatient('${p.patient_id}')">Vezi istoric</button></td>
        </tr>`;
      }
      html += '</table>';
      c.innerHTML = html;
    } catch (e) {
      c.innerHTML = '<div class="banner banner-err">Eroare: ' + e.message + '</div>';
    }
  }

  async function viewPatient(patientId) {
    const c = document.getElementById('patientsContent');
    c.innerHTML = '<div class="loading">Se încarcă istoricul...</div>';
    try {
      const r = await fetch('/medic/patient/' + patientId, { headers: authHeaders() });
      const data = await r.json();
      if (!r.ok) { c.innerHTML = '<div class="banner banner-err">Eroare</div>'; return; }

      let html = `<button class="btn btn-sm btn-secondary" onclick="loadPatients()">← Înapoi la listă</button>
        <h2 style="color:#667eea; margin:15px 0;">${data.patient.name}</h2>
        <p style="color:#666;">${data.patient.email} —
          <span class="pill ${data.patient.is_active?'pill-active':'pill-inactive'}">
          ${data.patient.is_active?'Cont activ':'Cont neactivat'}</span></p>`;

      if (!data.reports.length) {
        html += '<div class="banner banner-info">Niciun raport.</div>';
      } else {
        for (const rep of data.reports) {
          const date = new Date(rep.created_at).toLocaleString('ro-RO');
          // Build chips for non-null extracted values
          let chips = '';
          const vals = rep.extracted_values || {};
          for (const [k,v] of Object.entries(vals)) {
            if (v === null || v === undefined) continue;
            const meta = FIELD_META[k];
            if (!meta) continue;
            chips += `<span style="display:inline-block; background:#f0f4ff; padding:4px 10px; border-radius:12px; margin:3px; font-size:0.82em; color:#555;">${meta.label}: ${v}${meta.unit?' '+meta.unit:''}</span>`;
          }
          html += `<div style="border:1px solid #e0e0e0; border-radius:10px; padding:18px; margin:15px 0;">
            <div style="display:flex; justify-content:space-between;">
              <b>${date}</b>
              ${rep.has_pdf ? `<a href="#" onclick="downloadPdf('${rep.report_id}'); return false;"
                 style="color:#667eea;">📥 Descarcă PDF</a>` : ''}
            </div>
            <div style="margin:10px 0; font-size:1.1em;">
              🎯 <b>${rep.final_specialist}</b>
              ${rep.overridden ? `<span style="color:#e65100; font-size:0.85em;">
                (suprascris — sistemul recomandase ${rep.recommended_specialist})</span>` : ''}
              ${!rep.used_gpt ? '<span style="color:#888; font-size:0.85em;"> · mod offline</span>' : ''}
            </div>
            <div style="margin: 10px 0;">${chips}</div>
            <div style="background:#f8f9ff; padding:12px; border-radius:8px; font-size:0.9em; line-height:1.6;">
              ${rep.report_text.replace(/\n/g,'<br>')}
            </div>
          </div>`;
        }
      }
      c.innerHTML = html;
    } catch (e) {
      c.innerHTML = '<div class="banner banner-err">Eroare: ' + e.message + '</div>';
    }
  }

  async function downloadPdf(reportId) {
    try {
      const r = await fetch('/medic/report/' + reportId + '/pdf', { headers: authHeaders() });
      if (!r.ok) { alert('PDF indisponibil'); return; }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'analiza.pdf';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) { alert('Eroare descărcare: ' + e.message); }
  }
</script>
</body>
</html>
"""