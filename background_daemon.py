import os
import signal
import subprocess
import sys
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
LOCK_FILE = PROJECT_DIR / ".background_daemon.lock"
RUNNING = True


def stop_daemon(_signum, _frame):
    global RUNNING
    RUNNING = False


def process_exists(pid):
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return True


def acquire_lock():
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
            if process_exists(old_pid):
                return False
        except Exception:
            pass
        LOCK_FILE.unlink(missing_ok=True)
    descriptor = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(descriptor, str(os.getpid()).encode("utf-8"))
    os.close(descriptor)
    return True


def main():
    if not acquire_lock():
        print("Borsa robotu arka plan servisi zaten çalışıyor.")
        return 0
    signal.signal(signal.SIGTERM, stop_daemon)
    signal.signal(signal.SIGINT, stop_daemon)
    try:
        while RUNNING:
            subprocess.run(
                [sys.executable, str(PROJECT_DIR / "background_scanner.py")],
                cwd=str(PROJECT_DIR),
                check=False,
            )
            for _ in range(180):
                if not RUNNING:
                    break
                time.sleep(10)
        return 0
    finally:
        LOCK_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
