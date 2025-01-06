# Utility functions for package name normalization and string manipulation
import re
import os
from pathlib import Path


def normalize_name(name: str) -> str:
    """
    Normalize package name according to PEP 503
    https://peps.python.org/pep-0503/#normalized-names
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def get_current_shell():
    """Get the current shell executable path"""
    shell = os.environ.get("SHELL", "/bin/sh")
    shell_name = Path(shell).name
    return shell, shell_name


def get_environment_display_name(venv_path: Path) -> str:
    """Get a display name for the virtual environment"""
    if venv_path.name in ["env", "venv"]:
        return f"({venv_path.name}) "
    return ""
