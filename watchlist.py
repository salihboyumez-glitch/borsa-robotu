# ABD BORSA ROBOTU — ANA TAKIP HAVUZU
# Ana robot havuzu + paylaşılan TradingView takip listeleri

from tradingview_sync import load_cached_symbols

WATCHLIST = [

    # BUYUK TEKNOLOJI
    "NVDA", "GOOG", "AAPL", "MSFT", "TSLA",
    "AMZN", "META", "ORCL", "WMT",

    # CIP / DONANIM / AI ALTYAPI
    "ON", "STM", "IBM", "INTC", "ASML",
    "WDC", "STX", "AAOI", "DELL", "APLD",
    "CRDO", "LITE", "ANET", "ALAB", "AMD",
    "SMCI", "VRT", "GLW", "CRWV",

    # YAZILIM / BULUT
    "GTLB", "NET", "NOW", "ESTC", "TWLO",
    "OKTA", "CRM", "DDOG", "SNOW", "ZS",

    # SIBER GUVENLIK
    "NTSK", "CRWD", "PANW", "FTNT", "S",

    # ENERJI / AI VERI MERKEZI
    "FTK", "STEM", "NEE", "ENPH", "FSLR",
    "PCG", "CEG",

    # REIT / VERI MERKEZI
    "NMRK", "DLR", "BXP",

    # HAVAYOLU / UAM
    "AAL", "DAL", "JBLU", "LUV", "UAL",
    "ULCC", "JOBY", "ACHR",

    # MADEN / METAL / HOLDING
    "HL", "AEM", "GOLD", "NBIS", "AFRM", "BEEM",

    # BIYOTEK / ILAC
    "MRNA", "NVO", "LLY", "TLRY", "CTMX",
    "PFE", "RDHL", "TEM", "A",

    # KUCUK TEKNOLOJI / YAZILIM
    "UBER", "AMBQ", "FIGR", "GRAB", "SOUN",
    "BTQ", "LYFT", "KYIV", "VEON", "ISRG", "MELI",

    # LOJISTIK
    "LINE", "FDX", "GXO", "FDXF", "ODFL",
    "ARCB", "JBHT",

    # NADIR TOPRAK / MADENCILIK
    "MP", "ALB", "AREC", "CRML", "FCX",
    "HUT", "IDR", "IONR", "IPX", "KEEL",
    "LAC", "LAR", "LZM", "MARA", "METC",
    "NAK", "NB", "SLI", "TMC",

    # OYUN / EGLENCE
    "U", "GDEV", "RBLX", "PLTK", "SE", "UBSFY",

    # KUANTUM
    "IONQ", "QBTS", "RGTI", "QUBT", "QNTM",
    "ARQQ", "LAES", "FORM",

    # SAVUNMA / UZAY
    "KTOS", "HWM", "ISSC", "RTX", "LDOS",
    "HII", "LHX", "AVAV", "BA", "LMT",
    "GD", "NOC", "TDG", "RKLB", "CW",
    "BWXT", "ASTS", "SIDU", "PLTR", "RCAT",
    "LUNR", "UMAC",

    # TARIM / GIDA
    "NTR", "CF", "MOS", "CTVA", "ADM",
    "BG", "LNN", "DE",

    # E-TICARET / FINTECH
    "BABA", "EBAY", "MSTR",

    # EKSTRA TAKIP
    "PWRL", "IREN"
]

# Ana robot listesi, TradingView senkronundan bağımsız olarak korunur.
BASE_WATCHLIST = list(dict.fromkeys(WATCHLIST))

# Her taramada ayrıca mutlaka takip edilecek hisseler
PRIORITY_SYMBOLS = [
    "NTSK", "NVDA", "CRWD", "ALAB"
]

