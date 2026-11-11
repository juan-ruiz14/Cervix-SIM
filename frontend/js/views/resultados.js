import { h, icon } from '../dom.js';
import { submitSus, ApiError } from '../api.js';
import { minSec, mmss, LEVEL_LABELS } from '../format.js';
import { errorBox } from './shared.js';

const SUS_ITEMS = [
  'Creo que me gustaría utilizar este sistema con frecuencia.',
  'Encontré el sistema innecesariamente complejo.',
  'Pensé que el sistema era fácil de usar.',
  'Creo que necesitaría el apoyo de un técnico para poder usar este sistema.',
  'Encontré que las diversas funciones del sistema estaban bien integradas.',
  'Pensé que había demasiada inconsistencia en este sistema.',
  'Imagino que la mayoría de las personas aprenderían a usar este sistema muy rápidamente.',
  'Encontré el sistema muy complicado de usar.',
  'Me sentí muy seguro al usar el sistema.',
  'Necesité aprender muchas cosas antes de poder empezar con este sistema.',
];

const ESTADOS = {
  sobredependencia: { tone: 'bad', badge: 'Requiere reflexión', title: 'Alerta AOR (Sesgo de Automatización)',
    text: 'Tu respuesta coincide con la IA, pero difiere de la referencia docente. Este patrón sugiere posible dependencia de la recomendación automática; por sí solo, no confirma un sesgo.' },
  acuerdo_correcto: { tone: 'good', badge: 'Coincidencia', title: 'Interacción con el tutor IA',
    text: 'Tu respuesta coincide con la sugerencia del tutor y con la referencia docente.' },
  contraste_ia_inexacta: { tone: 'good', badge: 'Contraste crítico', title: 'Interacción con el tutor IA',
    text: 'La sugerencia del tutor difería de la referencia docente y no la seguiste. Contrastar la sugerencia con la evidencia es el comportamiento que busca este entrenamiento.' },
  desacuerdo_ia_correcta: { tone: 'warn', badge: 'Desacuerdo', title: 'Interacción con el tutor IA',
    text: 'Tu decisión difiere de la sugerencia del tutor, que coincidía con la referencia docente. Revisa qué evidencia te llevó a otra conclusión.' },
  sin_consulta: { tone: 'neutral', badge: 'Sin consulta', title: 'Interacción con el tutor IA',
    text: 'No consultaste al tutor en este caso, así que no hay datos de interacción para calcular el AOR.' },
};

const metric = (label, ico, valueNode, foot) => h('div', { class: 'metric' },
  h('div', { class: 'metric-head' }, h('span', {}, label), icon(ico, 18)), h('div', { class: 'metric-value' }, valueNode), h('p', { class: 'muted small' }, foot));

function aorCard(r) {
  const st = ESTADOS[r.estado];
  const children = [
    h('div', { class: 'aor-head' }, h('span', { class: `aor-ico ${st.tone}` }, icon('warning', 18)), h('h3', {}, st.title),
      h('span', { class: `badge ${st.tone}` }, st.badge)),
    h('p', { class: 'muted' }, st.text),
  ];
  if (r.tutor.consultado) {
    const iaWrong = r.tutor.codigo !== r.referencia.codigo;
    const userWrong = !r.correcta;
    children.push(h('div', { class: 'compare', role: 'table', 'aria-label': 'Comparación de respuestas' },
      h('div', { class: 'compare-row head', role: 'row' }, h('span', {}, 'Sugerencia del tutor IA'), h('span', {}, 'Tu decisión'), h('span', {}, 'Referencia docente')),
      h('div', { class: 'compare-row', role: 'row' },
        h('div', { class: iaWrong ? 'wrong' : '' }, h('strong', {}, r.tutor.etiqueta), h('span', { class: 'muted small' }, 'Hipótesis orientativa del agente')),
        h('div', { class: userWrong ? 'wrong' : '' }, h('strong', {}, r.decision.etiqueta), h('span', { class: 'muted small' }, r.tutor.siguio ? 'Coincide con la sugerencia de la IA' : 'Difiere de la sugerencia de la IA')),
        h('div', {}, h('strong', {}, r.referencia.etiqueta), h('span', { class: 'muted small' }, 'Criterio del caso simulado')))));
    children.push(h('p', { class: 'debrief' }, r.tutor.condicion === 'inexacta'
      ? 'Información del estudio: en este caso el tutor emitió una sugerencia deliberadamente inexacta, como parte del diseño para medir la calibración de la confianza.'
      : 'Información del estudio: en este caso la sugerencia del tutor fue calibrada, es decir, coincidía con la referencia docente.'));
  }
  children.push(h('p', { class: 'muted small' }, 'AOR: sobredependencia de la automatización. Comparación ilustrativa de una única decisión.'));
  return h('section', { class: 'card aor' }, children);
}

