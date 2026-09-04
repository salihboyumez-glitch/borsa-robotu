"""Borsa robotunun merkezi ve güvenli ayarları."""

import os


# Bu kimlik değişirse eski kalibrasyon sonuçları Telegram'da kullanılmaz.
STRATEGY_VERSION = "rsi45-68-volume1.4-sma50-entry0.4-stop1.6-target2-3.5-v1"

# Sinyal koşulları
RSI_MIN = 45.0
RSI_MAX = 68.0
MIN_HACIM_ORANI = 1.4
SMA_UZUNLUK = 50

# Seviye hesabı
ATR_UZUNLUK = 14
GIRIS_BANDI_ATR = 0.4
STOP_ATR = 1.6
HEDEF1_R = 2.0
HEDEF2_R = 3.5
MIN_RISK_KAZANC = 1.5

# Geçmiş test
GECMIS_GUN = 1500
VADE_GUN = 3
MIN_ORNEK = 30

# Yalnız önemli düşüşleri anlık bildir. Yükseliş bildirimi kapalıdır.
HAREKET_ESIKLERI = (3.0, 5.0, 8.0, 12.0)
HAREKET_SADECE_YUKSELIS = False
HAREKET_SADECE_DUSUS = False
HAREKET_GUN_ICI_YAKALA = True
HAREKET_ISTEK_ARALIGI = 1.05
SADECE_DUSUS = True
ONEMLI_DUSUS_ESIGI = -5.0
HACIMLI_DUSUS_ESIGI = -3.0
ANORMAL_HACIM_ORANI = 2.0

# Haber
ONEMLI_KELIMELER = (
    "earnings", "revenue", "guidance", "forecast", "profit warning",
    "upgrade", "downgrade", "acquisition", "merger", "takeover",
    "lawsuit", "settlement", "sec investigation", "investigation",
    "bankruptcy", "chapter 11", "layoff", "recall", "fda",
    "clinical trial", "resign", "buyback", "dividend", "split",
    "offering", "share sale", "halted", "delisting", "cyberattack",
    "data breach", "contract award",
)
HABER_GERI_GUN = 2

# Gizli anahtarlar yalnız ortam değişkenlerinden okunur.
def finnhub_key():
    return os.getenv("FINNHUB_API_KEY", os.getenv("FINNHUB_KEY", ""))


def telegram_token():
    return os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_TOKEN", ""))


def telegram_chat_id():
    return os.getenv("TELEGRAM_CHAT_ID", "")
