"""Borsa robotu için sade komut girişi.

Kullanım:
    python bot.py
    python bot.py tarama
    python bot.py haber
    python bot.py hareket
    python bot.py tarama --force --dry-run
"""

from background_scanner import main


if __name__ == "__main__":
    raise SystemExit(main())
