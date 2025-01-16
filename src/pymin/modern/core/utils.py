# Core utility functions for package management
import os
import subprocess
import sys
import importlib
import importlib.metadata
from pathlib import Path
from typing import Set, Optional

from .exceptions import EnvironmentError


def normalize_package_name(name: str) -> str:
    """
    Normalize package name by converting both hyphen and underscore to hyphen.

    Args:
        name: The package name to normalize

    Returns:
        Normalized package name in lowercase with hyphens
    """
    return name.lower().replace("_", "-")


def get_system_packages() -> Set[str]:
    """
    Get a set of known system packages that should be excluded from analysis.

    Returns:
        A set of package names that are considered system packages
    """
    return {
        "pip",
        "setuptools",
        "wheel",
    }


def get_venv_site_packages(python_path: str) -> str:
    """
    Get site-packages directory from Python interpreter.

    Args:
        python_path: Path to the Python interpreter

    Returns:
        Path to the site-packages directory

    Raises:
        EnvironmentError: If unable to get site-packages path
    """
    try:
        cmd = [
            python_path,
            "-c",
            "import site; print(site.getsitepackages()[0])",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise EnvironmentError(
            "Failed to get site-packages path", details=str(e)
        )


def switch_virtual_env(venv_path: str) -> None:
    """
    Switch to specified virtual environment.

    Args:
        venv_path: Path to the virtual environment

    Raises:
        EnvironmentError: If virtual environment is invalid or switching fails
    """
    python_path = os.path.join(venv_path, "bin", "python")
    if not os.path.exists(python_path):
        raise EnvironmentError(
            "Invalid virtual environment",
            details=f"Python executable not found: {python_path}",
        )

    site_packages = get_venv_site_packages(python_path)
    if not os.path.exists(site_packages):
        raise EnvironmentError(
            "Invalid virtual environment",
            details=f"Site-packages directory not found: {site_packages}",
        )

    # Remove all existing site-packages from sys.path
    sys.path = [p for p in sys.path if "site-packages" not in p]

    # Add the virtual environment's site-packages at the beginning
    sys.path.insert(0, site_packages)

    # Clear all existing distributions cache
    importlib.metadata.MetadataPathFinder.invalidate_caches()
    importlib.reload(importlib.metadata)


def get_canonical_name(name: str) -> str:
    """
    Get the canonical package name from installed distributions.

    Args:
        name: The package name to look up

    Returns:
        The canonical package name, or the input name if not found
    """
    try:
        normalized_name = normalize_package_name(name)
        for dist in importlib.metadata.distributions():
            if normalize_package_name(dist.metadata["Name"]) == normalized_name:
                return dist.metadata["Name"]
    except Exception:
        pass
    return name


def format_version(version: Optional[str] = None) -> str:
    """
    Format version string consistently.

    Args:
        version: Version string to format

    Returns:
        Formatted version string with == prefix if not empty
    """
    if not version:
        return ""
    if version.startswith("=="):
        return version
    return f"=={version}"