# Kaynaklar:
# - https://tr.tradingview.com/watchlists/36892357/ (TAKİP AMERİKAN HİSSELERİ)
# - https://tr.tradingview.com/watchlists/38678961/ (ALDIGIM 2 ÇİP DONANIM)
# - https://tr.tradingview.com/watchlists/40819901/ (AMERİKA BÜYÜK ŞİRKETLERİ TEKNOLOJİ ŞİRKETLERİ)
# - https://tr.tradingview.com/watchlists/40916025/ (AMERİKA ÇİP VE DONANIM FİRMAR)
# - https://tr.tradingview.com/watchlists/71973820/ (AMERİKA ENERJİ HİSSELERİ)
# - https://tr.tradingview.com/watchlists/40915820/ (AMERİKA GAYRIMENKUL HISSELRI)
# - https://tr.tradingview.com/watchlists/40852901/ (AMERİKA HAVA YOLLARI HİSSE)
# - https://tr.tradingview.com/watchlists/40874120/ (AMERİKA HOLDİNG HİSSSE)
# - https://tr.tradingview.com/watchlists/40854421/ (AMERİKA İLAÇ)
# - https://tr.tradingview.com/watchlists/74528880/ (AMERİKA KÜÇÜK YAZILIM VE TEKNOLOJİ HİİSE)
# - https://tr.tradingview.com/watchlists/41489478/ (AMERİKA LOJİSTİK HİSSELERİ)
# - https://tr.tradingview.com/watchlists/69825283/ (AMERİKA NADİR TOPRAK ELEMET)
# - https://tr.tradingview.com/watchlists/40932991/ (AMERİKA OYUN. SOSYA MEDYA .İLETİŞİM)
# - https://tr.tradingview.com/watchlists/41267568/ (AMERİKA QUANTUM HİSSE ve VERİ MERKEZLERİ)
# - https://tr.tradingview.com/watchlists/40820092/ (AMERİKA SAVUNMA HİSSLERİ)
# - https://tr.tradingview.com/watchlists/41525945/ (AMERİKA SİPER VE VERİ DEPOSU)
# - https://tr.tradingview.com/watchlists/40297832/ (AMERİKA TARIM ORMAN HİSSE)
# - https://tr.tradingview.com/watchlists/40916833/ (AMERİKAE-TİCARET SİTELERİİ)
# - https://tr.tradingview.com/watchlists/40819830/ (AMERİKAN AYLIK TAKİP)
# - https://tr.tradingview.com/watchlists/42295094/ (AMERİKAN BANKLARI ve SİGORTA HİSSELERİ)
# - https://tr.tradingview.com/watchlists/65944555/ (AMERİKAN ÇİN HİSSELERİ)
# - https://tr.tradingview.com/watchlists/41269883/ (AMERİKAN HİNDİSTAN NASDAĞ)
# - https://tr.tradingview.com/watchlists/71350971/ (AMERİKAN MARKET GIDA HİİSLERİ)
# - https://tr.tradingview.com/watchlists/65939161/ (AMERİKAN NÜKLER, FİSYON, MIKNATIS)
# - https://tr.tradingview.com/watchlists/42099764/ (AMERİKAN YAZILIM - TEKNOLOJİ-CİP)
# - https://tr.tradingview.com/watchlists/40819751/ (AMERİKAN YENİ HALK ARZ)
# Okuma tarihi: 2026-09-01
TRADINGVIEW_SHARED_WATCHLIST = [
    "BIDU", "NTSK", "FIG", "WIT", "ORCL",
    "SPCX", "WMT", "CRWD", "CRWV", "NBIS",
    "IREN", "IBM", "INTC", "ASML", "UBER",
    "SNOW", "SISE", "ALARK", "PGSUS", "THYAO",
    "SOUN", "PWRL", "BANVT", "ON", "STM",
    "GTLB", "NET", "SASA", "CRFSA", "PSKY",
    "WDC", "STX", "SNDK", "RTX", "AAOI",
    "BB", "NOW", "DELL", "SKHY", "POET",
    "QMLS", "AMKR", "CORZ", "SONY", "KVYO",
    "DOCN", "KEYS", "MBLY", "RR", "SERV", "KOID",
    "SPCX", "NVDA", "GOOG", "AAPL", "MSFT",
    "TSLA", "AMZN", "META", "GM", "ORCL",
    "QCOM", "AVGO", "IBM", "MU", "GE",
    "HPQ", "TSEM", "BABA", "DATABRICKS", "ARM",
    "SKHY", "HBM", "QCOM", "ORCL", "ALAB",
    "AVGO", "NBIS", "SNDK", "AMD", "AMKR",
    "LSCC", "RMBS", "SVCO", "VST", "OKLO",
    "FTNT", "MPWR", "VICR", "SMCI", "APLD",
    "CRDO", "LITE", "ANET", "TWLO", "OKTA",
    "ESTC", "PENG", "PRGS", "FSLY", "BLZE",
    "BE", "PCG", "XOM", "CVX", "OXY",
    "HAL", "PLUG", "MG", "EE", "FTK",
    "STEM", "NEE", "AEE", "MVST", "RNW",
    "ENPH", "FSLR", "AA", "AR", "NRGV",
    "HE", "CCJ", "VST", "CEG", "TLN",
    "NRG", "ET", "KMI", "INFQ",
    "NMRK", "DLR", "BXP",
    "AAL", "ALGT", "DAL", "JBLU", "LUV",
    "UAL", "ULCC", "JOBY", "BETA", "ACHR",
    "DOAS", "MZHLD", "ICHR", "ONDS", "AVAV",
    "UMAC", "KTOS", "BBY", "BCS",
    "ESGL", "ZS", "BEEM", "FPS", "NBIS",
    "HL", "AFRM", "AEM", "NEM", "KRP",
    "NOG", "AR", "GLOO", "NUE", "STLD",
    "YETI", "BKNG", "MMM", "AMP", "CLF",
    "MRNA", "NVO", "LLY", "TLRY", "CTMX",
    "HKD", "PFE", "RDHL", "EVAX", "MRK",
    "JNJ", "GILD", "UHS", "HNGE",
    "ALAB", "UBER", "SNOW", "NOW", "AMBQ",
    "FIGR", "GRAB", "SOUN", "A", "BTQ",
    "ESTC", "LYFT", "KYIV", "VEON", "TEM",
    "ISRG", "MELI", "SMCI", "CEG", "VRT",
    "WDC", "GLW",
    "LINE", "FDX", "GXO", "FDXF", "ODFL",
    "ARCB", "JBHT", "CHRW", "KNX", "MRTN",
    "SAIA", "XPO",
    "MP", "ALB", "AMC", "APLD", "AREC",
    "CLSK", "CRML", "FCX", "HIMS", "HIVE",
    "HL", "HUT", "IDR", "IONR", "IPX",
    "BITF", "LAC", "LAR", "LZM", "MARA",
    "METC", "NAK", "NB", "NEO", "RIOT",
    "SLI", "TMC", "TMQ", "USAR", "ALOY",
    "U", "GDEV", "AMT", "RBLX", "DJT", "PLTK", "SE", "UBSFY",
    "IONQ", "QBTS", "RGTI", "QUBT", "QSI",
    "PONY", "QCOM", "GFS", "INTU", "QNT",
    "IBM", "ARQQ", "LAES", "FORM", "HON",
    "DLR", "EQIX", "IRM", "HPE", "INFQ",
    "KTOS", "HWM", "ISSC", "RTX", "LDOS",
    "HII", "LHX", "AVAV", "BA", "LMT",
    "GD", "NOC", "TDG", "RKLB", "CW",
    "BWXT", "ASTS", "RKLX", "SIDU", "VZ",
    "ASPI", "PLTR", "RCAT", "LUNR", "UMAC", "AMAT",
    "DDOG", "NTSK", "CRWD", "PANW", "ZS",
    "FTNT", "NET", "SNOW", "OKTA", "S",
    "GRO", "NTR", "CF", "MOS", "CTVA", "ADM", "BG", "LNN", "DE",
    "BABA", "AMZN", "AFRM", "EBAY", "MSTR",
    "NOW", "NOK", "FIG", "QCOM", "ASPI", "NBIS",
    "LEO", "PATH", "CRM", "HIVE", "CBRS", "QMLS",
    "MS", "BAC", "JPM", "USB", "SMBK",
    "FNLC", "LSBK", "PBFS", "BANF", "CCNE",
    "WSBC", "INBK", "HBNC", "M", "CINF",
    "CB", "NP", "MET", "ACGL", "PNC",
    "SAR", "BX", "UPST", "OCC", "NODK",
    "NMIH", "HBAN", "EWBC", "APO", "BRO",
    "BABA", "NTES", "JD", "BIDU", "LI",
    "ZTO", "FUTU", "IQ", "GDS", "YUMC",
    "BEKE", "HTHT", "VIPS", "MOMO", "ATHM",
    "WB", "DT", "NIO", "PDD", "XPEV",
    "INFY", "HDB", "WIT", "RDY", "FRSH", "EXLS",
    "WMT", "VLGEA", "FRPT", "IMKTA", "GO",
    "CASY", "MCD", "BBY", "KO", "KRUS",
    "LSF", "BH", "AVGO", "PEP", "BJ", "TGT",
    "SMR", "UUUU", "OKLO", "CCJ", "UEC", "XE",
    "CEG", "AMSC", "BWXT", "UROY", "ISOU", "DNN",
    "APD", "NLR", "LTBR", "IPGP", "COHR", "NNE",
    "MG", "URA", "NXE", "LEU", "VST", "UAMY",
    "VRT", "TSM", "ON", "SMCI", "FORM", "IBM",
    "APP", "AVGO", "EQIX", "CRM", "QCOM", "ACN",
    "AMD", "CRDO", "NBIS", "SMTC", "ORCL",
    "CBRS", "QNT", "PWRL",
]

# Tekrarları otomatik temizle
TRADINGVIEW_SHARED_WATCHLIST = load_cached_symbols(
    fallback=TRADINGVIEW_SHARED_WATCHLIST
)


def get_watchlist():
    synced = load_cached_symbols(fallback=TRADINGVIEW_SHARED_WATCHLIST)
    return list(dict.fromkeys(BASE_WATCHLIST + synced))


WATCHLIST = get_watchlist()
