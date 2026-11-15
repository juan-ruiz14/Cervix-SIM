// Punto de entrada: controla las etapas (Portada, Inicio de sesión, Simulación, Resultados) y la persistencia de la sesión.
import { clear, h } from './dom.js';
import { ApiError, getLegal, getResults, getScenario, nextCase } from './api.js';
import { footer, header, legalBanner } from './views/shared.js';
import { renderPortada } from './views/portada.js';
import { renderInicio } from './views/inicio.js';
import { renderSimulacion } from './views/simulacion.js';
import { renderResultados } from './views/resultados.js';

const app = document.getElementById('app');
const KEY = 'cervix_sesion';
const state = {
  stage: 'portada', session: null, scenario: null, results: null,
  legal: 'Advertencia: entorno de simulación de aprendizaje. No apto para diagnóstico médico real.',
  aiNotice: 'La IA puede equivocarse. Evalúa la evidencia.',
};
let cleanup = null;

const store = {
  save(session) { try { sessionStorage.setItem(KEY, JSON.stringify(session)); } catch { /* modo privado */ } },
  load() { try { return JSON.parse(sessionStorage.getItem(KEY) || 'null'); } catch { return null; } },
  clear() { try { sessionStorage.removeItem(KEY); } catch { /* nada */ } },
};

const actions = {
  setCleanup(fn) { cleanup = fn; },
  getCleanup() { return cleanup; },
  onStartFlow() { go('inicio'); },
  onBack() { go('portada'); },
  onStarted(data) {
    state.session = { sesion_id: data.sesion_id, participante_id: data.participante_id };
    state.scenario = data.escenario;
    state.legal = data.aviso_legal || state.legal;
    store.save(state.session);
    go('simulacion');
  },
  // Tras registrar la decisión: pasa al siguiente caso o, si fue el último, a los resultados.
  async onContinue() {
    const sid = state.session.sesion_id;
    if (state.scenario.caso_numero < state.scenario.total_casos) {
      state.scenario = await nextCase(sid);
      go('simulacion');
    } else {
      state.results = await getResults(sid);
      go('resultados');
    }
  },
  onRestart() {
    store.clear();
    Object.assign(state, { session: null, scenario: null, results: null });
    go('portada');
  },
};

const TITLES = { portada: 'Cérvix-SIM · Entrena tu criterio', inicio: 'Cérvix-SIM · Prepara tu sesión',
  simulacion: 'Cérvix-SIM · Simulación', resultados: 'Cérvix-SIM · Resultados' };
const FOOTERS = {
  simulacion: () => ['Cérvix-SIM / Formación y reflexión clínica', `Sesión académica · Nivel ${state.scenario ? state.scenario.nivel : ''}`],
};

function go(stage) {
  if (cleanup) { cleanup(); cleanup = null; }
  state.stage = stage;
  const view = stage === 'portada' ? renderPortada(state, actions)
    : stage === 'inicio' ? renderInicio(state, actions)
      : stage === 'simulacion' ? renderSimulacion(state, actions) : renderResultados(state, actions);
  const [left, right] = (FOOTERS[stage] ? FOOTERS[stage]() : ['Cérvix-SIM / Formación y reflexión clínica']);
  clear(app);
  app.append(header(stage), legalBanner(state.legal), view, footer(left, right));
  document.title = TITLES[stage];
  window.scrollTo(0, 0);
  view.focus({ preventScroll: true });
}

async function boot() {
  try {
    const legal = await getLegal();
    state.legal = legal.aviso_legal;
    state.aiNotice = legal.aviso_ia;
  } catch { /* se usan los textos por defecto */ }
  // Reanudar una sesión abierta en esta pestaña (por ejemplo, tras recargar).
  const saved = store.load();
  if (saved && saved.sesion_id) {
    state.session = saved;
    try {
      state.results = await getResults(saved.sesion_id);
      go('resultados');
      return;
    } catch (err) {
      if (err instanceof ApiError && err.code === 'NO_DECISION') {
        try {
          state.scenario = await getScenario(saved.sesion_id);  // puede traer decidido=true
          go('simulacion');
          return;
        } catch { /* la sesión ya no existe */ }
      }
    }
    store.clear();
    state.session = null;
  }
  go('portada');
}

boot().catch(() => { clear(app); app.append(h('p', { class: 'form-error' }, 'No se pudo iniciar la aplicación.')); });
