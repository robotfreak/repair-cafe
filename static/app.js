/* Repair-Café-Assistent – Einseiten-App (Vanilla JS, kein Framework). */
'use strict';

/* ====================== Konstanten ====================== */

const TRANSITIONS = {
  'offen': ['in_arbeit'],
  'in_arbeit': ['erfolgreich', 'nicht_reparierbar', 'offen'],
  'erfolgreich': ['abgeholt'],
  'nicht_reparierbar': ['abgeholt'],
  'abgeholt': [],
};

const STATUS_LABELS = {
  'offen': 'Offen',
  'in_arbeit': 'In Arbeit',
  'erfolgreich': 'Erledigt',
  'nicht_reparierbar': 'Nicht reparierbar',
  'abgeholt': 'Abgeholt',
};

const ENTRY_TYPES = ['notiz', 'diagnose', 'schritt', 'ersatzteil', 'ergebnis'];
const ENTRY_LABELS = {
  notiz: 'Notiz', diagnose: 'Diagnose', schritt: 'Schritt',
  ersatzteil: 'Ersatzteil', ergebnis: 'Ergebnis',
};
const DOC_TYPES = ['datasheet', 'manual', 'schema', 'foto', 'sonstiges'];
const DOC_LABELS = {
  datasheet: 'Datenblatt', manual: 'Handbuch', schema: 'Schaltplan',
  foto: 'Foto', sonstiges: 'Sonstiges',
};
const SK_LABELS = {
  'I': 'SK I (Schutzleiter)',
  'II': 'SK II (Doppel-/Schutzisolierung)',
  'III': 'SK III (Schutzkleinspannung)',
};

function schutzklasseBadge(cls) {
  if (!cls) return null;
  return el('span', { class: 'badge badge-sk-' + cls, title: SK_LABELS[cls] || '' }, 'SK ' + cls);
}

/* ====================== Hilfsfunktionen ====================== */

const view = document.getElementById('view');
const toastEl = document.getElementById('toast');
let toastTimer = null;

function showToast(msg) {
  toastEl.textContent = msg;
  toastEl.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toastEl.hidden = true; }, 4000);
}

/** Zentrale Fetch-Hilfe: JSON, !ok → Fehler (deutsch), Ladezustand. */
async function api(path, options = {}) {
  const opts = { headers: {}, ...options };
  if (opts.body !== undefined && !(opts.body instanceof FormData)) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(opts.body);
  }
  let resp;
  try {
    resp = await fetch(path, opts);
  } catch (err) {
    throw new Error('Netzwerkfehler: Server nicht erreichbar');
  }
  let data = null;
  const text = await resp.text();
  if (text) {
    try { data = JSON.parse(text); } catch (err) { data = null; }
  }
  if (!resp.ok) {
    const msg = (data && data.error) ? data.error : ('Fehler ' + resp.status);
    throw new Error(msg);
  }
  return data;
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key === 'dataset') Object.assign(node.dataset, value);
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (key === 'value') node.value = value;
    else node.setAttribute(key, value);
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

/** Nutzerdaten niemals via innerHTML – nur textContent/Textnodes. */
function safeText(value) {
  return document.createTextNode(value === null || value === undefined ? '' : String(value));
}

function fmtDateTime(iso) {
  if (!iso) return '–';
  return iso.slice(0, 16).replace('T', ' ');
}

function fmtDate(iso) {
  if (!iso) return '–';
  return iso.slice(0, 10);
}

function todayIso() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate());
}

function fmtWait(createdAt) {
  const then = new Date(String(createdAt).replace(' ', 'T') + 'Z');
  if (isNaN(then.getTime())) return '';
  const mins = Math.max(0, Math.floor((Date.now() - then.getTime()) / 60000));
  if (mins < 1) return 'gerade eben';
  if (mins < 60) return mins + ' Min.';
  const hours = Math.floor(mins / 60);
  if (hours < 24) return hours + ' Std. ' + (mins % 60) + ' Min.';
  const days = Math.floor(hours / 24);
  return days + ' Tg. ' + (hours % 24) + ' Std.';
}

function truncate(text, max) {
  const s = String(text || '');
  return s.length > max ? s.slice(0, max - 1) + '…' : s;
}

