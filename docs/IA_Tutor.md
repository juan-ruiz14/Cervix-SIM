# Agente Tutor IA – Cérvix-SIM

**Responsable:** rama `IA`. **Código:** `backend/cervix_sim/tutor.py`. **Pruebas:** `backend/tests/test_tutor.py`.

## Cómo funciona
- El backend es el único intermediario con el tutor (el navegador nunca lo llama).
- Modelo: Llama 3 servido localmente con [Ollama](https://ollama.com) (`POST {OLLAMA_URL}/api/generate`).
- Tiempo máximo de espera: 10 s (`TUTOR_TIMEOUT`). Si falla o se agota, se responde con un texto de respaldo (degradación controlada).
- Máximo de consultas por sesión: 10. Cada tercera sugerencia es deliberadamente inexacta (`INEXACT_EVERY`), según el diseño del estudio; el estudiante la conoce solo al final (debrief).
- Cliente único (Singleton) para no saturar el servicio.

## Ejecutar con el modelo real
```bash
ollama pull llama3
cd backend && TUTOR_MODE=auto python -m cervix_sim
```
Modos: `auto` (Ollama y, si falla, respaldo), `ollama` (solo Ollama), `mock` (sin modelo, para pruebas).

## Pendiente
- Validar con el docente el prompt y el tono de las sugerencias.
- Decidir dónde se aloja el modelo durante el estudio (equipo del grupo o API gratuita).
