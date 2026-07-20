(() => {
    "use strict";

    const SESSION_KEY = "coachIaSessionId";
    const bienvenida = document.getElementById("bienvenida");
    const chat = document.getElementById("chat");
    const aceptarPoliticas = document.getElementById("aceptarPoliticas");
    const iniciarChat = document.getElementById("iniciarChat");
    const limpiarChat = document.getElementById("limpiarChat");
    const formulario = document.getElementById("formularioChat");
    const mensaje = document.getElementById("mensaje");
    const enviar = document.getElementById("enviarMensaje");
    const mensajes = document.getElementById("mensajes");
    const estado = document.getElementById("estado");

    let sessionId = sessionStorage.getItem(SESSION_KEY);
    let esperandoRespuesta = false;

    aceptarPoliticas.addEventListener("change", () => {
        iniciarChat.disabled = !aceptarPoliticas.checked;
    });

    iniciarChat.addEventListener("click", () => {
        if (!aceptarPoliticas.checked) {
            return;
        }
        bienvenida.hidden = true;
        chat.hidden = false;
        mostrarBienvenida();
        mensaje.focus();
    });

    formulario.addEventListener("submit", async (event) => {
        event.preventDefault();
        await enviarMensaje();
    });

    mensaje.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            formulario.requestSubmit();
        }
    });

    limpiarChat.addEventListener("click", async () => {
        if (esperandoRespuesta) {
            return;
        }
        const previousSession = sessionId;
        sessionId = null;
        sessionStorage.removeItem(SESSION_KEY);
        mensajes.replaceChildren();
        mostrarBienvenida();
        mostrarEstado("");
        mensaje.value = "";
        mensaje.focus();

        if (previousSession) {
            try {
                await fetch("/api/session/reset", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({session_id: previousSession})
                });
            } catch {
                mostrarEstado(
                    "La conversación local se limpió, aunque el servidor no respondió.",
                    true
                );
            }
        }
    });

    async function enviarMensaje() {
        const texto = mensaje.value.trim();
        if (!texto || esperandoRespuesta) {
            return;
        }

        agregarMensaje("usuario", texto);
        mensaje.value = "";
        establecerEspera(true);

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    session_id: sessionId || null,
                    message: texto,
                    accepted_policies: true
                })
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(obtenerDetalle(data));
            }

            sessionId = data.session_id;
            sessionStorage.setItem(SESSION_KEY, sessionId);
            agregarMensaje("coach", data.answer);
            mostrarEstado("");
        } catch (error) {
            const detail = error instanceof Error
                ? error.message
                : "No fue posible conectar con Coach IA.";
            mostrarEstado(detail, true);
        } finally {
            establecerEspera(false);
            mensaje.focus();
        }
    }

    function mostrarBienvenida() {
        if (mensajes.childElementCount > 0) {
            return;
        }
        agregarMensaje(
            "coach",
            "¡Hola! Bienvenido a Tu Entrenador IA.\n\n" +
            "Para preparar tu rutina necesito saber:\n" +
            "• ¿Cómo te llamas?\n" +
            "• ¿Qué edad tienes?\n" +
            "• ¿Cuál es tu objetivo?\n" +
            "• ¿Cuántos días puedes entrenar?\n" +
            "• ¿Cuánto tiempo tienes por sesión?\n" +
            "• ¿Confirmas que eres principiante?"
        );
    }

    function agregarMensaje(author, text) {
        const element = document.createElement("div");
        element.className = `mensaje mensaje-${author}`;
        element.textContent = text;
        element.setAttribute(
            "aria-label",
            author === "coach" ? "Coach IA" : "Tú"
        );
        mensajes.appendChild(element);
        mensajes.scrollTop = mensajes.scrollHeight;
    }

    function establecerEspera(waiting) {
        esperandoRespuesta = waiting;
        enviar.disabled = waiting;
        limpiarChat.disabled = waiting;
        mensaje.disabled = waiting;
        mostrarEstado(waiting ? "Coach IA está respondiendo..." : "");
    }

    function mostrarEstado(text, isError = false) {
        estado.textContent = text;
        estado.classList.toggle("estado-error", isError);
    }

    function obtenerDetalle(data) {
        if (typeof data.detail === "string") {
            return data.detail;
        }
        if (Array.isArray(data.detail) && data.detail.length > 0) {
            return "Revisa el contenido del mensaje antes de enviarlo.";
        }
        return "Coach IA no pudo responder en este momento.";
    }
})();

