"""
VFS Global randevu kontrol modülü — Playwright versiyonu.
Playwright, Selenium'a göre çok daha iyi Cloudflare geçer.
"""

import logging
import random
import time

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

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

VFS_FORM_CONFIG = {
    "Çekya":     {"center": "Istanbul", "category": "KISA DONEM", "subcategory": "TURIZM"},
    "Hollanda":  {"center": "Istanbul", "category": "SHORT STAY",  "subcategory": "TOURISM"},
    "Avusturya": {"center": "Istanbul", "category": "SHORT STAY",  "subcategory": "TOURISM"},
}


def check(target: dict, headless: bool = True) -> list[str]:
    country = target["country"]
    url = target["url"]
    form_cfg = VFS_FORM_CONFIG.get(country, {})

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="tr-TR",
                timezone_id="Europe/Istanbul",
                viewport={"width": random.choice([1920, 1366, 1536]), "height": random.choice([1080, 768, 864])},
            )

            # Bot tespitini engelle
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
                window.chrome = { runtime: {} };
            """)

            page = context.new_page()

            # Önce ana sayfaya git
            page.goto("https://visa.vfsglobal.com", wait_until="domcontentloaded", timeout=30000)
            time.sleep(random.uniform(2, 4))

            # Randevu sayfasına git
            page.goto(url, wait_until="networkidle", timeout=45000)
            time.sleep(random.uniform(5, 8))

            # Angular app-root yüklensin bekle
            try:
                page.wait_for_selector("app-root", timeout=15000)
            except Exception:
                pass
            time.sleep(random.uniform(2, 4))

            # Formu doldur
            if form_cfg:
                _fill_form(page, form_cfg, country)
                time.sleep(random.uniform(2, 4))

            page_text = page.inner_text("body").lower()

            browser.close()

        for phrase in NO_SLOT_PHRASES:
            if phrase in page_text:
                log.info(f"[VFS][{country}] Müsait randevu yok.")
                return []

        # Pozitif randevu işareti ara
        if any(kw in page_text for kw in ["select date", "tarih seç", "available", "book"]):
            log.info(f"[VFS][{country}] Randevu mevcut!")
            return [f"Randevu mevcut — hemen kontrol et: {url}"]

        log.warning(f"[VFS][{country}] Sayfa içeriği okunamadı, bildirim gönderilmiyor.")
        return []

    except PlaywrightTimeout:
        log.error(f"[VFS][{country}] Zaman aşımı: {url}")
        return []
    except Exception as e:
        log.error(f"[VFS][{country}] Hata: {e}")
        return []


def _fill_form(page, form_cfg: dict, country: str):
    """VFS formundaki dropdown'ları doldurur."""

    # mat-select dropdown'larını doldur
    selects = page.query_selector_all("mat-select")

    for sel in selects:
        try:
            sel.click()
            time.sleep(0.8)
            options = page.query_selector_all("mat-option")
            for opt in options:
                text = opt.inner_text().lower()
                if (form_cfg["center"].lower() in text or
                        form_cfg["category"].lower() in text or
                        form_cfg["subcategory"].lower() in text):
                    opt.click()
                    time.sleep(0.5)
                    break
            else:
                # Eşleşme yoksa kapat
                page.keyboard.press("Escape")
                time.sleep(0.3)
        except Exception:
            continue
