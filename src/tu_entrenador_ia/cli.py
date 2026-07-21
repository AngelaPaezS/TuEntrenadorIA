"""Interfaz de consola para inspeccionar, consultar y usar Coach IA."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from .coach import CoachIA, format_routine, format_search_results
from .document_loaders import DocumentLoadError
from .docx_reader import DocumentReadError
from .knowledge import KnowledgeError
from .langchain_agent import AgentExecutionError, LangChainCoachAgent
from .models import DomainValidationError, Objective
from .routine_engine import RoutineGenerationError
from .settings import (
    CohereSettings,
    ConfigurationError,
    WebSettings,
    check_cohere_api_key,
)
from .web_app import create_web_app


def build_parser() -> argparse.ArgumentParser:
    """Construye todos los comandos y argumentos admitidos por la aplicación."""

    parser = argparse.ArgumentParser(
        prog="coach-ia",
        description=(
            "Lee los documentos de Tu Entrenador IA, consulta su contenido y "
            "genera rutinas para principiantes."
        ),
    )
    parser.add_argument(
        "--documents",
        type=Path,
        default=_default_documents_directory(),
        help=(
            "Carpeta que contiene los documentos compatibles "
            "(por defecto: detección automática)."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Comprueba y resume los documentos procesados.",
    )
    inspect_parser.set_defaults(handler=_handle_inspect)

    config_parser = subparsers.add_parser(
        "check-config",
        help="Valida la configuración y la API key de Cohere sin mostrarla.",
    )
    config_parser.set_defaults(handler=_handle_check_config)

    chat_parser = subparsers.add_parser(
        "chat",
        help="Inicia una conversación con el agente LangChain y Cohere.",
    )
    chat_parser.set_defaults(handler=_handle_chat)

    web_parser = subparsers.add_parser(
        "web",
        help="Inicia la vista web simple con el agente.",
    )
    web_parser.add_argument(
        "--host",
        help="Dirección de escucha; reemplaza WEB_HOST.",
    )
    web_parser.add_argument(
        "--port",
        type=int,
        help="Puerto de escucha; reemplaza WEB_PORT.",
    )
    web_parser.set_defaults(handler=_handle_web)

    ask_parser = subparsers.add_parser(
        "ask",
        help="Busca una pregunta dentro del conocimiento documental.",
    )
    ask_parser.add_argument("question", help="Pregunta o texto que se desea buscar.")
    ask_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Número máximo de fragmentos (por defecto: 5).",
    )
    ask_parser.set_defaults(handler=_handle_ask)

    routine_parser = subparsers.add_parser(
        "routine",
        help="Genera una rutina; pregunta los datos que no se proporcionen.",
    )
    routine_parser.add_argument("--name", help="Nombre de la persona.")
    routine_parser.add_argument("--age", type=int, help="Edad de la persona.")
    routine_parser.add_argument(
        "--objective",
        help=(
            "Bajar de peso, mejorar condición física o crear el hábito "
            "del ejercicio."
        ),
    )
    routine_parser.add_argument(
        "--days",
        type=int,
        choices=(2, 3, 4, 5),
        help="Días disponibles por semana.",
    )
    routine_parser.add_argument(
        "--minutes",
        type=int,
        choices=(15, 20, 30, 45),
        help="Duración objetivo de cada sesión.",
    )
    routine_parser.add_argument(
        "--beginner",
        action="store_true",
        default=None,
        help="Confirma que el nivel es principiante.",
    )
    routine_parser.add_argument(
        "--accept-policies",
        action="store_true",
        default=None,
        help="Confirma la lectura y aceptación de las políticas.",
    )
    routine_parser.set_defaults(handler=_handle_routine)
    return parser


def main(arguments: list[str] | None = None) -> int:
    """Ejecuta el comando solicitado y devuelve un código apto para automatización."""

    _configure_output_encoding()
    parser = build_parser()
    parsed = parser.parse_args(arguments)
    try:
        coach = CoachIA.from_directory(parsed.documents)
        parsed.handler(coach, parsed)
        return 0
    except (
        DocumentReadError,
        KnowledgeError,
        DocumentLoadError,
        DomainValidationError,
        RoutineGenerationError,
        ConfigurationError,
        AgentExecutionError,
        ValueError,
    ) as exc:
        _print_error(exc)
        return 2
    except KeyboardInterrupt:
        print("\nOperación cancelada.", file=sys.stderr)
        return 130


def _default_documents_directory() -> Path:
    """Localiza las fuentes configuradas, incluidas o cercanas al proyecto."""

    configured = os.environ.get("COACH_DOCS_DIR")
    if configured:
        return Path(configured)

    current_directory = Path.cwd()
    if any(current_directory.glob("*.docx")):
        return current_directory

    bundled_directory = _project_directory() / "documents"
    if any(bundled_directory.glob("*.docx")):
        return bundled_directory

    parent_directory = current_directory.parent
    if any(parent_directory.glob("*.docx")):
        return parent_directory
    return current_directory


def _project_directory() -> Path:
    """Obtiene la raíz de TuEntrenadorIA desde la ubicación del paquete."""

    return Path(__file__).resolve().parents[2]


def _configure_output_encoding() -> None:
    """Usa UTF-8 cuando la terminal permite reconfigurar sus flujos de salida."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def _handle_check_config(coach: CoachIA, arguments: argparse.Namespace) -> None:
    """Valida el archivo local y consulta el endpoint oficial de Cohere."""

    del coach, arguments
    settings = CohereSettings.from_project(_project_directory())
    if not check_cohere_api_key(settings):
        raise ConfigurationError("Cohere indicó que la API key no es válida.")
    print("Configuración de Cohere válida.")
    print(f"Modelo configurado: {settings.model}")
    print("La API key está activa y no fue mostrada.")