function escAttr(value) {
  return String(value ?? '').replace(/&/g, '&amp;').replace(/"/g, '&quot;')
    .replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function statusBadge(status) {
  return el('span', { class: 'badge badge-' + status }, STATUS_LABELS[status] || status);
}

function entryBadge(type) {
  return el('span', { class: 'badge badge-entry-' + type }, ENTRY_LABELS[type] || type);
}

function errorBox(msg) {
  return el('div', { class: 'error-box', role: 'alert' }, safeText(msg));
}

function fieldErrorBox() {
  return el('div', { class: 'error-box', role: 'alert', hidden: true });
}

/** Kleine 2-Spalten-Info-Tabelle für Gerätedetails. */
function infoGrid(rows) {
  return el('dl', { class: 'info-grid' },
    rows.map(([label, value]) => [
      el('dt', {}, safeText(label)),
      el('dd', {}, safeText(value)),
    ]));
}

function showFieldError(box, err) {
  box.textContent = err && err.message ? err.message : String(err);
  box.hidden = false;
}

/** Buttons während eines Requests sperren. */
async function withBusy(button, fn) {
  if (button.disabled) return;
  button.disabled = true;
  const prev = button.dataset.label || button.textContent;
  button.dataset.label = prev;
  button.classList.add('is-busy');
  try {
    await fn();
  } catch (err) {
    showToast(err.message || 'Unbekannter Fehler');
    throw err;
  } finally {
    button.disabled = false;
    button.classList.remove('is-busy');
    if (button.dataset.label) button.textContent = button.dataset.label;
  }
}

function emptyHint(text) {
  return el('p', { class: 'empty-hint' }, safeText(text));
}

/* ====================== Hash-Routing ====================== */

const routes = [
  { pattern: /^#\/board$/, handler: renderBoard },
  { pattern: /^#\/ticket\/(\d+)$/, handler: renderTicket },
  { pattern: /^#\/search$/, handler: renderSearch },
  { pattern: /^#\/documents$/, handler: renderDocuments },
  { pattern: /^#\/devices$/, handler: renderDevices },
];

function parseRoute() {
  const hash = location.hash || '#/board';
  for (const r of routes) {
    const m = hash.match(r.pattern);
    if (m) return { handler: r.handler, params: m.slice(1) };
  }
  return { handler: renderBoard, params: [] };
}

async function render() {
  const route = parseRoute();
  document.querySelectorAll('.nav-link').forEach((a) => {
    a.classList.toggle('active', location.hash.startsWith('#/' + a.dataset.nav));
  });
  view.replaceChildren(el('section', { class: 'loading' }, safeText('Lade …')));
  try {
    await route.handler(...route.params);
  } catch (err) {
    view.replaceChildren(
      el('section', { class: 'panel' },
        errorBox('Fehler beim Laden: ' + (err.message || 'unbekannt')),
        el('a', { class: 'btn', href: '#/board' }, 'Zurück zum Board')));
  }
}

window.addEventListener('hashchange', render);

/* ====================== BOARD ====================== */

async function renderBoard() {
  const [board, devices] = await Promise.all([api('/api/board'), api('/api/devices')]);
  const today = todayIso();

  const finishedToday = board['erfolgreich'].filter((t) => fmtDate(t.finished_at) === today)
    .concat(board['nicht_reparierbar'].filter((t) => fmtDate(t.finished_at) === today));
  const finishedOther = board['erfolgreich'].concat(board['nicht_reparierbar'])
    .filter((t) => fmtDate(t.finished_at) !== today);

  const colOpen = el('section', { class: 'board-col' },
    el('h2', { class: 'board-col-title' }, 'Offen ',
      el('span', { class: 'count' }, String(board['offen'].length))),
    board['offen'].length ? board['offen'].map(ticketCard) : emptyHint('Keine offenen Laufzettel'));

  const colWorking = el('section', { class: 'board-col' },
    el('h2', { class: 'board-col-title' }, 'In Arbeit ',
      el('span', { class: 'count' }, String(board['in_arbeit'].length))),
    board['in_arbeit'].length ? board['in_arbeit'].map(ticketCard) : emptyHint('Nichts in Arbeit'));

  const colDone = el('section', { class: 'board-col' },
    el('h2', { class: 'board-col-title' }, 'Erledigt heute ',
      el('span', { class: 'count' }, String(finishedToday.length))),
    finishedToday.length ? finishedToday.map(ticketCard) : emptyHint('Heute noch nichts erledigt'),
    finishedOther.length
      ? el('div', { class: 'board-dim' },
          el('h3', { class: 'board-dim-title' }, 'Früher erledigt'),
          finishedOther.map(ticketCard))
      : null);

  const colPickup = el('section', { class: 'board-col' },
    el('h2', { class: 'board-col-title' }, 'Abzuholen ',
      el('span', { class: 'count' }, String(board['abgeholt'].length))),
    board['abgeholt'].length ? board['abgeholt'].map(ticketCard) : emptyHint('Keine Geräte abzuholen'));

  view.replaceChildren(
    el('div', { class: 'board-head' },
      el('h1', {}, 'Board'),
      el('button', {
        type: 'button', class: 'btn btn-primary',
        onclick: () => openNewTicketModal(devices),
      }, '+ Neuer Laufzettel')),
    el('div', { class: 'board' }, colOpen, colWorking, colDone, colPickup));
}

function ticketCard(ticket) {
  const wait = ticket.status === 'offen' || ticket.status === 'in_arbeit'
    ? el('span', { class: 'wait', title: 'seit ' + fmtDateTime(ticket.created_at) },
        '⏱ ' + fmtWait(ticket.created_at))
    : el('span', { class: 'wait' }, safeText(fmtDate(ticket.created_at)));
  return el('a', { class: 'card ticket-card', href: '#/ticket/' + ticket.id },
    el('div', { class: 'card-title' }, safeText(ticket.device_name), ' ',
      el('span', { class: 'ticket-no' }, '#' + ticket.id)),
    el('p', { class: 'card-fault' }, safeText(truncate(ticket.fault_description, 120))),
    el('div', { class: 'card-meta' },
      wait,
      schutzklasseBadge(ticket.schutzklasse),
      ticket.assignee ? el('span', { class: 'badge badge-assignee' }, safeText(ticket.assignee)) : null,
      statusBadge(ticket.status)));
}

/* ====================== NEUER LAUFZETTEL (Modal) ====================== */

function openNewTicketModal(devices) {
  const overlay = document.getElementById('modal-new-ticket');
  const body = document.getElementById('modal-body');
  buildNewTicketForm(body, devices);
  overlay.hidden = false;
}

function closeNewTicketModal() {
  const overlay = document.getElementById('modal-new-ticket');
  overlay.hidden = true;
  document.getElementById('modal-body').replaceChildren();
}

document.getElementById('btn-new-ticket').addEventListener('click', async () => {
  try {
    const devices = await api('/api/devices');
    openNewTicketModal(devices);
  } catch (err) {
    showToast(err.message);
  }
});
document.querySelectorAll('[data-close-modal]').forEach((btn) => {
  btn.addEventListener('click', closeNewTicketModal);
});
document.getElementById('modal-new-ticket').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) closeNewTicketModal();
});

function buildNewTicketForm(container, devices) {
  const errBox = fieldErrorBox();
  const devSel = el('select', { id: 'nt-device', required: true },
    el('option', { value: '' }, '– Gerät wählen –'),
    devices.map((d) => el('option', { value: String(d.id) }, safeText(d.name))),
    el('option', { value: 'new' }, 'Neues Gerät…'));

  const newFields = el('div', { class: 'new-device-fields', hidden: true },
    labeledInput('Name *', 'nt-name', { maxlength: 200 }),
    labeledInput('Hersteller', 'nt-manufacturer', { maxlength: 500 }),
    labeledInput('Modell', 'nt-model', { maxlength: 500 }),
    el('div', { class: 'form-row' },
      el('label', { for: 'nt-schutzklasse' }, 'Schutzklasse (für VDE-Prüfung)'),
      el('select', { id: 'nt-schutzklasse' },
        el('option', { value: '' }, 'unbekannt / später ergänzen'),
        el('option', { value: 'I' }, SK_LABELS['I']),
        el('option', { value: 'II' }, SK_LABELS['II']),
        el('option', { value: 'III' }, SK_LABELS['III']))),
    labeledInput('Heizleistung in kW (nur bei Heizelementen)', 'nt-heating-kw', { type: 'number', min: '0.1', step: '0.1' }),
    labeledTextarea('Zubehör', 'nt-accessories', { maxlength: 500 }));

  devSel.addEventListener('change', () => {
    newFields.hidden = devSel.value !== 'new';
  });

  const fault = el('textarea', { id: 'nt-fault', rows: 3, required: true, maxlength: 2000 });
  const assignee = el('input', { id: 'nt-assignee', type: 'text', maxlength: 100 });

  /* --- Waiver-Pflichtblock --- */
  const waiverTextPre = el('pre', { class: 'waiver-text' }, safeText('Lade Haftungsausschluss …'));
  const waiverVersion = el('span', { class: 'muted' });
  const accept = el('input', { id: 'nt-accept', type: 'checkbox' });

  const canvas = el('canvas', { id: 'nt-canvas', class: 'sig-canvas', width: 320, height: 140 });
  const sig = initSignatureCanvas(canvas, () => updateButton());

  const signedName = el('input', { id: 'nt-signedname', type: 'text', maxlength: 100, autocomplete: 'off' });

  const submitBtn = el('button', { type: 'submit', class: 'btn btn-primary btn-wide' }, 'Laufzettel anlegen');
  function updateButton() {
    submitBtn.disabled = !(accept.checked && sig.hasDrawn() && signedName.value.trim() !== '');
  }
  accept.addEventListener('change', updateButton);
  signedName.addEventListener('input', updateButton);

  const form = el('form', { class: 'form' },
    el('h3', {}, 'Gerät & Fehler'),
    el('div', { class: 'form-row' }, el('label', { for: 'nt-device' }, 'Gerät *'), devSel),
    newFields,
    el('div', { class: 'form-row' }, el('label', { for: 'nt-fault' }, 'Fehlerbeschreibung *'), fault),
    el('div', { class: 'form-row' }, el('label', { for: 'nt-assignee' }, 'Zuweisen an'), assignee),

    el('h3', {}, 'Haftungsausschluss (Pflicht)'),
    el('details', { class: 'waiver-details' },
      el('summary', {}, 'Haftungsausschluss lesen ', waiverVersion),
      waiverTextPre),
    el('label', { class: 'check-row', for: 'nt-accept' },
      accept, el('span', {}, 'Ich akzeptiere den Haftungsausschluss')),
    el('div', { class: 'form-row' },
      el('label', {}, 'Unterschrift *'),
      canvas,
      el('div', { class: 'row-between' },
        el('span', { class: 'muted' }, 'Mit Maus, Finger oder Stift signieren'),
        el('button', { type: 'button', class: 'btn btn-small', onclick: () => sig.clear() }, 'Signatur löschen'))),
    el('div', { class: 'form-row' },
      el('label', { for: 'nt-signedname' }, 'Print-Name *'), signedName),
    errBox,
    submitBtn);

  api('/api/waiver').then((w) => {
    waiverTextPre.textContent = w.text;
    waiverVersion.textContent = '(Version ' + w.version + ')';
  }).catch((err) => {
    waiverTextPre.textContent = 'Haftungsausschluss konnte nicht geladen werden: ' + err.message;
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!form.reportValidity()) return;
    if (!sig.hasDrawn()) {
      showFieldError(errBox, new Error('Bitte unterschreiben Sie im Feld'));
      return;
    }
    submitBtn.disabled = true;
    try {
      let deviceId = devSel.value === 'new' ? null : Number(devSel.value);
      if (devSel.value === 'new') {
        const name = document.getElementById('nt-name').value.trim();
        if (!name) throw new Error('Name des neuen Geräts ist erforderlich');
        const heatRaw = document.getElementById('nt-heating-kw').value.trim();
        const device = await api('/api/devices', {
          method: 'POST',
          body: {
            name,
            manufacturer: document.getElementById('nt-manufacturer').value.trim() || null,
            model: document.getElementById('nt-model').value.trim() || null,
            schutzklasse: document.getElementById('nt-schutzklasse').value || null,
            heating_kw: heatRaw ? Number(heatRaw) : null,
            accessories: document.getElementById('nt-accessories').value.trim() || null,
          },
        });
        deviceId = device.id;
      }
      const ticket = await api('/api/tickets', {
        method: 'POST',
        body: {
          device_id: deviceId,
          fault_description: fault.value.trim(),
          assignee: assignee.value.trim() || null,
          waiver: {
            signed_name: signedName.value.trim(),
            accepted: true,
            signature_data_url: canvas.toDataURL('image/png'),
          },
        },
      });
      closeNewTicketModal();
      showToast('Laufzettel #' + ticket.id + ' angelegt');
      location.hash = '#/ticket/' + ticket.id;
    } catch (err) {
      showFieldError(errBox, err);
      submitBtn.disabled = false;
    }
  });

  container.replaceChildren(form);
  updateButton();
}

function labeledInput(label, id, attrs = {}) {
  const input = el('input', { id, type: 'text', ...attrs });
  return el('div', { class: 'form-row' }, el('label', { for: id }, label), input);
}

function labeledTextarea(label, id, attrs = {}) {
  const input = el('textarea', { id, rows: 2, ...attrs });
  return el('div', { class: 'form-row' }, el('label', { for: id }, label), input);
}

/* ====================== Unterschriften-Canvas ====================== */

/** Pointer-Events: Maus + Touch + Stift. setPointerCapture hält Striche stabil. */
function initSignatureCanvas(canvas, onChange) {
  const ctx = canvas.getContext('2d');
  ctx.lineWidth = 2.5;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--foreground') || '#111';
  let drawing = false;
  let drawn = false;

  function pos(event) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: (event.clientX - rect.left) * (canvas.width / rect.width),
      y: (event.clientY - rect.top) * (canvas.height / rect.height),
    };
  }

  canvas.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    canvas.setPointerCapture(e.pointerId);
    drawing = true;
    const p = pos(e);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    ctx.lineTo(p.x + 0.01, p.y + 0.01);
    ctx.stroke();
    drawn = true;
    onChange && onChange();
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!drawing) return;
    e.preventDefault();
    const p = pos(e);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
  });
  const stop = () => { drawing = false; };
  canvas.addEventListener('pointerup', stop);
  canvas.addEventListener('pointercancel', stop);
  canvas.addEventListener('pointerleave', stop);

  return {
    clear() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      drawn = false;
      onChange && onChange();
    },
    hasDrawn() { return drawn; },
  };
}

