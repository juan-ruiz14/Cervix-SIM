# Cérvix-SIM

Simulador académico de interpretación de imágenes cervicales con un **Agente Tutor IA** para medir la calibración de la confianza y la sobredependencia de la automatización (AOR). Proyecto de Gestión de Proyectos TI, Universidad Santiago de Cali.

> **Advertencia:** entorno de simulación de aprendizaje. No apto para diagnóstico médico real. Todos los casos son modelos 3D sintéticos; no hay datos de pacientes.

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

Tutor real con Gemini: crea una clave en Google AI Studio y define `GEMINI_API_KEY` (y `TUTOR_MODE=gemini` o `auto`). Alternativa local: [Ollama](https://ollama.com), `ollama pull llama3` y `TUTOR_MODE=ollama`. Si el proveedor falla o tarda más de 10 s se muestra un texto de respaldo. Guía completa: `docs/guia_ia_gemini.md`.

## Visor 3D (una sola vez)
Los 5 modelos `.glb` viven en `backend/cervix_sim/static_models/`. El visor usa three.js servido desde el propio proyecto:
```bash
cd frontend
npm install three@0.160.0 --no-save && node tools/instalar_three.mjs   # llena frontend/vendor/three
```
Después sube `frontend/vendor/three/` a GitHub junto con el resto. Sin ese paso el visor muestra un aviso y el resto de la app funciona.

## Casos y secuencias
Cada sesión tiene 3 casos en orden fijo según el nivel: básico CS-001 → CS-003 → CS-004; intermedio CS-004 → CS-003 → CS-001; avanzado CS-009 → CS-007 → CS-004. El veredicto del tutor está predefinido por caso en `data/cases.json` (`ia_veredicto`, `ia_condicion`): solo CS-004 es inexacta (sugiere LSIL; la referencia es «sin lesión»), así que cada secuencia tiene exactamente 1 sugerencia inexacta de 3.

## Pruebas
```bash
cd backend && python -m unittest discover -s tests -t .   # backend (52 pruebas)
python -m cervix_sim.tools.validate_cases                 # valida el banco de casos
node e2e/run_e2e.mjs                                      # extremo a extremo (requiere playwright)
```

## API
`GET /api/health`, `GET /api/legal`, `POST /api/sessions`, `GET /api/sessions/{id}/scenario`, `POST /api/sessions/{id}/tutor`, `POST /api/sessions/{id}/decision`, `POST /api/sessions/{id}/next`, `POST /api/sessions/{id}/comment`, `GET /api/sessions/{id}/results`, `POST /api/sessions/{id}/sus`, `GET /api/admin/summary` (cabecera `X-Admin-Token`).

## Despliegue gratuito
- Backend: Render (comando `cd backend && python -m cervix_sim`, `HOST=0.0.0.0`), base en MongoDB Atlas free.
- Frontend aparte (opcional): Vercel/GitHub Pages; edita `frontend/config.js` con la URL del backend y define `ALLOWED_ORIGINS`.
- `Dockerfile` y `docker-compose.yml` incluidos (no probados en el entorno de desarrollo).

## Limitaciones conocidas
- Los casos y sus referencias son sintéticos y **requieren validación del docente** antes de usarse en el estudio.
- La definición operativa del AOR (seguir sugerencias inexactas / sugerencias inexactas mostradas) debe confirmarse con el docente.
- Los modelos 3D son pesados (CS-007: 13,6 MB y ~406 mil triángulos); conviene comprimirlos con Meshopt si la carga es lenta en móviles.
- El panel agregado sólo está disponible vía el endpoint de administración.
- Starlette se usa en lugar de FastAPI y el frontend es JS puro (sin React) por restricciones de instalación del entorno de desarrollo; migrar es sencillo porque la lógica está separada de la API.

## Subir a GitHub
```bash
git init && git add . && git commit -m "Cérvix-SIM v1.0"
git branch -M main
git remote add origin https://github.com/<usuario>/cervix-sim.git
git push -u origin main
```

Equipo: Juan David Uribe Enciso (líder), Juan Pablo Ruiz Meneses, Daniel Andrés Rodríguez Castro, Juan Pablo Ortiz Ramírez, Santiago Meneses Berdugo. Docente: Jair Enrique Sanclemente Castro.
