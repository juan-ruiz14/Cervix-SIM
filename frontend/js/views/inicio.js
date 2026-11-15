import { h, icon } from '../dom.js';
import { startSession, ApiError } from '../api.js';
import { errorBox } from './shared.js';

export function renderInicio(state, actions) {
  const errorSlot = h('div', { 'aria-live': 'polite' });
  const field = (label, control, id) => h('div', { class: 'field' }, h('label', { for: id }, label), control);
  const nombre = h('input', { id: 'nombre', type: 'text', required: true, maxlength: '80', autocomplete: 'name', placeholder: 'Tu nombre completo' });
  const rol = h('select', { id: 'rol' }, h('option', { value: 'estudiante' }, 'Estudiante'), h('option', { value: 'profesional' }, 'Profesional'));
  const correo = h('input', { id: 'correo', type: 'email', required: true, maxlength: '120', autocomplete: 'email', placeholder: 'nombre@universidad.edu.co' });
  const nivel = h('select', { id: 'nivel' },
    h('option', { value: 'basico' }, 'Básico'), h('option', { value: 'intermedio', selected: true }, 'Intermedio'), h('option', { value: 'avanzado' }, 'Avanzado'));
  const consent = h('input', { id: 'consentimiento', type: 'checkbox', required: true });
  const submit = h('button', { type: 'submit', class: 'btn primary block' }, h('span', {}, 'Iniciar Simulación'), icon('arrow', 16));

  const form = h('form', { class: 'card form', novalidate: true, onsubmit: async (ev) => {
    ev.preventDefault();
    errorSlot.replaceChildren();
    if (!form.checkValidity()) { form.reportValidity(); return; }
    submit.disabled = true;
    try {
      const data = await startSession({
        nombre: nombre.value.trim(), rol: rol.value, correo: correo.value.trim(),
        nivel: nivel.value, consentimiento: consent.checked,
      });
      actions.onStarted(data);
    } catch (err) {
      errorSlot.append(errorBox(err instanceof ApiError ? err.message : 'No se pudo iniciar la sesión.'));
      submit.disabled = false;
    }
  } },
    h('div', {}, h('h2', {}, 'Prepara tu sesión'), h('p', { class: 'muted small' }, 'Un espacio seguro para aprender a decidir.')),
    field('Nombre', nombre, 'nombre'),
    field('Rol (Estudiante/Profesional)', rol, 'rol'),
    field('Correo', correo, 'correo'),
    field('Nivel de Dificultad', nivel, 'nivel'),
    h('label', { class: 'consent', for: 'consentimiento' }, consent,
      h('span', {}, 'Autorizo el tratamiento de mis datos con fines académicos y de investigación del proyecto (Ley 1581 de 2012). ',
        'Entiendo que el tutor de IA puede dar sugerencias incorrectas y que, al finalizar, se me indicará si fue así.')),
    errorSlot, submit);

  return h('main', { class: 'page narrow enter', tabindex: '-1' },
    h('button', { type: 'button', class: 'btn link', onclick: actions.onBack }, icon('back', 16), h('span', {}, 'Volver a la portada')),
    h('section', { class: 'hero stagger' },
      h('p', { class: 'eyebrow' }, 'APRENDIZAJE CLÍNICO ASISTIDO POR IA'),
      h('h1', { class: 'h1-sm' }, 'Entrena tu criterio. Decide con evidencia.')),
    form,
    h('p', { class: 'form-foot' }, icon('shield', 14), h('span', {}, 'Datos sintéticos. Aprendizaje sin riesgo para pacientes.')));
}
