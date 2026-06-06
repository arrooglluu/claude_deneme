"""
BLS International randevu kontrol modülü (İspanya için kullanılır).

BLS sayfası kısmen server-side render olduğundan önce requests ile dener,
başarısız olursa Selenium'a geçer.
"""

import logging
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

NO_SLOT_PHRASES = [
    "no appointment",
    "not available",
    "müsait randevu yok",
    "no slots",
    "there are no available",
    "appointment not available",
]


def check(target: dict, headless: bool = True) -> list[str]:
    """
    BLS randevu sayfasını kontrol eder.
    Boş slot varsa slot bilgilerini döndürür, yoksa boş liste döner.
    """
    # Önce hızlı requests dene
    slots = _check_with_requests(target)
    if slots is not None:
        return slots

    # Requests başarısız olduysa Selenium ile dene
    log.info(f"[BLS][{target['country']}] Selenium ile tekrar deneniyor...")
    return _check_with_selenium(target, headless)


def _check_with_requests(target: dict) -> list[str] | None:
    """None döner = requests ile kontrol yapılamadı (Selenium gerekli)."""
    try:
        resp = requests.get(target["url"], headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        page_text = soup.get_text(separator=" ").lower()

        for phrase in NO_SLOT_PHRASES:
            if phrase in page_text:
                log.info(f"[BLS][{target['country']}] Müsait randevu yok (requests).")
                return []

        # Randevu tarihlerini çek
        slots = _parse_slots_from_soup(soup, target.get("city_filter", "").lower())

        if not slots and "appointment" not in page_text:
            # Sayfa düzgün yüklenmemiş, Selenium gerekli
            return None

        return slots

    except requests.RequestException:
        return None


def _check_with_selenium(target: dict, headless: bool) -> list[str]:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(f"user-agent={HEADERS['User-Agent']}")

    driver = None
    try:
        driver = webdriver.Chrome(options=opts)
        driver.get(target["url"])
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()

        for phrase in NO_SLOT_PHRASES:
            if phrase in page_text:
                log.info(f"[BLS][{target['country']}] Müsait randevu yok (Selenium).")
                return []

        city_filter = target.get("city_filter", "").lower()
        slots = []
        try:
            elements = driver.find_elements(
                By.CSS_SELECTOR,
                "select option, .appointment-date, td.available, .slot"
            )
            for el in elements:
                text = el.text.strip()
                if not text or text.lower() in ("select", "seç", "--"):
                    continue
                if city_filter and city_filter not in text.lower():
                    continue
                slots.append(text)
        except Exception:
            pass

        if not slots:
            slots = ["Sayfa manuel kontrol gerektirebilir — link'i ziyaret et."]

        return slots

    except TimeoutException:
        log.error(f"[BLS][{target['country']}] Sayfa zaman aşımına uğradı.")
        return []
    except Exception as e:
        log.error(f"[BLS][{target['country']}] Hata: {e}")
        return []
    finally:
        if driver:
            driver.quit()


def _parse_slots_from_soup(soup: BeautifulSoup, city_filter: str) -> list[str]:
    slots = []
    for el in soup.select("select option, .date, td.open, .slot-available"):
        text = el.get_text(strip=True)
        if not text or text.lower() in ("select", "seç", "--"):
            continue
        if city_filter and city_filter not in text.lower():
            continue
        slots.append(text)
    return slots[:20]
