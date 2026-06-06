"""
VFS Global randevu kontrol modülü.
Önce resmi API endpoint'ini dener, başarısız olursa Selenium'a geçer.
"""

import logging
import random
import time

import requests
from fake_useragent import UserAgent
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from browser import build_driver, human_delay, human_scroll

log = logging.getLogger(__name__)
UA = UserAgent()

# VFS Global API — ülke kodlarına göre slot kontrolü
VFS_API_BASE = "https://lift-api.vfsglobal.com"

COUNTRY_CODES = {
    "Çekya":    ("tur", "cze"),
    "Hollanda": ("tur", "nld"),
    "Avusturya":("tur", "aut"),
}

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
    country = target["country"]

    if country in COUNTRY_CODES:
        slots = _check_via_api(target)
        if slots is not None:
            return slots

    log.info(f"[VFS][{country}] API başarısız, Selenium ile deneniyor...")
    return _check_with_selenium(target, headless)


def _check_via_api(target: dict) -> list[str] | None:
    """VFS API üzerinden slot kontrolü yapar."""
    country = target["country"]
    mission_code, country_code = COUNTRY_CODES[country]
    city = target.get("city_filter", "Istanbul")

    headers = {
        "User-Agent": UA.random,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Origin": "https://visa.vfsglobal.com",
        "Referer": f"https://visa.vfsglobal.com/{mission_code}/tr/{country_code}/book-an-appointment",
    }

    try:
        # Önce ana sayfayı ziyaret et (session cookie al)
        session = requests.Session()
        session.get(
            f"https://visa.vfsglobal.com/{mission_code}/tr/{country_code}/book-an-appointment",
            headers=headers, timeout=15
        )
        time.sleep(random.uniform(2, 4))

        # Slot availability endpoint
        url = (
            f"{VFS_API_BASE}/appointment/slot/checkslotavailable"
            f"?countryCode={country_code.upper()}"
            f"&missionCode={mission_code.upper()}"
            f"&centerCode={city}"
            f"&visaCategoryCode=-"
            f"&languageCode=tr"
        )
        resp = session.get(url, headers=headers, timeout=15)

        if resp.status_code == 401 or resp.status_code == 403:
            log.info(f"[VFS-API][{country}] Yetkilendirme gerekiyor, Selenium'a geçiliyor.")
            return None

        if resp.status_code != 200:
            return None

        data = resp.json()

        # API yanıtını parse et
        if isinstance(data, list) and len(data) > 0:
            slots = []
            for item in data:
                date = item.get("appointmentDate") or item.get("date") or str(item)
                if date:
                    slots.append(date)
            log.info(f"[VFS-API][{country}] {len(slots)} slot bulundu!")
            return slots

        if isinstance(data, dict):
            if data.get("isSlotAvailable") is False or data.get("slotAvailable") is False:
                log.info(f"[VFS-API][{country}] Müsait randevu yok.")
                return []
            if data.get("isSlotAvailable") is True or data.get("slotAvailable") is True:
                return [f"Randevu mevcut — sayfayı kontrol et: {target['url']}"]

        return None  # Beklenmedik format, Selenium'a geç

    except (requests.RequestException, ValueError):
        return None


def _check_with_selenium(target: dict, headless: bool) -> list[str]:
    url = target["url"]
    city_filter = target.get("city_filter", "").lower()
    driver = None

    try:
        driver = build_driver(headless)
        driver.get("https://visa.vfsglobal.com")
        human_delay(2, 4)
        driver.get(url)

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
            log.info(f"[VFS][{target['country']}] {city_filter} için slot yok.")
            return []

        slots = _extract_slots(driver, city_filter)

        if not slots:
            log.warning(f"[VFS][{target['country']}] 'Slot yok' mesajı yok — manuel kontrol et!")
            slots = [f"Randevu sayfasını kontrol et: {url}"]

        return slots

    except TimeoutException:
        log.error(f"[VFS][{target['country']}] Zaman aşımı: {url}")
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
    for selector in ["mat-option", "li.slot", "div.slot-time", "td.available", ".appointment-slot"]:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, selector):
                text = el.text.strip()
                if text and (not city_filter or city_filter in text.lower()):
                    slots.append(text)
        except Exception:
            continue

    if not slots:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, "td, .date-cell"):
                text = el.text.strip()
                if any(y in text for y in ["2025", "2026"]):
                    slots.append(text)
        except Exception:
            pass

    return list(dict.fromkeys(slots))[:20]
