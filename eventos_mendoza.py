import requests
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")

PALABRAS_CLAVE = [
    "inteligencia artificial Mendoza 2026",
    "robótica Mendoza 2026",
    "charla tecnología Mendoza",
    "evento ciencia Mendoza 2026",
    "machine learning Mendoza",
]

ARCHIVO_VISTOS = "eventos_vistos.json"

def cargar_vistos():
    if os.path.exists(ARCHIVO_VISTOS):
        with open(ARCHIVO_VISTOS, "r") as f:
            return json.load(f)
    return []

def guardar_vistos(vistos):
    with open(ARCHIVO_VISTOS, "w") as f:
        json.dump(vistos, f)

def buscar_eventos():
    eventos_encontrados = []
    for palabra in PALABRAS_CLAVE:
        try:
            url = "https://serpapi.com/search"
            params = {
                "api_key": SERPAPI_KEY,
                "engine": "google",
                "q": palabra,
                "hl": "es",
                "gl": "ar",
                "num": 5,
                "tbs": "qdr:m",
            }
            resp = requests.get(url, params=params, timeout=15)
            print(f"Buscando: '{palabra}' → status {resp.status_code}")
            if resp.status_code != 200:
                print(f"  Error: {resp.text[:200]}")
                continue
            data = resp.json()
            resultados = data.get("organic_results", [])
            print(f"  Encontrados: {len(resultados)} resultados")
            for item in resultados:
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

def filtrar_nuevos(eventos, vistos):
    nuevos = []
    links_vistos = set(vistos)
    links_nuevos = set()
    for e in eventos:
        if e["link"] not in links_vistos and e["link"] not in links_nuevos:
            nuevos.append(e)
            links_nuevos.add(e["link"])
    return nuevos

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        print(f"Telegram: {resp.status_code}")
    except Exception as e:
        print(f"Error Telegram: {e}")

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

def main():
    print(f"🔍 Buscando eventos... {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"SerpAPI Key: {'OK' if SERPAPI_KEY else 'FALTA'}")

    vistos = cargar_vistos()
    eventos = buscar_eventos()
    print(f"\nTotal encontrados: {len(eventos)}")
    nuevos = filtrar_nuevos(eventos, vistos)
    print(f"Nuevos: {len(nuevos)}")

    if not nuevos:
        print("Sin eventos nuevos hoy.")
        return

    msg_telegram = f"🔔 <b>Eventos Mendoza Tech</b> — {datetime.now().strftime('%d/%m/%Y')}\n\n"
    msg_email_html = f"<h2>🔔 Eventos Mendoza Tech — {datetime.now().strftime('%d/%m/%Y')}</h2>"

    for e in nuevos[:5]:
        msg_telegram += f"📌 <b>{e['titulo']}</b>\n🔎 <i>{e['keyword']}</i>\n📝 {e['descripcion'][:150]}\n🔗 <a href='{e['link']}'>Ver más</a>\n\n"
        msg_email_html += f"<div style='border:1px solid #ddd;padding:15px;margin:10px 0;border-radius:8px;'><h3 style='color:#1a73e8;'>{e['titulo']}</h3><p>{e['descripcion']}</p><a href='{e['link']}' style='background:#1a73e8;color:white;padding:8px 15px;border-radius:5px;text-decoration:none;'>Ver evento</a></div>"

    enviar_telegram(msg_telegram)
    enviar_email(f"🔔 {len(nuevos)} evento(s) nuevo(s) en Mendoza Tech — {datetime.now().strftime('%d/%m/%Y')}", msg_email_html)

    for e in nuevos:
        vistos.append(e["link"])
    guardar_vistos(vistos)

if __name__ == "__main__":
    main()
