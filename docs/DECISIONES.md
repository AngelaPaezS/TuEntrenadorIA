# Decisiones funcionales y límites

Este documento registra las interpretaciones aplicadas al convertir los documentos
de negocio en reglas ejecutables.

## Fuentes y prioridad

Las fuentes se interpretan en este orden:

1. Políticas y reglas de seguridad.
2. Restricciones del Prompt Maestro.
3. Manual de Generación de Rutinas.
4. Biblioteca de Ejercicios.
5. Base de Conocimiento.
6. Presentación del proyecto.

Una regla de menor prioridad nunca puede ampliar un límite de seguridad.

## Reglas cerradas

- Edad permitida: de 18 a 59 años, ambos límites incluidos.
- Nivel permitido: únicamente principiante.
- Objetivos permitidos: bajar de peso, mejorar condición física y crear el hábito.
- Días permitidos: 2, 3, 4 o 5.
- Duraciones permitidas: 15, 20, 30 o 45 minutos.
- Crear el hábito: restringido a 15 o 20 minutos.
- Ejercicios: únicamente los extraídos de la Biblioteca de Ejercicios.
- El usuario debe aceptar las políticas antes de recibir una rutina.

## Seguridad

Las políticas actuales no contienen un cuestionario clínico. Para no realizar una
evaluación médica que el proyecto prohíbe, el programa muestra una advertencia y
remite a un profesional cuando el usuario declara que no puede confirmar que está
en condiciones de realizar actividad física.

La exención incluida en los documentos no se interpreta como sustituto de controles
de producto. Antes de publicar el sistema se recomienda una revisión profesional
de seguridad física, privacidad y texto legal.

## Integración con IA generativa

La lectura, recuperación de conocimiento y generación de rutinas son locales. El
agente usa LangChain con Cohere para conversar y seleccionar herramientas:

- El motor local conserva la autoridad sobre validaciones y ejercicios.
- El modelo recibe solamente conocimiento recuperado y una rutina ya validada.
- La salida del modelo debe verificarse antes de mostrarse.
- Las claves se suministran mediante variables de entorno, nunca en el repositorio.
- La búsqueda BM25 evita llamadas de embeddings para esta base documental pequeña.
- La conversación vive en memoria y se elimina al cerrar el proceso.
