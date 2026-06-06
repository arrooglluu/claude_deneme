"""
Anti-ban tarayıcı fabrikası.
undetected-chromedriver + selenium-stealth kombinasyonu kullanır.
"""

import logging
import random
import time

import undetected_chromedriver as uc
from selenium_stealth import stealth
from fake_useragent import UserAgent

log = logging.getLogger(__name__)

UA = UserAgent()

# Gerçek tarayıcı pencere boyutları
WINDOW_SIZES = [
    (1920, 1080), (1366, 768), (1536, 864),
    (1440, 900), (1280, 800), (1600, 900),
]


def build_driver(headless: bool = True) -> uc.Chrome:
    opts = uc.ChromeOptions()

    if headless:
        opts.add_argument("--headless=new")

    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")

    # Rastgele pencere boyutu
    w, h = random.choice(WINDOW_SIZES)
    opts.add_argument(f"--window-size={w},{h}")

    # Dil ve timezone — Türkiye gibi görün
    opts.add_argument("--lang=tr-TR")
    opts.add_argument("--timezone=Europe/Istanbul")

    try:
        driver = uc.Chrome(options=opts, version_main=None)
    except Exception as e:
        log.error(f"undetected-chromedriver başlatılamadı: {e}")
        raise

    # selenium-stealth ile ek iz silme
    stealth(
        driver,
        languages=["tr-TR", "tr", "en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    # navigator.webdriver = false yap
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def human_delay(min_s: float = 1.5, max_s: float = 4.5):
    """İnsan gibi rastgele bekleme."""
    time.sleep(random.uniform(min_s, max_s))


def human_scroll(driver):
    """Sayfayı insan gibi yavaş scroll et."""
    total_height = driver.execute_script("return document.body.scrollHeight")
    steps = random.randint(3, 7)
    for _ in range(steps):
        scroll_to = random.randint(100, max(200, total_height))
        driver.execute_script(f"window.scrollTo(0, {scroll_to});")
        time.sleep(random.uniform(0.3, 0.9))
    # Başa dön
    driver.execute_script("window.scrollTo(0, 0);")


def jitter_interval(base_minutes: int) -> float:
    """
    Tam periyodik istek yerine ±%40 rastgele sapma ekle.
    Örn: 5 dk → 3-7 dk arası rastgele
    """
    factor = random.uniform(0.6, 1.4)
    return base_minutes * factor * 60  # saniye cinsinden
