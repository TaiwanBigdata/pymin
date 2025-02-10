"""Version checker for PyMin package"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import tomllib
import requests
import importlib.metadata
from ..ui.console import console


def check_for_updates() -> None:
    """Check for PyMin updates on PyPI"""
    cache_dir = Path.home() / ".cache" / "pymin"
    cache_file = cache_dir / "version_check.json"

    try:
        # Get current version
        current_version = importlib.metadata.version("pymin")

        # Check cache first
        if cache_file.exists():
            with open(cache_file) as f:
                cache = json.load(f)
                last_check = datetime.fromtimestamp(cache["last_check"])
                # Only check once per day
                if datetime.now() - last_check < timedelta(minutes=1):
                    latest_version = cache["latest_version"]
                    if latest_version != current_version:
                        console.print(
                            f"[yellow]New version available: [cyan]{latest_version}[/cyan] (current: {current_version})[/yellow]"
                        )
                        console.print(
                            "[yellow]To update, run: [cyan]pipx upgrade pymin[/cyan][/yellow]\n"
                        )
                    return

        # Get latest version from PyPI
        response = requests.get("https://pypi.org/pypi/pymin/json", timeout=5)
        if response.status_code == 200:
            latest_version = response.json()["info"]["version"]

            # Create cache directory if it doesn't exist
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Update cache
            with open(cache_file, "w") as f:
                json.dump(
                    {
                        "last_check": time.time(),
                        "latest_version": latest_version,
                    },
                    f,
                )

            # Show update message if needed
            if latest_version != current_version:
                console.print(
                    f"[yellow]New version available: [cyan]{latest_version}[/cyan] (current: {current_version})[/yellow]"
                )
                console.print(
                    "[yellow]To update, run: [cyan]pipx upgrade pymin[/cyan][/yellow]\n"
                )

    except Exception:
        # Silently fail on any error
        pass
