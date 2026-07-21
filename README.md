<p align="center">
  <img src="web/assets/logo.png" alt="Tu Entrenador IA" width="220">
</p>

<h1 align="center">Tu Entrenador IA</h1>

<p align="center">
  Agente de inteligencia artificial para generar rutinas de entrenamiento en casa para principiantes.
</p>

Aplicación conversacional construida con LangChain, Cohere y FastAPI. Consulta
una base documental, responde preguntas y genera rutinas mediante un motor de
reglas que solo utiliza los ejercicios autorizados.

## Capacidades

- Agente creado con `langchain.agents.create_agent`.
- Modelo de lenguaje conectado mediante `langchain-cohere`.
- Lectura local de PDF, Word, Excel, CSV, PowerPoint, TXT y Markdown.
- Extracción estructurada de los documentos Word del dominio.
- Recuperación BM25 local sin costo de embeddings.
- Caché actualizada automáticamente cuando cambia un documento.
- Generación determinista de rutinas con validaciones de seguridad.
- Interfaz adaptable construida solamente con HTML, CSS y JavaScript.
- API FastAPI con sesiones temporales y aisladas.
- Límite gratuito de diez mensajes por minuto y dirección IP.
- Configuración reproducible para Render mediante `render.yaml`.

## Estructura

```text
TuEntrenadorIA/
├── documents/                     # Seis documentos Word publicados
├── docs/
├── src/tu_entrenador_ia/
├── tests/
├── web/                           # HTML, CSS, JavaScript y logotipo
├── .env.example                   # Plantilla local sin secretos
├── .gitignore                     # Excluye .env, cachés y entorno virtual
├── pyproject.toml                 # Proyecto y dependencias de Python
└── render.yaml                    # Servicio web gratuito de Render
```

Los documentos de `documents/` forman parte de este repositorio público y pueden
ser descargados por cualquier persona. La API key de Cohere no forma parte del
repositorio.

## Requisitos locales

- Python 3.11 o superior. El despliegue está fijado a Python 3.13.3, que es la
  versión con la que se validó el proyecto.
- Una API key de Cohere.
- PowerShell para seguir los ejemplos de Windows.

## Instalación en Windows

Abre PowerShell dentro de `TuEntrenadorIA` y ejecuta cada comando por separado:

```powershell
python -m venv .venv
```

```powershell
.\.venv\Scripts\Activate.ps1
```

```powershell
python -m pip install -e .
```

Si PowerShell bloquea la activación:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Después vuelve a ejecutar el comando de activación.

## Configuración local

Copia `.env.example` como `.env` y registra tu clave:

```env
COHERE_API_KEY=tu_clave_real
COHERE_MODEL=command-a-03-2025
COACH_DOCS_DIR=documents
WEB_HOST=127.0.0.1
WEB_PORT=8000
```

No agregues comillas ni espacios alrededor de la clave. El archivo `.env` está
ignorado por Git y no debe subirse ni compartirse.

Valida la configuración sin mostrar la credencial:

```powershell
python -m tu_entrenador_ia check-config
```

## Ejecución local

Inicia el servidor:

```powershell
python -m tu_entrenador_ia web
```

Mantén la terminal abierta y visita:

```text
http://127.0.0.1:8000
```

Presiona `Ctrl+C` en la terminal solamente cuando quieras detenerlo.

## Despliegue gratuito en Render

El repositorio incluye un [Blueprint de Render](render.yaml). No se necesita
Docker, una base de datos ni un framework adicional para el frontend.

1. Publica este repositorio en GitHub y confirma que `.env` no aparezca entre
   los archivos.