/* ====================== TICKET-VIEW ====================== */

async function renderTicket(id) {
  const [ticket, entries, waiver, documents, checksData, initialTest] = await Promise.all([
    api('/api/tickets/' + id),
    api('/api/tickets/' + id + '/entries'),
    api('/api/tickets/' + id + '/waiver').catch(() => null),
    api('/api/documents?ticket_id=' + id).catch(() => []),
    api('/api/tickets/' + id + '/equipment-test/checks').catch(() => null),
    api('/api/tickets/' + id + '/equipment-test').catch(() => null),
  ]);
  let savedTest = initialTest;

  const statusActions = el('div', { class: 'status-actions' });
  for (const next of TRANSITIONS[ticket.status] || []) {
    statusActions.append(el('button', {
      type: 'button',
      class: 'btn btn-status btn-' + next,
      onclick: () => changeStatus(ticket, next),
    }, '→ ' + STATUS_LABELS[next]));
  }
  if (!statusActions.children.length) {
    statusActions.append(el('span', { class: 'muted' }, 'Kein Statuswechsel mehr möglich'));
  }

  const waiverBox = buildWaiverBox(waiver);

  /* --- VDE/DGUV-Geräteprüfung (Schutzklasse-abhängige Checkliste) --- */
  function evaluateLocal(check, value) {
    if (check.direction === 'bool') return value === 'ok';
    const num = Number(value);
    if (!isFinite(num) || num < 0) return false;
    return check.direction === 'max' ? num <= check.limit : num >= check.limit;
  }
  function limitLabel(check) {
    if (check.direction === 'max') return '≤ ' + check.limit + ' ' + check.unit;
    if (check.direction === 'min') return '≥ ' + check.limit + ' ' + check.unit;
    return 'Sichtprüfung';
  }
  function buildEquipmentSection() {
    const wrap = el('section', { class: 'equipment-section' });
    if (!ticket.schutzklasse || !checksData || !checksData.checks) {
      wrap.append(el('details', { class: 'equipment-details' },
        el('summary', {}, '⚡ VDE-Prüfung (DGUV V3 · optional)',
          el('span', { class: 'badge test-verdict' }, 'offen')),
        el('p', { class: 'muted' },
          'Für dieses Gerät ist keine Schutzklasse hinterlegt. Bitte im Geräte-Tab setzen '
          + '(SK I = Schutzleiter/Stecker mit Kontakt, SK II = Doppelisolierung-Symbol, '
          + 'SK III = Schutzkleinspannung). Erst dann kann die Prüfung ausgefüllt werden.')));
      return wrap;
    }
    const summaryBadge = el('span', { class: 'badge test-verdict' },
      savedTest ? (savedTest.verdict === 'bestanden' ? 'bestanden' : 'NICHT bestanden') : 'offen');
    if (savedTest) summaryBadge.classList.add(
      savedTest.verdict === 'bestanden' ? 'test-ok' : 'test-fail');

    const inputs = [];
    const table = el('div', { class: 'equipment-table' });
    for (const check of checksData.checks) {
      const ex = savedTest && savedTest.measurements[check.key];
      const verdict = el('span', { class: 'badge test-verdict' }, ex ? (ex.ok ? 'ok' : 'Mangel') : '—');
      if (ex) verdict.classList.add(ex.ok ? 'test-ok' : 'test-fail');
      let input;
      if (check.direction === 'bool') {
        input = el('select', { class: 'test-input', 'aria-label': check.label },
          el('option', { value: '' }, '– bitte prüfen –'),
          el('option', { value: 'ok' }, 'in Ordnung'),
          el('option', { value: 'mangelhaft' }, 'Mangel festgestellt'));
      } else {
        input = el('input', { class: 'test-input', type: 'number', step: 'any',
          inputmode: 'decimal', min: '0', 'aria-label': check.label,
          placeholder: 'Messwert in ' + check.unit });
      }
      if (ex) input.value = ex.value;
      inputs.push({ check, input, verdict });
      const refresh = () => {
        if (input.value === '') { verdict.textContent = '—'; verdict.className = 'badge test-verdict'; return; }
        const ok = evaluateLocal(check, input.value);
        verdict.textContent = ok ? 'ok' : 'Mangel';
        verdict.className = 'badge test-verdict ' + (ok ? 'test-ok' : 'test-fail');
      };
      input.addEventListener('input', refresh);
      table.append(el('div', { class: 'equipment-row' },
        el('div', { class: 'equipment-label' },
          el('strong', {}, safeText(check.label)),
          el('span', { class: 'muted' }, limitLabel(check) + (check.hint ? ' · ' + check.hint : ''))),
        input, verdict));
    }
    const tester = el('input', { type: 'text', maxlength: 100, placeholder: 'Prüfer *',
      value: (savedTest && savedTest.tester) || localStorage.getItem('rc_author') || '' });
    const notes = el('input', { type: 'text', maxlength: 1000, placeholder: 'Bemerkung (optional)',
      value: (savedTest && savedTest.notes) || '' });
    const saveBtn = el('button', { type: 'button', class: 'btn btn-primary' },
      savedTest ? 'Prüfung aktualisieren' : 'Prüfung speichern');
    const info = el('p', { class: 'muted' });
    if (savedTest) info.textContent = 'Gespeichert: ' + fmtDateTime(savedTest.created_at)
      + (savedTest.tester ? ' · Prüfer: ' + savedTest.tester : '');

    const errBoxEq = fieldErrorBox();
    saveBtn.addEventListener('click', () => withBusy(saveBtn, async () => {
      errBoxEq.hidden = true;
      if (!tester.value.trim()) throw new Error('Prüfer ist erforderlich');
      const payloadMeasurements = {};
      for (const { check, input } of inputs) {
        if (input.value !== '') payloadMeasurements[check.label] = input.value;
      }
      const res = await api('/api/tickets/' + id + '/equipment-test', {
        method: 'POST',
        body: { measurements: payloadMeasurements, tester: tester.value.trim(),
          notes: notes.value.trim() || null },
      });
      savedTest = res;
      showToast('Prüfung gespeichert: ' + (res.verdict === 'bestanden' ? 'BESTANDEN ✓' : 'NICHT bestanden'));
      const fresh = buildEquipmentSection();
      wrap.replaceChildren(...fresh.childNodes);
    }));

    const inner = () => el('div', { class: 'equipment-body' },
      el('p', { class: 'muted' }, 'Schutzklasse SK ' + checksData.protection_class
        + (checksData.heating_kw ? ' · Heizelement ' + checksData.heating_kw + ' kW' : '')
        + ' · Prüfgrundsatz DIN VDE 0701-0702 / DGUV V3'),
      table,
      el('div', { class: 'equipment-meta' }, tester, notes, saveBtn),
      info, errBoxEq);
    wrap.append(el('details', { class: 'equipment-details', open: !savedTest },
      el('summary', {}, '⚡ VDE-Prüfung (DGUV V3 · optional · SK ' + checksData.protection_class + ') ', summaryBadge),
      inner()));
    return wrap;
  }
  const equipmentSection = buildEquipmentSection();

  const journalList = el('div', { class: 'journal' });
  async function reloadJournal() {
    const fresh = await api('/api/tickets/' + id + '/entries');
    journalList.replaceChildren(
      ...(fresh.length ? fresh.map((e) => journalEntry(e, reloadJournal))
        : [emptyHint('Noch keine Einträge im Tagebuch')]));
  }
  journalList.replaceChildren(
    ...(entries.length ? entries.map((e) => journalEntry(e, reloadJournal))
      : [emptyHint('Noch keine Einträge im Tagebuch')]));

  const entryType = el('select', { id: 'je-type', 'aria-label': 'Eintragstyp' },
    ENTRY_TYPES.map((t) => el('option', { value: t }, ENTRY_LABELS[t])));
  const entryText = el('textarea', { id: 'je-text', rows: 2, placeholder: 'Neuer Tagebucheintrag …' });
  const entryBtn = el('button', { type: 'button', class: 'btn btn-primary' }, 'Eintrag hinzufügen');

  async function submitEntry() {
    const content = entryText.value.trim();
    if (!content) { showToast('Eintragstext ist erforderlich'); return; }
    await withBusy(entryBtn, async () => {
      await api('/api/tickets/' + id + '/entries', {
        method: 'POST',
        body: {
          content,
          entry_type: entryType.value,
          author: localStorage.getItem('rc_author') || null,
        },
      });
      entryText.value = '';
      await reloadJournal();
    });
  }
  entryBtn.addEventListener('click', submitEntry);
  entryText.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitEntry();
    }
  });

  /* --- Dokumente/Fotos zu diesem Ticket --- */
  const docList = el('ul', { class: 'mini-list' });
  async function reloadTicketDocs() {
    const fresh = await api('/api/documents?ticket_id=' + id).catch(() => []);
    docList.replaceChildren(...(fresh.length
      ? fresh.map((d) => el('li', {},
          el('strong', {}, safeText(d.title)), ' ',
          el('span', { class: 'badge badge-doc' }, safeText(DOC_LABELS[d.doc_type] || d.doc_type)), ' ',
          d.file_path
            ? el('a', { href: '/api/documents/' + d.id + '/file', target: '_blank', rel: 'noopener' }, 'Anzeigen')
            : el('span', { class: 'muted' }, 'nur URL'), ' ',
          el('button', {
            type: 'button', class: 'btn-txt btn-txt-danger', title: 'Dokument löschen',
            onclick: async () => {
              if (!confirm('Dokument „' + d.title + '" wirklich löschen?')) return;
              await api('/api/documents/' + d.id, { method: 'DELETE' });
              showToast('Dokument gelöscht');
              await reloadTicketDocs();
            },
          }, 'Löschen')))
      : emptyHint('Keine Dokumente zu diesem Laufzettel')));
  }
  reloadTicketDocs();

  const docTitle = el('input', { type: 'text', placeholder: 'Titel *', maxlength: 300 });
  const docType = el('select', { 'aria-label': 'Dokumenttyp' },
    DOC_TYPES.map((t) => el('option', { value: t }, DOC_LABELS[t])));
  const docFile = el('input', { type: 'file', accept: '.pdf,.jpg,.jpeg,.png,.webp' });
  const docBtn = el('button', { type: 'button', class: 'btn' }, 'Hochladen');
  docBtn.addEventListener('click', () => withBusy(docBtn, async () => {
    if (!docTitle.value.trim()) throw new Error('Titel ist erforderlich');
    if (!docFile.files || !docFile.files.length) throw new Error('Bitte eine Datei wählen');
    const fd = new FormData();
    fd.append('file', docFile.files[0]);
    fd.append('title', docTitle.value.trim());
    fd.append('doc_type', docType.value);
    fd.append('ticket_id', id);
    await api('/api/documents', { method: 'POST', body: fd });
    docTitle.value = '';
    docFile.value = '';
    await reloadTicketDocs();
    showToast('Dokument hochgeladen');
  }));

  /* --- Druck-Anhänge: Ankreuzzeilen, Notizlinien, URL (nur @media print) --- */
  const statusLine = (label, value, done) => el('div', { class: 'checkline' },
    el('span', { class: 'checkbox' }),
    el('span', { class: done ? 'done' : '' }, label),
    value ? el('span', { class: 'ts' }, safeText(value)) : null);
  const printChecklines = el('div', { class: 'print-checklines' },
    statusLine('offen', fmtDateTime(ticket.created_at), Boolean(ticket.created_at)),
    statusLine('in Arbeit', fmtDateTime(ticket.started_at), Boolean(ticket.started_at)),
    statusLine('erledigt', fmtDateTime(ticket.finished_at), Boolean(ticket.finished_at)),
    statusLine('nicht reparierbar', fmtDateTime(ticket.finished_at), false),
    statusLine('abgeholt', fmtDateTime(ticket.picked_up_at), Boolean(ticket.picked_up_at)));
  const printNotes = el('div', { class: 'print-notes' },
    el('p', { class: 'notes-title' }, 'Notizen:'),
    ...Array.from({ length: 10 }, () => el('div', { class: 'note-line' })));
  const printUrl = el('div', { class: 'print-url' },
    'Laufzettel im Netz: http://' + location.host + '/#/ticket/' + ticket.id);

  /* --- VDE-Prüfprotokoll im Druck (aus gespeicherter Prüfung) --- */
  let printProtocol;
  if (savedTest && savedTest.measurements) {
    printProtocol = el('div', { class: 'print-equipment' },
      el('p', { class: 'notes-title' },
        '⚡ VDE-Prüfung nach DIN VDE 0701-0702 (DGUV V3) — optional: ',
        savedTest.verdict === 'bestanden' ? 'BESTANDEN' : 'NICHT BESTANDEN',
        ' · Schutzklasse ' + savedTest.protection_class
        + (savedTest.heating_kw ? ' (' + savedTest.heating_kw + ' kW)' : '')),
      ...Object.values(savedTest.measurements).map((m) =>
        el('div', { class: 'checkline' },
          el('span', { class: 'checkbox' }),
          el('span', { class: m.ok ? 'done' : '' }, m.label || ''),
          el('span', { class: 'ts' }, String(m.value) + (m.unit ? ' ' + m.unit : '')))),
      el('p', { class: 'print-waiver-meta' },
        'Prüfer: ' + (savedTest.tester || '—')
        + ' · Geprüft: ' + fmtDateTime(savedTest.created_at)
        + (savedTest.notes ? ' · ' + savedTest.notes : '')));
  } else {
    printProtocol = el('div', { class: 'print-equipment' },
      el('p', { class: 'notes-title' }, '⚡ VDE-Prüfung nach DIN VDE 0701-0702 (DGUV V3) — optional:'),
      schutzklasseHintLines());
  }
  function schutzklasseHintLines() {
    if (!ticket.schutzklasse) {
      return [el('div', { class: 'checkline' },
        el('span', { class: 'checkbox' }),
        el('span', {}, 'Schutzklasse noch nicht hinterlegt (bitte nachtragen)'))];
    }
    const rows = checksData && checksData.checks
      ? checksData.checks.map((c) => el('div', { class: 'checkline' },
          el('span', { class: 'checkbox' }),
          el('span', {}, c.label),
          el('span', { class: 'ts' }, limitLabel(c))))
      : [el('div', { class: 'checkline' },
          el('span', { class: 'checkbox' }),
          el('span', {}, 'Schutzklasse ' + ticket.schutzklasse))];
    return rows;
  }

  /* --- Separates VDE-Messprotokoll (A4-hoch, eigener Druckmodus) --- */
  function buildProtocolPage() {
    const hasSaved = savedTest && savedTest.measurements;
    const checks = checksData && checksData.checks ? checksData.checks : [];
    const sk = hasSaved ? savedTest.protection_class : ticket.schutzklasse;
    const heating = hasSaved ? savedTest.heating_kw
      : (checksData ? checksData.heating_kw : ticket.heating_kw);

    const rows = [];
    if (hasSaved) {
      for (const m of Object.values(savedTest.measurements)) {
        const check = checks.find((c) => c.label === m.label);
        rows.push(el('div', { class: 'protocol-row' },
          el('span', { class: 'pr-name' }, safeText(m.label)),
          el('span', { class: 'pr-limit' }, safeText(check ? limitLabel(check) : '')),
          el('div', { class: 'pr-value' },
            safeText(String(m.value) + (m.unit ? ' ' + m.unit : ''))),
          el('span', { class: 'pr-verdict' }, m.ok ? '✓' : '✗')));
      }
    } else if (checks.length) {
      for (const c of checks) {
        rows.push(el('div', { class: 'protocol-row' },
          el('span', { class: 'pr-name' }, safeText(c.label)),
          el('span', { class: 'pr-limit' }, safeText(limitLabel(c))),
          el('div', { class: 'pr-value' }, ' '),
          el('span', { class: 'pr-verdict' }, ' ')));
      }
    } else {
      rows.push(el('div', { class: 'protocol-row' },
        el('span', { class: 'pr-name' },
          'Schutzklasse noch nicht hinterlegt — bitte im Geräte-Tab setzen'),
        el('span', { class: 'pr-limit' }), el('div', { class: 'pr-value' }, ' '),
        el('span', { class: 'pr-verdict' }, ' ')));
    }

    const metaFill = (label, value) => el('div', { class: 'protocol-meta-item' },
      el('span', { class: 'pm-label' }, safeText(label)),
      el('span', { class: 'pm-value' }, safeText(value || ' ')));

    return el('div', { class: 'print-protocol-page' },
      el('div', { class: 'protocol-page' },
        el('h1', { class: 'protocol-title' },
          'Messprotokoll — Prüfung nach DIN VDE 0701-0702 (DGUV V3)'),
        el('div', { class: 'protocol-head-grid' },
          metaFill('Gerät', ticket.device_name),
          metaFill('Laufzettel', '#' + ticket.id + ' · ' + ticket.fault_description),
          metaFill('Schutzklasse', sk ? 'SK ' + sk + (heating ? ' · ' + heating + ' kW' : '') : '—'),
          metaFill('Prüfdatum', hasSaved ? fmtDateTime(savedTest.created_at) : ''),
          metaFill('Prüfer', hasSaved ? (savedTest.tester || '') : '')),
        el('div', { class: 'protocol-grid protocol-header-row' },
          el('span', { class: 'pr-name' }, 'Messgröße'),
          el('span', { class: 'pr-limit' }, 'Grenzwert'),
          el('span', { class: 'pr-value' }, 'Messwert'),
          el('span', { class: 'pr-verdict' }, 'Bewertung')),
        ...rows,
        el('div', { class: 'protocol-verdict' },
          el('span', { class: 'pv-label' }, 'Gesamturteil:'),
          el('span', { class: 'pv-box pv-' + (hasSaved ? savedTest.verdict : 'leer') },
            hasSaved ? (savedTest.verdict === 'bestanden'
              ? '✓ BESTANDEN — Gerät darf betrieben werden'
              : '✗ NICHT BESTANDEN — keine Inbetriebnahme!')
            : ' ')),
        hasSaved && savedTest.notes
          ? el('p', { class: 'protocol-notes' }, safeText('Bemerkung: ' + savedTest.notes))
          : el('p', { class: 'protocol-notes' }, safeText('Bemerkung: ')),
        el('div', { class: 'protocol-signs' },
          el('div', { class: 'protocol-sign' }, el('div', { class: 'sign-line' }),
            el('span', {}, 'Prüfer (Unterschrift)')),
          el('div', { class: 'protocol-sign' }, el('div', { class: 'sign-line' }),
            el('span', {}, 'Ort, Datum'))),
        el('p', { class: 'protocol-footnote' },
          'Repair-Café-Assistent · Laufzettel im Netz: http://'
          + location.host + '/#/ticket/' + ticket.id
          + (hasSaved ? '' : ' · Blanko-Formular: Messwerte handschriftlich eintragen'))));
  }
  /* Host für das Protokoll wird erst beim Klick mit FRISCHEM Status befüllt
     (nach dem Speichern wäre sonst der Stand vom Seitenaufbau gedruckt). */
  const protoHost = el('div', { class: 'print-protocol-page' });

  function printWithPage(size, before, after) {
    protoHost.replaceChildren(buildProtocolPage());
    let style = document.getElementById('print-page-style');
    if (!style) {
      style = document.createElement('style');
      style.id = 'print-page-style';
      document.head.append(style);
    }
    style.textContent = '@page { size: ' + size + '; margin: 12mm; }';
    const cleanup = () => {
      document.body.classList.remove('printing-protocol');
      const s = document.getElementById('print-page-style');
      if (s) s.remove();
      window.removeEventListener('afterprint', cleanup);
    };
    window.addEventListener('afterprint', cleanup);
    if (before) before();
    window.print();
    setTimeout(cleanup, 120000); // Fallback für Browser ohne afterprint
  }

  /* --- Assistent-Panel (Unit E kommt später: 404 graceful) --- */
  const chatLog = el('div', { class: 'chat-log' });
  const chatInput = el('input', { type: 'text', placeholder: 'Frage an den Assistenten …' });
  const chatBtn = el('button', { type: 'button', class: 'btn' }, 'Senden');
  const chatHistory = [];
  function chatBubble(role, text) {
    chatHistory.push({ role, text });
    chatLog.append(el('div', { class: 'chat-msg chat-' + role }, safeText(text)));
    chatLog.scrollTop = chatLog.scrollHeight;
  }
  async function sendChat() {
    const question = chatInput.value.trim();
    if (!question) return;
    chatBubble('user', question);
    chatInput.value = '';
    try {
      const data = await api('/api/assistant/chat', {
        method: 'POST',
        body: { ticket_id: Number(id), question },
      });
      const answer = (data && (data.answer ?? data.reply ?? data.message)) || 'Leere Antwort';
      chatBubble('assistant', String(answer));
    } catch (err) {
      chatBubble('assistant', 'Assistent ist aktuell nicht verfügbar' +
        (err.message && err.message !== 'Fehler 404' ? ' (' + err.message + ')' : ''));
    }
  }
  chatBtn.addEventListener('click', sendChat);
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); sendChat(); }
  });

  view.replaceChildren(
    el('section', { class: 'ticket-view' },
      el('div', { class: 'panel ticket-main' },
        el('a', { class: 'back-link', href: '#/board' }, '← Board'),
        el('header', { class: 'ticket-head' },
          el('div', {},
            el('h1', {}, safeText(ticket.device_name), ' ',
              schutzklasseBadge(ticket.schutzklasse),
              el('span', { class: 'ticket-no' }, '#' + ticket.id)),
            el('p', { class: 'fault' }, safeText(ticket.fault_description)),
            el('p', { class: 'muted' },
              'Angelegt: ' + fmtDateTime(ticket.created_at),
              ticket.assignee ? ' · Bearbeiter: ' + ticket.assignee : '',
              ticket.status === 'offen' || ticket.status === 'in_arbeit'
                ? ' · Wartezeit: ' + fmtWait(ticket.created_at) : '')),
          statusBadge(ticket.status)),
        statusActions,
        waiverBox,
        equipmentSection,
        printChecklines,
        printNotes,
        printUrl,

        el('h2', {}, 'Tagebuch'),
        journalList,
        el('div', { class: 'entry-form' },
          el('div', { class: 'entry-row' }, entryType, entryText, entryBtn)),

        el('h2', {}, 'Dokumente & Fotos'),
        docList,
        el('div', { class: 'doc-upload' },
          el('div', { class: 'doc-upload-row' }, docTitle, docType),
          el('div', { class: 'doc-upload-row' }, docFile, docBtn))),

      el('aside', { class: 'panel assistant-panel' },
        el('h2', {}, 'Assistent'),
        chatLog,
        el('div', { class: 'chat-input-row' }, chatInput, chatBtn),
        el('button', {
          type: 'button', class: 'btn btn-wide',
          onclick: () => printWithPage('A5 landscape', null, null),
        }, '🖨 Laufzettel drucken'),
        el('button', {
          type: 'button', class: 'btn btn-wide',
          onclick: () => printWithPage('A4 portrait',
            () => document.body.classList.add('printing-protocol'),
            () => document.body.classList.remove('printing-protocol')),
        }, '📄 VDE-Messprotokoll drucken'))));
    /* Protokoll-Host MUSS außerhalb von .ticket-view liegen — sie wird
       im Protokoll-Druck ausgeblendet; drin wäre es immer eine leere Seite. */
    view.append(protoHost);
}

