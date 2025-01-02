# Package version validation service using PEP 440 standards
from packaging.version import Version, InvalidVersion


def validate_version(version_str: str) -> Tuple[bool, str]:
    """
    Validate version string format
    """
    try:
        Version(version_str)
        return True, ""
    except InvalidVersion:
        return False, "Invalid version format"
