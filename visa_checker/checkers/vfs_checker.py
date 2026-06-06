"""
VFS Global randevu kontrol modülü — anti-ban versiyonu.
"""

import logging
import time
import random

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from browser import build_driver, human_delay, human_scroll

log = logging.getLogger(__name__)

NO_SLOT_PHRASES = [
    "no appointment slots",
    "no slots available",
    "there are no open",
    "no open appointment",
    "currently no appointment",
    "randevu slotu bulunmamaktadır",
    "müsait randevu bulunmamaktadır",
]


def check(target: dict, headless: bool = True) -> list[str]:
    url = target["url"]
    city_filter = target.get("city_filter", "").lower()
    driver = None

    try:
        driver = build_driver(headless)

        # Önce ana sayfaya git (doğrudan randevu sayfasına gitme — bot gibi görünür)
        base_url = "https://visa.vfsglobal.com"
        driver.get(base_url)
        human_delay(2, 5)

        # Şimdi hedef sayfaya git
        driver.get(url)

        # Angular uygulamasının yüklenmesini bekle
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.TAG_NAME, "app-root"))
        )
        human_delay(3, 6)
        human_scroll(driver)
        human_delay(1, 3)

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()

        for phrase in NO_SLOT_PHRASES:
            if phrase in page_text:
                log.info(f"[VFS][{target['country']}] Müsait randevu yok.")
                return []

        if city_filter and city_filter not in page_text:
            log.info(f"[VFS][{target['country']}] {city_filter} için slot bulunamadı.")
            return []

        slots = _extract_slots(driver, city_filter)

        if slots:
            log.info(f"[VFS][{target['country']}] {len(slots)} slot bulundu!")
        else:
            log.warning(f"[VFS][{target['country']}] 'Slot yok' mesajı yok ama slot da çıkmadı — manuel kontrol et!")
            slots = [f"Randevu sayfasını kontrol et: {url}"]

        return slots

    except TimeoutException:
        log.error(f"[VFS][{target['country']}] Sayfa zaman aşımı: {url}")
        return []
    except Exception as e:
        log.error(f"[VFS][{target['country']}] Hata: {e}")
        return []
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def _extract_slots(driver, city_filter: str) -> list[str]:
    slots = []

    selectors = [
        "mat-option",
        "li.slot",
        "div.slot-time",
        "td.available",
        ".appointment-slot",
        "button.date-btn",
    ]

    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                text = el.text.strip()
                if not text:
                    continue
                if city_filter and city_filter not in text.lower():
                    continue
                slots.append(text)
        except NoSuchElementException:
            continue

    # Tarih içeren genel hücreleri de tara
    if not slots:
        try:
            cells = driver.find_elements(By.CSS_SELECTOR, "td, .date-cell")
            for el in cells:
                text = el.text.strip()
                if any(y in text for y in ["2025", "2026"]):
                    slots.append(text)
        except Exception:
            pass

    return list(dict.fromkeys(slots))[:20]  # Tekrarları kaldır, max 20
