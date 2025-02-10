"""Custom exceptions for the package management system"""


class PyMinError(Exception):
    """Base exception for PyMin"""

    pass


class VirtualEnvError(PyMinError):
    """Virtual environment related errors"""

    pass


class PackageError(PyMinError):
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


class PyPIError(PyMinError):
    """PyPI interaction errors"""

    pass
