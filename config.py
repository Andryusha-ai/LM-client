import json
from pathlib import Path

CONFIG_DIR = Path("config")
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "api_url": "http://127.0.0.1:1234/v1",
    "api_key": ""
}


def load_config():
    """
    Загружает конфиг.
    Если файла нет или он битый —
    создаёт новый с настройками по умолчанию.
    """

    CONFIG_DIR.mkdir(exist_ok=True)

    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Добавляем отсутствующие параметры
        for key, value in DEFAULT_CONFIG.items():
            config.setdefault(key, value)

        return config

    except Exception:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """
    Сохраняет конфиг.
    """

    CONFIG_DIR.mkdir(exist_ok=True)

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

