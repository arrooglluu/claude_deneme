"""
Vize Randevu Takip Sistemi
--------------------------
Kullanım:
  python main.py                  # config.yaml'dan okur, döngüsel çalışır
  python main.py --once           # Tek seferlik kontrol
  python main.py --test-notify    # Telegram ve e-posta test bildirimi gönderir
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule
import yaml

from notifier import notify
from checkers import vfs_checker, bls_checker

# ---------------------------------------------------------------------------
# Loglama
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("visa_checker.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# Her hedef için son bildirim zamanını tut (aynı slot için spam önle)
_last_notified: dict[str, str] = {}


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_target(config: dict, target: dict):
    if not target.get("enabled", True):
        return

    center = target["center"].upper()
    country = target["country"]
    log.info(f"Kontrol ediliyor: {center} / {country}")

    headless = config.get("headless", True)

    try:
        if center == "VFS":
            slots = vfs_checker.check(target, headless=headless)
        elif center == "BLS":
            slots = bls_checker.check(target, headless=headless)
        else:
            log.warning(f"Bilinmeyen merkez türü: {center}")
            return
    except Exception as e:
        log.error(f"[{center}][{country}] Kontrol sırasında hata: {e}")
        return

    if not slots:
        log.info(f"  → Müsait randevu yok.")
        return

    # Spam önleme: aynı slot listesi daha önce bildirilmişse tekrar bildirme
    slot_key = "|".join(sorted(slots))
    target_id = target["id"]
    if _last_notified.get(target_id) == slot_key:
        log.info(f"  → Slot zaten bildirildi, tekrar gönderilmiyor.")
        return

    _last_notified[target_id] = slot_key
    log.info(f"  → {len(slots)} slot bulundu! Bildirim gönderiliyor...")
    notify(config, target, slots)


def run_all_checks(config: dict):
    log.info("=" * 60)
    log.info(f"Tüm hedefler kontrol ediliyor — {datetime.now().strftime('%H:%M:%S')}")
    log.info("=" * 60)
    for target in config.get("targets", []):
        check_target(config, target)
    log.info("Kontrol tamamlandı.")


def test_notifications(config: dict):
    """Telegram ve e-posta bağlantısını test eder."""
    dummy_target = {
        "country": "TEST Ülkesi",
        "center": "VFS",
        "url": "https://example.com",
        "id": "test",
    }
    notify(config, dummy_target, ["2025-08-01 10:00", "2025-08-02 14:30"])
    log.info("Test bildirimi gönderildi. Telegram ve e-postanı kontrol et.")


def main():
    parser = argparse.ArgumentParser(description="Vize Randevu Takip Sistemi")
    parser.add_argument("--once", action="store_true", help="Tek seferlik kontrol yap, çık")
    parser.add_argument("--test-notify", action="store_true", help="Bildirim testi gönder")
    parser.add_argument("--config", default="config.yaml", help="Config dosyası yolu")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        log.error(f"Config dosyası bulunamadı: {config_path}")
        sys.exit(1)

    config = load_config(str(config_path))

    if args.test_notify:
        test_notifications(config)
        return

    if args.once:
        run_all_checks(config)
        return

    # Periyodik mod
    interval = config.get("check_interval_minutes", 5)
    log.info(f"Periyodik mod: her {interval} dakikada bir kontrol yapılacak.")
    log.info("Durdurmak için Ctrl+C")

    # İlk kontrolü hemen yap
    run_all_checks(config)

    schedule.every(interval).minutes.do(run_all_checks, config=config)

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        log.info("Kullanıcı tarafından durduruldu.")


if __name__ == "__main__":
    main()
