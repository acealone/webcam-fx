"""Find and load gestures (gestures/<name>/gesture.py) and effects (effects/<name>/effect.py)."""
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLASS_NAMES = {"gesture": "Gesture", "effect": "Effect"}


class PluginError(Exception):
    pass


def available(kind: str, root: Path = REPO_ROOT) -> list[str]:
    folder = Path(root) / f"{kind}s"
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir() if (p / f"{kind}.py").is_file())


def _load_class(kind: str, name: str, root: Path):
    path = Path(root) / f"{kind}s" / name / f"{kind}.py"
    if not path.is_file():
        names = ", ".join(available(kind, root)) or "none"
        raise PluginError(f'Unknown {kind} "{name}". Available {kind}s: {names}')
    spec = importlib.util.spec_from_file_location(f"{kind}s.{name}.{kind}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, CLASS_NAMES[kind], None)
    if cls is None:
        raise PluginError(f"{path} has no class {CLASS_NAMES[kind]}")
    return cls, path.parent


def load_gesture(name: str, settings: dict, root: Path = REPO_ROOT):
    cls, _ = _load_class("gesture", name, root)
    return cls(settings)


def load_effect(name: str, settings: dict, root: Path = REPO_ROOT):
    cls, folder = _load_class("effect", name, root)
    return cls(settings, folder)
