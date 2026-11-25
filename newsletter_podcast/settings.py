"""Read config.toml and .env."""

import re
import stat
import tomllib
from pathlib import Path

from . import PodcastError

DEFAULTS = {
    "show": {"name": "My Newsletter Briefing", "minutes": 15, "listener": "", "always_cover": []},
    "mail": {"host": "imap.gmail.com", "port": 993, "user": "", "folder": "Newsletters",
             "hours": 24, "minimum_issues": 3, "skip": [], "include_trash": False},
    "writer": {"backend": "api", "model": "claude-opus-5-5", "effort": "medium",
               "max_characters": 1_000_000},
    "audio": {"engine": "mac", "voice": "", "speed": 1.0},
    "output": {"folder": "output", "keep_days": 14},
    "feed": {"host": "127.0.0.1", "port": 8765, "base_url": "http://127.0.0.1:8765"},
}


def load_config(path):
    """Return the settings, with defaults filled in. Unknown names are an error,
    so a typo can't be silently ignored."""
    config = {section: dict(values) for section, values in DEFAULTS.items()}
    if not path.exists():
        return config
    try:
        found = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as problem:
        raise PodcastError(f"{path.name} has a typo: {problem}")
    for section, values in found.items():
        if section not in config or not isinstance(values, dict):
            raise PodcastError(f"{path.name} has an unknown section: [{section}]")
        for name, value in values.items():
            if name not in config[section]:
                raise PodcastError(f"{path.name} has an unknown setting: {name} in [{section}]")
            default = DEFAULTS[section][name]
            right_type = (int, float) if isinstance(default, float) else type(default)
            if not isinstance(value, right_type) or (isinstance(value, bool) and not isinstance(default, bool)):
                raise PodcastError(f"{path.name}: {name} in [{section}] should look like {default!r}")
            if isinstance(value, list) and not all(isinstance(item, str) for item in value):
                raise PodcastError(f'{path.name}: every item in {name} in [{section}] should be text in quotes, like ["Example"]')
            config[section][name] = value
    if config["writer"]["backend"] not in ("api", "claude-code"):
        raise PodcastError('config.toml: backend must be "api" or "claude-code"')
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", config["audio"]["engine"]):      # a folder name, never a path
        raise PodcastError('config.toml: engine must be "mac", "none" or the name of a folder in voices/')
    if config["audio"]["speed"] <= 0:
        raise PodcastError("config.toml: speed must be more than 0")
    if config["show"]["minutes"] < 1 or config["mail"]["hours"] < 1 or config["output"]["keep_days"] < 1:
        raise PodcastError("config.toml: minutes, hours and keep_days must be 1 or more")
    return config


def load_secrets(path):
    """Read NAME=value lines from .env. Refuse a file other accounts can read."""
    if not path.exists():
        return {}
    if path.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise PodcastError(f"Other accounts on this computer can read {path.name}. Run: chmod 600 {path}")
    secrets = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":      # quotes around the whole value
                value = value[1:-1]
            secrets[name.strip()] = value
    return secrets


def output_folder(config, root, demo=False):
    folder = (root / Path(config["output"]["folder"]).expanduser()).resolve()
    return folder / "demo" if demo else folder
