

PATIENT_DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MedRec — Pacient</title>
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
    max-width: 1000px; width: 100%; margin: 0 auto;
  }
  .topbar {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 25px; padding-bottom: 20px; border-bottom: 2px solid #eee;
  }
  h1 { color: #667eea; font-size: 1.7em; }
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

  .banner { padding: 14px; border-radius: 8px; margin: 15px 0; }
  .banner-info { background: #e3f2fd; border-left: 4px solid #2196f3; color: #1565c0; }
  .banner-warn { background: #fff3e0; border-left: 4px solid #ff9800; color: #e65100; }
  .banner-ok   { background: #e8f5e9; border-left: 4px solid #4caf50; color: #2e7d32; }
  .banner-err  { background: #fee; border-left: 4px solid #c33; color: #c33; }

  .report-card {
    border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px;
    margin: 15px 0;
  }
  .report-card .date { color: #888; font-size: 0.9em; }
  .report-card .specialist {
    font-size: 1.3em; font-weight: bold; color: #667eea; margin: 10px 0;
  }
  .values-row {
    display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0;
  }
  .value-chip {
    background: #f0f4ff; padding: 4px 10px; border-radius: 12px;
    font-size: 0.82em; color: #555;
  }
  .report-body {
    background: #f8f9ff; padding: 14px; border-radius: 8px;
    line-height: 1.6; font-size: 0.92em; margin-top: 10px;
  }

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
  .btn-secondary { background: #aaa; }

  .group { margin: 22px 0 10px; }
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

  .specialist-result {
    font-size: 1.5em; font-weight: bold; color: #667eea; text-align: center;
    padding: 20px; background: #f8f9ff; border-radius: 10px; margin: 15px 0;
  }
  .confidence {
    font-size: 0.6em; color: #666; font-weight: 500; display: block;
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

  .loading { text-align: center; padding: 30px; color: #667eea; }
  .hidden { display: none; }
</style>
</head>
<body>
  <div class="container">
    <div class="topbar">
      <h1> MedRec — Pacient</h1>
      <div class="user-info">
        <span id="patientName"></span>
        <span class="logout" onclick="logout()">Logout</span>
      </div>
    </div>

    <div class="tabs">
      <div class="tab active" id="tab-reports" onclick="switchTab('reports')">📋 Rapoartele mele</div>
      <div class="tab" id="tab-try" onclick="switchTab('try')">🔬 Testează singur</div>
    </div>

    <!-- ===== TAB: REPORTS ===== -->
    <div id="view-reports">
      <div id="reportsContent"><div class="loading">Se încarcă...</div></div>
    </div>

    <!-- ===== TAB: TRY YOURSELF ===== -->
    <div id="view-try" class="hidden">
      <div class="banner banner-info">
        ℹ️ Aici poți rula sistemul pe propriile analize pentru a vedea o estimare.
        <b>Rezultatul NU se salvează</b> în istoricul tău — doar rapoartele
        încărcate de un medic apar acolo, deoarece au nevoie de validare medicală.
      </div>

      <!-- Stage 1: pick -->
      <div id="stage-pick">
        <div class="upload-box">
          <p style="color:#764ba2; font-size:1.1em; margin-bottom:15px;">
            Încarcă analizele tale de laborator
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
            Dezactivat = extragere doar prin OCR local, fără internet.
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
          ℹ️ Verifică valorile. Câmpurile galbene = lipsesc din PDF.
          Câmpurile violete (înălțime, greutate, IMC, SpO₂) = nu sunt în analize, introdu manual.
        </div>
        <div id="confirmBanner"></div>
        <div id="groupsContainer"></div>
        <div style="text-align:center; margin-top:20px;">
          <button class="btn btn-secondary" onclick="backToPick()">↺ Reîncepe</button>
          <button class="btn" onclick="doPredict()">🎯 Vezi recomandarea</button>
        </div>
      </div>

      <!-- Stage 3: result -->
      <div id="stage-result" class="hidden">
        <div id="resultContent"></div>
        <div style="text-align:center;">
          <button class="btn" onclick="backToPick()">🔬 Testează altă analiză</button>
        </div>
      </div>

      <div id="loadingBox" class="loading hidden">⏳ Se procesează...</div>
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
    { title: '👤 Date personale',       fields: ['age','sex'] },
    { title: '🍬 Metabolic glucidic',   fields: ['glucose','hba1c'] },
    { title: '🫀 Profil lipidic',       fields: ['cholesterol_total','hdl','ldl','triglycerides'] },
    { title: '🩸 Hematologie',          fields: ['hemoglobin','hematocrit','wbc'] },
    { title: '🫘 Funcție renală',       fields: ['creatinine','egfr','bun'] },
    { title: '🫁 Funcție hepatică',     fields: ['alt','ast','bilirubin_total'] },
    { title: '💓 Tensiune arterială',   fields: ['systolic_bp','diastolic_bp'] },
    { title: '📏 Antropometrie & vitale', fields: ['height_cm','weight_kg','bmi','oxygen_saturation'],
      note: 'Aceste valori nu apar în buletinul de analize — introdu-le manual.' },
  ];

  const token = localStorage.getItem('medrec_token');
  if (!token || localStorage.getItem('medrec_role') !== 'patient') {
    window.location.href = '/';
  }
  document.getElementById('patientName').textContent =
    localStorage.getItem('medrec_name') || '';

  function logout() { localStorage.clear(); window.location.href = '/'; }
  function authHeaders(extra) {
    return Object.assign({ 'Authorization': 'Bearer ' + token }, extra || {});
  }

  function switchTab(name) {
    document.getElementById('view-reports').classList.toggle('hidden', name !== 'reports');
    document.getElementById('view-try').classList.toggle('hidden', name !== 'try');
    document.getElementById('tab-reports').classList.toggle('active', name === 'reports');
    document.getElementById('tab-try').classList.toggle('active', name === 'try');
    if (name === 'reports') loadReports();
  }

  // ============================================================
  // REPORTS (saved by medic)
  // ============================================================
  async function loadReports() {
    const c = document.getElementById('reportsContent');
    c.innerHTML = '<div class="loading">Se încarcă...</div>';
    try {
      const r = await fetch('/patient/reports', { headers: authHeaders() });
      const data = await r.json();
      if (!r.ok) { c.innerHTML = '<div class="banner banner-err">Eroare la încărcare</div>'; return; }

      if (!data.reports.length) {
        c.innerHTML = `<div class="banner banner-info">
          Nu ai încă rapoarte. Rapoartele apar aici după ce un medic
          îți încarcă analizele.</div>`;
        return;
      }

      let html = '';
      for (const rep of data.reports) {
        const date = new Date(rep.created_at).toLocaleString('ro-RO');
        let chips = '';
        const vals = rep.extracted_values || {};
        for (const [k,v] of Object.entries(vals)) {
          if (v === null || v === undefined) continue;
          const meta = FIELD_META[k];
          if (!meta) continue;
          chips += `<span class="value-chip">${meta.label}: ${v}${meta.unit?' '+meta.unit:''}</span>`;
        }
        html += `<div class="report-card">
          <div class="date">${date}${!rep.used_gpt ? ' · mod offline' : ''}</div>
          <div class="specialist">🎯 ${rep.final_specialist}</div>
          <div class="values-row">${chips}</div>
          <div class="report-body">${rep.report_text.replace(/\n/g,'<br>')}</div>
        </div>`;
      }
      c.innerHTML = html;
    } catch (e) {
      c.innerHTML = '<div class="banner banner-err">Eroare: ' + e.message + '</div>';
    }
  }

  // ============================================================
  // TRY YOURSELF (no save)
  // ============================================================
  let selfData = null;

  document.getElementById('gptToggle').addEventListener('change', e => {
    document.getElementById('gptLabel').textContent =
      e.target.checked ? 'Activat' : 'Dezactivat (offline)';
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
    selfData = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('fileName').textContent = '';
    document.getElementById('extractBtn').disabled = true;
    showStage('pick');
  }

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
      const r = await fetch('/patient/self-extract', {
        method: 'POST', headers: authHeaders(), body: fd
      });
      const data = await r.json();
      showLoading(false);
      if (!r.ok) { alert('Eroare: ' + (data.error || data.detail)); showStage('pick'); return; }
      selfData = data;
      renderConfirm(data);
      showStage('confirm');
    } catch (e) {
      showLoading(false); alert('Eroare: ' + e.message); showStage('pick');
    }
  }

  function renderConfirm(data) {
    // Banner: cate valori lipsesc din cele extractabile
    const userOnlySet = new Set(data.user_only_fields || []);
    const missingExtractable = (data.missing_fields || [])
      .filter(f => !userOnlySet.has(f));
    const banner = document.getElementById('confirmBanner');
    if (missingExtractable.length) {
      banner.className = 'banner banner-warn';
      banner.innerHTML = '⚠️ <b>' + missingExtractable.length +
        '</b> valori din laborator nu au putut fi extrase. Completează manual sau lasă goale.';
    } else {
      banner.className = 'banner banner-ok';
      banner.textContent = '✓ Toate valorile extractabile au fost găsite în fișier.';
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

    // BMI auto-calc
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

  async function doPredict() {
    const payload = { use_gpt: selfData.used_gpt };
    for (const field of Object.keys(FIELD_META)) {
      const el = document.getElementById('f-' + field);
      const val = el ? el.value : '';
      payload[field] = val === '' ? null : parseFloat(val);
    }

    document.getElementById('stage-confirm').classList.add('hidden');
    showLoading(true);
    try {
      const r = await fetch('/patient/self-predict', {
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
      showLoading(false); alert('Eroare: ' + e.message); showStage('confirm');
    }
  }

  function renderResult(data) {
    const c = document.getElementById('resultContent');
    const conf = data.confidence ? Math.round(data.confidence * 100) : null;

    let html = `<div class="specialist-result">
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

    // SHAP factors
    if (data.explanation && data.explanation.top_factors && data.explanation.top_factors.length) {
      html += `<div class="shap-box">
        <h4>🔍 Factori care au contat la decizie</h4>`;
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
        ℹ️ Câmpuri completate automat cu valori implicite: <b>${labels}</b></div>`;
    }
    if (!data.used_gpt) {
      html += `<div class="banner banner-info">🔌 Mod offline — raport fără AI.</div>`;
    }

    html += `<div class="report-body"><b>📋 Raport:</b><br>${data.report_text.replace(/\n/g,'<br>')}</div>`;
    html += `<div class="banner banner-warn">
      ⚠️ Acest rezultat NU a fost salvat. Pentru un raport în istoricul tău,
      adresează-te medicului tău.</div>`;
    c.innerHTML = html;
  }

  // Load reports on first open
  loadReports();
</script>
</body>
</html>
"""