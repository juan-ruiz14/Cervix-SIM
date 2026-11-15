import { h, icon } from '../dom.js';

const STEPS = [['inicio', 'Inicio'], ['simulacion', 'Simulación'], ['resultados', 'Resultados']];
// La portada y el formulario pertenecen ambos al primer paso.
const STEP_OF = { portada: 'inicio', inicio: 'inicio', simulacion: 'simulacion', resultados: 'resultados' };

export function header(stage) {
  const current = STEPS.findIndex(([key]) => key === STEP_OF[stage]);
  const steps = STEPS.map(([key, label], i) =>
    h('li', { class: `step ${i === current ? 'active' : ''} ${i < current ? 'done' : ''}`, 'aria-current': i === current ? 'step' : false },
      h('span', { class: 'step-n' }, i < current ? icon('check', 14) : String(i + 1)), h('span', { class: 'step-l' }, label)));
  return h('header', { class: 'topbar' },
    h('div', { class: 'brand' }, h('img', { src: 'assets/logo-icono.png', alt: '' }), h('span', {}, 'Cérvix-SIM')),
    h('ol', { class: 'stepper', 'aria-label': 'Progreso' }, steps),
    h('div', { class: 'env' }, icon('school', 16), h('span', {}, 'Entorno académico · v1.0')));
}

// Advertencia de no diagnóstico (UC-07). El texto viene del backend, que es su fuente única.
export function legalBanner(text) {
  return h('div', { class: 'legal', role: 'note' }, icon('warning', 18), h('span', {}, text));
}

export function footer(left, right = 'Datos ficticios · Sin información de pacientes') {
  return h('footer', { class: 'footer' }, h('span', {}, left), h('span', {}, right));
}

export function errorBox(message) {
  return h('p', { class: 'form-error', role: 'alert' }, message);
}
