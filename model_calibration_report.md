# Fırsat modeli doğrulama raporu

Üretim zamanı (UTC): 2026-09-04T11:18:13.299827+00:00

## Ayrı test sonucu

- Model sinyali: %51.1 (sinyalsiz ortalama: %51.7, n=2080)
- %95 güven aralığı: %48.9–%53.2
- Üç günde stop öncesi 2R hedef başarısı: %3.9

## Piyasa rejimleri

| Rejim | 3G yükseliş | n | %95 güven aralığı |
|---|---:|---:|---:|
| Yükselen | %48.8 | 1640 | %46.4–%51.2 |
| Yatay | %58.9 | 280 | %53.1–%64.5 |
| Düşen | %60.6 | 160 | %52.9–%67.9 |

## Kalibrasyon kontrolü

| Modelin eğitimde söylediği aralık | Eğitim ortalaması | Testte gerçekleşen | n | %95 güven aralığı |
|---|---:|---:|---:|---:|
| %50-59 | %53.2 | %51.1 | 2080 | %48.9–%53.2 |

## Yöntem

- Eğitim/kalibrasyon dönemi: 2020-01-01..2024-12-31
- Hiç dokunulmamış test dönemi: 2025-01-01..2026-09-04
- 3 işlem günü sonrası pozitif kapanış; işlem başarısı, 3 günde stopa değmeden önce 2R hedefe ulaşmadır. Aynı gün iki bariyer de görülürse kayıp, zaman aşımı başarısız sayılır. Test verisi eğitimden ayrıdır.
- n<30 olan gruplar Telegram çıktısında olasılık olarak gösterilmez.