async function changeStatus(ticket, next) {
  if (!confirm('Status wirklich ändern zu „' + STATUS_LABELS[next] + '"?')) return;
  try {
    await api('/api/tickets/' + ticket.id + '/status', { method: 'POST', body: { status: next } });
    showToast('Status geändert: ' + STATUS_LABELS[next]);
  } catch (err) {
    showToast(err.message);
  }
  render();
}

function buildWaiverBox(waiver) {
  if (!waiver) {
    return el('details', { class: 'waiver-box' },
      el('summary', {}, 'Haftungsausschluss'),
      el('p', { class: 'muted' }, 'Kein Haftungsausschluss zum Laufzettel gefunden'));
  }
  const img = el('img', {
    class: 'signature-img',
    src: waiver.signature_url,
    alt: 'Unterschrift von ' + waiver.signed_name,
  });
  img.addEventListener('error', () => {
    img.replaceWith(el('span', { class: 'muted' }, 'Signaturbild nicht verfügbar'));
  });
  return el('details', { class: 'waiver-box' },
    el('summary', {},
      'Haftungsausschluss – unterschrieben von ' + waiver.signed_name + ' am ' + fmtDateTime(waiver.signed_at)),
    el('div', { class: 'waiver-box-body' },
      el('img', { src: waiver.signature_url, alt: 'Unterschrift', class: 'signature-img' }),
      el('p', { class: 'muted print-waiver-meta' },
        'Version ' + waiver.waiver_version + ' · unterschrieben am ' + fmtDateTime(waiver.signed_at))));
}