def _handle_chat(coach: CoachIA, arguments: argparse.Namespace) -> None:
    """Mantiene una sesión interactiva con memoria solamente en RAM."""

    settings = CohereSettings.from_project(_project_directory())
    agent = LangChainCoachAgent.from_project(
        coach=coach,
        documents_directory=arguments.documents,
        project_directory=_project_directory(),
        settings=settings,
    )
    print(
        f"Coach IA conectado con {agent.model_name}. "
        f"Fragmentos documentales disponibles: {agent.document_count}."
    )
    print("Escribe tu mensaje. Usa 'borrar' para limpiar la conversación o 'salir'.")
    while True:
        message = input("\nTú: ").strip()
        if message.casefold() in {"salir", "exit", "quit"}:
            print("Coach IA: ¡Hasta pronto!")
            return
        if message.casefold() in {"borrar", "limpiar"}:
            agent.clear_history()
            print("Coach IA: Conversación temporal eliminada.")
            continue
        if not message:
            continue
        print(f"\nCoach IA: {agent.ask(message)}")


def _handle_web(coach: CoachIA, arguments: argparse.Namespace) -> None:
    """Inicia Uvicorn con la API y los archivos HTML estáticos."""

    import uvicorn

    configured = WebSettings.from_project(_project_directory())
    host = arguments.host or configured.host
    port = arguments.port if arguments.port is not None else configured.port
    if not 1 <= port <= 65_535:
        raise ConfigurationError("El puerto debe estar entre 1 y 65535.")

    application = create_web_app(
        documents_directory=arguments.documents,
        project_directory=_project_directory(),
        coach=coach,
    )
    visible_host = "127.0.0.1" if host == "0.0.0.0" else host
    print(f"Tu Entrenador IA disponible en http://{visible_host}:{port}")
    print("Presiona Ctrl + C para detener el servidor.")
    uvicorn.run(
        application,
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )


def _handle_inspect(coach: CoachIA, arguments: argparse.Namespace) -> None:
    """Muestra métricas y nombres para comprobar la carga documental."""

    del arguments
    print(coach.summary())
    print("\nArchivos:")
    for document in coach.knowledge.documents:
        print(f"  - {document.path.name}")
    print("\nCatálogo de ejercicios:")
    for number, exercise in enumerate(coach.knowledge.exercises, start=1):
        print(f"  {number:02d}. {exercise.name} — {exercise.muscle_group}")


