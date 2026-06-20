from __future__ import annotations

import ctypes
import logging
import os
import socket
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from pathlib import Path

from uvicorn import Config, Server

from app.core.config import APP_NAME, DEFAULT_HOST, DEFAULT_PORT, get_data_dir
from app.main import app

LOG_STREAM = None


def get_log_path() -> Path:
    log_dir = get_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "desktop.log"


def configure_logging() -> Path:
    global LOG_STREAM
    log_path = get_log_path()
    LOG_STREAM = log_path.open("a", encoding="utf-8", buffering=1)
    sys.stdout = LOG_STREAM
    sys.stderr = LOG_STREAM
    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )
    return log_path


def find_available_port() -> int:
    preferred_ports = [DEFAULT_PORT, 8778, 8779, 8780, 8781, 8782, 8783, 8784, 8785]
    for port in preferred_ports:
        if port_is_free(port):
            return port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((DEFAULT_HOST, 0))
        return int(probe.getsockname()[1])


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.2)
        return probe.connect_ex((DEFAULT_HOST, port)) != 0


def wait_for_server(url: str) -> bool:
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{url}/api/status", timeout=0.5) as response:
                if response.status == 200:
                    return True
        except OSError:
            time.sleep(0.25)
    return False


def open_browser_when_ready(url: str) -> None:
    if wait_for_server(url):
        logging.info("Opening browser at %s", url)
        webbrowser.open(url)
        return

    logging.error("Server did not become ready at %s", url)
    show_error(f"O servidor local nao iniciou corretamente.\n\nVeja o log em:\n{get_log_path()}")


def show_error(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10)
    except Exception:
        logging.error(message)


def main() -> None:
    configure_logging()
    port = find_available_port()
    url = f"http://{DEFAULT_HOST}:{port}"
    logging.info("Starting %s at %s", APP_NAME, url)

    threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True).start()
    config = Config(
        app=app,
        host=DEFAULT_HOST,
        port=port,
        log_level="warning",
        access_log=False,
        log_config=None,
    )
    Server(config).run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        details = traceback.format_exc()
        try:
            log_path = get_log_path()
            with log_path.open("a", encoding="utf-8") as error_log:
                error_log.write("\n")
                error_log.write(details)
        except Exception:
            log_path = Path(os.getenv("TEMP", ".")) / "SistemaDeSenhas-error.log"
            with log_path.open("a", encoding="utf-8") as error_log:
                error_log.write("\n")
                error_log.write(details)
        show_error(f"O aplicativo encontrou um erro ao iniciar.\n\nLog:\n{log_path}")
