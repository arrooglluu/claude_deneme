"""
VFS Global randevu kontrol modülü.
Selenium ile formu doldurup (merkez + kategori + alt kategori) slot kontrolü yapar.
"""

import logging
import random
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from browser import build_driver, human_delay, human_scroll

log = logging.getLogger(__name__)

NO_SLOT_PHRASES = [
    "uygun randevu bulunamamaktadır",
    "şu an için uygun randevu",
    "no appointment slots",
    "no slots available",
    "there are no open",
    "no open appointment",
    "currently no appointment",
    "randevu slotu bulunmamaktadır",
    "müsait randevu bulunmamaktadır",
]

# Her ülke için merkez adı, kategori ve alt kategori anahtar kelimeleri
VFS_FORM_CONFIG = {
    "Çekya": {
        "center_keyword": "Istanbul",
        "category_keyword": "KISA DONEM",
        "subcategory_keyword": "TURIZM",
    },
    "Hollanda": {
        "center_keyword": "Istanbul",
        "category_keyword": "SHORT STAY",
        "subcategory_keyword": "TOURISM",
    },
    "Avusturya": {
        "center_keyword": "Istanbul",
        "category_keyword": "SHORT STAY",
        "subcategory_keyword": "TOURISM",
    },
}


def check(target: dict, headless: bool = True) -> list[str]:
    return _check_with_selenium(target, headless)


def _check_with_selenium(target: dict, headless: bool) -> list[str]:
    url = target["url"]
    country = target["country"]
    form_cfg = VFS_FORM_CONFIG.get(country, {})
    driver = None

    try:
        driver = build_driver(headless)
        driver.get("https://visa.vfsglobal.com")
        human_delay(2, 4)
        driver.get(url)

        # Angular uygulamasının yüklenmesini bekle
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "app-root"))
        )
        human_delay(3, 5)
        human_scroll(driver)

        # Merkez seç
        if form_cfg.get("center_keyword"):
            _select_dropdown(driver, "center_keyword", form_cfg["center_keyword"], country)
            human_delay(1, 3)

        # Kategori seç
        if form_cfg.get("category_keyword"):
            _select_dropdown(driver, "category_keyword", form_cfg["category_keyword"], country)
            human_delay(1, 3)

        # Alt kategori seç
        if form_cfg.get("subcategory_keyword"):
            _select_dropdown(driver, "subcategory_keyword", form_cfg["subcategory_keyword"], country)
            human_delay(2, 4)

        # Sonucu oku
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()

        for phrase in NO_SLOT_PHRASES:
            if phrase.lower() in page_text:
                log.info(f"[VFS][{country}] Müsait randevu yok.")
                return []

        slots = _extract_slots(driver)

        if slots:
            log.info(f"[VFS][{country}] {len(slots)} slot bulundu!")
        else:
            log.warning(f"[VFS][{country}] 'Slot yok' mesajı yok — manuel kontrol et!")
            slots = [f"Randevu sayfasını kontrol et: {url}"]

        return slots

    except TimeoutException:
        log.error(f"[VFS][{country}] Zaman aşımı: {url}")
        return []
    except Exception as e:
        log.error(f"[VFS][{country}] Hata: {e}")
        return []
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def _select_dropdown(driver, field: str, keyword: str, country: str):
    """Mat-select veya native select içinden keyword'e uyan seçeneği seçer."""
    keyword_lower = keyword.lower()

    # Önce mat-select dene (Angular Material)
    try:
        selects = driver.find_elements(By.CSS_SELECTOR, "mat-select")
        for sel in selects:
            if not sel.is_displayed():
                continue
            sel.click()
            human_delay(0.5, 1.5)

            options = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option"))
            )
            matched = False
            for opt in options:
                if keyword_lower in opt.text.lower():
                    opt.click()
                    matched = True
                    break

            if matched:
                return

            # Eşleşme yoksa kapat
            try:
                driver.find_element(By.CSS_SELECTOR, ".cdk-overlay-backdrop").click()
            except Exception:
                pass

    except Exception:
        pass

    # Native select dene
    try:
        selects = driver.find_elements(By.TAG_NAME, "select")
        for sel in selects:
            if not sel.is_displayed():
                continue
            select_obj = Select(sel)
            for opt in select_obj.options:
                if keyword_lower in opt.text.lower():
                    select_obj.select_by_visible_text(opt.text)
                    return
    except Exception:
        pass

    log.warning(f"[VFS][{country}] '{keyword}' seçeneği bulunamadı ({field})")


def _extract_slots(driver) -> list[str]:
    slots = []
    for selector in ["mat-option", ".slot", "td.available", ".appointment-slot", "button.date-btn"]:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, selector):
                text = el.text.strip()
                if text and any(y in text for y in ["2025", "2026", ":"]):
                    slots.append(text)
        except Exception:
            continue

    return list(dict.fromkeys(slots))[:20]
