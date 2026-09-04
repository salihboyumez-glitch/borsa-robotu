# Fırsat modeli doğrulama raporu

Üretim zamanı (UTC): 2026-09-04T11:36:30.247344+00:00

## Ayrı test sonucu

- Model sinyali: %53.3 (sinyalsiz ortalama: %50.9, n=1479)
- %95 güven aralığı: %50.8–%55.9
- Üç günde stop öncesi 2R hedef başarısı: %3.8
- Yön katkısı: +2.4 puan — Yön tahmininde pratik bir katkı gösteremedi

## Piyasa rejimleri

| Rejim | 3G yükseliş | n | %95 güven aralığı |
|---|---:|---:|---:|
| Yükselen | %52.5 | 1184 | %49.7–%55.4 |
| Yatay | %55.8 | 154 | %48.0–%63.5 |
| Düşen | %57.4 | 141 | %49.2–%65.3 |

## Kalibrasyon kontrolü

| Modelin eğitimde söylediği aralık | Eğitim ortalaması | Testte gerçekleşen | n | %95 güven aralığı |
|---|---:|---:|---:|---:|
| %50-59 | %53.0 | %53.3 | 1469 | %50.7–%55.8 |
| %60-69 | %63.4 | %55.6 | 9 | %26.7–%81.1 |

## Yöntem

- Eğitim/kalibrasyon dönemi: 2020-01-01..2024-12-31
- Hiç dokunulmamış test dönemi: 2025-01-01..2026-09-04
- 3 işlem günü sonrası pozitif kapanış; işlem başarısı, 3 günde stopa değmeden önce 2R hedefe ulaşmadır. Aynı gün iki bariyer de görülürse kayıp, zaman aşımı başarısız sayılır. Test verisi eğitimden ayrıdır.
- n<30 olan gruplar Telegram çıktısında olasılık olarak gösterilmez.

## Hisse bazında ayrı test