function journalEntry(entry, onChanged) {
  const contentWrap = el('div', { class: 'journal-content-wrap' });
  function drawStatic() {
    contentWrap.replaceChildren(
      el('p', { class: 'journal-content' }, safeText(entry.content)));
  }
  drawStatic();

  function startEdit() {
    const ta = el('textarea', { class: 'edit-content', rows: 3, maxlength: 5000 });
    ta.value = entry.content;
    const typeSel = el('select', { class: 'edit-type', 'aria-label': 'Eintragstyp' },
      ENTRY_TYPES.map((t) => el('option', { value: t }, ENTRY_LABELS[t])));
    typeSel.value = entry.entry_type;
    const saveB = el('button', { type: 'button', class: 'btn btn-small btn-primary' }, 'Speichern');
    const cancelB = el('button', { type: 'button', class: 'btn btn-small' }, 'Abbrechen');
    const errB = fieldErrorBox();
    saveB.addEventListener('click', () => withBusy(saveB, async () => {
      if (!ta.value.trim()) throw new Error('Inhalt ist erforderlich');
      const updated = await api(
        '/api/tickets/' + entry.ticket_id + '/entries/' + entry.id, {
        method: 'PATCH',
        body: { content: ta.value, entry_type: typeSel.value,
          author: localStorage.getItem('rc_author') || null },
      });
      Object.assign(entry, updated);
      drawStatic();
      showToast('Eintrag korrigiert');
      onChanged && onChanged();
    }));
    cancelB.addEventListener('click', drawStatic);
    contentWrap.replaceChildren(
      ta, errB,
      el('div', { class: 'entry-row' }, typeSel, saveB, cancelB));
    ta.focus();
  }

  const delButton = el('button', {
    type: 'button', class: 'btn-txt btn-txt-danger', title: 'Eintrag löschen',
    onclick: async () => {
      if (!confirm('Diesen Tagebucheintrag wirklich löschen?')) return;
      await api('/api/tickets/' + entry.ticket_id + '/entries/' + entry.id, { method: 'DELETE' });
      showToast('Eintrag gelöscht');
      onChanged && onChanged();
    },
  }, 'Löschen');
  const editBtn = el('button', { type: 'button', class: 'btn-txt', onclick: startEdit }, 'Bearbeiten');
  const edited = entry.edited_at
    ? el('span', {
        class: 'journal-edited',
        title: 'Zuletzt geändert: ' + fmtDateTime(entry.edited_at)
          + (entry.edited_by ? ' von ' + entry.edited_by : ''),
      }, ' (bearbeitet)')
    : null;

  return el('article', { class: 'journal-entry' },
    el('header', { class: 'journal-head' },
      entryBadge(entry.entry_type),
      el('span', { class: 'journal-author' }, safeText(entry.author || 'unbekannt')),
      el('time', { class: 'journal-time', datetime: entry.created_at }, safeText(fmtDateTime(entry.created_at))),
      edited,
      el('span', { class: 'journal-actions' }, editBtn, delButton)),
    contentWrap);
}

