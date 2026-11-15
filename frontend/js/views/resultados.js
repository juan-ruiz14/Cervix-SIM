import { h, icon } from '../dom.js';
import { submitSus, sendComment, ApiError } from '../api.js';
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

// Mensaje global de la sesión (se elige por prioridad en el backend).
const ESTADOS = {
  sobredependencia: { tone: 'bad', badge: 'Requiere reflexión', title: 'Alerta AOR (Sesgo de Automatización)',
    text: 'En al menos un caso tu respuesta coincidió con una sugerencia del tutor que difería de la referencia docente. Este patrón sugiere posible dependencia de la recomendación automática; por sí solo, no confirma un sesgo.' },
  acuerdo_correcto: { tone: 'good', badge: 'Coincidencia', title: 'Interacción con el tutor IA',
    text: 'Cuando consultaste al tutor, tus respuestas coincidieron con su sugerencia y con la referencia docente.' },
  contraste_ia_inexacta: { tone: 'good', badge: 'Contraste crítico', title: 'Interacción con el tutor IA',
    text: 'Cuando la sugerencia del tutor difería de la referencia docente, no la seguiste. Contrastar la sugerencia con la evidencia es el comportamiento que busca este entrenamiento.' },
  desacuerdo_ia_correcta: { tone: 'warn', badge: 'Desacuerdo', title: 'Interacción con el tutor IA',
    text: 'En algún caso tu decisión difirió de una sugerencia del tutor que coincidía con la referencia docente. Revisa qué evidencia te llevó a otra conclusión.' },
  sin_consulta: { tone: 'neutral', badge: 'Sin consulta', title: 'Interacción con el tutor IA',
    text: 'No consultaste al tutor en ningún caso, así que no hay datos de interacción para calcular el AOR.' },
};

const MAX_COMMENT = 1000;

function commentCard(state) {
  const sid = state.session.sesion_id;
  const errorSlot = h('div', { 'aria-live': 'polite' });
  const area = h('textarea', { id: 'comentario', maxlength: String(MAX_COMMENT), rows: '4',
    placeholder: 'Cuéntanos qué te pareció la experiencia, qué fue confuso o qué mejorarías.' });
  const counter = h('span', { class: 'counter' }, `0 / ${MAX_COMMENT}`);
  const send = h('button', { type: 'button', class: 'btn primary', disabled: true }, h('span', {}, 'Enviar comentario'), icon('arrow', 16));
  const card = h('section', { class: 'card comment', 'aria-label': 'Comentario final' });
  area.addEventListener('input', () => {
    counter.textContent = `${area.value.length} / ${MAX_COMMENT}`;
    send.disabled = !area.value.trim();
  });
  send.addEventListener('click', async () => {
    errorSlot.replaceChildren();
    send.disabled = true;
    try {
      await sendComment(sid, area.value.trim());
      card.replaceChildren(h('p', { class: 'thanks', role: 'status' }, icon('check', 20), h('span', {}, '¡Gracias! Recibimos tu comentario.')));
    } catch (err) {
      errorSlot.append(errorBox(err instanceof ApiError ? err.message : 'No se pudo enviar el comentario.'));
      send.disabled = !area.value.trim();
    }
  });
  card.append(
    h('div', { class: 'comment-head' }, h('span', { class: 'tutor-ico' }, icon('chat', 18)),
      h('div', {}, h('label', { for: 'comentario' }, '¿Quieres dejarnos un comentario?'),
        h('div', { class: 'muted small' }, 'Es opcional y anónimo; se usa solo con fines académicos. No escribas datos personales.'))),
    area, errorSlot,
    h('div', { class: 'comment-foot' }, counter, send));
  return card;
}

const metric = (label, ico, valueNode, foot) => h('div', { class: 'metric' },
  h('div', { class: 'metric-head' }, h('span', {}, label), icon(ico, 18)), h('div', { class: 'metric-value' }, valueNode), h('p', { class: 'muted small' }, foot));

function aorCard(res) {
  const st = ESTADOS[res.estado];
  const t = res.resumen.tutor;
  return h('section', { class: 'card aor' },
    h('div', { class: 'aor-head' }, h('span', { class: `aor-ico ${st.tone}` }, icon(st.tone === 'good' ? 'check' : st.tone === 'neutral' ? 'info' : 'warning', 18)), h('h3', {}, st.title),
      h('span', { class: `badge ${st.tone}` }, st.badge)),
    h('p', { class: 'muted' }, st.text),
    h('p', { class: 'muted small' }, `Consultaste al tutor en ${t.consultas} de ${res.resumen.total} casos. Sugerencias inexactas mostradas: ${t.inexactas_mostradas}; seguidas: ${t.seguidas_inexactas}.`),
    h('p', { class: 'muted small' }, 'AOR: sobredependencia de la automatización. Con tan pocos casos la comparación es solo ilustrativa.'));
}

