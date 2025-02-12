"""Version utilities for package management"""

import re
from typing import Tuple, List, Literal
from packaging.version import Version, parse as parse_version
from packaging.specifiers import SpecifierSet


VERSION_CONSTRAINTS = Literal[">=", "==", "<=", "!=", "~=", ">", "<"]
VALID_CONSTRAINTS = [">=", "==", "<=", "!=", "~=", ">", "<"]

# Version pattern following PEP 440 and common practices
VERSION_PATTERN = re.compile(
    r"^(\d+\.\d+|\d+\.\d+\.\d+)"  # Major.Minor or Major.Minor.Patch
    r"((a|b|rc|alpha|beta)\d+)?"  # Pre-release version (optional, without dot)
    r"(\.dev\d+)?"  # Development release (optional)
    r"(\.post\d+)?"  # Post-release version (optional)
    r"(\+[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*)?$"  # Local version identifier (optional)
)

# Dependency pattern for parsing package specs
DEPENDENCY_PATTERN = re.compile(
    r"^([a-zA-Z0-9-_.]+)([>=<!~]=?|!=)(.+)$"  # Package name, constraint, version
)


def validate_version(version: str) -> bool:
    """
    Validate version string format following PEP 440

    Args:
        version: Version string to validate

    Returns:
        bool: True if version format is valid
    """
    return bool(VERSION_PATTERN.match(version))


def parse_dependency(dep_str: str) -> Tuple[str, str, str]:
    """
    Parse dependency string into components

    Args:
        dep_str: Dependency string (e.g., 'pytest>=7.0.0')

    Returns:
        Tuple[str, str, str]: Package name, constraint, version

    Raises:
        ValueError: If dependency string format is invalid
    """
    match = DEPENDENCY_PATTERN.match(dep_str)
    if not match:
        raise ValueError(f"Invalid dependency format: {dep_str}")

    package_name, constraint, version = match.groups()
    return package_name.strip(), constraint, version.strip()


def check_version_compatibility(
    installed_version: str, required_spec: str
) -> bool:
    """
    Check if installed version matches the required specification

    Args:
        installed_version: Currently installed version
        required_spec: Version specification (e.g., '>=1.0.0')

    Returns:
        bool: True if version is compatible
    """
    if not required_spec:
        return True

    try:
        return parse_version(installed_version) in SpecifierSet(required_spec)
    except Exception:
        return False


def normalize_package_name(name: str) -> str:
    """
    Normalize package name following PEP 503

    Args:
        name: Package name to normalize

    Returns:
        str: Normalized package name
    """
    return name.lower().replace("_", "-")