/* ====================== SUCHE ====================== */

async function renderSearch() {
  const input = el('input', {
    type: 'search', id: 'search-input', placeholder: 'Suche in Tagebuch & Dokumenten …',
  });
  const btn = el('button', { type: 'button', class: 'btn btn-primary' }, 'Suchen');
  const results = el('div', { id: 'search-results' },
    emptyHint('Begriff eingeben und „Suchen" klicken'));

  async function run() {
    const q = input.value.trim();
    if (!q) { showToast('Suchbegriff erforderlich'); return; }
    await withBusy(btn, async () => {
      const data = await api('/api/search?q=' + encodeURIComponent(q));
      const jSection = data.journal.length
        ? el('div', { class: 'result-group' },
            el('h2', {}, 'Tagebuch (' + data.journal.length + ')'),
            data.journal.map((hit) => el('a', {
              class: 'card result-card', href: '#/ticket/' + hit.ticket_id,
            },
              el('strong', {}, safeText(hit.device_name)),
              el('span', { class: 'badge badge-entry-' + hit.entry_type }, safeText(ENTRY_LABELS[hit.entry_type] || hit.entry_type)),
              el('p', { class: 'card-fault' }, safeText(truncate(hit.fault_description, 100))),
              el('p', { class: 'snippet' }, safeText(truncate(hit.snippet, 200))))))
        : el('div', { class: 'result-group' },
            el('h2', {}, 'Tagebuch'),
            emptyHint('Keine Tagebuch-Treffer'));

      const dSection = data.documents.length
        ? el('div', { class: 'result-group' },
            el('h2', {}, 'Dokumente (' + data.documents.length + ')'),
            data.documents.map((hit) => el('div', { class: 'card result-card' },
              el('strong', {}, safeText(hit.snippet)),
              hit.file_path
                ? el('a', { href: '/api/documents/' + hit.id + '/file', target: '_blank', rel: 'noopener' }, 'Datei öffnen')
                : el('span', { class: 'muted' }, 'keine Datei'),
              hit.device_id ? el('span', { class: 'muted' }, ' · Gerät ' + hit.device_id) : null,
              hit.ticket_id ? el('a', { href: '#/ticket/' + hit.ticket_id }, ' · Laufzettel #' + hit.ticket_id) : null)))
        : el('div', { class: 'result-group' },
            el('h2', {}, 'Dokumente'),
            emptyHint('Keine Dokument-Treffer'));

      results.replaceChildren(jSection, dSection);
    });
  }

  btn.addEventListener('click', run);
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); run(); } });

  view.replaceChildren(
    el('section', { class: 'panel' },
      el('h1', {}, 'Suche'),
      el('div', { class: 'search-row' }, input, btn),
      results));
}

