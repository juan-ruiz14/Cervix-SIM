# Arquitectura y Diseño del Sistema

Cérvix-SIM implementa una arquitectura **cliente-servidor en capas con backend modular**, separando la interfaz web, la orquestación de sesiones, el cliente del Agente Tutor IA y la persistencia de telemetría.

## 1. Capas y Patrones de Diseño

| Capa / Patrón | Ubicación | Responsabilidad |
| :--- | :--- | :--- |
| **Presentación (SPA)** | `frontend/` (`main.js`, `api.js`) | Interfaz web estática en JavaScript puro y visor 3D (`model3d.js`). |
| **API REST** | `backend/cervix_sim/api.py` | Exposición de endpoints HTTP sobre el framework **Starlette**. |
| **Lógica de Negocio** | `backend/cervix_sim/service.py` | Gestión del ciclo de vida de la sesión, métricas (`metrics.py`) y cálculo SUS (`sus.py`). |
| **Patrón Factory** | `backend/cervix_sim/domain/factory.py` | Construcción dinámica de escenarios clínicos según el nivel de dificultad. |
| **Patrón Singleton** | `backend/cervix_sim/tutor.py` | Instancia única del cliente del Agente Tutor IA (Ollama o modo simulado *mock*). |
| **Patrón Observer** | `domain/events.py`, `telemetry.py` | Publicación y suscripción asíncrona de eventos de telemetría y métricas. |
| **Persistencia** | `backend/cervix_sim/store.py` | Almacenamiento desacoplado en MongoDB o en memoria volátil. |
| **Banco de Casos** | `cervix_sim/data/cases.json` | Repositorio de casos sintéticos validados con `tools/validate_cases.py`. |

## 2. Flujo de Vistas del Participante (`frontend/`)
La aplicación funciona como una *Single Page Application* (SPA) controlada por `main.js`, estructurada en tres vistas secuenciales:
1. **Inicio y Configuración de Sesión (`inicio.js`):** Presenta el consentimiento informado (`GET /api/legal`) y registra al participante con un identificador seudónimo (`POST /api/sessions`).
2. **Simulación de Caso y Visor 3D (`simulacion.js` + `model3d.js`):** Carga el escenario asignado (`GET /api/sessions/{id}/scenario`), renderiza el modelo anatómico en 3D, permite consultar al Agente Tutor (`POST /api/sessions/{id}/tutor`) y registra el diagnóstico junto con el nivel de confianza (`POST /api/sessions/{id}/decision`).
3. **Resultados y Evaluación SUS (`resultados.js`):** Revela la referencia docente comparada con la decisión tomada (`GET /api/sessions/{id}/results`) y recopila la encuesta de usabilidad SUS (`POST /api/sessions/{id}/sus`).

## 3. Decisiones Arquitectónicas Clave
* **Aislamiento de la referencia docente:** El navegador nunca recibe la respuesta correcta ni la condición de exactitud de la sugerencia IA antes de confirmar la decisión.
* **Degradación controlada:** Si el modelo de IA falla o tarda más de **10 segundos**, el servidor responde con un mensaje de respaldo sin interrumpir la sesión.
* **Privacidad por diseño:** El participante opera bajo un ID seudónimo y sus datos de contacto se almacenan por separado.

## 4. Endpoints de la API REST
* `GET /api/health` — Estado operativo del servicio.
* `GET /api/legal` — Términos legales y consentimiento académico.
* `POST /api/sessions` — Creación de sesión seudónima.
* `GET /api/sessions/{id}/scenario` — Obtención del caso clínico asignado.
* `POST /api/sessions/{id}/tutor` — Consulta de sugerencia al Agente Tutor IA.
* `POST /api/sessions/{id}/decision` — Registro de diagnóstico y nivel de confianza.
* `GET /api/sessions/{id}/results` — Retroalimentación docente y métricas de la sesión.
* `POST /api/sessions/{id}/sus` — Envío del cuestionario de usabilidad SUS.
* `GET /api/admin/summary` — Resumen agregado para el docente (requiere cabecera `X-Admin-Token`).
