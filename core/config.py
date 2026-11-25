"""Load config.toml and fill in defaults."""
import tomllib
from pathlib import Path

CAMERA_DEFAULTS = {"index": 0, "width": 640, "height": 480, "fps": 30}
TRIGGER_DEFAULTS = {"hold": 0.3, "rearm": 0.5}


class ConfigError(Exception):
    pass


def check_number(value, name: str, positive: bool = False) -> float:
    """A number >= 0 (or > 0 if positive). Raises ConfigError otherwise, e.g. for "0.3" in quotes."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or (positive and value == 0):
        need = "a number greater than 0" if positive else "a number of 0 or more"
        raise ConfigError(f"{name} must be {need}, got {value!r}")
    return float(value)


def load_config(path: Path) -> dict:
    path = Path(path)
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {path}") from None
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path} is not valid TOML: {e}") from None

    raw_triggers = raw.get("triggers", [])
    if not isinstance(raw_triggers, list) or not all(isinstance(t, dict) for t in raw_triggers):
        raise ConfigError(f"{path.name}: use [[triggers]] (double brackets), one block per trigger")
    triggers = []
    for i, t in enumerate(raw_triggers, start=1):
        for key in ("gesture", "effect"):
            if not t.get(key):
                raise ConfigError(f'Trigger {i} in {path.name} has no "{key}"')
            if not isinstance(t[key], str):
                raise ConfigError(f'Trigger {i} in {path.name}: "{key}" must be a name in quotes, got {t[key]!r}')
        t = {**TRIGGER_DEFAULTS, **t}
        for key in ("hold", "rearm"):
            t[key] = check_number(t[key], f"Trigger {i} {key}")
        triggers.append(t)

    return {
        "camera": {**CAMERA_DEFAULTS, **raw.get("camera", {})},
        "triggers": triggers,
        "gestures": raw.get("gestures", {}),
        "effects": raw.get("effects", {}),
        "sound": {"mixer": True, "keep_alive": True, **raw.get("sound", {})},
    }
