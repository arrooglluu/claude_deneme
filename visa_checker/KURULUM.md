# Vize Randevu Takip Sistemi — Kurulum Rehberi

## 1. Python Gereksinimleri Kur

```
pip install -r requirements.txt
```

---

## 2. Telegram Bot Oluştur (5 dakika)

### Adım 1 — BotFather'dan token al
1. Telegram'da **@BotFather** hesabını aç
2. `/newbot` yaz
3. Bot adını gir (örn: `Vize Takip`)
4. Kullanıcı adını gir — `_bot` ile bitmeli (örn: `vizeTakipim_bot`)
5. BotFather sana şöyle bir şey verecek:
   ```
   Use this token to access the HTTP API:
   7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   Bu token'ı kopyala.

### Adım 2 — Chat ID öğren
1. Telegram'da **@userinfobot** hesabına git
2. Herhangi bir mesaj gönder
3. `Your id: 123456789` şeklinde ID'ni verecek

### Adım 3 — config.yaml'ı güncelle
```yaml
telegram:
  bot_token: "7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  chat_id: "123456789"
```

---

## 3. Gmail Ayarı (Uygulama Şifresi)

Gmail'in normal şifresi çalışmaz, "App Password" gerekli:

1. Google Hesabım → Güvenlik → **2 Adımlı Doğrulama**'yı aç (zaten açıksa atla)
2. Güvenlik sayfasında **Uygulama şifreleri** ara
3. Uygulama: `Diğer` → isim: `VizeTakip` → **Oluştur**
4. 16 haneli şifreyi kopyala (örn: `abcd efgh ijkl mnop`)

config.yaml'a yaz:
```yaml
email:
  sender: "seninadresin@gmail.com"
  password: "abcdefghijklmnop"   # boşluksuz
  recipients:
    - "seninadresin@gmail.com"
```

---

## 4. Chrome Driver

Selenium, Chrome tarayıcısını otomatik yönetir (webdriver-manager ile).
Bilgisayarında **Google Chrome** kurulu olması yeterli.

---

## 5. Çalıştır

### Test bildirimi (önce bunu yap — Telegram ve mail çalışıyor mu kontrol et)
```
python main.py --test-notify
```

### Tek seferlik kontrol
```
python main.py --once
```

### Sürekli çalıştır (her 5 dakikada bir)
```
python main.py
```

veya `baslat.bat` dosyasına çift tıkla.

---

## 6. Windows'ta Otomatik Başlatma (isteğe bağlı)

Bilgisayar açılışında otomatik çalışması için:

1. `Win + R` → `shell:startup` yaz → Enter
2. `baslat.bat` dosyasının kısayolunu bu klasöre koy

---

## Log Dosyası

Her kontrol `visa_checker.log` dosyasına yazılır.
Sorun çıkarsa bu dosyaya bak.
