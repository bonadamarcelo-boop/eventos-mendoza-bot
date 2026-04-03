import requests
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ============================================================
# CONFIGURACIÓN
# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")

PALABRAS_CLAVE = [
    "inteligencia artificial Mendoza",
    "robótica Mendoza",
    "charla tecnología Mendoza",
    "evento ciencia Mendoza",
    "machine learning Mendoza",
    "innovación tecnológica Mendoza",
    "IoT Mendoza",
    "automatización industrial Mendoza",
]

ARCHIVO_VISTOS = "eventos_vistos.json"

# ============================================================
# CARGAR / GUARDAR EVENTOS YA NOTIFICADOS
# ============================================================
def cargar_vistos():
    if os.path.exists(ARCHIVO_VISTOS):
        with open(ARCHIVO_VISTOS, "r") as f:
            return json.load(f)
    return []

def guardar_vistos(vistos):
    with open(ARCHIVO_VISTOS, "w") as f:
        json.dump(vistos, f)

# ============================================================
# BUSCAR EVENTOS EN GOOGLE (via SerpAPI gratuita alternativa)
# ============================================================
def buscar_eventos():
    eventos_encontrados = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for palabra in PALABRAS_CLAVE:
        try:
            query = requests.utils.quote(f"{palabra} 2026")
            url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={os.environ.get('GOOGLE_API_KEY')}&cx={os.environ.get('GOOGLE_CX')}&num=3"
            resp = requests.get(url, timeout=10)
            data = resp.json()

            if "items" in data:
                for item in data["items"]:
                    evento = {
                        "titulo": item.get("title", ""),
                        "link": item.get("link", ""),
                        "descripcion": item.get("snippet", ""),
                        "keyword": palabra
                    }
                    eventos_encontrados.append(evento)
        except Exception as e:
            print(f"Error buscando '{palabra}': {e}")

    return eventos_encontrados

# ============================================================
# FILTRAR EVENTOS NUEVOS (no notificados antes)
# ============================================================
def filtrar_nuevos(eventos, vistos):
    nuevos = []
    for e in eventos:
        if e["link"] not in vistos:
            nuevos.append(e)
    return nuevos

# ============================================================
# ENVIAR MENSAJE TELEGRAM
# ============================================================
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        print(f"Telegram: {resp.status_code}")
    except Exception as e:
        print(f"Error Telegram: {e}")

# ============================================================
# ENVIAR EMAIL
# ============================================================
def enviar_email(asunto, cuerpo_html):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"] = GMAIL_USER
        msg["To"] = GMAIL_USER
        msg.attach(MIMEText(cuerpo_html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())
        print("Email enviado OK")
    except Exception as e:
        print(f"Error email: {e}")

# ============================================================
# MAIN
# ============================================================
def main():
    print(f"🔍 Buscando eventos... {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    vistos = cargar_vistos()
    eventos = buscar_eventos()
    nuevos = filtrar_nuevos(eventos, vistos)

    if not nuevos:
        print("Sin eventos nuevos hoy.")
        return

    print(f"✅ {len(nuevos)} evento(s) nuevo(s) encontrado(s)!")

    # Armar mensaje Telegram
    msg_telegram = f"🔔 <b>Eventos Mendoza Tech</b> — {datetime.now().strftime('%d/%m/%Y')}\n\n"
    msg_email_html = f"<h2>🔔 Eventos Mendoza Tech — {datetime.now().strftime('%d/%m/%Y')}</h2>"

    for e in nuevos[:5]:  # máximo 5 por vez
        msg_telegram += f"📌 <b>{e['titulo']}</b>\n"
        msg_telegram += f"🔎 <i>{e['keyword']}</i>\n"
        msg_telegram += f"📝 {e['descripcion'][:150]}...\n"
        msg_telegram += f"🔗 <a href='{e['link']}'>Ver más</a>\n\n"

        msg_email_html += f"""
        <div style='border:1px solid #ddd; padding:15px; margin:10px 0; border-radius:8px;'>
            <h3 style='color:#1a73e8;'>{e['titulo']}</h3>
            <p><b>Búsqueda:</b> {e['keyword']}</p>
            <p>{e['descripcion']}</p>
            <a href='{e['link']}' style='background:#1a73e8;color:white;padding:8px 15px;border-radius:5px;text-decoration:none;'>Ver evento</a>
        </div>
        """

    enviar_telegram(msg_telegram)
    enviar_email(
        f"🔔 {len(nuevos)} evento(s) nuevo(s) en Mendoza Tech — {datetime.now().strftime('%d/%m/%Y')}",
        msg_email_html
    )

    # Guardar como vistos
    for e in nuevos:
        vistos.append(e["link"])
    guardar_vistos(vistos)

if __name__ == "__main__":
    main()
