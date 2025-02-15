from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
import tomlkit
from contextlib import contextmanager

from .version_utils import (
    VERSION_CONSTRAINTS,
    VALID_CONSTRAINTS,
    parse_requirement_string,
    validate_version,
    normalize_package_name,
)
from .package_analyzer import PackageAnalyzer


class PyProjectManager:
    """A class to manage Python project dependencies in pyproject.toml file following PEP 440"""

    def __init__(self, file_path: Union[str, Path]):
        """
        Initialize PyProjectManager

        Args:
            file_path: Path to pyproject.toml file
        """
        self.file_path = Path(file_path)
        self._data: Optional[tomlkit.TOMLDocument] = None
        self.valid_constraints = VALID_CONSTRAINTS

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
        return validate_version(version)

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
        self, name: str, version: str, constraint: str = ">="
    ) -> None:
        """Add a dependency to pyproject.toml

        Args:
            name: Package name (can include extras)
            version: Version string
            constraint: Version constraint (default: ">=")
        """
        self._ensure_dependencies_table()
        dep_list = self.data["project"]["dependencies"]

        # Parse the new dependency name to get base name and extras
        new_name, new_extras, _, _ = parse_requirement_string(name)

        # Format dependency string
        dep_str = f"{name}{constraint}{version}"

        # Remove existing dependency if present (considering extras)
        for i, dep in enumerate(dep_list):
            current_name, current_extras, _, _ = parse_requirement_string(dep)
            # Compare base names and extras
            if current_name == new_name:
                # If new package has extras, it should replace the one without extras
                # If current package has extras and new one doesn't, keep the one with extras
                if new_extras or not current_extras:
                    dep_list.pop(i)
                    break

        # Add new dependency
        dep_list.append(dep_str)
        self._write()

    def remove_dependency(self, package_name: str) -> None:
        """
        Remove a dependency

        Args:
            package_name: Name of the package to remove (can include extras)
        """
        if "project" in self.data and "dependencies" in self.data["project"]:
            dep_list = self.data["project"]["dependencies"]
            new_dep_list = tomlkit.array()
            new_dep_list.multiline(True)

            # 解析要移除的套件名稱和 extras
            remove_name, remove_extras, _, _ = parse_requirement_string(
                package_name
            )
            normalized_remove_name = normalize_package_name(remove_name)

            for dep in dep_list:
                try:
                    current_name, current_extras, _, _ = (
                        parse_requirement_string(dep)
                    )
                    normalized_current_name = normalize_package_name(
                        current_name
                    )

                    # 如果基礎套件名稱不同，保留該套件
                    if normalized_current_name != normalized_remove_name:
                        new_dep_list.append(dep)
                    # 如果基礎套件名稱相同，但 extras 不同且要移除的沒有 extras，保留該套件
                    elif current_extras and not remove_extras:
                        new_dep_list.append(dep)
                except ValueError:
                    new_dep_list.append(dep)

            self.data["project"]["dependencies"] = new_dep_list
            self._write()

    def bulk_add_dependencies(
        self, dependencies: Dict[str, Union[str, Tuple[str, str]]]
    ) -> None:
        """Add multiple dependencies at once

        Args:
            dependencies: Dict mapping package names to either:
                - version string (uses default >=)
                - tuple of (version, constraint)
        """
        with self.bulk_operation():
            for name, version_info in dependencies.items():
                if isinstance(version_info, tuple):
                    version, constraint = version_info
                else:
                    version = version_info
                    constraint = ">="
                self.add_dependency(name, version, constraint)

    def get_dependencies(self) -> Dict[str, Tuple[str, str]]:
        """Get dependencies from pyproject.toml

        Returns:
            Dict mapping package names to tuples of (constraint, version)
        """
        if not self.data or "project" not in self.data:
            return {}

        deps = {}
        if "dependencies" in self.data["project"]:
            for dep in self.data["project"]["dependencies"]:
                name, extras, constraint, version = parse_requirement_string(
                    dep
                )
                if name and constraint and version:
                    deps[name] = (constraint, version)

        return deps
