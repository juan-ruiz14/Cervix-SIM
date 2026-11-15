# Control de Calidad y Métricas TSP

El desarrollo de **Cérvix-SIM** aplica prácticas de **Team Software Process (TSP)** junto con el *Plan de Gestión de Calidad* del proyecto, asegurando el orden en el trabajo colaborativo, la estabilidad de la arquitectura y la validez metodológica de los datos recopilados.

---

## 1. Organización y Roles TSP del Equipo

Cada integrante asume responsabilidades específicas para garantizar la calidad técnica y documental del proyecto:

| Rol TSP | Integrante | Responsabilidades de Calidad y Proceso |
| :--- | :--- | :--- |
| **Líder de Equipo (*Team Leader*)** | Juan David Uribe Enciso | Coordinación general, seguimiento de entregables por corte y alineación con los criterios del docente. |
| **Planificación y Procesos (*Planning & Process Manager*)** | Juan Pablo Ruiz Meneses | Control del cronograma, trazabilidad de requisitos, gestión de ramas/Pull Requests y documentación en GitBook. |
| **Calidad y Pruebas (*Quality & Test Manager*)** | Daniel Andrés Rodríguez Castro | Definición de criterios de aceptación, revisión de casos sintéticos y verificación funcional de los flujos. |
| **Desarrollo e Integración (*Development Manager*)** | Juan Pablo Ortiz Ramírez | Construcción modular del backend, reglas de negocio y aislamiento de la lógica del Agente Tutor IA. |
| **Soporte y Despliegue (*Support Manager*)** | Santiago Meneses Berdugo | Estandarización de entornos, integración continua en GitHub, interfaz web/3D y persistencia de datos. |

---

## 2. Controles de Aseguramiento de Calidad (QA)

En lugar de depender únicamente de revisiones manuales al final del proyecto, el equipo incorporó controles preventivos dentro de la estructura del repositorio:

* **Flujo de trabajo por ramas y Pull Requests:** Cada módulo (*Backend*, *IA*, *Frontend* y documentación) se desarrolla en ramas separadas antes de integrarse a la rama principal (`main`), evitando sobrescrituras de código.
* **Integración Continua (CI):** El repositorio cuenta con flujos automatizados en GitHub Actions (`.github/workflows/ci.yml`) que verifican la integridad del proyecto ante cada integración.
* **Verificación multicapa incorporada:** La arquitectura contempla validación estructural del banco de casos sintéticos, pruebas unitarias sobre la lógica del backend (45 casos de prueba) y recorridos completos de usuario (E2E).
* **Tolerancia a fallos (Degradación controlada):** Si el modelo de Inteligencia Artificial tarda más de **10 segundos** o presenta fallas de conexión, el servidor entrega automáticamente una respuesta de respaldo para no bloquear la simulación del estudiante.
* **Integridad experimental:** El backend retiene la respuesta correcta del caso y la exactitud de la sugerencia del tutor hasta que el participante confirma su decisión final.

---

## 3. Métricas de Proceso TSP (Seguimiento del Equipo)

Para evaluar el desempeño del equipo durante los ciclos de construcción, se monitorean los siguientes indicadores de gestión:

| Indicador | Propósito | Criterio de Cumplimiento |
| :--- | :--- | :--- |
| **Cumplimiento de Entregables por Corte** | Medir el avance planificado frente al ejecutado en los cortes académicos (`Corte_1` y `Corte_2`). | **100 %** de artefactos documentales y técnicos entregados en fecha. |
| **Estabilidad de Integración** | Controlar que las fusiones a `main` no rompan funcionalidades previas del sistema. | **0 bloqueos críticos** activos en la rama principal. |
| **Trazabilidad de Requisitos** | Verificar que cada módulo implementado responda a los requisitos priorizados en la Matriz MoSCoW. | Cobertura total de los requisitos obligatorios (*Must Have*). |

---

## 4. Métricas de Calidad del Producto y Estudio Piloto

El simulador está diseñado para calcular automáticamente tres indicadores clave al finalizar cada sesión:

1. **Tasa de Sobredependencia de la Automatización (AOR):** Mide la proporción en la que el participante adopta una sugerencia **inexacta** generada por el Agente Tutor IA en lugar de mantener su propio criterio clínico.
2. **Calibración de la Confianza:** Contrasta el nivel de seguridad declarado por el estudiante al emitir su diagnóstico frente a su acierto real respecto a la referencia docente.
3. **Puntaje de Usabilidad del Sistema (SUS):** Evalúa la facilidad de uso e interacción con la plataforma mediante un cuestionario estandarizado aplicado al cierre de la simulación.

---

## 5. Criterios de Aceptación Académica

* **Validación docente:** Todos los casos clínicos sintéticos y la definición operativa del índice AOR deben contar con revisión del docente antes de aplicar el simulador con estudiantes.
* **Privacidad y ética:** Los participantes operan mediante identificadores seudónimos y la plataforma mantiene visible la advertencia de uso exclusivamente académico (no apto para diagnóstico médico real).
