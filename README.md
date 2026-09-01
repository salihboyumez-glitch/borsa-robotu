# Borsa Robotu

Streamlit tabanlı ABD hisseleri fırsat radarı. TradingView izleme listelerini birleştirir, tekrarları ayıklar ve teknik/risk puanlarıyla fırsat seviyeleri üretir.

## Yerel çalıştırma

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Çevrim içi yayın

Streamlit Community Cloud üzerinde giriş dosyası olarak `app.py` seçilir. Gizli değerler uygulamanın **Advanced settings → Secrets** alanına eklenmelidir:

```toml
FINNHUB_API_KEY = "..."
TELEGRAM_BOT_TOKEN = "..."
TELEGRAM_CHAT_ID = "..."
```

`.env` ve `secrets.toml` Git deposuna eklenmez.