def _handle_ask(coach: CoachIA, arguments: argparse.Namespace) -> None:
    """Busca la pregunta y presenta fragmentos trazables a la fuente."""

    results = coach.search(arguments.question, arguments.limit)
    print(format_search_results(results))


def _handle_routine(coach: CoachIA, arguments: argparse.Namespace) -> None:
    """Completa datos faltantes de forma interactiva y muestra la rutina."""

    name = arguments.name or _ask_non_empty("¿Cómo te llamas? ")
    age = (
        arguments.age
        if arguments.age is not None
        else _ask_integer("¿Qué edad tienes? ")
    )
    objective = arguments.objective or _ask_objective()
    days = (
        arguments.days
        if arguments.days is not None
        else _ask_choice(
            "¿Cuántos días por semana puedes entrenar? (2, 3, 4 o 5) ",
            {2, 3, 4, 5},
        )
    )
    minutes = (
        arguments.minutes
        if arguments.minutes is not None
        else _ask_choice(
            "¿Cuántos minutos puedes dedicar por sesión? (15, 20, 30 o 45) ",
            {15, 20, 30, 45},
        )
    )
    is_beginner = (
        arguments.beginner
        if arguments.beginner is not None
        else _ask_yes_no("¿Confirmas que tu nivel es principiante? [s/n] ")
    )
    accepted_policies = arguments.accept_policies
    if accepted_policies is None:
        print(
            "\nLa rutina es informativa y no sustituye la asesoría médica, "
            "fisioterapéutica o de un entrenador profesional. Se realiza de "
            "forma voluntaria y bajo responsabilidad del usuario."
        )
        accepted_policies = _ask_yes_no(
            "¿Leíste y aceptas las políticas de uso? [s/n] "
        )

    routine = coach.create_routine(
        name=name,
        age=age,
        objective=objective,
        days=days,
        minutes=minutes,
        is_beginner=bool(is_beginner),
        accepted_policies=bool(accepted_policies),
    )
    print()
    print(format_routine(routine))


def _ask_non_empty(prompt: str) -> str:
    """Solicita texto hasta recibir al menos un carácter visible."""

    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Este dato es obligatorio.")


def _ask_integer(prompt: str) -> int:
    """Solicita un número entero y explica los errores de formato."""

    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("Escribe un número entero.")


def _ask_choice(prompt: str, choices: set[int]) -> int:
    """Solicita un entero hasta que pertenezca al conjunto permitido."""

    while True:
        value = _ask_integer(prompt)
        if value in choices:
            return value
        allowed = ", ".join(str(item) for item in sorted(choices))
        print(f"Opciones permitidas: {allowed}.")


def _ask_yes_no(prompt: str) -> bool:
    """Interpreta respuestas afirmativas o negativas comunes en español."""

    while True:
        answer = input(prompt).strip().casefold()
        if answer in {"s", "si", "sí"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Responde s o n.")


def _ask_objective() -> Objective:
    """Muestra los objetivos documentados y valida la selección."""

    print("Objetivos disponibles:")
    for position, objective in enumerate(Objective, start=1):
        print(f"  {position}. {objective.value}")
    while True:
        raw_value = input("¿Cuál es tu objetivo? ").strip()
        if raw_value.isdigit():
            position = int(raw_value)
            objectives = tuple(Objective)
            if 1 <= position <= len(objectives):
                return objectives[position - 1]
        try:
            return Objective.parse(raw_value)
        except DomainValidationError as exc:
            print(exc)


def _print_error(error: Exception) -> None:
    """Imprime errores del dominio de forma clara sin mostrar trazas internas."""

    if isinstance(error, DomainValidationError):
        print("No se pudo generar la rutina:", file=sys.stderr)
        for message in error.messages:
            print(f"  - {message}", file=sys.stderr)
    else:
        print(f"Error: {error}", file=sys.stderr)
