# Package name validation service
import re
import keyword
from packaging.utils import canonicalize_name


class PackageNameValidator:
    """Validate package names according to PyPI naming rules"""

    def __init__(self):
        pass

    def validate(self, name: str) -> tuple[bool, str]:
        """
        Validate a package name according to PyPI naming rules.

        Args:
            name: Package name to validate

        Returns:
            Tuple of (is_valid, message)
        """
        # Use packaging's standardization function
        normalized_name = canonicalize_name(name)

        # Basic length check
        if not name:
            return False, "Package name cannot be empty"
        if len(name) > 214:
            return False, "Package name must be 214 characters or less"

        # Python keyword check
        if name.lower() in keyword.kwlist:
            return False, "Package name cannot be a Python keyword"

        # Character validation
        if not re.match(r"^[A-Za-z0-9][-A-Za-z0-9._]+[A-Za-z0-9]$", name):
            return (
                False,
                "Package name can only contain ASCII letters, numbers, ., -, _",
            )

        # Consecutive punctuation check
        if re.search(r"[-._]{2,}", name):
            return False, "Package name cannot have consecutive . - _"

        # Full punctuation check
        if all(c in ".-_" for c in name):
            return False, "Package name cannot be composed entirely of . - _"

        return True, ""