/* ====================== DOKUMENTE ====================== */

async function renderDocuments() {
  const [docs, devices] = await Promise.all([
    api('/api/documents'),
    api('/api/devices').catch(() => []),
  ]);

  const errBox = fieldErrorBox();
  const deviceSel = el('select', { id: 'doc-device' },
    el('option', { value: '' }, 'kein Gerät'),
    devices.map((d) => el('option', { value: String(d.id) }, safeText(d.name))));

  /* Tab 1: Datei */
  const fTitle = el('input', { type: 'text', placeholder: 'Titel *', maxlength: 300 });
  const fType = el('select', { 'aria-label': 'Dokumenttyp' },
    DOC_TYPES.map((t) => el('option', { value: t }, DOC_LABELS[t])));
  const fFile = el('input', { type: 'file', accept: '.pdf,.jpg,.jpeg,.png,.webp' });
  const fDevSel = deviceSel.cloneNode(true);
  fDevSel.id = '';
  const fileForm = el('form', { class: 'form' },
    el('div', { class: 'form-row' }, el('label', {}, 'Titel *'), fTitle),
    el('div', { class: 'form-row' }, el('label', {}, 'Typ'), fType),
    el('div', { class: 'form-row' }, el('label', {}, 'Datei * (pdf/jpg/png/webp, max. 20 MB)'), fFile),
    el('div', { class: 'form-row' }, el('label', {}, 'Gerät'), fDevSel),
    el('button', { type: 'submit', class: 'btn btn-primary' }, 'Dokument hochladen'));

  /* Tab 2: URL */
  const uTitle = el('input', { type: 'text', placeholder: 'Titel *', maxlength: 300 });
  const uUrl = el('input', { type: 'url', placeholder: 'https://…' });
  const uType = el('select', { 'aria-label': 'Dokumenttyp' },
    DOC_TYPES.map((t) => el('option', { value: t }, DOC_LABELS[t])));
  const uDevSel = deviceSel.cloneNode(true);
  uDevSel.id = '';
  const urlForm = el('form', { class: 'form' },
    el('div', { class: 'form-row' }, el('label', {}, 'Titel *'), uTitle),
    el('div', { class: 'form-row' }, el('label', {}, 'URL *'), uUrl),
    el('div', { class: 'form-row' }, el('label', {}, 'Typ'), uType),
    el('div', { class: 'form-row' }, el('label', {}, 'Gerät'), uDevSel),
    el('button', { type: 'submit', class: 'btn btn-primary' }, 'URL-Dokument anlegen'));

  const tabFile = el('button', { type: 'button', class: 'tab active', dataset: { tab: 'file' } }, 'Datei');
  const tabUrl = el('button', { type: 'button', class: 'tab', dataset: { tab: 'url' } }, 'URL');
  const filePane = el('div', { class: 'tab-pane' }, fileForm);
  const urlPane = el('div', { class: 'tab-pane', hidden: true }, urlForm);
  [tabFile, tabUrl].forEach((t) => t.addEventListener('click', () => {
    tabFile.classList.toggle('active', t === tabFile);
    tabUrl.classList.toggle('active', t === tabUrl);
    filePane.hidden = t !== tabFile;
    urlPane.hidden = t !== tabUrl;
  }));

  const list = el('div', { class: 'doc-list' });

  function docRow(d) {
    const delBtn = el('button', {
      type: 'button', class: 'btn btn-small btn-danger',
      onclick: async () => {
        if (!confirm('Dokument „' + d.title + '" wirklich löschen?')) return;
        await api('/api/documents/' + d.id, { method: 'DELETE' });
        showToast('Dokument gelöscht');
        await reloadList();
      },
    }, 'Löschen');
    return el('div', { class: 'card doc-row' },
      el('div', { class: 'doc-info' },
        el('strong', {}, safeText(d.title)),
        el('span', { class: 'badge badge-doc' }, safeText(DOC_LABELS[d.doc_type] || d.doc_type)),
        d.device_id ? el('span', { class: 'muted' }, 'Gerät ' + d.device_id) : null,
        d.ticket_id ? el('a', { href: '#/ticket/' + d.ticket_id }, 'Laufzettel #' + d.ticket_id) : null),
      el('div', { class: 'doc-actions' },
        d.file_path
          ? el('a', { class: 'btn btn-small', href: '/api/documents/' + d.id + '/file', target: '_blank', rel: 'noopener' }, 'Anzeigen')
          : null,
        d.url
          ? el('a', { class: 'btn btn-small', href: d.url, target: '_blank', rel: 'noopener' }, 'Herunterladen')
          : null,
        d.url && !d.file_path
          ? el('button', {
              type: 'button', class: 'btn btn-small', dataset: { fetch: String(d.id) },
              onclick: (e) => withBusy(e.currentTarget, async () => {
                await api('/api/documents/' + d.id + '/fetch', { method: 'POST' });
                showToast('Datei serverseitig geholt');
                await reloadList();
              }),
            }, 'Jetzt herunterladen')
          : null,
        delBtn));
  }

  async function reloadList() {
    const fresh = await api('/api/documents');
    list.replaceChildren(...(fresh.length
      ? fresh.map(docRow)
      : emptyHint('Noch keine Dokumente')));
  }

  async function submitFile(e) {
    e.preventDefault();
    if (!fTitle.value.trim()) throw new Error('Titel ist erforderlich');
    if (!fFile.files || !fFile.files.length) throw new Error('Bitte eine Datei wählen');
    const fd = new FormData();
    fd.append('file', fFile.files[0]);
    fd.append('title', fTitle.value.trim());
    fd.append('doc_type', fType.value);
    if (fDevSel.value) fd.append('device_id', fDevSel.value);
    await api('/api/documents', { method: 'POST', body: fd });
    fTitle.value = ''; fFile.value = '';
    await reloadList();
    showToast('Dokument hochgeladen');
  }
  async function submitUrl(e) {
    e.preventDefault();
    if (!uTitle.value.trim()) throw new Error('Titel ist erforderlich');
    const url = uUrl.value.trim();
    if (!(url.startsWith('http://') || url.startsWith('https://'))) {
      throw new Error('URL muss mit http:// oder https:// beginnen');
    }
    await api('/api/documents', {
      method: 'POST',
      body: {
        title: uTitle.value.trim(), url,
        doc_type: uType.value,
        device_id: uDevSel.value ? Number(uDevSel.value) : null,
      },
    });
    uTitle.value = ''; uUrl.value = '';
    await reloadList();
    showToast('URL-Dokument angelegt');
  }
  fileForm.addEventListener('submit', (e) => withBusySubmit(fileForm, submitFile, e, errBox));
  urlForm.addEventListener('submit', (e) => withBusySubmit(urlForm, submitUrl, e, errBox));

  view.replaceChildren(
    el('section', { class: 'panel' },
      el('h1', {}, 'Dokumente'),
      el('div', { class: 'tabs' }, tabFile, tabUrl),
      filePane, urlPane,
      errBox,
      el('h2', {}, 'Alle Dokumente'),
      list));

  await reloadList().catch((err) => {
    list.replaceChildren(emptyHint('Dokumente konnten nicht geladen werden: ' + err.message));
  });
}

/** Formular-Submit-Wrapper: validiert, zeigt Fehler im Panel, sperren während Request. */
async function withBusySubmit(form, fn, event, errBox) {
  event.preventDefault();
  errBox.hidden = true;
  const submit = form.querySelector('[type="submit"]');
  if (submit) submit.disabled = true;
  try {
    await fn(event);
  } catch (err) {
    showFieldError(errBox, err);
  } finally {
    if (submit) submit.disabled = false;
  }
}

/* ====================== GERÄTE ====================== */

