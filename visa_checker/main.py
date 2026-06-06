"""
Vize Randevu Takip Sistemi
--------------------------
Kullanım:
  python main.py                  # Döngüsel çalışır
  python main.py --once           # Tek seferlik kontrol
  python main.py --test-notify    # Telegram ve e-posta test bildirimi
"""

import argparse
import logging
import random
import sys
import time
from datetime import datetime

import config_loader
from notifier import notify
from checkers import vfs_checker, bls_checker, asvisa_checker, idata_checker
from browser import jitter_interval

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

_last_notified: dict[str, str] = {}


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
        elif center == "ASVISA":
            slots = asvisa_checker.check(target, headless=headless)
        elif center == "IDATA":
            slots = idata_checker.check(target, headless=headless)
        else:
            log.warning(f"Bilinmeyen merkez: {center}")
            return
    except Exception as e:
        log.error(f"[{center}][{country}] Hata: {e}")
        return

    if not slots:
        log.info(f"  → Müsait randevu yok.")
        return

    slot_key = "|".join(sorted(slots))
    target_id = target["id"]
    if _last_notified.get(target_id) == slot_key:
        log.info(f"  → Zaten bildirildi, tekrar gönderilmiyor.")
        return

    _last_notified[target_id] = slot_key
    log.info(f"  → {len(slots)} slot bulundu! Bildirim gönderiliyor...")
    notify(config, target, slots)


def run_all_checks(config: dict):
    log.info("=" * 60)
    log.info(f"Kontrol başlıyor — {datetime.now().strftime('%H:%M:%S')}")
    log.info("=" * 60)

    targets = config.get("targets", [])
    random.shuffle(targets)  # Her seferinde farklı sırada kontrol et

    for i, target in enumerate(targets):
        check_target(config, target)
        # Hedefler arası insan gibi bekle (son hedeften sonra bekleme)
        if i < len(targets) - 1:
            delay = random.uniform(8, 20)
            log.info(f"  Sonraki kontrol için {delay:.0f}s bekleniyor...")
            time.sleep(delay)

    log.info("Kontrol tamamlandı.")


def test_notifications(config: dict):
    dummy_target = {
        "country": "TEST Ülkesi",
        "center": "VFS",
        "url": "https://example.com",
        "id": "test",
    }
    notify(config, dummy_target, ["2026-08-01 10:00", "2026-08-02 14:30"])
    log.info("Test bildirimi gönderildi.")


def main():
    parser = argparse.ArgumentParser(description="Vize Randevu Takip Sistemi")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--test-notify", action="store_true")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    config = config_loader.load()

    if args.test_notify:
        test_notifications(config)
        return

    if args.once:
        run_all_checks(config)
        return

    base_interval = config.get("check_interval_minutes", 7)
    log.info(f"Periyodik mod başladı. Baz aralık: {base_interval} dk (±%40 rastgele sapma)")
    log.info("Durdurmak için Ctrl+C")

    run_all_checks(config)

    while True:
        wait_seconds = jitter_interval(base_interval)
        next_check = datetime.fromtimestamp(time.time() + wait_seconds).strftime("%H:%M:%S")
        log.info(f"Sonraki kontrol: {next_check} ({wait_seconds/60:.1f} dk sonra)")
        time.sleep(wait_seconds)
        run_all_checks(config)


if __name__ == "__main__":
    main()
