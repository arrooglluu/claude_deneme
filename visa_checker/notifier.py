import smtplib
import logging
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

log = logging.getLogger(__name__)


def send_telegram(bot_token: str, chat_id: str, message: str) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=10)
        resp.raise_for_status()
        log.info("Telegram bildirimi gönderildi.")
        return True
    except Exception as e:
        log.error(f"Telegram hatası: {e}")
        return False


def send_email(cfg: dict, subject: str, body: str) -> bool:
    if not cfg.get("enabled"):
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = cfg["sender"]
        msg["To"] = ", ".join(cfg["recipients"])
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as server:
            server.starttls()
            server.login(cfg["sender"], cfg["password"])
            server.sendmail(cfg["sender"], cfg["recipients"], msg.as_string())
        log.info("E-posta gönderildi.")
        return True
    except Exception as e:
        log.error(f"E-posta hatası: {e}")
        return False


def notify(config: dict, target: dict, slots: list[str]):
    """Boş randevu bulunduğunda Telegram + e-posta bildirimi gönderir."""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    country = target["country"]
    center = target["center"]

    slot_text = "\n".join(f"  • {s}" for s in slots) if slots else "  • (tarih bilgisi alınamadı)"

    message = (
        f"🟢 <b>VİZE RANDEVUSU BULUNDU!</b>\n\n"
        f"🌍 <b>Ülke:</b> {country}\n"
        f"🏢 <b>Merkez:</b> {center}\n"
        f"📅 <b>Müsait slotlar:</b>\n{slot_text}\n\n"
        f"🔗 <b>Link:</b> {target['url']}\n"
        f"🕐 <b>Kontrol zamanı:</b> {now}"
    )

    plain = (
        f"VİZE RANDEVUSU BULUNDU!\n\n"
        f"Ülke: {country}\n"
        f"Merkez: {center}\n"
        f"Müsait slotlar:\n{slot_text}\n\n"
        f"Link: {target['url']}\n"
        f"Kontrol zamanı: {now}"
    )

    tg_cfg = config.get("telegram", {})
    if tg_cfg.get("bot_token") and tg_cfg.get("chat_id"):
        send_telegram(tg_cfg["bot_token"], tg_cfg["chat_id"], message)

    send_email(config.get("email", {}), f"[VİZE] {country} randevusu açıldı!", plain)
