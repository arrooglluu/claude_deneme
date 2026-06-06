FROM python:3.12-slim-bookworm

# Chrome bağımlılıkları
RUN apt-get update && apt-get install -y \
    wget curl gnupg unzip \
    fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 libnspr4 \
    libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
    xdg-utils libgbm1 libxkbcommon0 libgtk-3-0 libvulkan1 \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Google Chrome kur
RUN wget -q -O /tmp/chrome.deb \
    https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y /tmp/chrome.deb && \
    rm /tmp/chrome.deb

WORKDIR /app
COPY visa_checker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY visa_checker/ .

CMD ["python", "main.py"]