function susDialog(state, onDone) {
  const answers = new Array(10).fill(null);
  const errorSlot = h('div', { 'aria-live': 'polite' });
  const submit = h('button', { type: 'submit', class: 'btn primary', disabled: true }, 'Enviar cuestionario');
  const dialog = h('dialog', { class: 'dialog', 'aria-labelledby': 'sus-title' });
  const items = SUS_ITEMS.map((text, i) => h('fieldset', { class: 'sus-item' },
    h('legend', {}, `${i + 1}. ${text}`),
    h('div', { class: 'sus-scale' }, [1, 2, 3, 4, 5].map((n) => h('label', { class: 'sus-opt' },
      h('input', { type: 'radio', name: `sus${i}`, value: String(n), onchange: () => {
        answers[i] = n; submit.disabled = answers.some((a) => a === null); } }),
      h('span', {}, String(n)))),
    ),
    h('div', { class: 'scale-labels' }, h('span', {}, 'Totalmente en desacuerdo'), h('span', {}, 'Totalmente de acuerdo'))));
  const form = h('form', { method: 'dialog', onsubmit: async (e) => {
    e.preventDefault();
    errorSlot.replaceChildren();
    submit.disabled = true;
    try {
      const r = await submitSus(state.session.sesion_id, answers);
      form.replaceChildren(h('h2', { id: 'sus-title' }, 'Gracias por tu opinión'),
        h('p', {}, `Tu puntaje SUS es ${r.puntaje} de 100.`),
        h('button', { type: 'button', class: 'btn primary', onclick: () => dialog.close() }, 'Cerrar'));
      onDone(r.puntaje);
    } catch (err) {
      errorSlot.append(errorBox(err instanceof ApiError ? err.message : 'No se pudo enviar el cuestionario.'));
      submit.disabled = false;
    }
  } },
    h('h2', { id: 'sus-title' }, 'Reporte de usabilidad (SUS)'),
    h('p', { class: 'muted' }, 'Indica qué tan de acuerdo estás con cada afirmación (1 a 5).'),
    items, errorSlot,
    h('div', { class: 'dialog-actions' }, h('button', { type: 'button', class: 'btn ghost', onclick: () => dialog.close() }, 'Cancelar'), submit));
  dialog.append(form);
  return dialog;
}

export function renderResultados(state, actions) {
  const r = state.results;
  const susBtn = h('button', { type: 'button', class: 'btn outline' }, icon('file', 16), h('span', {}, 'Reporte SUS'));
  const dialog = susDialog(state, (score) => { susBtn.disabled = true; susBtn.replaceChildren(icon('file', 16), h('span', {}, `SUS enviado: ${score}`)); });
  susBtn.addEventListener('click', () => dialog.showModal());
  const ex = r.exactitud_pct;
  return h('main', { class: 'page wide' },
    h('div', { class: 'page-head' },
      h('div', {}, h('h1', { class: 'h1-sm' }, 'Dashboard de Resultados'),
        h('p', { class: 'muted' }, `Participante ${state.session.participante_id} · Caso ${r.caso.id} · Nivel ${LEVEL_LABELS[r.caso.nivel]}`)),
      h('span', { class: 'pill' }, 'Resultado de tu sesión')),
    h('div', { class: 'metrics' },
      metric('Exactitud de la Decisión (%)', 'target', [String(ex), h('span', { class: 'unit' }, '%')], `${r.correcta ? 1 : 0} de 1 decisiones correctas en este caso`),
      metric('Tiempo de Respuesta', 'clock', mmss(r.tiempo_respuesta_s), `${minSec(r.tiempo_respuesta_s)} desde el inicio del caso`),
      metric('Nivel de Confianza', 'sliders', [String(r.confianza), h('span', { class: 'unit' }, '/ 5')], `${r.confianza >= 4 ? 'Confianza alta' : r.confianza <= 2 ? 'Confianza baja' : 'Confianza media'} · Autovaloración registrada`)),
    aorCard(r),
    h('section', { class: 'note-card' }, h('span', { class: 'note-ico' }, icon('book', 18)),
      h('div', {}, h('strong', {}, 'La confianza no sustituye a la evidencia'), h('p', { class: 'muted' }, r.referencia.justificacion))),
    h('div', { class: 'actions' },
      h('span', { class: 'muted small' }, 'Resultados ilustrativos · No constituyen una evaluación clínica.'),
      h('div', { class: 'actions-btns' }, susBtn, h('button', { type: 'button', class: 'btn primary', onclick: actions.onRestart }, h('span', {}, 'Volver al Inicio'), icon('arrow', 16)))),
    dialog);
}
