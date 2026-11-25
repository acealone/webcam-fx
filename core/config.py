"""Load config.toml and fill in defaults."""
import tomllib
from pathlib import Path

CAMERA_DEFAULTS = {"index": 0, "width": 640, "height": 480, "fps": 30}
TRIGGER_DEFAULTS = {"hold": 0.3, "rearm": 0.5}


class ConfigError(Exception):
    pass


def load_config(path: Path) -> dict:
    path = Path(path)
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {path}") from None
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path} is not valid TOML: {e}") from None

    triggers = []
    for i, t in enumerate(raw.get("triggers", []), start=1):
        for key in ("gesture", "effect"):
            if not t.get(key):
                raise ConfigError(f'Trigger {i} in {path.name} has no "{key}"')
        triggers.append({**TRIGGER_DEFAULTS, **t})

    return {
        "camera": {**CAMERA_DEFAULTS, **raw.get("camera", {})},
        "triggers": triggers,
        "gestures": raw.get("gestures", {}),
        "effects": raw.get("effects", {}),
    }
