# Cérvix-SIM

Simulador académico de interpretación de imágenes cervicales con un **Agente Tutor IA** para medir la calibración de la confianza y la sobredependencia de la automatización (AOR). Proyecto de Gestión de Proyectos TI, Universidad Santiago de Cali.

> **Advertencia:** entorno de simulación de aprendizaje. No apto para diagnóstico médico real. Todos los casos son esquemas sintéticos; no hay datos de pacientes.

## Arquitectura (resumen)
Cliente-servidor en capas con backend modular (ver `docs/Arquitectura_del_Sistema_Cervix-SIM_v2.0.docx`).

| Capa / patrón | Dónde está |
|---|---|
| Presentación (SPA estática, JS puro) | `frontend/` |
| API (Starlette) | `backend/cervix_sim/api.py` |
| Lógica de negocio | `backend/cervix_sim/service.py`, `domain/` |
| Factory (escenario por nivel) | `domain/factory.py` |
| Singleton (cliente del tutor) | `tutor.py` |
| Observer (métricas y telemetría asíncronas) | `domain/events.py`, `telemetry.py` |
| Datos (MongoDB o memoria) | `store.py` |
| Banco de casos (UC-06/UC-08) | `cervix_sim/data/cases.json`, `tools/validate_cases.py` |

Decisiones clave: el backend es el único intermediario con el tutor y **nunca envía al navegador** la referencia docente ni la condición de la sugerencia hasta que se registra la decisión; si el tutor falla o tarda más de 10 s se responde con un texto de respaldo (degradación controlada); el participante se identifica con un id seudónimo y los datos de contacto se guardan aparte.

## Ejecutar en local
Requisitos: Python 3.10+.
```bash
cd backend
pip install -r requirements.txt          # añade requirements-mongo.txt para MongoDB
TUTOR_MODE=mock python -m cervix_sim     # http://127.0.0.1:8000
```
La misma aplicación sirve el frontend. Variables en `.env.example` (`MONGODB_URI`, `TUTOR_MODE=auto|ollama|mock`, `OLLAMA_URL`, `ADMIN_TOKEN`, `ALLOWED_ORIGINS`...). Sin `MONGODB_URI` los datos se guardan en memoria (se pierden al reiniciar).

Tutor real: instala [Ollama](https://ollama.com), `ollama pull llama3` y usa `TUTOR_MODE=auto`.

## Pruebas
```bash
cd backend && python -m unittest discover -s tests -t .   # backend (45 pruebas)
python -m cervix_sim.tools.validate_cases                 # valida el banco de casos
node e2e/run_e2e.mjs                                      # extremo a extremo (requiere playwright)
```

## API
`GET /api/health`, `GET /api/legal`, `POST /api/sessions`, `GET /api/sessions/{id}/scenario`, `POST /api/sessions/{id}/tutor`, `POST /api/sessions/{id}/decision`, `GET /api/sessions/{id}/results`, `POST /api/sessions/{id}/sus`, `GET /api/admin/summary` (cabecera `X-Admin-Token`).

## Despliegue gratuito
- Backend: Render (comando `cd backend && python -m cervix_sim`, `HOST=0.0.0.0`), base en MongoDB Atlas free.
- Frontend aparte (opcional): Vercel/GitHub Pages; edita `frontend/config.js` con la URL del backend y define `ALLOWED_ORIGINS`.
- `Dockerfile` y `docker-compose.yml` incluidos (no probados en el entorno de desarrollo).

## Limitaciones conocidas
- Los casos y sus referencias son sintéticos y **requieren validación del docente** antes de usarse en el estudio.
- La definición operativa del AOR (seguir sugerencias inexactas / sugerencias inexactas mostradas) debe confirmarse con el docente.
- Cada sesión presenta un caso; el panel agregado sólo está disponible vía el endpoint de administración.
- Starlette se usa en lugar de FastAPI y el frontend es JS puro (sin React) por restricciones de instalación del entorno de desarrollo; migrar es sencillo porque la lógica está separada de la API.

## Subir a GitHub
```bash
git init && git add . && git commit -m "Cérvix-SIM v1.0"
git branch -M main
git remote add origin https://github.com/<usuario>/cervix-sim.git
git push -u origin main
```

Equipo: Juan David Uribe Enciso (líder), Juan Pablo Ruiz Meneses, Daniel Andrés Rodríguez Castro, Juan Pablo Ortiz Ramírez, Santiago Meneses Berdugo. Docente: Jair Enrique Sanclemente Castro.