function casoCard(c) {
  const ok = c.correcta;
  const children = [
    h('div', { class: 'aor-head' }, h('span', { class: `aor-ico ${ok ? 'good' : 'bad'}` }, icon(ok ? 'check' : 'warning', 18)),
      h('h3', {}, `Caso ${c.numero} · ${c.caso.id}`), h('span', { class: `badge ${ok ? 'good' : 'bad'}` }, ok ? 'Coincide con la referencia' : 'Difiere de la referencia')),
  ];
  if (c.tutor.consultado) {
    const iaWrong = c.tutor.codigo !== c.referencia.codigo;
    children.push(h('div', { class: 'compare', role: 'table', 'aria-label': `Comparación de respuestas del caso ${c.numero}` },
      h('div', { class: 'compare-row head', role: 'row' }, h('span', {}, 'Sugerencia del tutor IA'), h('span', {}, 'Tu decisión'), h('span', {}, 'Referencia docente')),
      h('div', { class: 'compare-row', role: 'row' },
        h('div', { class: iaWrong ? 'wrong' : '' }, h('strong', {}, c.tutor.etiqueta), h('span', { class: 'muted small' }, 'Hipótesis orientativa del agente')),
        h('div', { class: ok ? '' : 'wrong' }, h('strong', {}, c.decision.etiqueta), h('span', { class: 'muted small' }, c.tutor.siguio ? 'Coincide con la sugerencia de la IA' : 'Difiere de la sugerencia de la IA')),
        h('div', {}, h('strong', {}, c.referencia.etiqueta), h('span', { class: 'muted small' }, 'Criterio del caso simulado')))));
    children.push(h('p', { class: 'debrief' }, c.tutor.condicion === 'inexacta'
      ? 'Información del estudio: en este caso el tutor emitió una sugerencia deliberadamente inexacta, como parte del diseño para medir la calibración de la confianza.'
      : 'Información del estudio: en este caso la sugerencia del tutor fue calibrada, es decir, coincidía con la referencia docente.'));
  } else {
    children.push(h('p', { class: 'muted' }, `Tu decisión: ${c.decision.etiqueta}. Referencia docente: ${c.referencia.etiqueta}. No consultaste al tutor en este caso.`));
  }
  children.push(h('p', { class: 'muted small' }, `Confianza ${c.confianza}/5 · ${minSec(c.tiempo_respuesta_s)}`),
    h('p', { class: 'case-why' }, h('strong', {}, 'Por qué: '), c.referencia.justificacion));
  return h('section', { class: 'card aor case-card' }, children);
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
  const sm = r.resumen;
  return h('main', { class: 'page wide enter', tabindex: '-1' },
    h('div', { class: 'page-head' },
      h('div', {}, h('h1', { class: 'h1-sm' }, 'Dashboard de Resultados'),
        h('p', { class: 'muted' }, `Participante ${state.session.participante_id} · ${sm.total} casos · Nivel ${LEVEL_LABELS[r.nivel]}`)),
      h('span', { class: 'pill' }, 'Resultado de tu sesión')),
    h('div', { class: 'metrics stagger' },
      metric('Exactitud de la Decisión (%)', 'target', [String(Math.round(sm.exactitud_pct)), h('span', { class: 'unit' }, '%')], `${sm.aciertos} de ${sm.total} decisiones coinciden con la referencia`),
      metric('Tiempo de Respuesta', 'clock', mmss(sm.tiempo_total_s), `${minSec(sm.tiempo_total_s)} en total entre los ${sm.total} casos`),
      metric('Nivel de Confianza', 'sliders', [String(sm.confianza_media), h('span', { class: 'unit' }, '/ 5')], `${sm.confianza_media >= 4 ? 'Confianza alta' : sm.confianza_media <= 2 ? 'Confianza baja' : 'Confianza media'} · Promedio de tus autovaloraciones`)),
    aorCard(r),
    h('h2', { class: 'h2-sm' }, 'Detalle por caso'),
    h('div', { class: 'case-list stagger' }, r.casos.map(casoCard)),
    h('section', { class: 'note-card' }, h('span', { class: 'note-ico' }, icon('book', 18)),
      h('div', {}, h('strong', {}, 'La confianza no sustituye a la evidencia'), h('p', { class: 'muted' }, 'Contrasta siempre cualquier sugerencia, incluida la de una IA, con lo que observas en el modelo.'))),
    h('div', { class: 'actions' },
      h('span', { class: 'muted small' }, 'Resultados ilustrativos · No constituyen una evaluación clínica.'),
      h('div', { class: 'actions-btns' }, susBtn, h('button', { type: 'button', class: 'btn primary', onclick: actions.onRestart }, h('span', {}, 'Volver al Inicio'), icon('arrow', 16)))),
    commentCard(state),
    dialog);
}
