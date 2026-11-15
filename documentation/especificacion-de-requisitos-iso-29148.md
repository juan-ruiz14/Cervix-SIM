# Especificación de Requisitos (ISO 29148)

## Especificación de Requisitos (ISO/IEC/IEEE 29148)&#x20;

El levantamiento y documentación de requisitos de **Cérvix-SIM** se rige por el estándar internacional **ISO/IEC/IEEE 29148**, garantizando que todas las reglas técnicas y éticas queden definidas antes de iniciar la fase de codificación.

***

### Requisitos Funcionales (RF)

| ID        | Requisito                          | Descripción Técnica                                                                                                                                                                                       | Prioridad |
| --------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| **RF-01** | **Simulación de Casos Clínicos**   | El sistema debe presentar casos clínicos interactivos de cuello uterino con soporte visual y mecánicas de gamificación.                                                                                   | Alta      |
| **RF-02** | **Agente Tutor Inteligente**       | Integración de un agente basado en IA capaz de ofrecer sugerencias, pistas y retroalimentación contextual durante la evaluación del caso.                                                                 | Alta      |
| **RF-03** | **Medición de Sesgo (AOR)**        | La plataforma debe registrar la decisión inicial del usuario y su decisión final tras recibir la sugerencia de la IA para calcular la Exactitud de Decisión y el índice de Sesgo de Automatización (AOR). | Crítica   |
| **RF-04** | **Gestión de Sesiones y Métricas** | Almacenamiento estructurado de los tiempos de respuesta y tasas de acierto por cada escenario completado.                                                                                                 | Media     |

***

### &#x20;   Requisitos No Funcionales (RNF) y Restricciones

* **RNF-01 | Privacidad y Anonimización de Datos:** Todos los conjuntos de datos (_datasets_) e imágenes médicas empleadas en el simulador deben estar **100% anonimizados**, eliminando cualquier metadato o identificador de pacientes reales.
* **RNF-02 | Restricción Presupuestal ($0 COP):** La arquitectura completa (alojamiento, base de datos y consumo de modelos IA) debe operar con un costo de **$0 COP**, utilizando exclusivamente servicios en la nube de capa gratuita.
* **RNF-03 | Usabilidad (Escala SUS):** Una vez construido el prototipo funcional, la interfaz será evaluada mediante el cuestionario estándar **SUS (**_**System Usability Scale**_**)** para validar su facilidad de uso.
* **RNF-04 | Rendimiento y Optimización:** Las imágenes clínicas cargadas en el navegador deben estar optimizadas para evitar tiempos de espera prolongados o saturación de ancho de banda.