| Hisse | Sinyal yükseliş | Sinyal n | Sinyalsiz | Fark | %95 güven aralığı |
|---|---:|---:|---:|---:|---:|
| A | yetersiz | 20 | %49.2 | -4.2 | %25.8–%65.8 |
| AAL | yetersiz | 17 | %46.9 | +29.6 | %52.7–%90.4 |
| AAOI | yetersiz | 15 | %51.6 | -18.3 | %15.2–%58.3 |
| AAPL | yetersiz | 8 | %55.4 | +7.1 | %30.6–%86.3 |
| ACHR | yetersiz | 13 | %44.7 | +1.5 | %23.2–%70.9 |
| ADM | yetersiz | 17 | %53.1 | +5.7 | %36.0–%78.4 |
| AEM | yetersiz | 13 | %57.1 | +19.8 | %49.7–%91.8 |
| AFRM | yetersiz | 15 | %50.4 | +2.9 | %30.1–%75.2 |
| ALAB | yetersiz | 8 | %52.7 | -27.7 | %7.1–%59.1 |
| ALB | yetersiz | 10 | %50.0 | +0.0 | %23.7–%76.3 |
| AMBQ | yetersiz | 2 | %53.4 | -3.4 | %9.5–%90.5 |
| AMD | yetersiz | 7 | %59.2 | -2.1 | %25.0–%84.2 |
| AMZN | yetersiz | 9 | %49.6 | -16.3 | %12.1–%64.6 |
| ANET | yetersiz | 14 | %55.5 | +1.6 | %32.6–%78.6 |
| APLD | yetersiz | 14 | %51.7 | +26.9 | %52.4–%92.4 |
| ARCB | yetersiz | 6 | %52.0 | +14.7 | %30.0–%90.3 |
| AREC | yetersiz | 0 | %48.3 | -48.3 | %0.0–%0.0 |
| ARQQ | yetersiz | 2 | %42.5 | +7.5 | %9.5–%90.5 |
| ASML | yetersiz | 13 | %54.6 | +22.3 | %49.7–%91.8 |
| ASTS | yetersiz | 18 | %47.5 | -3.1 | %24.6–%66.3 |
| AVAV | yetersiz | 9 | %47.4 | +8.2 | %26.7–%81.1 |
| BA | yetersiz | 12 | %51.5 | -18.2 | %13.8–%60.9 |
| BABA | yetersiz | 16 | %50.5 | -19.3 | %14.2–%55.6 |
| BEEM | yetersiz | 0 | %44.7 | -44.7 | %0.0–%0.0 |
| BG | yetersiz | 14 | %51.5 | +34.2 | %60.1–%96.0 |
| BTQ | yetersiz | 0 | %41.4 | -41.4 | %0.0–%0.0 |
| BWXT | yetersiz | 11 | %54.1 | +9.5 | %35.4–%84.8 |
| BXP | yetersiz | 4 | %50.2 | +24.8 | %30.1–%95.4 |
| CEG | yetersiz | 10 | %52.7 | +27.3 | %49.0–%94.3 |
| CF | yetersiz | 10 | %56.9 | -16.9 | %16.8–%68.7 |
| CRDO | yetersiz | 18 | %53.5 | +18.7 | %49.1–%87.5 |
| CRM | yetersiz | 9 | %50.4 | -17.1 | %12.1–%64.6 |
| CRML | yetersiz | 5 | %45.7 | +14.3 | %23.1–%88.2 |
| CRWD | yetersiz | 7 | %55.3 | -41.0 | %2.6–%51.3 |
| CRWV | yetersiz | 8 | %47.9 | -35.4 | %2.2–%47.1 |
| CTMX | yetersiz | 1 | %50.6 | -50.6 | %0.0–%79.3 |
| CTVA | yetersiz | 15 | %62.1 | -22.1 | %19.8–%64.3 |
| CW | yetersiz | 10 | %55.2 | +24.8 | %49.0–%94.3 |
| DAL | yetersiz | 7 | %50.6 | +35.1 | %48.7–%97.4 |
| DDOG | yetersiz | 8 | %52.7 | -2.7 | %21.5–%78.5 |
| DE | yetersiz | 13 | %50.9 | +10.6 | %35.5–%82.3 |
| DELL | yetersiz | 10 | %57.6 | -7.6 | %23.7–%76.3 |
| DLR | yetersiz | 11 | %51.6 | +2.9 | %28.0–%78.7 |
| EBAY | yetersiz | 15 | %56.4 | -3.1 | %30.1–%75.2 |
| ENPH | yetersiz | 2 | %47.1 | +2.9 | %9.5–%90.5 |
| ESTC | yetersiz | 13 | %53.1 | -22.3 | %12.7–%57.6 |
| FCX | yetersiz | 8 | %57.4 | +5.1 | %30.6–%86.3 |
| FDX | yetersiz | 12 | %55.9 | +19.1 | %46.8–%91.1 |
| FIGR | yetersiz | 1 | %45.3 | +54.7 | %20.7–%100.0 |
| FORM | yetersiz | 13 | %52.9 | -14.4 | %17.7–%64.5 |
| FSLR | yetersiz | 8 | %50.2 | +12.3 | %30.6–%86.3 |
| FTK | yetersiz | 3 | %49.6 | -16.3 | %6.1–%79.2 |
| FTNT | yetersiz | 6 | %53.9 | -20.6 | %9.7–%70.0 |
| GD | yetersiz | 13 | %53.1 | -6.9 | %23.2–%70.9 |
| GDEV | yetersiz | 0 | %42.1 | -42.1 | %0.0–%0.0 |
| GLW | yetersiz | 20 | %60.1 | +14.9 | %53.1–%88.8 |
| GOLD | yetersiz | 2 | %53.6 | +46.4 | %34.2–%100.0 |
| GOOG | yetersiz | 11 | %56.5 | +7.1 | %35.4–%84.8 |
| GRAB | yetersiz | 6 | %46.8 | -13.5 | %9.7–%70.0 |
| GTLB | yetersiz | 10 | %48.3 | +11.7 | %31.3–%83.2 |
| GXO | yetersiz | 12 | %50.5 | +7.8 | %32.0–%80.7 |
| HII | yetersiz | 13 | %50.9 | +18.3 | %42.4–%87.3 |
| HL | yetersiz | 11 | %57.5 | -12.0 | %21.3–%72.0 |
| HUT | yetersiz | 14 | %52.7 | -9.8 | %21.4–%67.4 |
| HWM | yetersiz | 13 | %57.3 | +19.6 | %49.7–%91.8 |
| IBM | yetersiz | 12 | %57.4 | +0.9 | %32.0–%80.7 |
| IDR | yetersiz | 12 | %55.7 | +2.6 | %32.0–%80.7 |
| INTC | yetersiz | 11 | %52.3 | +11.3 | %35.4–%84.8 |
| IONQ | yetersiz | 7 | %46.5 | +10.6 | %25.0–%84.2 |
| IONR | yetersiz | 0 | %45.7 | -45.7 | %0.0–%0.0 |
| IPX | yetersiz | 0 | %49.3 | -49.3 | %0.0–%0.0 |
| IREN | yetersiz | 17 | %54.9 | -7.8 | %26.2–%69.0 |
| ISRG | yetersiz | 4 | %43.7 | +31.3 | %30.1–%95.4 |
| JBHT | yetersiz | 16 | %51.5 | +4.7 | %33.2–%76.9 |
| JBLU | yetersiz | 16 | %46.8 | +28.2 | %50.5–%89.8 |
| JOBY | yetersiz | 12 | %44.6 | -19.6 | %8.9–%53.2 |
| KEEL | yetersiz | 3 | %48.7 | -15.4 | %6.1–%79.2 |
| KTOS | yetersiz | 9 | %52.3 | +3.3 | %26.7–%81.1 |
| KYIV | yetersiz | 4 | %47.6 | +2.4 | %15.0–%85.0 |
| LAC | yetersiz | 5 | %46.5 | -6.5 | %11.8–%76.9 |
| LAES | yetersiz | 1 | %40.7 | -40.7 | %0.0–%79.3 |
| LAR | yetersiz | 3 | %52.3 | -19.0 | %6.1–%79.2 |
| LDOS | yetersiz | 6 | %49.5 | +0.5 | %18.8–%81.2 |
| LHX | yetersiz | 8 | %56.1 | +6.4 | %30.6–%86.3 |
| LINE | yetersiz | 9 | %46.9 | +8.7 | %26.7–%81.1 |
| LITE | yetersiz | 18 | %58.3 | +19.5 | %54.8–%91.0 |
| LLY | yetersiz | 7 | %54.5 | +2.6 | %25.0–%84.2 |
| LMT | yetersiz | 9 | %55.8 | -11.4 | %18.9–%73.3 |
| LNN | yetersiz | 15 | %55.1 | -28.4 | %10.9–%52.0 |
| LUNR | yetersiz | 10 | %48.0 | +2.0 | %23.7–%76.3 |
| LUV | yetersiz | 5 | %50.4 | -10.4 | %11.8–%76.9 |
| LYFT | yetersiz | 11 | %48.6 | -12.2 | %15.2–%64.6 |
| LZM | yetersiz | 0 | %43.0 | -43.0 | %0.0–%0.0 |
| MARA | yetersiz | 4 | %46.8 | +3.2 | %15.0–%85.0 |
| MELI | yetersiz | 7 | %53.1 | -24.5 | %8.2–%64.1 |
| META | yetersiz | 8 | %49.0 | +26.0 | %40.9–%92.9 |
| METC | yetersiz | 7 | %51.3 | +20.1 | %35.9–%91.8 |
| MOS | yetersiz | 13 | %50.9 | -20.1 | %12.7–%57.6 |
| MP | %46.7 | 30 | %50.8 | -4.1 | %30.2–%63.9 |
| MRNA | yetersiz | 6 | %49.8 | +0.2 | %18.8–%81.2 |
| MSFT | yetersiz | 1 | %51.8 | -51.8 | %0.0–%79.3 |
| MSTR | yetersiz | 4 | %45.4 | +4.6 | %15.0–%85.0 |
| NAK | yetersiz | 0 | %50.5 | -50.5 | %0.0–%0.0 |
| NB | yetersiz | 3 | %50.6 | +16.1 | %20.8–%93.9 |
| NBIS | yetersiz | 16 | %52.1 | +10.4 | %38.6–%81.5 |
| NEE | yetersiz | 15 | %53.9 | +6.1 | %35.7–%80.2 |
| NET | yetersiz | 11 | %57.8 | -3.3 | %28.0–%78.7 |
| NMRK | yetersiz | 12 | %52.7 | +14.0 | %39.1–%86.2 |
| NOC | yetersiz | 9 | %54.3 | +12.4 | %35.4–%87.9 |
| NOW | yetersiz | 4 | %45.9 | -20.9 | %4.6–%69.9 |
| NTR | yetersiz | 16 | %54.2 | +14.6 | %44.4–%85.8 |
| NVDA | yetersiz | 9 | %55.5 | -11.1 | %18.9–%73.3 |
| NVO | yetersiz | 1 | %48.7 | -48.7 | %0.0–%79.3 |
| ODFL | yetersiz | 7 | %52.3 | +4.8 | %25.0–%84.2 |
| OKTA | yetersiz | 7 | %49.1 | -6.2 | %15.8–%75.0 |
| ON | yetersiz | 9 | %49.4 | +6.2 | %26.7–%81.1 |
| ORCL | yetersiz | 8 | %48.8 | +1.2 | %21.5–%78.5 |
| PANW | yetersiz | 4 | %59.0 | -34.0 | %4.6–%69.9 |
| PCG | yetersiz | 18 | %52.0 | -2.0 | %29.0–%71.0 |
| PFE | yetersiz | 11 | %50.9 | +3.6 | %28.0–%78.7 |
| PLTK | yetersiz | 0 | %45.7 | -45.7 | %0.0–%0.0 |
| PLTR | yetersiz | 10 | %57.4 | -17.4 | %16.8–%68.7 |
| QBTS | yetersiz | 15 | %45.6 | +7.7 | %30.1–%75.2 |
| QNTM | yetersiz | 0 | %41.6 | -41.6 | %0.0–%0.0 |
| QUBT | yetersiz | 11 | %43.2 | +2.3 | %21.3–%72.0 |
| RBLX | yetersiz | 7 | %53.1 | +4.0 | %25.0–%84.2 |
| RCAT | yetersiz | 22 | %45.9 | +4.1 | %30.7–%69.3 |
| RDHL | yetersiz | 0 | %39.2 | -39.2 | %0.0–%0.0 |
| RGTI | yetersiz | 8 | %46.6 | -21.6 | %7.1–%59.1 |
| RKLB | yetersiz | 21 | %48.4 | +8.7 | %36.5–%75.5 |
| RTX | yetersiz | 12 | %55.9 | +10.8 | %39.1–%86.2 |
| S | yetersiz | 15 | %51.6 | -24.9 | %10.9–%52.0 |
| SE | yetersiz | 14 | %53.2 | +3.9 | %32.6–%78.6 |
| SIDU | yetersiz | 2 | %42.0 | +8.0 | %9.5–%90.5 |
| SLI | yetersiz | 5 | %51.8 | -51.8 | %0.0–%43.4 |
| SMCI | yetersiz | 5 | %48.2 | -8.2 | %11.8–%76.9 |
| SNOW | yetersiz | 14 | %54.5 | +2.6 | %32.6–%78.6 |
| SOUN | yetersiz | 1 | %44.6 | -44.6 | %0.0–%79.3 |
| STEM | yetersiz | 0 | %43.3 | -43.3 | %0.0–%0.0 |
| STM | yetersiz | 11 | %53.6 | -17.2 | %15.2–%64.6 |
| STX | yetersiz | 16 | %59.8 | +15.2 | %50.5–%89.8 |
| TDG | yetersiz | 11 | %55.3 | -28.0 | %9.7–%56.6 |
| TEM | yetersiz | 13 | %45.2 | +31.7 | %49.7–%91.8 |
| TLRY | yetersiz | 5 | %38.0 | +2.0 | %11.8–%76.9 |
| TMC | yetersiz | 10 | %47.5 | -7.5 | %16.8–%68.7 |
| TSLA | yetersiz | 6 | %47.1 | +19.6 | %30.0–%90.3 |
| TWLO | yetersiz | 15 | %52.6 | +34.1 | %62.1–%96.3 |
| U | yetersiz | 15 | %52.1 | -18.8 | %15.2–%58.3 |
| UAL | yetersiz | 10 | %51.2 | +18.8 | %39.7–%89.2 |
| UBER | yetersiz | 13 | %50.1 | -11.6 | %17.7–%64.5 |
| UBSFY | yetersiz | 0 | %46.6 | -46.6 | %0.0–%0.0 |
| ULCC | yetersiz | 6 | %44.9 | +5.1 | %18.8–%81.2 |
| UMAC | yetersiz | 27 | %47.0 | +4.9 | %34.0–%69.3 |
| VEON | yetersiz | 5 | %51.3 | -31.3 | %3.6–%62.4 |
| VRT | yetersiz | 13 | %56.3 | +20.6 | %49.7–%91.8 |
| WDC | yetersiz | 13 | %64.0 | -17.8 | %23.2–%70.9 |
| WMT | yetersiz | 13 | %58.1 | +3.4 | %35.5–%82.3 |
| ZS | yetersiz | 10 | %53.7 | -33.7 | %5.7–%51.0 |
