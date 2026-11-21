"""Curated product knowledge; no document access or user-claimed permissions."""

import re
import unicodedata


def normalize(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", value.lower()) if not unicodedata.combining(c)
    )


ANDROID_SCOPE = (
    "En Android puedes consultar tus documentos, repasar preguntas y diapositivas, "
    "guardar o compartir PDF y PowerPoint, ver resultados y usar Ayuda. "
    "La creación de cuentas, la recuperación de contraseña, la subida y generación de materiales "
    "y las simulaciones se realizan en la versión web."
)


def guidance(question: str, platform: str, *, is_admin: bool = False) -> dict:
    text = normalize(question)
    android = platform == "android" or bool(re.search(r"\b(android|apk|celular|movil)\b", text))
    platform = "android" if android else "web"
    topic, url, web_only, fixed = "overview", "/documents", False, False
    if any(word in text for word in ("contras", "olvide", "recuper", "restablec")):
        topic, url, web_only = "password", "/forgot-password", True
        reply = "En la web, abre Iniciar sesión y pulsa ¿La olvidaste? o entra en /forgot-password. Escribe el correo de tu cuenta y solicita el enlace. Revisa tu bandeja y spam; el envío requiere que el servicio de correo esté disponible. Abre el enlace recibido para crear una contraseña nueva. No compartas el enlace ni tu contraseña."
    elif any(
        word in text
        for word in (
            "administr",
            "permis",
            "rol",
            "otros usuarios",
            "companeros",
            "privad",
            "clave api",
            "api key",
        )
    ):
        topic, fixed = "permissions", True
        if is_admin and not android:
            url = "/admin/users"
            reply = "Tu cuenta tiene el rol Administrator verificado por el servidor. En la web, Administración → Usuarios permite gestionar usuarios y roles. La ayuda solo orienta: no modifica permisos ni muestra secretos o documentos privados. Cada operación vuelve a comprobar tus permisos."
        else:
            url = "/profile"
            reply = "La ayuda no cambia permisos ni muestra claves o documentos privados. Solo un administrador autorizado puede gestionar roles desde la web. Tu rol se comprueba en el servidor; escribir que eres administrador no concede acceso. Cada estudiante consulta sus propios documentos y resultados."
    elif any(word in text for word in ("registr", "crear cuenta")):
        topic, url, web_only = "registration", "/register", True
        reply = "En la web, abre Crear cuenta en /register y completa tus datos. El registro público crea una cuenta de estudiante cuando está habilitado. Después puedes usar ese mismo correo y contraseña en Android. Los roles de administración no se eligen en el registro público."
    elif any(word in text for word in ("iniciar sesion", "login", "ingresar", "entrar", "acceso")):
        topic, url = "login", "/login"
        reply = "En Iniciar sesión introduce el correo y la contraseña de tu cuenta de Socratia. Web y Android usan la misma cuenta. Si la sesión venció, vuelve a entrar; si olvidaste la contraseña, recupérala desde /forgot-password en la web."
    elif any(word in text for word in ("notific", "push", "aviso")):
        topic = "notifications"
        if android:
            url = "/mobile/account"
            reply = "En Android abre Mi cuenta → Activar notificaciones y acepta el permiso del celular. Cuando estén activas puedes usar Enviar aviso de prueba. Los avisos informan cuando termina o falla la preparación. Al tocar uno se abre tu material; puedes desactivarlos desde Mi cuenta. La entrega depende de conexión, permisos y del sistema operativo."
        else:
            reply = "En Documentos, en Avisos de preparación, pulsa Activar avisos y acepta el permiso del navegador. Usa Probar aviso para comprobarlo en el dispositivo. Puedes desactivarlos en ese apartado. En iPhone se necesita abrir Socratia instalada desde Safari mediante Añadir a pantalla de inicio."
    elif any(
        word in text
        for word in ("simul", "jurado", "camara", "microfono", "defensa", "postura", "mirada")
    ):
        topic, url, web_only = "simulation", "/simulations/new", True
        reply = "En la web abre Simulaciones, elige un documento procesado con banco de preguntas, tribunal y duración. Continúa a la calibración y permite cámara y micrófono. Puedes responder por voz o texto. Finaliza la defensa para ver su evaluación en Resultados. Las mediciones de cámara son estimaciones y pueden indicar sin medición."
    elif any(word in text for word in ("resultado", "evaluacion", "nota", "historial", "reporte")):
        topic, url = "results", "/mobile/results" if android else "/history"
        reply = "En Android abre Resultados → Ver evaluación para consultar tus defensas realizadas en la web. En la web abre Resultados y el reporte de tu defensa. Una evaluación pendiente todavía no tiene nota; las dimensiones sin evidencia no deben interpretarse como mediciones reales."
    elif any(word in text for word in ("diaposit", "powerpoint", "presentacion", "pptx")):
        topic, web_only = "slides", bool(re.search(r"gener|crea|estructura", text))
        reply = (
            "En Android abre Documentos → Ver materiales. Si las diapositivas ya están listas, puedes repasarlas y usar Guardar o compartir PowerPoint. Para crearlas, abre el documento procesado en la web, elige la duración y genera el material. La tarea continúa si sales de la página."
            if android
            else "En Documentos abre un documento procesado, elige la duración y genera tu material. La tarea continúa si sales de la página. Cuando termine puedes descargar el PowerPoint; abrir material ya preparado no lo vuelve a generar."
        )
    elif any(word in text for word in ("pregunta", "banco", "pdf", "descarg")) and not re.search(
        r"\b(subir|subida|cargar|tamano)\b", text
    ):
        topic, web_only = "questions", bool(re.search(r"gener|crea", text))
        reply = (
            "En Android abre Documentos → Ver materiales. Si el banco está preparado, puedes repasar las preguntas y pulsar Guardar o compartir PDF. Para generar el banco abre el documento procesado en la web y usa Generar banco de preguntas. No se descargan las respuestas internas del evaluador."
            if android
            else "En Documentos abre tu documento procesado y pulsa Generar banco de preguntas. Cuando termine, usa Descargar preguntas en PDF. El banco incluye preguntas de práctica; las respuestas internas del evaluador no se descargan."
        )
    elif any(
        word in text
        for word in ("document", "material", "subir", "subida", "archivo", "cargar", "tamano")
    ):
        topic, web_only = "documents", bool(re.search(r"sub|carg|proces|tamano", text))
        reply = (
            "En Android abre Documentos → Ver materiales para consultar los archivos y materiales de tu cuenta. Para subir y procesar un PDF o DOCX utiliza Documentos en la web. Allí se muestra el límite real del servidor; un escaneo sin texto puede necesitar OCR."
            if android
            else "En Documentos selecciona un PDF o DOCX. La pantalla muestra el límite real del servidor. Abre el archivo y pulsa Procesar documento. Después puedes preparar preguntas y diapositivas. Un PDF escaneado sin texto puede necesitar OCR."
        )
    else:
        reply = (
            ANDROID_SCOPE
            if android
            else "Puedo guiarte con inicio de sesión, recuperación de contraseña, documentos, preguntas, diapositivas, simulaciones, resultados y avisos. Dime qué quieres hacer. Las funciones de Android son de consulta y repaso; la generación y las simulaciones se realizan en la web."
        )
    if android and web_only:
        reply = "Esta operación se realiza en la versión web, no desde Android. " + reply
    if android and topic not in ("overview", "notifications"):
        reply += " En Android la generación y las simulaciones no están disponibles."
    return {
        "answer": reply,
        "url": url,
        "engine": "guia_local",
        "platform": platform,
        "topic": topic,
        "web_only": web_only,
        "fixed": fixed,
    }


def valid_explanation(text: str, guide: dict) -> bool:
    if not isinstance(text, str) or not 10 <= len(text.strip()) <= 2000:
        return False
    if not text.rstrip().endswith((".", "!", "?", "…")):
        return False
    if re.search(r"https?://|\[[^\]]+\]\(|<[^>]+>", text):
        return False
    if guide["platform"] == "android" and re.search(
        r"pulsa.{0,20}generar|crea.{0,15}simulacion", normalize(text)
    ):
        return False
    return True
