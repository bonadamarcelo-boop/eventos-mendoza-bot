import requests
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
GMAIL_USER       = os.environ.get("GMAIL_USER", "")
GMAIL_PASSWORD   = os.environ.get("GMAIL_PASSWORD", "")
SERPAPI_KEY      = os.environ.get("SERPAPI_KEY", "")

VISTAS_FILE = "vacantes_vistas.json"

KEYWORDS = [
    # Oil & Gas
    "instrumentación oil gas Argentina",
    "integridad activos oil gas Argentina",
    "SCADA oil gas Argentina",
    "mantenimiento yacimientos Argentina",
    "confiabilidad activos petróleo Argentina",
    # Minería
    "instrumentación minería Argentina",
    "mantenimiento planta minera Argentina",
    "automatización industrial minería Argentina",
    "reliability mining Argentina",
    # Energía renovable
    "mantenimiento parque eólico Argentina",
    "O&M energía solar Argentina",
    "SCADA energías renovables Argentina",
    # Transversal
    "jefe mantenimiento industrial Mendoza",
    "business intelligence industrial Argentina",
    "confiabilidad mantenimiento Cuyo",
]

TERMINOS_EXCLUIR = ["prácticas", "pasantía", "junior sin experiencia", "reclutador"]


def cargar_vistas():
    if os.path.exists(VISTAS_FILE):
        with open(VISTAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def guardar_vistas(vistas):
    with open(VISTAS_FILE, "w", encoding="utf-8") as f:
        json.dump(vistas[-500:], f, ensure_ascii=False, indent=2)


def buscar_vacantes():
    vacantes = []
    for keyword in KEYWORDS:
        query = f"{keyword} vacante empleo trabajo site:linkedin.com OR site:bumeran.com OR site:computrabajo.com OR site:indeed.com"
        params = {
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": 5,
            "hl": "es",
            "gl": "ar",
        }
        try:
            resp = requests.get("https://serpapi.com/search", params=params, timeout=15)
            data = resp.json()
            resultados = data.get("organic_results", [])
            for r in resultados:
                link = r.get("link", "")
                titulo = r.get("title", "")
                descripcion = r.get("snippet", "")
                if not link or not titulo:
                    continue
                excluir = any(t.lower() in titulo.lower() or t.lower() in descripcion.lower()
                              for t in TERMINOS_EXCLUIR)
                if excluir:
                    continue
                vacantes.append({
                    "titulo": titulo,
                    "link": link,
                    "descripcion": descripcion,
                    "keyword": keyword,
                })
        except Exception as e:
            print(f"Error buscando '{keyword}': {e}")
    return vacantes


def filtrar_nuevas(vacantes, vistas):
    return [v for v in vacantes if v["link"] not in vistas]


def dedup(vacantes):
    vistos = set()
    resultado = []
    for v in vacantes:
        if v["link"] not in vistos:
            vistos.add(v["link"])
            resultado.append(v)
    return resultado


def enviar_telegram(mensaje):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram: credenciales faltantes")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        print(f"Telegram: {resp.status_code}")
    except Exception as e:
        print(f"Error Telegram: {e}")


def enviar_email(asunto, cuerpo_html):
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("Gmail: credenciales faltantes")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"]    = GMAIL_USER
        msg["To"]      = GMAIL_USER
        msg.attach(MIMEText(cuerpo_html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())
        print("Email enviado OK")
    except Exception as e:
        print(f"Error email: {e}")


def main():
    print(f"Buscando vacantes... {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"SerpAPI Key: {'OK' if SERPAPI_KEY else 'FALTA'}")

    vistas   = cargar_vistas()
    vacantes = buscar_vacantes()
    vacantes = dedup(vacantes)
    print(f"Total encontradas: {len(vacantes)}")

    nuevas = filtrar_nuevas(vacantes, vistas)
    print(f"Nuevas: {len(nuevas)}")

    if not nuevas:
        print("Sin vacantes nuevas hoy.")
        return

    fecha = datetime.now().strftime("%d/%m/%Y")

    # Telegram (máx 5 para no saturar)
    msg_telegram = f"💼 <b>Vacantes nuevas</b> — {fecha}\n\n"
    for v in nuevas[:5]:
        msg_telegram += (
            f"📌 <b>{v['titulo']}</b>\n"
            f"🔎 <i>{v['keyword']}</i>\n"
            f"📝 {v['descripcion'][:120]}...\n"
            f"🔗 <a href='{v['link']}'>Ver vacante</a>\n\n"
        )
    if len(nuevas) > 5:
        msg_telegram += f"...y {len(nuevas) - 5} más. Revisá el email para ver todas."
    enviar_telegram(msg_telegram)

    # Email (todas)
    cards_html = ""
    for v in nuevas:
        cards_html += f"""
        <div style="border:1px solid #ddd;padding:15px;margin:10px 0;border-radius:8px;">
            <h3 style="color:#1a73e8;margin:0 0 6px;">{v['titulo']}</h3>
            <p style="font-size:12px;color:#888;margin:0 0 8px;">Búsqueda: {v['keyword']}</p>
            <p style="margin:0 0 10px;">{v['descripcion']}</p>
            <a href="{v['link']}" style="background:#1a73e8;color:white;padding:8px 15px;
               border-radius:5px;text-decoration:none;font-size:14px;">Ver vacante</a>
        </div>"""

    cuerpo_html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;padding:20px;">
        <h2 style="color:#1a73e8;">💼 {len(nuevas)} vacante(s) nueva(s) — {fecha}</h2>
        <p style="color:#555;">Resultados de búsqueda automática en LinkedIn, Bumeran, Computrabajo e Indeed.</p>
        {cards_html}
        <hr style="margin-top:30px;">
        <p style="color:#aaa;font-size:12px;">Bot de vacantes — bonadamarcelo-boop/eventos-mendoza-bot</p>
    </body></html>"""

    enviar_email(
        f"💼 {len(nuevas)} vacante(s) nueva(s) — {fecha}",
        cuerpo_html
    )

    for v in nuevas:
        vistas.append(v["link"])
    guardar_vistas(vistas)
    print("Proceso completado.")


if __name__ == "__main__":
    main()
