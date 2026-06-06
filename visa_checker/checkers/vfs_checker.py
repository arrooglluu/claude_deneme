"""
VFS Global randevu kontrol modülü.

VFS sistemi JavaScript ile render edilen bir SPA olduğu için Selenium kullanır.
Randevu sayfasında "No appointment slots" mesajı yoksa slot var demektir.
"""

import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

log = logging.getLogger(__name__)

# VFS sayfasında "boş randevu yok" olduğunda görünen metin parçaları
NO_SLOT_PHRASES = [
    "no appointment slots",
    "no slots available",
    "there are no open",
    "randevu slotu bulunmamaktadır",
    "müsait randevu",
]

# Randevu butonunun CSS seçicisi (VFS Global sayfası için)
BOOK_BUTTON_SELECTOR = "button.mat-flat-button"
SLOT_CONTAINER_SELECTOR = "div.container"


def _build_driver(headless: bool) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=opts)


def check(target: dict, headless: bool = True) -> list[str]:
    """
    VFS randevu sayfasını kontrol eder.
    Boş slot varsa slot bilgilerini (tarih/saat) döndürür, yoksa boş liste döner.
    """
    url = target["url"]
    city_filter = target.get("city_filter", "").lower()
    driver = None

    try:
        driver = _build_driver(headless)
        driver.get(url)

        # Sayfanın yüklenmesini bekle
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "app-root"))
        )
        time.sleep(3)  # Angular render için ekstra bekleme

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()

        # "Randevu yok" mesajı var mı kontrol et
        for phrase in NO_SLOT_PHRASES:
            if phrase in page_text:
                log.info(f"[VFS][{target['country']}] Müsait randevu yok.")
                return []

        # Şehir filtresi
        if city_filter and city_filter not in page_text:
            log.info(f"[VFS][{target['country']}] {city_filter} için slot bulunamadı.")
            return []

        # Slot bul — tarih içeren elementleri topla
        slots = _extract_slots(driver, city_filter)

        if slots:
            log.info(f"[VFS][{target['country']}] {len(slots)} slot bulundu!")
        else:
            # Sayfa "no slot" demiyor ama slot da bulamadık → büyük ihtimalle var
            log.warning(
                f"[VFS][{target['country']}] Sayfada 'slot yok' mesajı yok, "
                "manuel kontrol gerekebilir."
            )
            slots = ["Sayfa manuel kontrol gerektirebilir — link'i ziyaret et."]

        return slots

    except TimeoutException:
        log.error(f"[VFS][{target['country']}] Sayfa zaman aşımına uğradı: {url}")
        return []
    except Exception as e:
        log.error(f"[VFS][{target['country']}] Beklenmedik hata: {e}")
        return []
    finally:
        if driver:
            driver.quit()


def _extract_slots(driver: webdriver.Chrome, city_filter: str) -> list[str]:
    """Sayfadan tarih/saat içeren slot bilgilerini toplar."""
    slots = []
    try:
        # VFS genellikle mat-option veya li elementleri kullanır
        candidates = driver.find_elements(By.CSS_SELECTOR, "mat-option, li.slot, div.slot-time")
        for el in candidates:
            text = el.text.strip()
            if not text:
                continue
            if city_filter and city_filter not in text.lower():
                continue
            slots.append(text)
    except NoSuchElementException:
        pass

    # Alternatif: tablo hücrelerinde tarih ara
    if not slots:
        try:
            cells = driver.find_elements(By.CSS_SELECTOR, "td, .date-cell, .time-slot")
            for el in cells:
                text = el.text.strip()
                # Tarih formatına uyan hücreleri al (2024, 2025 içeren)
                if any(y in text for y in ["2024", "2025", "2026"]):
                    slots.append(text)
        except NoSuchElementException:
            pass

    return slots[:20]  # En fazla 20 slot döndür
