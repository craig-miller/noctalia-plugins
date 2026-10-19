#!/usr/bin/env python3
"""Print the next timed event from Noctalia's configured vdir accounts as JSON."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from datetime import date
from pathlib import Path
from typing import Any


def noctalia_state_dir() -> Path:
    override = os.environ.get("NOCTALIA_STATE_HOME")
    if override:
        return Path(override).expanduser()
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "noctalia"


def config_files() -> list[Path]:
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "noctalia"
    files = sorted(config_dir.glob("*.toml"))
    settings = noctalia_state_dir() / "settings.toml"
    if settings.exists():
        files.append(settings)
    return files


def vdir_accounts() -> dict[str, dict[str, Any]]:
    accounts: dict[str, dict[str, Any]] = {}
    for path in config_files():
        try:
            with path.open("rb") as fh:
                data = tomllib.load(fh)
        except (OSError, tomllib.TOMLDecodeError):
            continue
        calendar = data.get("calendar", {})
        if not isinstance(calendar, dict):
            continue
        raw_accounts = calendar.get("account", {})
        if not isinstance(raw_accounts, dict):
            continue
        for account_id, settings in raw_accounts.items():
            if isinstance(settings, dict):
                accounts[str(account_id)] = settings
    return {
        account_id: settings
        for account_id, settings in accounts.items()
        if settings.get("type") == "vdir" and settings.get("path")
    }


def collection_dirs(root: Path, selected: set[str]) -> list[Path]:
    if not root.is_dir():
        return []
    found: list[Path] = []
    candidates = [root]
    candidates.extend(path for path in root.rglob("*") if path.is_dir())
    for path in candidates:
        try:
            depth = len(path.relative_to(root).parts)
        except ValueError:
            continue
        if depth > 5 or (selected and path.name not in selected):
            continue
        try:
            has_events = any(path.glob("*.ics"))
        except OSError:
            continue
        if has_events:
            found.append(path)
    return sorted(found)


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")
    return cleaned or "calendar"


def build_khal_config(accounts: dict[str, dict[str, Any]], cache_dir: Path) -> tuple[Path, dict[str, str]]:
    entries: list[tuple[str, Path, str]] = []
    seen: set[Path] = set()
    for account_id, settings in sorted(accounts.items()):
        root = Path(os.path.expandvars(os.path.expanduser(str(settings["path"])))).resolve()
        selected_value = settings.get("calendars", [])
        selected = {str(item) for item in selected_value} if isinstance(selected_value, list) else set()
        display = str(settings.get("name") or account_id)
        for index, path in enumerate(collection_dirs(root, selected), start=1):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            alias = safe_name(f"{account_id}_{index}_{path.name}")
            entries.append((alias, resolved, display))

    if not entries:
        raise RuntimeError("No event collections found in Noctalia's vdir accounts")

    cache_dir.mkdir(parents=True, exist_ok=True)
    config_path = cache_dir / "khal.toml"
    lines = ["[calendars]"]
    aliases: dict[str, str] = {}
    for alias, path, display in entries:
        aliases[alias] = display
        lines.extend((
            f"[[{alias}]]",
            f"path = {json.dumps(str(path))}",
            "readonly = true",
            "",
        ))
    lines.extend((
        "[sqlite]",
        f"path = {json.dumps(str(cache_dir / 'khal.db'))}",
        "",
        "[locale]",
        f"local_timezone = {json.dumps(os.environ.get('TZ', 'America/Los_Angeles'))}",
        f"default_timezone = {json.dumps(os.environ.get('TZ', 'America/Los_Angeles'))}",
        "timeformat = %H:%M",
        "dateformat = %Y-%m-%d",
        "longdateformat = %Y-%m-%d",
        "datetimeformat = %Y-%m-%d %H:%M",
        "longdatetimeformat = %Y-%m-%d %H:%M",
        "firstweekday = 6",
        "",
        "[default]",
        "timedelta = 7d",
    ))
    content = "\n".join(lines) + "\n"
    if not config_path.exists() or config_path.read_text(encoding="utf-8") != content:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=cache_dir, delete=False) as fh:
            fh.write(content)
            temporary = Path(fh.name)
        temporary.replace(config_path)
    return config_path, aliases


def next_event(config_path: Path, aliases: dict[str, str]) -> dict[str, Any]:
    command = [
        "/usr/bin/khal", "-v", "ERROR", "-c", str(config_path),
        "list", "now", "tomorrow", "--notstarted",
        "--json", "calendar", "--json", "start-date", "--json", "start-time",
        "--json", "end-time", "--json", "title",
    ]
    result = subprocess.run(command, text=True, capture_output=True, timeout=30, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "khal list failed")
    try:
        events = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError("khal returned invalid JSON") from exc

    today = date.today().isoformat()
    event = next(
        (
            item for item in events
            if isinstance(item, dict)
            and item.get("start-date") == today
            and item.get("start-time")
        ),
        None,
    )
    if event is None:
        return {"text": "No events today", "tooltip": "No more timed events today", "ok": True}

    start = str(event["start-time"])
    hour, minute = (int(part) for part in start.split(":", 1))
    display_hour = 12 if hour == 0 else hour - 12 if hour > 12 else hour
    title = str(event.get("title") or "Untitled event")
    calendar = str(event.get("calendar") or "")
    account = aliases.get(calendar, calendar or "Noctalia calendar")
    return {
        "text": f"{title} - {display_hour}:{minute:02d}",
        "tooltip": f"Next event from {account}",
        "ok": True,
    }


def main() -> int:
    accounts = vdir_accounts()
    if not accounts:
        raise RuntimeError("No Noctalia vdir calendar accounts are configured")
    cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    config_path, aliases = build_khal_config(accounts, cache_home / "noctalia-next-event")
    print(json.dumps(next_event(config_path, aliases), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
