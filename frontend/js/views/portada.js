import { h, icon } from '../dom.js';
import { CONTENT as C } from '../content.js';

export function renderPortada(state, actions) {
  const cta = (extra = '') => h('button', { type: 'button', class: `btn primary lg ${extra}`, onclick: actions.onStartFlow },
    h('span', {}, C.cta), icon('arrow', 18));

  const hero = h('section', { class: 'hero stagger' },
    h('img', { class: 'hero-logo', src: 'assets/logo-completo.png', alt: 'Logo de Cérvix-SIM' }),
    h('p', { class: 'eyebrow' }, C.eyebrow),
    h('h1', {}, C.titulo[0], h('br'), C.titulo[1]),
    h('p', { class: 'lead' }, C.lead),
    h('div', { class: 'hero-cta' }, cta(), h('p', { class: 'muted small' }, C.nota)));

  const about = h('section', { class: 'section' },
    h('h2', { class: 'section-title' }, C.quienes.titulo),
    h('div', { class: 'about' }, h('span', { class: 'about-ico' }, icon('users', 22)),
      h('div', {}, C.quienes.texto.map((t) => h('p', {}, t)))));

  const steps = h('section', { class: 'section' },
    h('h2', { class: 'section-title' }, C.que.titulo),
    h('ol', { class: 'steps stagger' }, C.que.pasos.map(([t, d]) =>
      h('li', { class: 'step-card' }, h('h3', {}, t), h('p', { class: 'muted small' }, d)))));

  const pledges = h('section', { class: 'section' },
    h('ul', { class: 'pledges stagger' }, C.garantias.map(([ico, t, d]) =>
      h('li', { class: 'pledge' }, h('span', { class: 'pledge-ico' }, icon(ico, 18)),
        h('div', {}, h('strong', {}, t), h('span', { class: 'muted small' }, d))))));

  return h('main', { class: 'page mid enter', tabindex: '-1' }, hero, about, steps, pledges,
    h('div', { class: 'final-cta' }, cta()));
}
