# Tu Entrenador IA

Agente conversacional construido con LangChain y Cohere. Lee la base documental,
responde preguntas con fuentes y genera rutinas para principiantes mediante un
motor de reglas que solo utiliza los ejercicios autorizados.

## Capacidades

- Agente creado con `langchain.agents.create_agent`.
- Modelo Cohere conectado mediante `langchain-cohere`.
- Lectura local de PDF, Word, Excel, CSV, PowerPoint, TXT y Markdown.
- Fragmentación con `RecursiveCharacterTextSplitter`.
- Recuperación BM25 local sin costo de embeddings.
- Caché invalidada automáticamente cuando cambia un archivo.
- Herramientas cerradas para consultar fuentes, políticas y ejercicios.
- Generación determinista de rutinas con validaciones de seguridad.
- Historial conversacional guardado únicamente en memoria.
- Interfaz web adaptable construida solamente con HTML, CSS y JavaScript.
- API privada con FastAPI para comunicar la página con el agente.

## Estructura de carpetas

```text
AGENTE IA 2.0/
├── documentos Word y logotipo        # Base de información
└── TuEntrenadorIA/                    # Programa
    ├── .env                           # Credencial local, ignorada por Git
    ├── .env.example                   # Plantilla sin secretos
    ├── .venv/                         # Entorno virtual, ignorado por Git
    ├── docs/
    ├── src/tu_entrenador_ia/
    ├── tests/
    └── web/                           # Interfaz HTML, CSS, JavaScript y logotipo
```

## Instalación en Windows

Abre PowerShell en `TuEntrenadorIA` y ejecuta:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Si PowerShell bloquea la activación:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Configuración de Cohere

El archivo `.env` debe contener:

```env
COHERE_API_KEY=tu_clave_real
COHERE_MODEL=command-a-03-2025
WEB_HOST=127.0.0.1
WEB_PORT=8000
```

No agregues comillas ni espacios alrededor de la clave. No compartas ni subas
`.env`. Para validar la configuración sin mostrar la credencial:

```powershell
python -m tu_entrenador_ia check-config
```

## Vista web

Desde `TuEntrenadorIA`, con el entorno virtual activo:

```powershell
python -m tu_entrenador_ia web
```

Abre `http://127.0.0.1:8000` en el navegador. Para detener el servidor, vuelve a
PowerShell y presiona `Ctrl+C`.

La página usa únicamente HTML, CSS y JavaScript. La clave de Cohere permanece en
el backend y nunca se envía al navegador.

## Conversación con el agente

Desde `TuEntrenadorIA`, con el entorno virtual activo:

```powershell
python -m tu_entrenador_ia chat
```

Comandos durante la conversación:

- `borrar`: elimina el historial temporal.
- `salir`: termina el programa.

El agente solicitará nombre, edad, objetivo, días, duración, nivel y aceptación de
políticas antes de llamar a la herramienta que genera la rutina.

## Comandos locales

Estos comandos no consumen la API de Cohere:

```powershell
# Verificar los documentos y el catálogo
python -m tu_entrenador_ia inspect

# Buscar fragmentos localmente
python -m tu_entrenador_ia ask "¿Qué ejercicios están autorizados?"

# Generar una rutina sin modelo de lenguaje
python -m tu_entrenador_ia routine
```

Para usar otra carpeta documental:

```powershell
python -m tu_entrenador_ia --documents "C:\ruta\documentos" chat
```

## Pruebas

Desde `TuEntrenadorIA`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas normales simulan servicios externos y no consumen la API. Las pruebas
de integración reales se ejecutan de forma separada.

## Arquitectura

```text
src/tu_entrenador_ia/
├── document_loaders.py  # PDF, Word, Excel, CSV, PowerPoint y texto
├── retrieval.py         # Fragmentación LangChain, BM25 y caché
├── langchain_agent.py   # Agente, Cohere, herramientas y límites
├── settings.py          # Lectura segura de .env y validación
├── docx_reader.py       # Extracción estructurada de los Word del dominio
├── knowledge.py         # Base de conocimiento y catálogo
├── models.py            # Datos y validaciones
├── routine_engine.py    # Generación determinista de rutinas
├── coach.py             # Fachada del dominio
├── web_sessions.py      # Sesiones web aisladas y temporales
├── web_app.py           # API FastAPI y publicación de la interfaz
└── cli.py               # Comandos de consola y servidor web

web/
├── assets/logo.png      # Logotipo oficial del proyecto
├── index.html           # Estructura y contenido de la vista
├── styles.css           # Diseño adaptable
└── app.js               # Conversación con la API
```

El modelo conversa y selecciona herramientas. No tiene autoridad para crear
ejercicios o evadir reglas: `routine_engine.py` sigue siendo la única fuente para
construir rutinas.

## Preparación para OCI

En una instancia o contenedor de OCI configura:

```env
WEB_HOST=0.0.0.0
WEB_PORT=8000
```

El endpoint `GET /api/health` permite comprobar que la aplicación está activa.
Las conversaciones son temporales y se reinician cuando se reinicia el proceso;
esta primera versión debe ejecutarse con un solo proceso.

## Privacidad

La lectura, fragmentación y búsqueda se realizan localmente. Al usar `chat` o la
vista web, el mensaje del usuario y los fragmentos recuperados que necesita la
respuesta se envían a Cohere. Nombre, edad e historial no se guardan en disco por
el programa. La caché contiene texto de los documentos, nunca la API key.
