from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Literal
import tomlkit
from contextlib import contextmanager
import re


class PyProjectManager:
    """A class to manage Python project dependencies in pyproject.toml file following PEP 440"""

    VERSION_CONSTRAINTS = Literal[">=", "==", "<=", "!=", "~=", ">", "<"]

    def __init__(self, file_path: Union[str, Path]):
        """
        Initialize PyProjectManager

        Args:
            file_path: Path to pyproject.toml file
        """
        self.file_path = Path(file_path)
        self._data: Optional[tomlkit.TOMLDocument] = None
        self._version_pattern = re.compile(r"^(\d+\.)?(\d+\.)?(\d+)$")
        self._dependency_pattern = re.compile(
            r"^([a-zA-Z0-9-_.]+)([>=<!~]=?|!=)(.+)$"
        )
        self.valid_constraints = [">=", "==", "<=", "!=", "~=", ">", "<"]

    @property
    def data(self) -> tomlkit.TOMLDocument:
        """Cached property to access pyproject.toml content"""
        if self._data is None:
            self._read()
        return self._data

    def _read(self) -> None:
        """Read and parse pyproject.toml file"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        with self.file_path.open("r", encoding="utf-8") as f:
            self._data = tomlkit.parse(f.read())

    def _write(self) -> None:
        """Write current data back to pyproject.toml"""
        with self.file_path.open("w", encoding="utf-8") as f:
            f.write(tomlkit.dumps(self._data))

    def _validate_version(self, version: str) -> bool:
        """
        Validate version string format

        Args:
            version: Version string to validate

        Returns:
            bool: True if version format is valid
        """
        return bool(self._version_pattern.match(version))

    def _parse_dependency(self, dep_str: str) -> Tuple[str, str, str]:
        """
        Parse dependency string into components

        Args:
            dep_str: Dependency string (e.g., 'pytest>=7.0.0')

        Returns:
            Tuple[str, str, str]: Package name, constraint, version

        Raises:
            ValueError: If dependency string format is invalid
        """
        match = self._dependency_pattern.match(dep_str)
        if not match:
            raise ValueError(f"Invalid dependency format: {dep_str}")

        package_name, constraint, version = match.groups()
        return package_name.strip(), constraint, version.strip()

    def _ensure_dependencies_table(self) -> None:
        """Ensure project.dependencies section exists"""
        if "project" not in self.data:
            self.data["project"] = tomlkit.table()
        if "dependencies" not in self.data["project"]:
            self.data["project"]["dependencies"] = tomlkit.array()
            self.data["project"]["dependencies"].multiline(True)

    @contextmanager
    def bulk_operation(self):
        """Context manager for bulk operations"""
        try:
            yield self
        finally:
            self._write()

    def add_dependency(
        self,
        package_name: str,
        version: str,
        constraint: VERSION_CONSTRAINTS = ">=",
    ) -> None:
        """
        Add or update a dependency

        Args:
            package_name: Name of the package
            version: Version of the package
            constraint: Version constraint (>=, ==, <=, !=, ~=, >, <)

        Raises:
            ValueError: If version format or constraint is invalid
        """
        if constraint not in self.valid_constraints:
            raise ValueError(
                f"Invalid constraint: {constraint}. "
                f"Valid constraints are: {', '.join(self.valid_constraints)}"
            )

        if not self._validate_version(version):
            raise ValueError(f"Invalid version format: {version}")

        self._ensure_dependencies_table()
        dep_list = self.data["project"]["dependencies"]
        new_dep_str = f"{package_name}{constraint}{version}"

        # Create new array preserving format
        new_dep_list = tomlkit.array()
        new_dep_list.multiline(True)

        # Update or append dependency
        found = False
        for dep in dep_list:
            try:
                current_name, _, _ = self._parse_dependency(dep)
                if current_name == package_name:
                    new_dep_list.append(new_dep_str)
                    found = True
                else:
                    new_dep_list.append(dep)
            except ValueError:
                new_dep_list.append(dep)

        if not found:
            new_dep_list.append(new_dep_str)

        self.data["project"]["dependencies"] = new_dep_list
        self._write()

    def remove_dependency(self, package_name: str) -> None:
        """
        Remove a dependency

        Args:
            package_name: Name of the package to remove
        """
        if "project" in self.data and "dependencies" in self.data["project"]:
            dep_list = self.data["project"]["dependencies"]
            new_dep_list = tomlkit.array()
            new_dep_list.multiline(True)

            for dep in dep_list:
                try:
                    current_name, _, _ = self._parse_dependency(dep)
                    if current_name != package_name:
                        new_dep_list.append(dep)
                except ValueError:
                    new_dep_list.append(dep)

            self.data["project"]["dependencies"] = new_dep_list
            self._write()

    def bulk_add_dependencies(
        self, dependencies: Dict[str, Union[str, Tuple[str, str]]]
    ) -> None:
        """
        Add multiple dependencies at once

        Args:
            dependencies: Dictionary of package names and versions.
                        Values can be either version strings (uses >=)
                        or tuples of (version, constraint)
        """
        with self.bulk_operation():
            for package_name, version_info in dependencies.items():
                if isinstance(version_info, tuple):
                    version, constraint = version_info
                    self.add_dependency(package_name, version, constraint)
                else:
                    self.add_dependency(package_name, version_info)

    def get_dependencies(self) -> Dict[str, Tuple[str, str]]:
        """
        Get current dependencies

        Returns:
            Dict[str, Tuple[str, str]]: Dictionary of package names and (constraint, version) tuples
        """
        if (
            "project" not in self.data
            or "dependencies" not in self.data["project"]
        ):
            return {}

        result = {}
        for dep in self.data["project"]["dependencies"]:
            try:
                package_name, constraint, version = self._parse_dependency(dep)
                result[package_name] = (constraint, version)
            except ValueError:
                continue
        return result
