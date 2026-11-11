import { h, icon } from '../dom.js';
import { askTutor, registerDecision, ApiError, imageUrl } from '../api.js';
import { mmss, LEVEL_LABELS } from '../format.js';
import { errorBox } from './shared.js';

function viewer(scenario) {
  let scale = 1, tx = 0, ty = 0, drag = null;
  const img = h('img', { src: imageUrl(scenario.imagen_url), alt: `Esquema cervical sintético del caso ${scenario.caso_id}`, draggable: 'false' });
  const stage = h('div', { class: 'viewer-stage', tabindex: '0', 'aria-label': 'Imagen del caso. Usa los botones para acercar o alejar.' }, img,
    h('span', { class: 'viewer-tag' }, 'ESQUEMA DE SIMULACIÓN · NO CLÍNICO'));
  const pct = h('span', { class: 'zoom-pct' }, '100 %');
  const apply = () => {
    img.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
    pct.textContent = `${Math.round(scale * 100)} %`;
  };
  const zoom = (delta) => {
    scale = Math.min(4, Math.max(0.5, +(scale + delta).toFixed(2)));
    if (scale <= 1) { tx = 0; ty = 0; }
    apply();
  };
  stage.addEventListener('wheel', (e) => { e.preventDefault(); zoom(e.deltaY < 0 ? 0.25 : -0.25); }, { passive: false });
  stage.addEventListener('pointerdown', (e) => { if (scale > 1) { drag = { x: e.clientX - tx, y: e.clientY - ty }; stage.setPointerCapture(e.pointerId); } });
  stage.addEventListener('pointermove', (e) => { if (drag) { tx = e.clientX - drag.x; ty = e.clientY - drag.y; apply(); } });
  stage.addEventListener('pointerup', () => { drag = null; });
  const btn = (label, name, fn) => h('button', { type: 'button', class: 'icon-btn', 'aria-label': label, title: label, onclick: fn }, icon(name, 18));
  const hintBox = scenario.pistas.length
    ? h('div', { class: 'viewer-foot' }, icon('info', 16), h('div', {}, h('strong', {}, 'Pistas del nivel ' + LEVEL_LABELS[scenario.nivel] + ': '), h('ul', {}, scenario.pistas.map((p) => h('li', {}, p)))))
    : h('div', { class: 'viewer-foot' }, icon('info', 16), h('span', {}, 'Observa la distribución y los bordes del área de contraste antes de decidir.'));
  return h('section', { class: 'viewer', 'aria-label': 'Visor 2D' },
    h('div', { class: 'viewer-head' }, h('span', { class: 'viewer-title' }, icon('expand', 16), h('span', {}, `Visor 2D · ${scenario.modalidad}`)),
      h('div', { class: 'viewer-tools' }, pct, btn('Alejar', 'zoomOut', () => zoom(-0.25)), btn('Acercar', 'zoomIn', () => zoom(0.25)),
        btn('Pantalla completa', 'expand', () => { if (stage.requestFullscreen) stage.requestFullscreen(); }))),
    stage, hintBox);
}

