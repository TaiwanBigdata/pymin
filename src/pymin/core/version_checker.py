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
    try:
        # Get current version from installed package
        current_version = importlib.metadata.version("pymin")

        # Get latest version from PyPI
        response = requests.get("https://pypi.org/pypi/pymin/json", timeout=5)
        if response.status_code == 200:
            latest_version = response.json()["info"]["version"]

            # Compare versions
            if latest_version != current_version:
                console.print(
                    f"\n[yellow]New version available: [cyan]{latest_version}[/cyan] (current: {current_version})[/yellow]"
                )
                console.print(
                    "[yellow]To update, run: [cyan]pipx upgrade pymin[/cyan][/yellow]\n"
                )

    except Exception:
        # Silently fail on any error
        pass
