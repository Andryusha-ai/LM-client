# config.py
import json
from pathlib import Path

CONFIG_FILE = Path("config.json")
PRESETS_DIR = Path("config/presets")

# Настройки уровня приложения. Здесь НЕ храним api_url/api_key/model/persona —
# они целиком живут в файле пресета (config/presets/<name>.json).
DEFAULT_CONFIG = {
    "current_preset": "",
}

# Единственные ключи, которым разрешено попадать из config.json в рантайм.
# Это защищает от старых config.json (созданных до перехода на пресеты),
# в которых ещё могут валяться плоские api_url/api_key/model/persona —
# если бы они просто копировались, то перекрывали бы собой свежие данные
# из пресета при слиянии в load_config().
_ALLOWED_APP_KEYS = set(DEFAULT_CONFIG.keys())

# Значения по умолчанию для полей пресета — используются, если пресет
# ещё не выбран/не создан, чтобы у приложения были рабочие значения.
DEFAULT_PRESET = {
    "api_url": "",
    "api_key": "",
    "model": "openrouter/free",
    "persona": "Без личности",
}


def _load_preset(name: str) -> dict:
    """Читает файл пресета по имени. Если пресета нет — возвращает {}."""
    if not name:
        return {}

    preset_file = PRESETS_DIR / f"{name}.json"
    if not preset_file.exists():
        return {}

    try:
        with open(preset_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    # поле "name" нужно только внутри самого файла пресета,
    # в рантайм-конфиге оно не используется
    data.pop("name", None)
    return data


def load_config() -> dict:
    """
    Загружает config.json (там хранится только current_preset и, возможно,
    другие настройки уровня приложения) и подмешивает в него настройки
    активного пресета (api_url, api_key, model, persona).

    Возвращает "эффективный" конфиг, готовый к использованию в рантайме —
    ChatUI/App/LMWorker как и раньше могут просто делать
    config.get("api_url") и т.д.
    """
    config = DEFAULT_CONFIG.copy()

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                # Берём только известные app-level ключи (сейчас — только
                # current_preset). Любые старые api_url/api_key/model/persona,
                # оставшиеся в файле с прошлых версий, игнорируются.
                for key in _ALLOWED_APP_KEYS:
                    if key in saved:
                        config[key] = saved[key]
        except Exception:
            pass

    preset_data = _load_preset(config.get("current_preset", ""))

    effective = DEFAULT_PRESET.copy()
    effective.update(preset_data)   # значения из пресета
    effective.update(config)        # current_preset и прочие app-level поля поверх

    return effective


def save_config(config: dict):
    """
    Сохраняет в config.json ТОЛЬКО ссылку на активный пресет (current_preset).

    Сами настройки (api_url/api_key/model/persona) в config.json больше
    не пишутся — они сохраняются отдельно, в файл пресета, внутри
    SettingsDialog._save_current_as_preset(). Это устраняет дублирование
    и цикл "пресет -> конфиг -> пресет".
    """
    persisted = {
        "current_preset": config.get("current_preset", ""),
    }

    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(persisted, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
