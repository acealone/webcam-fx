"""Start webcam-fx:  python run.py [--config config.toml]"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.config import ConfigError, load_config  # noqa: E402
from core.plugins import PluginError  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Gesture-triggered webcam effects for Teams (via OBS Virtual Camera).")
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml", help="settings file (default: config.toml)")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        from core.app import run
        run(config, ROOT / "data" / "background.png")
    except (ConfigError, PluginError) as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
