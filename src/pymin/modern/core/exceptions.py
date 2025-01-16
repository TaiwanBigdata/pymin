# Custom exceptions for package management
from typing import Optional


class PackageError(Exception):
    """Base exception for all package-related errors."""

    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(message)


class VersionError(PackageError):
    """Exception raised for version-related errors."""

    pass


class DependencyError(PackageError):
    """Exception raised for dependency-related errors."""

    pass


class RequirementsError(PackageError):
    """Exception raised for requirements.txt related errors."""

    pass


class PipError(PackageError):
    """Exception raised for pip command related errors."""

    def __init__(
        self,
        message: str,
        pip_output: Optional[str] = None,
        details: Optional[str] = None,
    ):
        self.pip_output = pip_output
        super().__init__(message, details)


class EnvironmentError(PackageError):
    """Exception raised for virtual environment related errors."""

    pass