function tutorPanel(state, aiNotice) {
  const sid = state.session.sesion_id;
  const log = h('div', { class: 'chat', 'aria-live': 'polite' });
  const empty = h('p', { class: 'chat-empty' }, 'Pide una sugerencia al tutor cuando la necesites. Decidir sin consultarlo también es válido.');
  log.append(empty);
  const counter = h('span', { class: 'muted small' }, '');
  const input = h('input', { type: 'text', maxlength: '500', placeholder: 'Escribe una consulta para el tutor', 'aria-label': 'Consulta para el tutor' });
  const send = h('button', { type: 'submit', class: 'btn secondary' }, 'Enviar');
  const ask = h('button', { type: 'button', class: 'btn ghost block' }, 'Pedir sugerencia al tutor');
  let first = true, busy = false;

  const push = (cls, text, meta) => {
    empty.remove();
    const bubble = h('div', { class: `bubble ${cls}` }, h('p', {}, text), meta ? h('span', { class: 'bubble-meta' }, meta) : null);
    log.append(bubble);
    log.scrollTop = log.scrollHeight;
    return bubble;
  };
  const setBusy = (v) => { busy = v; input.disabled = v; send.disabled = v; ask.disabled = v; };

  async function consult(message) {
    if (busy) return;
    setBusy(true);
    if (message) push('user', message);
    const loading = push('loading', 'El tutor está analizando el caso…');
    loading.prepend(h('span', { class: 'spinner', 'aria-hidden': 'true' }));
    try {
      const r = await askTutor(sid, message);
      loading.remove();
      push('tutor', r.texto, `Tutor IA · consulta ${r.indice}${r.fuente === 'respaldo' ? ' · respuesta de respaldo' : ''}`);
      counter.textContent = `Consultas restantes: ${r.restantes}`;
      first = false;
      ask.hidden = true;
    } catch (err) {
      loading.remove();
      push('error', (err instanceof ApiError ? err.message : 'No pudimos obtener la sugerencia.') + ' Puedes continuar sin ella.');
    } finally {
      setBusy(false);
      input.value = '';
    }
  }
  ask.addEventListener('click', () => consult(null));
  const form = h('form', { class: 'chat-form', onsubmit: (e) => { e.preventDefault(); const m = input.value.trim(); if (m) consult(m); } }, input, send);
  return h('section', { class: 'card tutor', 'aria-label': 'Agente Tutor IA' },
    h('div', { class: 'tutor-head' }, h('span', { class: 'tutor-ico' }, icon('bot', 18)),
      h('div', {}, h('strong', {}, 'Agente Tutor IA'), h('div', { class: 'muted small' }, 'Asistencia para el aprendizaje'))),
    log, ask, form,
    h('div', { class: 'tutor-foot' }, h('span', { class: 'muted small' }, icon('info', 14), ' ' + aiNotice), counter));
}

function decisionPanel(state, actions) {
  const sid = state.session.sesion_id;
  const sc = state.scenario;
  const errorSlot = h('div', { 'aria-live': 'polite' });
  const value = h('span', { class: 'conf-value' }, '3 / 5');
  const slider = h('input', { type: 'range', id: 'confianza', min: '1', max: '5', step: '1', value: '3', 'aria-label': 'Nivel de confianza de 1 a 5' });
  slider.addEventListener('input', () => { value.textContent = `${slider.value} / 5`; });
  const select = h('select', { id: 'interpretacion' }, h('option', { value: '' }, 'Selecciona una opción…'),
    sc.opciones.map((o) => h('option', { value: o.codigo }, o.etiqueta)));
  const submit = h('button', { type: 'button', class: 'btn primary block', disabled: true }, h('span', {}, 'Registrar Decisión'), icon('arrow', 16));
  select.addEventListener('change', () => { submit.disabled = !select.value; });
  submit.addEventListener('click', async () => {
    errorSlot.replaceChildren();
    submit.disabled = true;
    try {
      await registerDecision(sid, select.value, Number(slider.value));
      actions.onDecided();
    } catch (err) {
      errorSlot.append(errorBox(err instanceof ApiError ? err.message : 'No se pudo registrar la decisión.'));
      submit.disabled = !select.value;
    }
  });
  return h('section', { class: 'card decision', 'aria-label': 'Registrar decisión' },
    h('div', { class: 'card-head' }, h('h3', {}, 'Calibración de Confianza'), value),
    slider,
    h('div', { class: 'scale-labels' }, h('span', {}, 'Muy baja'), h('span', {}, 'Muy alta')),
    h('label', { class: 'label', for: 'interpretacion' }, 'Interpretación'), select,
    errorSlot, submit,
    h('p', { class: 'muted small center' }, 'Tu decisión se contrastará con la referencia docente.'));
}

export function renderSimulacion(state, actions) {
  const sc = state.scenario;
  const timer = h('span', { class: 'timer', 'aria-label': 'Tiempo transcurrido' }, mmss(sc.transcurrido_s || 0));
  let elapsed = sc.transcurrido_s || 0;
  const id = setInterval(() => { elapsed += 1; timer.textContent = mmss(elapsed); }, 1000);
  actions.setCleanup(() => clearInterval(id));
  return h('main', { class: 'page wide' },
    h('div', { class: 'page-head' },
      h('div', {}, h('h1', { class: 'h1-sm' }, 'Entorno de Simulación'),
        h('p', { class: 'muted' }, `Caso ${sc.caso_id} · ${sc.titulo} · Nivel ${LEVEL_LABELS[sc.nivel]}`)),
      h('div', { class: 'head-right' }, h('span', { class: 'pill' }, 'Caso de simulación'), h('span', { class: 'clock' }, icon('clock', 16), timer))),
    h('div', { class: 'sim-grid' }, viewer(sc), h('div', { class: 'side' }, tutorPanel(state, state.aiNotice), decisionPanel(state, actions))));
}
