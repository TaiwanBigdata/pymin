"""Version utilities for package management"""

import re
from typing import Set, Tuple, List, Literal, Optional
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

# Updated dependency pattern to support extras
DEPENDENCY_PATTERN = re.compile(
    r"^([a-zA-Z0-9-_.]+)"  # Package name
    r"(?:\[((?:[a-zA-Z0-9-_.]+(?:\s*,\s*[a-zA-Z0-9-_.]+)*)?)\])?"  # Optional extras in brackets
    r"([>=<!~]=?|!=)?"  # Optional version constraint
    r"(.+)?$"  # Optional version
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


def parse_requirement_string(
    spec: str,
) -> Tuple[Optional[str], Optional[Set[str]], Optional[str], Optional[str]]:
    """
    Parse package requirement string into components following PEP 508.

    Args:
        spec: Package specification string, can be:
            - Full spec with extras (e.g., 'uvicorn[standard]==0.27.0')
            - Multiple extras (e.g., 'uvicorn[standard,asyncio]>=0.27.0')
            - Full spec (e.g., 'python-dotenv==1.0.1')
            - Version constraint only (e.g., '>=1.0.1')
            - Package name only (e.g., 'python-dotenv')
            - Version only (e.g., '1.0.1', '2.1.0a1', '1.0.0.dev1')

    Returns:
        Tuple[Optional[str], Optional[Set[str]], Optional[str], Optional[str]]:
            - Package name (None if only version provided)
            - Set of extras (None if no extras provided)
            - Version constraint (None if not provided)
            - Version (None if not provided)

    Raises:
        ValueError: If the input format is invalid or version doesn't follow PEP 440
    """
    if not spec.strip():
        raise ValueError("Empty requirement string")

    # Check for pure version number
    if VERSION_PATTERN.match(spec):
        return None, None, None, spec

    # Validate package name format (no spaces, valid characters)
    PACKAGE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][\w\d._-]*$")

    # Parse package name and extras
    name_extras_match = re.match(r"^([\w\d._-]+)(?:\[([\w\d._,-]+)\])?", spec)
    if not name_extras_match:
        raise ValueError("Invalid package name format")

    name = name_extras_match.group(1)
    if not PACKAGE_NAME_PATTERN.match(name):
        raise ValueError("Invalid package name format")

    extras_str = name_extras_match.group(2)
    extras = None
    if extras_str:
        if not extras_str.strip():
            raise ValueError("Empty extras")
        try:
            extras = {extra.strip() for extra in extras_str.split(",")}
            # Validate each extra
            for extra in extras:
                if not PACKAGE_NAME_PATTERN.match(extra):
                    raise ValueError("Invalid characters in extras")
        except Exception:
            raise ValueError("Invalid extras format")

    # Parse version constraint and version
    remaining = spec[len(name_extras_match.group(0)) :].strip()
    if not remaining:
        return name, extras, None, None

    constraint_match = re.match(r"^(>=|<=|!=|==|~=|>|<)(.+)$", remaining)
    if not constraint_match:
        raise ValueError("Invalid version constraint format")

    constraint = constraint_match.group(1)
    version = constraint_match.group(2).strip()

    if not VERSION_PATTERN.match(version):
        raise ValueError("Invalid version format")

    return name, extras, constraint, version


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
