"""
iDATA randevu kontrol modülü (İtalya için).
"""

import logging
import random
import time

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from fake_useragent import UserAgent

from browser import build_driver, human_delay, human_scroll

log = logging.getLogger(__name__)
UA = UserAgent()

# Sayfada bu metinlerden biri varsa randevu yok demektir
NO_SLOT_PHRASES = [
    "uygun randevu tarihi bulunmamaktadır",
    "aşağıdaki tarihe kadar randevular açılmıştır",
    "müsait randevu bulunmamaktadır",
    "randevu mevcut değil",
    "uygun randevu yok",
    "randevu bulunamadı",
    "no appointment",
    "no available",
]

# Sayfada bu metinler varsa gerçekten randevu VAR demektir
SLOT_AVAILABLE_PHRASES = [
    "randevu al",
    "tarih seç",
    "uygun tarihler",
    "müsait tarih",
    "book appointment",
]


def check(target: dict, headless: bool = True) -> list[str]:
    # Önce requests ile dene (hızlı)
    slots = _check_with_requests(target)
    if slots is not None:
        return slots
    log.info(f"[iDATA][{target['country']}] Selenium ile deneniyor...")
    return _check_with_selenium(target, headless)


def _check_with_requests(target: dict) -> list[str] | None:
    headers = {
        "User-Agent": UA.random,
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.idata.com.tr/",
    }
    try:
        session = requests.Session()
        session.get("https://www.idata.com.tr/", headers=headers, timeout=15)
        time.sleep(random.uniform(1.5, 3.0))

        resp = session.get(target["url"], headers=headers, timeout=15)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        page_text = soup.get_text(separator=" ").lower()

        for phrase in NO_SLOT_PHRASES:
            if phrase in page_text:
                log.info(f"[iDATA][{target['country']}] Müsait randevu yok (requests).")
                return []

        # Sayfa JS ile yükleniyorsa içerik boş gelir
        if "randevu" not in page_text and "appointment" not in page_text:
            return None

        # Gerçekten slot var mı kontrol et
        for phrase in SLOT_AVAILABLE_PHRASES:
            if phrase in page_text:
                return [f"Randevu mevcut olabilir — kontrol et: {target['url']}"]

        return []

    except requests.RequestException:
        return None


def _check_with_selenium(target: dict, headless: bool) -> list[str]:
    driver = None
    try:
        driver = build_driver(headless)
        driver.get("https://www.idata.com.tr/")
        human_delay(2, 3)
        driver.get(target["url"])

        # Sayfanın tamamen yüklenmesini bekle
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        # iDATA sayfası JS render için ekstra bekleme
        human_delay(5, 8)
        human_scroll(driver)
        human_delay(2, 3)

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()

        # Önce "randevu yok" kontrolü
        for phrase in NO_SLOT_PHRASES:
            if phrase in page_text:
                log.info(f"[iDATA][{target['country']}] Müsait randevu yok.")
                return []

        # Randevu var mı kontrol et
        for phrase in SLOT_AVAILABLE_PHRASES:
            if phrase in page_text:
                log.info(f"[iDATA][{target['country']}] Randevu mevcut!")
                return [f"Randevu mevcut — hemen kontrol et: {target['url']}"]

        # İkisi de yoksa sayfayı okuyamadık — sessiz kal, yanlış bildirim verme
        log.warning(f"[iDATA][{target['country']}] Sayfa içeriği okunamadı, bildirim gönderilmiyor.")
        return []

    except TimeoutException:
        log.error(f"[iDATA][{target['country']}] Zaman aşımı.")
        return []
    except Exception as e:
        log.error(f"[iDATA][{target['country']}] Hata: {e}")
        return []
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