async function renderDevices() {
  const devices = await api('/api/devices');
  const errBox = fieldErrorBox();

  const searchInput = el('input', {
    type: 'search', placeholder: 'Geräte durchsuchen …', 'aria-label': 'Geräte suchen',
  });
  const searchBtn = el('button', { type: 'button', class: 'btn' }, 'Suchen');
  const list = el('div', { class: 'device-list' });

  async function drawList(items) {
    if (!items.length) { list.replaceChildren(emptyHint('Keine Geräte gefunden')); return; }
    const tickets = await api('/api/tickets').catch(() => []);
    list.replaceChildren(...items.map((d) => deviceRow(d, tickets)));
  }

  async function runSearch() {
    const q = searchInput.value.trim();
    const items = q ? await api('/api/devices?q=' + encodeURIComponent(q)) : await api('/api/devices');
    await drawList(items);
  }
  searchBtn.addEventListener('click', () => withBusy(searchBtn, runSearch));
  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); withBusy(searchBtn, runSearch); }
  });

  /* Anlegen */
  const nameInput = el('input', { type: 'text', placeholder: 'Name *', maxlength: 200 });
  const catInput = el('input', { type: 'text', placeholder: 'Kategorie', maxlength: 500 });
  const manInput = el('input', { type: 'text', placeholder: 'Hersteller', maxlength: 500 });
  const modInput = el('input', { type: 'text', placeholder: 'Modell', maxlength: 500 });
  const skInput = el('select', { 'aria-label': 'Schutzklasse' },
    el('option', { value: '' }, 'Schutzklasse…'),
    el('option', { value: 'I' }, 'SK I'),
    el('option', { value: 'II' }, 'SK II'),
    el('option', { value: 'III' }, 'SK III'));
  const heatInput = el('input', { type: 'number', step: 'any', min: '0', placeholder: 'kW (Heizelement)' });
  const createForm = el('form', { class: 'device-create' },
    nameInput, catInput, manInput, modInput, skInput, heatInput,
    el('button', { type: 'submit', class: 'btn btn-primary' }, 'Gerät anlegen'));
  createForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    errBox.hidden = true;
    const btn = createForm.querySelector('[type="submit"]');
    btn.disabled = true;
    try {
      const device = await api('/api/devices', {
        method: 'POST',
        body: {
          name: nameInput.value.trim(),
          category: catInput.value.trim() || null,
          manufacturer: manInput.value.trim() || null,
          model: modInput.value.trim() || null,
          schutzklasse: skInput.value || null,
          heating_kw: heatInput.value.trim() ? Number(heatInput.value) : null,
        },
      });
      nameInput.value = catInput.value = manInput.value = modInput.value = '';
      skInput.value = ''; heatInput.value = '';
      showToast('Gerät "' + device.name + '" angelegt');
      await drawList(await api('/api/devices'));
    } catch (err) {
      showFieldError(errBox, err);
    } finally {
      btn.disabled = false;
    }
  });

  view.replaceChildren(
    el('section', { class: 'panel' },
      el('h1', {}, 'Geräte'),
      createForm,
      errBox,
      el('div', { class: 'search-row' }, searchInput, searchBtn),
      list));

  await drawList(devices).catch((err) => {
    list.replaceChildren(emptyHint('Geräte konnten nicht geladen werden: ' + err.message));
  });
}

function deviceRow(device, tickets) {
  const details = el('div', { class: 'device-details', hidden: true });
  const head = el('button', {
    type: 'button', class: 'device-row',
    onclick: async () => {
      const open = !details.hidden;
      details.hidden = open;
      head.classList.toggle('open', !open);
      if (!details.hidden && !details.dataset.loaded) {
        details.dataset.loaded = '1';
        details.replaceChildren(el('p', { class: 'muted' }, 'Lade …'));
        try {
          let [full, docs] = await Promise.all([
            api('/api/devices/' + device.id),
            api('/api/documents?device_id=' + device.id).catch(() => []),
          ]);
          const myTickets = tickets.filter((t) => t.device_id === device.id);
          const renderDetail = () => {
            const infoRows = [
              ['Kategorie', full.category], ['Hersteller', full.manufacturer],
              ['Modell', full.model], ['Seriennummer', full.serial_number],
              ['Schutzklasse', full.schutzklasse ? 'SK ' + full.schutzklasse : null],
              ['Heizleistung', full.heating_kw != null ? full.heating_kw + ' kW' : null],
              ['Eigentümer', full.owner_name], ['Kontakt', full.owner_contact],
              ['Zubehör', full.accessories],
            ].filter(([, v]) => v);
            const skEditor = el('div', { class: 'sk-editor' });
            const skSel = el('select', { 'aria-label': 'Schutzklasse wählen' },
              el('option', { value: '' }, 'unbekannt / nicht eingestuft'),
              ...['I', 'II', 'III'].map((c) => el('option', { value: c }, SK_LABELS[c])));
            skSel.value = full.schutzklasse || '';
            const heatIn = el('input', { type: 'number', step: 'any', min: '0',
              placeholder: 'z. B. 2 (wenn Heizelement)',
              value: full.heating_kw == null ? '' : String(full.heating_kw) });
            const skSave = el('button', { type: 'button', class: 'btn btn-small' }, 'Schutzklasse speichern');
            skSave.addEventListener('click', () => withBusy(skSave, async () => {
              const heatText = heatIn.value.trim();
              if (heatText && (!isFinite(Number(heatText)) || Number(heatText) <= 0)) {
                throw new Error('Heizleistung muss eine Zahl größer 0 sein');
              }
              const upd = await api('/api/devices/' + device.id, {
                method: 'PATCH',
                body: { schutzklasse: skSel.value || null,
                  heating_kw: heatText ? Number(heatText) : null },
              });
              full = upd;
              showToast('Schutzklasse gespeichert (SK ' + (upd.schutzklasse || '—') + ')');
              renderDetail();
            }));
            skEditor.append(
              el('div', { class: 'form-row' },
                el('label', {}, 'Schutzklasse (VDE/DGUV-Prüfung)'), skSel),
              el('div', { class: 'form-row' },
                el('label', {}, 'Heizleistung in kW (nur bei Heizelementen)'), heatIn),
              skSave);
            details.replaceChildren(
              el('div', { class: 'device-meta' }, infoGrid(infoRows)),
              skEditor,
              el('h4', {}, 'Laufzettel-Historie'),
            myTickets.length
                ? el('ul', { class: 'mini-list' },
                    myTickets.map((t) => el('li', {},
                      el('a', { href: '#/ticket/' + t.id }, '#' + t.id + ' ' + STATUS_LABELS[t.status]),
                      ' ', el('span', { class: 'muted' }, safeText(fmtDate(t.created_at))),
                      ' ', statusBadge(t.status))))
                : emptyHint('Keine Laufzettel'),
              el('h4', {}, 'Dokumente'),
              docs.length
                ? el('ul', { class: 'mini-list' },
                    docs.map((d) => el('li', {},
                      el('strong', {}, safeText(d.title)),
                      d.file_path ? el('a', { href: '/api/documents/' + d.id + '/file', target: '_blank', rel: 'noopener' }, 'Anzeigen') : null)))
                : emptyHint('Keine Dokumente'));
          };
          renderDetail();
        } catch (err) {
          details.replaceChildren(errorBox(err.message));
        }
      }
    },
  },
    el('span', { class: 'device-name' }, safeText(device.name)),
    el('span', { class: 'muted' }, safeText([device.manufacturer, device.model].filter(Boolean).join(' ') || '')),
    el('span', { class: 'chevron', 'aria-hidden': 'true' }, '▸'));

  return el('div', { class: 'card device-card' }, head, details);
}

/* ====================== Start ====================== */

if (!location.hash) location.hash = '#/board';
render();

/* ====================== Techniker:in-Name (localStorage) ====================== */

(function initAuthorField() {
  const input = document.getElementById('nav-author');
  if (!input) return;
  input.value = localStorage.getItem('rc_author') || '';
  input.addEventListener('change', () => {
    const v = input.value.trim();
    if (v) localStorage.setItem('rc_author', v);
    else localStorage.removeItem('rc_author');
    showToast(v ? 'Name gesetzt — neue Einträge erscheinen mit deinem Namen' : 'Name entfernt');
  });
})();