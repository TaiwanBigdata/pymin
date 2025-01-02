# Package name validation service implementing PyPI naming conventions
import re
import keyword
from typing import Tuple


class PackageNameValidator:
    """Package name validator following PyPI naming rules"""

    @staticmethod
    def validate(name: str) -> Tuple[bool, str]:
        """
        Validate package name according to PyPI rules

        Args:
            name: Package name to validate

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not name:
            return False, "Package name cannot be empty"

        if len(name) > 214:
            return False, "Package name must be 214 characters or less"

        if name.lower() in keyword.kwlist:
            return False, "Package name cannot be a Python keyword"

        if not re.match(
            "^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", name.upper()
        ):
            return (
                False,
                "Package name can only contain ASCII letters, numbers, ., -, _",
            )

        if re.search("[-_.]{2,}", name):
            return (
                False,
                "Package name has consecutive dots, hyphens, or underscores",
            )

        if all(c in ".-_" for c in name):
            return False, "Package name cannot be composed entirely of . - _"

        return True, ""


# Keep original function as a convenience method
def validate_package_name(name: str) -> Tuple[bool, str]:
    """Convenience function that uses PackageNameValidator"""
    return PackageNameValidator.validate(name)
