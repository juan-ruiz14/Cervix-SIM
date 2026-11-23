import { h, icon } from '../dom.js';
import { askTutor, registerDecision, ApiError, imageUrl } from '../api.js';
import { mmss, LEVEL_LABELS } from '../format.js';
import { errorBox } from './shared.js';

// Visor 3D del caso: arrastrar para girar, rueda o botones para acercar. Sin puntos ni marcas sobre el modelo.
function viewer(scenario, actions) {
  const status = h('div', { class: 'viewer-status', role: 'status' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), h('span', {}, 'Cargando modelo 3D…'));
  const stage = h('div', { class: 'viewer-stage', tabindex: '0',
    'aria-label': 'Visor 3D del caso. Arrastra para girar el modelo y usa la rueda o los botones para acercar o alejar.' },
    h('span', { class: 'vtag tl' }, 'Modelo 3D · Sintético'),
    h('span', { class: 'vtag tr' }, 'No diagnóstico'),
    h('div', { class: 'vcase' }, icon('file', 16), h('div', {}, h('strong', {}, `Caso ${scenario.caso_numero} de ${scenario.total_casos}`), h('span', {}, 'Datos 100 % sintéticos'))),
    h('div', { class: 'vcap' }, h('div', {}, 'Arrastra para girar'), h('div', {}, 'Representación educativa, no imagen clínica')),
    status);
  let api = null, disposed = false;
  const tool = (label, name, fn) => h('button', { type: 'button', class: 'icon-btn', 'aria-label': label, title: label, onclick: () => api && fn() }, icon(name, 18));
  stage.append(h('div', { class: 'vtools' },
    tool('Acercar', 'zoomIn', () => api.zoom(0.8)), tool('Alejar', 'zoomOut', () => api.zoom(1.25)),
    tool('Restablecer vista', 'scan', () => api.reset()),
    tool('Pantalla completa', 'expand', () => { if (stage.requestFullscreen) stage.requestFullscreen(); })));

  import('../model3d.js')
    .then(({ createViewer }) => createViewer(stage, imageUrl(scenario.modelo_url), {
      onProgress: (p) => { status.lastChild.textContent = `Cargando modelo 3D… ${Math.round(p * 100)} %`; },
    }))
    .then((v) => { if (disposed) { v.dispose(); } else { api = v; status.remove(); } })
    .catch((err) => {
      console.error('Visor 3D', err);
      status.replaceChildren(h('span', {}, 'No se pudo cargar el visor 3D. Recarga la página; si persiste, avisa al equipo.'));
      status.classList.add('error');
    });
  const prevCleanup = actions.getCleanup();
  actions.setCleanup(() => { disposed = true; if (api) api.dispose(); if (prevCleanup) prevCleanup(); });

  const foot = scenario.pistas.length
    ? h('div', { class: 'viewer-foot' }, icon('info', 16), h('div', {}, h('strong', {}, `Pistas del nivel ${LEVEL_LABELS[scenario.nivel]}`),
        h('ul', {}, scenario.pistas.map((p) => h('li', {}, p)))))
    : h('div', { class: 'viewer-foot' }, icon('info', 16), h('span', {}, 'Gira el modelo y observa la superficie: color, relieve y bordes.'));
  return h('section', { class: 'viewer', 'aria-label': 'Visor 3D del caso' }, stage, foot);
}

function tutorPanel(state, aiNotice) {
  const sid = state.session.sesion_id;
  const log = h('div', { class: 'chat', 'aria-live': 'polite' });
  const empty = h('p', { class: 'chat-empty' }, 'Pide una sugerencia al tutor o escríbele una pregunta. Decidir sin consultarlo también es válido.');
  log.append(empty);
  const counter = h('span', { class: 'muted small' }, '');
  const input = h('input', { type: 'text', maxlength: '500', placeholder: 'Escríbele una consulta al tutor', 'aria-label': 'Consulta para el tutor' });
  const send = h('button', { type: 'submit', class: 'btn secondary' }, 'Enviar');
  const ask = h('button', { type: 'button', class: 'btn ghost block' }, icon('sparkle', 16), h('span', {}, 'Pedir sugerencia al tutor'));
  let busy = false;

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
    const loading = push('loading', 'El tutor está analizando el caso');
    loading.append(h('span', { class: 'dots', 'aria-hidden': 'true' }, h('i'), h('i'), h('i')));
    try {
      const r = await askTutor(sid, message);
      loading.remove();
      push('tutor', r.texto, `Tutor IA · consulta ${r.indice}${r.fuente === 'respaldo' ? ' · respuesta de respaldo' : ''}`);
      counter.textContent = `Consultas restantes: ${r.restantes}`;
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
    h('div', { class: 'tutor-head' }, h('span', { class: 'tutor-ico' }, icon('sparkle', 18)),
      h('div', {}, h('strong', {}, 'Agente Tutor IA'), h('div', { class: 'muted small' }, 'Sugerencia simulada para el ejercicio'))),
    log, ask, form,
    h('div', { class: 'tutor-foot' }, h('span', { class: 'muted small' }, icon('info', 14), h('span', {}, aiNotice + ' Contrástala con tu propia observación.')), counter));
}

