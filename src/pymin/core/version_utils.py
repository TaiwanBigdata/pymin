"""Version utilities for package management"""

import re
from typing import Tuple, List, Literal, Optional
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


def parse_requirement_string(
    spec: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse package requirement string into components following PEP 440.

    Args:
        spec: Package specification string, can be:
            - Full spec (e.g., 'python-dotenv==1.0.1')
            - Version constraint only (e.g., '>=1.0.1')
            - Package name only (e.g., 'python-dotenv')
            - Version only (e.g., '1.0.1', '2.1.0a1', '1.0.0.dev1')

    Returns:
        Tuple[Optional[str], Optional[str], Optional[str]]:
            - Package name (None if only version/constraint provided)
            - Version constraint (None if not provided)
            - Version (None if not provided)

    Raises:
        ValueError: If the input format is invalid or version doesn't follow PEP 440
    """
    # Try to match full dependency pattern first
    dep_match = DEPENDENCY_PATTERN.match(spec)
    if dep_match:
        name, constraint, version = dep_match.groups()
        if constraint not in VALID_CONSTRAINTS:
            raise ValueError(f"Invalid version constraint: {constraint}")
        if not VERSION_PATTERN.match(version):
            raise ValueError(f"Invalid version format: {version}")
        return name, constraint, version

    # Try to match version constraint pattern
    for constraint in VALID_CONSTRAINTS:
        if spec.startswith(constraint):
            version = spec[len(constraint) :]
            if not VERSION_PATTERN.match(version):
                raise ValueError(f"Invalid version format: {version}")
            return None, constraint, version

    # Check if it's just a version
    if VERSION_PATTERN.match(spec):
        return None, None, spec

    # Check if it's just a package name
    if re.match(r"^[a-zA-Z][a-zA-Z0-9-_.]*$", spec):
        return spec, None, None

    raise ValueError(f"Invalid requirement format: {spec}")


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
