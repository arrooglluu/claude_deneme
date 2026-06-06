"""
BLS International randevu kontrol modülü — anti-ban versiyonu.
"""

import logging
import random

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

NO_SLOT_PHRASES = [
    "no appointment",
    "not available",
    "appointment not available",
    "no slots",
    "there are no available",
    "müsait randevu yok",
]


def check(target: dict, headless: bool = True) -> list[str]:
    slots = _check_with_requests(target)
    if slots is not None:
        return slots
    log.info(f"[BLS][{target['country']}] Selenium ile deneniyor...")
    return _check_with_selenium(target, headless)


def _check_with_requests(target: dict) -> list[str] | None:
    headers = {
        "User-Agent": UA.random,
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://tr.blsinternational.com/",
    }
    try:
        session = requests.Session()
        # Önce ana sayfayı ziyaret et
        session.get("https://tr.blsinternational.com/", headers=headers, timeout=15)
        import time; time.sleep(random.uniform(1.5, 3.5))

        resp = session.get(target["url"], headers=headers, timeout=15)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        page_text = soup.get_text(separator=" ").lower()

        for phrase in NO_SLOT_PHRASES:
            if phrase in page_text:
                log.info(f"[BLS][{target['country']}] Müsait randevu yok.")
                return []

        slots = _parse_soup(soup, target.get("city_filter", "").lower())
        if not slots and "appointment" not in page_text:
            return None  # JS gerekli, Selenium'a geç

        return slots

    except requests.RequestException:
        return None


def _check_with_selenium(target: dict, headless: bool) -> list[str]:
    driver = None
    try:
        driver = build_driver(headless)
        driver.get("https://tr.blsinternational.com/")
        human_delay(2, 4)
        driver.get(target["url"])

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        human_delay(2, 4)
        human_scroll(driver)

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()

        for phrase in NO_SLOT_PHRASES:
            if phrase in page_text:
                log.info(f"[BLS][{target['country']}] Müsait randevu yok.")
                return []

        city_filter = target.get("city_filter", "").lower()
        slots = []
        try:
            elements = driver.find_elements(
                By.CSS_SELECTOR,
                "select option, .appointment-date, td.available, .slot, button.date"
            )
            for el in elements:
                text = el.text.strip()
                if not text or text.lower() in ("select", "seç", "--", "lütfen seçin"):
                    continue
                if city_filter and city_filter not in text.lower():
                    continue
                slots.append(text)
        except Exception:
            pass

        if not slots:
            slots = [f"Randevu sayfasını kontrol et: {target['url']}"]

        return slots

    except TimeoutException:
        log.error(f"[BLS][{target['country']}] Zaman aşımı.")
        return []
    except Exception as e:
        log.error(f"[BLS][{target['country']}] Hata: {e}")
        return []
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def _parse_soup(soup: BeautifulSoup, city_filter: str) -> list[str]:
    slots = []
    for el in soup.select("select option, .date, td.open, .slot-available"):
        text = el.get_text(strip=True)
        if not text or text.lower() in ("select", "seç", "--"):
            continue
        if city_filter and city_filter not in text.lower():
            continue
        slots.append(text)
    return slots[:20]
