import { h, icon } from '../dom.js';

const STEPS = [['inicio', 'Inicio'], ['simulacion', 'Simulación'], ['resultados', 'Resultados']];

export function header(stage) {
  const current = STEPS.findIndex(([key]) => key === stage);
  const steps = STEPS.map(([key, label], i) =>
    h('li', { class: `step ${i === current ? 'active' : ''} ${i < current ? 'done' : ''}`, 'aria-current': i === current ? 'step' : false },
      h('span', { class: 'step-n' }, String(i + 1)), h('span', { class: 'step-l' }, label)));
  return h('header', { class: 'topbar' },
    h('div', { class: 'brand' }, h('span', { class: 'brand-logo' }, icon('scan', 20)), h('span', { class: 'brand-name' }, 'Cérvix-SIM')),
    h('ol', { class: 'stepper', 'aria-label': 'Progreso' }, steps),
    h('div', { class: 'env' }, icon('school', 16), h('span', {}, 'Entorno académico · v1.0')));
}

// Advertencia de no diagnóstico (UC-07). El texto viene del backend, que es su fuente única.
export function legalBanner(text) {
  return h('div', { class: 'legal', role: 'note' }, icon('warning', 18), h('span', {}, text));
}

export function footer(left) {
  return h('footer', { class: 'footer' }, h('span', {}, left), h('span', {}, 'Datos ficticios · Sin información de pacientes'));
}

export function errorBox(message) {
  return h('p', { class: 'form-error', role: 'alert' }, message);
}