2. Crea una cuenta en [Render](https://render.com/).
3. En el Dashboard selecciona **New > Blueprint**.
4. Conecta el repositorio público de GitHub.
5. Render detectará `render.yaml` y solicitará `COHERE_API_KEY`.
6. Pega la clave únicamente en el campo secreto de Render.
7. Confirma la creación del servicio `tu-entrenador-ia`.
8. Espera a que el despliegue termine y abre la dirección `onrender.com` que
   Render asigne.

La configuración ejecuta:

```text
Build Command: pip install -e .
Start Command: python -m tu_entrenador_ia web
Health Check: /api/health
```

Render proporciona automáticamente `PORT`; la aplicación lo utiliza con
prioridad sobre `WEB_PORT` y escucha en `0.0.0.0` dentro del servicio.

La documentación oficial relevante es:

- [Desplegar FastAPI en Render](https://render.com/docs/deploy-fastapi)
- [Puertos de servicios web](https://render.com/docs/web-services#port-binding)
- [Variables y secretos](https://render.com/docs/configure-environment-variables)
- [Especificación de Blueprint](https://render.com/docs/blueprint-spec)

### Limitaciones del plan gratuito

- El servicio entra en reposo después de 15 minutos sin tráfico.
- La primera visita posterior puede tardar aproximadamente un minuto.
- Las conversaciones están en memoria y se pierden al reiniciar o suspender el
  servicio.
- La caché documental también puede reconstruirse, pero los Word permanecen
  disponibles porque forman parte del repositorio.
- No se usa almacenamiento persistente ni base de datos.
- Las claves Trial de Cohere son gratuitas y limitadas, pero Cohere las destina
  a evaluación y prototipos, no a aplicaciones comerciales o productivas.
- Si se alcanza el límite gratuito de Cohere, el agente dejará de responder hasta
  que la cuota vuelva a estar disponible; Render continuará funcionando.

Consulta las [limitaciones oficiales del plan gratuito](https://render.com/docs/free).
Consulta también los [límites de las claves de Cohere](https://docs.cohere.com/v2/docs/rate-limits)
y sus [condiciones de precios](https://cohere.com/pricing).

## Actualizar los documentos

Para actualizar la información desplegada:

1. Sustituye los archivos correspondientes dentro de `documents/`.
2. Conserva sus nombres y el formato Word para mantener la extracción
   estructurada.
3. Ejecuta `inspect` y las pruebas.
4. Confirma los cambios en Git y súbelos a GitHub.

Render realizará un nuevo despliegue y la caché se regenerará al detectar los
cambios.

## Comandos disponibles

```powershell
# Verificar los documentos y el catálogo
python -m tu_entrenador_ia inspect

# Buscar información sin consumir Cohere
python -m tu_entrenador_ia ask "¿Qué ejercicios están autorizados?"

# Generar una rutina sin usar el modelo de lenguaje
python -m tu_entrenador_ia routine

# Conversar en la terminal mediante Cohere
python -m tu_entrenador_ia chat
```

Durante `chat`, utiliza `borrar` para eliminar la conversación temporal y
`salir` para terminar.

## Pruebas

Desde `TuEntrenadorIA`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas normales simulan servicios externos y no consumen la API. La prueba
real de Cohere se mantiene separada.

## Arquitectura

```text
src/tu_entrenador_ia/
├── document_loaders.py  # PDF, Word, Excel, CSV, PowerPoint y texto
├── retrieval.py         # Fragmentación LangChain, BM25 y caché
├── langchain_agent.py   # Agente, Cohere, herramientas y límites
├── settings.py          # Variables locales, PORT de Render y secretos
├── docx_reader.py       # Extracción estructurada de Word
├── knowledge.py         # Base de conocimiento y catálogo
├── models.py            # Datos y validaciones
├── routine_engine.py    # Generación determinista de rutinas
├── coach.py             # Fachada del dominio
├── web_sessions.py      # Sesiones aisladas y temporales
├── web_rate_limit.py    # Protección gratuita por IP
├── web_app.py           # API FastAPI y publicación de la interfaz
└── cli.py               # Consola y servidor web
```

El modelo conversa y selecciona herramientas. No tiene autoridad para inventar
ejercicios o evadir reglas: `routine_engine.py` es la única fuente autorizada
para construir rutinas.

## Privacidad y seguridad

- La clave de Cohere solo se lee desde `.env` o las variables secretas de
  Render; nunca se envía al navegador.
- La lectura, fragmentación y búsqueda de documentos se realizan dentro del
  servidor.
- Los mensajes y fragmentos necesarios para responder se envían a Cohere.
- Nombre, edad e historial no se guardan en una base de datos.
- La API limita mensajes por IP para reducir el consumo abusivo de Cohere.
- Los documentos de `documents/` son públicos porque el repositorio de GitHub es
  público.
