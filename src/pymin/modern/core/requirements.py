# Requirements.txt management functionality
from pathlib import Path
from typing import Dict, Optional

from .exceptions import RequirementsError
from .utils import normalize_package_name, format_version


class RequirementsManager:
    """Manages requirements.txt file operations."""

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize requirements manager.

        Args:
            project_root: Project root directory, defaults to current directory
        """
        self.project_root = project_root or Path.cwd()
        self.requirements_file = self.project_root / "requirements.txt"

    def parse(self) -> Dict[str, str]:
        """
        Parse requirements.txt into a dictionary of package names and versions.

        Returns:
            Dictionary mapping package names to version constraints

        Raises:
            RequirementsError: If requirements.txt cannot be parsed
        """
        if not self.requirements_file.exists():
            return {}

        packages = {}
        try:
            with open(self.requirements_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Handle different requirement formats
                        if "==" in line:
                            name, version = line.split("==")
                            packages[name] = f"=={version}"
                        elif ">=" in line:
                            name, version = line.split(">=")
                            packages[name] = f">={version}"
                        elif "<=" in line:
                            name, version = line.split("<=")
                            packages[name] = f"<={version}"
                        else:
                            packages[line] = ""
            return packages
        except Exception as e:
            raise RequirementsError(
                "Failed to parse requirements.txt", details=str(e)
            )

    def write(self, packages: Dict[str, str]) -> None:
        """
        Write packages to requirements.txt.

        Args:
            packages: Dictionary mapping package names to version constraints

        Raises:
            RequirementsError: If writing to requirements.txt fails
        """
        try:
            with open(self.requirements_file, "w") as f:
                for name, version in sorted(packages.items()):
                    f.write(f"{name}{version}\n")
        except Exception as e:
            raise RequirementsError(
                "Failed to write requirements.txt", details=str(e)
            )

    def add_package(self, name: str, version: Optional[str] = None) -> None:
        """
        Add a package to requirements.txt.

        Args:
            name: Package name
            version: Optional version constraint

        Raises:
            RequirementsError: If adding package fails
        """
        packages = self.parse()
        packages[name] = format_version(version)
        self.write(packages)

    def remove_package(self, name: str) -> bool:
        """
        Remove a package from requirements.txt.

        Args:
            name: Package name

        Returns:
            True if package was removed, False if not found

        Raises:
            RequirementsError: If removing package fails
        """
        packages = self.parse()
        normalized_name = normalize_package_name(name)

        # Find the package with case-insensitive match
        for pkg_name in list(packages.keys()):
            if normalize_package_name(pkg_name) == normalized_name:
                del packages[pkg_name]
                self.write(packages)
                return True
        return False

    def get_package_version(self, name: str) -> Optional[str]:
        """
        Get version constraint for a package.

        Args:
            name: Package name

        Returns:
            Version constraint if found, None otherwise
        """
        packages = self.parse()
        normalized_name = normalize_package_name(name)

        for pkg_name, version in packages.items():
            if normalize_package_name(pkg_name) == normalized_name:
                return version.lstrip("=") if version else None
        return None

    def validate(self) -> bool:
        """
        Validate requirements.txt format.

        Returns:
            True if valid, False otherwise

        Raises:
            RequirementsError: If validation fails
        """
        try:
            packages = self.parse()
            # Basic validation of package names and version formats
            for name, version in packages.items():
                if not name:
                    raise RequirementsError(
                        "Invalid package name",
                        details=f"Empty package name found",
                    )
                if version and not any(
                    version.startswith(op) for op in ["==", ">=", "<="]
                ):
                    raise RequirementsError(
                        "Invalid version format",
                        details=f"Package {name} has invalid version format: {version}",
                    )
            return True
        except RequirementsError:
            raise
        except Exception as e:
            raise RequirementsError(
                "Failed to validate requirements.txt", details=str(e)
            )
