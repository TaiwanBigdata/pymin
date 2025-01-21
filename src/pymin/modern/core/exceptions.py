"""Custom exceptions for the modern package management system"""


class PyMinModernError(Exception):
    """Base exception for PyMin Modern"""

    pass


class VirtualEnvError(PyMinModernError):
    """Virtual environment related errors"""

    pass


class PackageError(PyMinModernError):
    """Package management related errors"""

    pass


class DependencyError(PackageError):
    """Dependency resolution errors"""

    pass


class VersionError(PackageError):
    """Version related errors"""

    pass


class InstallationError(PackageError):
    """Package installation errors"""

    pass


class UninstallationError(PackageError):
    """Package uninstallation errors"""

    pass


class RequirementsError(PackageError):
    """Requirements.txt related errors"""

    pass


class PyPIError(PyMinModernError):
    """PyPI interaction errors"""

    pass
