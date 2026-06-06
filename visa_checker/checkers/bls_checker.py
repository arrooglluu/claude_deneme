"""
BLS International randevu kontrol modülü (İspanya için).
Formu doldurup (Istanbul, Individual, Tourist Visa, Normal) submit eder ve sonucu okur.
"""

import logging
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from browser import build_driver, human_delay, human_scroll

log = logging.getLogger(__name__)

NO_SLOT_PHRASES = [
    "currently, no slots are available",
    "no slots are available",
    "no appointment",
    "kindly try again",
    "try again after sometime",
]

SLOT_AVAILABLE_PHRASES = [
    "select a date",
    "choose a date",
    "available slots",
    "book appointment",
    "select slot",
]


def check(target: dict, headless: bool = True) -> list[str]:
    return _check_with_selenium(target, headless)


def _check_with_selenium(target: dict, headless: bool) -> list[str]:
    driver = None
    try:
        driver = build_driver(headless)
        driver.get(target["url"])

        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        human_delay(3, 5)

        # Jurisdiction → Istanbul
        _select_by_text(driver, "Jurisdiction", "Istanbul")
        human_delay(1, 2)

        # Appointment For → Individual
        try:
            radios = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for r in radios:
                val = r.get_attribute("value") or ""
                if "individual" in val.lower():
                    driver.execute_script("arguments[0].click();", r)
                    break
        except Exception:
            pass
        human_delay(1, 2)

        # Location → Istanbul
        _select_by_text(driver, "Location", "Istanbul")
        human_delay(1, 2)

        # Visa Type → Schengen
        _select_by_text(driver, "Visa Type", "Schengen")
        human_delay(1, 2)

        # Visa Sub Type → Tourist
        _select_by_text(driver, "Visa Sub Type", "Tourist")
        human_delay(1, 2)

        # Category → Normal
        _select_by_text(driver, "Category", "Normal")
        human_delay(1, 2)

        # Submit
        try:
            btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], button.submit")
            driver.execute_script("arguments[0].click();", btn)
        except NoSuchElementException:
            try:
                btn = driver.find_element(By.XPATH, "//button[contains(text(),'Submit') or contains(text(),'submit')]")
                driver.execute_script("arguments[0].click();", btn)
            except Exception:
                pass

        human_delay(4, 6)
        human_scroll(driver)

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()

        for phrase in NO_SLOT_PHRASES:
            if phrase in page_text:
                log.info(f"[BLS][{target['country']}] Müsait randevu yok.")
                return []

        for phrase in SLOT_AVAILABLE_PHRASES:
            if phrase in page_text:
                log.info(f"[BLS][{target['country']}] Randevu mevcut!")
                return [f"Randevu mevcut — hemen kontrol et: {target['url']}"]

        log.warning(f"[BLS][{target['country']}] Sayfa içeriği okunamadı, bildirim gönderilmiyor.")
        return []

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


def _select_by_text(driver, label: str, keyword: str):
    """Label'a göre yakındaki select'i bulur ve keyword içeren seçeneği seçer."""
    keyword_lower = keyword.lower()
    try:
        selects = driver.find_elements(By.TAG_NAME, "select")
        for sel in selects:
            try:
                select_obj = Select(sel)
                for opt in select_obj.options:
                    if keyword_lower in opt.text.lower():
                        select_obj.select_by_visible_text(opt.text)
                        time.sleep(0.5)
                        return
            except Exception:
                continue
    except Exception as e:
        log.warning(f"[BLS] '{label}' seçimi başarısız: {e}")