function decisionPanel(state, actions) {
  const sid = state.session.sesion_id;
  const sc = state.scenario;
  const errorSlot = h('div', { 'aria-live': 'polite' });
  const value = h('span', { class: 'conf-value' }, '3 de 5');
  const slider = h('input', { type: 'range', class: 'range', id: 'confianza', min: '1', max: '5', step: '1', value: '3', 'aria-label': 'Nivel de confianza de 1 a 5' });
  const paint = () => { slider.style.setProperty('--pct', `${(Number(slider.value) - 1) * 25}%`); value.textContent = `${slider.value} de 5`; };
  slider.addEventListener('input', paint);
  paint();
  const select = h('select', { id: 'interpretacion' }, h('option', { value: '' }, 'Selecciona una opción…'),
    sc.opciones.map((o) => h('option', { value: o.codigo }, o.etiqueta)));
  const submit = h('button', { type: 'button', class: 'btn primary block', disabled: true }, h('span', {}, 'Registrar Decisión'), icon('arrow', 16));
  select.addEventListener('change', () => { submit.disabled = !select.value; });
  const hasNext = sc.caso_numero < sc.total_casos;
  const goNext = h('button', { type: 'button', class: 'btn primary block' }, h('span', {}, hasNext ? 'Siguiente caso' : 'Ver resultados'), icon('arrow', 16));
  goNext.addEventListener('click', async () => {
    goNext.disabled = true;
    errorSlot.replaceChildren();
    try { await actions.onContinue(); } catch (err) {
      errorSlot.append(errorBox(err instanceof ApiError ? err.message : 'No se pudo continuar. Inténtalo de nuevo.'));
      goNext.disabled = false;
    }
  });
  const lock = () => {
    select.disabled = true; slider.disabled = true;
    submit.replaceWith(h('div', { class: 'done-note', role: 'status' }, icon('check', 16),
      h('span', {}, `Decisión del caso ${sc.caso_numero} registrada.`)), );
    errorSlot.after(goNext);
  };
  submit.addEventListener('click', async () => {
    errorSlot.replaceChildren();
    submit.disabled = true;
    try {
      await registerDecision(sid, select.value, Number(slider.value));
      lock();
    } catch (err) {
      errorSlot.append(errorBox(err instanceof ApiError ? err.message : 'No se pudo registrar la decisión.'));
      submit.disabled = !select.value;
    }
  });
  const panel = h('section', { class: 'card decision', 'aria-label': 'Calibración de confianza y decisión' },
    h('h3', {}, 'Calibración de Confianza'),
    h('div', { class: 'conf-head' }, h('span', { class: 'muted small' }, '¿Qué seguridad tienes?'), value),
    slider,
    h('div', { class: 'ticks', 'aria-hidden': 'true' }, ['1', '2', '3', '4', '5'].map((n) => h('span', {}, n))),
    h('div', { class: 'scale-labels' }, h('span', {}, 'Muy baja'), h('span', {}, 'Muy alta')),
    h('div', { class: 'field' }, h('label', { for: 'interpretacion' }, 'Diagnóstico'), select),
    errorSlot, submit,
    h('p', { class: 'muted small center' }, 'Tu decisión se contrastará con la referencia docente al final de los 3 casos.'));
  if (sc.decidido) lock();
  return panel;
}

export function renderSimulacion(state, actions) {
  const sc = state.scenario;
  const timer = h('span', { class: 'timer', 'aria-label': 'Tiempo transcurrido' }, mmss(sc.transcurrido_s || 0));
  let elapsed = sc.transcurrido_s || 0;
  const id = setInterval(() => { elapsed += 1; timer.textContent = mmss(elapsed); }, 1000);
  actions.setCleanup(() => clearInterval(id));
  return h('main', { class: 'page wide enter', tabindex: '-1' },
    h('div', { class: 'page-head' },
      h('div', {}, h('p', { class: 'eyebrow' }, `Práctica clínica / Caso ${sc.caso_numero} de ${sc.total_casos}`),
        h('h1', { class: 'h1-sm' }, `Entorno de Simulación. Caso ${sc.caso_numero} de ${sc.total_casos}`),
        h('p', { class: 'muted' }, 'Gira el modelo 3D, contrasta la sugerencia y registra tu criterio.'),
        h('div', { class: 'case-dots', role: 'img', 'aria-label': `Caso ${sc.caso_numero} de ${sc.total_casos}` },
          Array.from({ length: sc.total_casos }, (_, i) => h('i', { class: i + 1 < sc.caso_numero ? 'done' : i + 1 === sc.caso_numero ? 'now' : '' })))),
      h('div', { class: 'timer-card' }, h('span', { class: 'timer-ico' }, icon('clock', 20)),
        h('div', {}, h('small', {}, 'TIEMPO DE SESIÓN'), timer))),
    h('div', { class: 'sim-grid' }, viewer(sc, actions), h('div', { class: 'side stagger' }, tutorPanel(state, state.aiNotice), decisionPanel(state, actions))));
}
