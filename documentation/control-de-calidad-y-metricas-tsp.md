# Control de Calidad y Métricas (TSP)

## Control de Calidad y Métricas (TSP)&#x20;

Para garantizar la calidad desde las etapas tempranas del ciclo de vida del software, el equipo integra la gestión visual con el control cuantitativo de ingeniería bajo **TSP (**_**Team Software Process**_**)**.

***

### Gestión Visual del Flujo (Kanban - Trello)

El seguimiento operativo de tareas se centraliza en un tablero Kanban dividido en cuatro estados:

* **Backlog:** Tareas de desarrollo web y programación pendientes para la fase de construcción.
* **En Proceso:** Actividades activas de análisis de requisitos, diseño y selección de datasets.
* **En Revisión:** Artefactos técnicos sometidos a validación por el Director o el Tester.
* **Terminado:** Documentación aprobada y versionada en GitHub / GitBook.

***

### Métricas Cuantitativas (Process Dashboard)

El esfuerzo técnico de la fase actual se registra mediante cronómetro activo en **Process Dashboard**, permitiendo calcular el **Valor Ganado (Earned Value)** real del equipo:

| Métrica TSP                           | Valor Registrado | Estado / Interpretación                                                                                                          |
| ------------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Horas Planeadas (Fase Documental)** | `38.0 horas`     | Presupuesto total de tiempo estimado para planeación y diseño.                                                                   |
| **Horas Reales Ejecutadas**           | `19.0 horas`     | Tiempo neto registrado en actividades de análisis y documentación.                                                               |
| **Avance de Fase (Valor Ganado)**     | `50%`            | Cumplimiento exacto de la mitad del cronograma de diseño.                                                                        |
| **Defectos Detectados y Corregidos**  | `102 defectos`   | Errores de sintaxis, lógica y consistencia detectados y resueltos **directamente en la documentación** antes de escribir código. |

> **Impacto en Calidad:** Detectar y corregir estos 102 defectos durante la fase de requisitos y diseño evita retrabajos costosos cuando inicie la programación del simulador.
