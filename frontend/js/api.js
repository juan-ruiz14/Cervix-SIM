// Cliente de la API REST del backend. Todos los errores llegan como ApiError con un mensaje legible (CE-07).
const BASE = (window.CERVIX_API_URL || '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(code, message, status, campos) {
    super(message);
    this.code = code;
    this.status = status;
    this.campos = campos || [];
  }
}

async function request(method, path, body) {
  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError('NETWORK', 'No hay conexión con el servidor. Revisa tu conexión e inténtalo de nuevo.', 0);
  }
  let data = null;
  try { data = await res.json(); } catch { /* respuesta sin JSON */ }
  if (!res.ok) {
    const e = data && data.error;
    throw new ApiError((e && e.code) || `HTTP_${res.status}`,
      (e && e.message) || 'Ocurrió un error inesperado. Inténtalo de nuevo.', res.status, e && e.campos);
  }
  return data;
}

export const imageUrl = (path) => BASE + path;
export const getLegal = () => request('GET', '/api/legal');
export const startSession = (payload) => request('POST', '/api/sessions', payload);
export const getScenario = (sid) => request('GET', `/api/sessions/${sid}/scenario`);
export const askTutor = (sid, mensaje) => request('POST', `/api/sessions/${sid}/tutor`, mensaje ? { mensaje } : {});
export const registerDecision = (sid, decision, confianza) =>
  request('POST', `/api/sessions/${sid}/decision`, { decision, confianza });
export const getResults = (sid) => request('GET', `/api/sessions/${sid}/results`);
export const submitSus = (sid, respuestas) => request('POST', `/api/sessions/${sid}/sus`, { respuestas });
