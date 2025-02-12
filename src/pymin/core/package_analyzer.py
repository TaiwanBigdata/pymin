import sys
from typing import Any, Set, Dict, Optional, List, Tuple
from packaging.requirements import Requirement
from packaging.version import Version, parse as parse_version
import importlib.metadata
from enum import Enum
import tomlkit
from pathlib import Path
from rich.text import Text

from .venv_analyzer import VenvAnalyzer
from .version_utils import (
    check_version_compatibility,
    normalize_package_name,
    parse_dependency,
    validate_version,
)


class PackageStatus(str, Enum):
    """
    Package status enumeration
    Inherits from str to make it JSON serializable and human-readable
    """

    REDUNDANT = (
        "redundant"  # Package is in requirements.txt but is also a dependency
    )
    NORMAL = "normal"  # Package is properly installed and listed
    NOT_INSTALLED = (
        "not_installed"  # Package is in requirements.txt but not installed
    )
    NOT_IN_REQUIREMENTS = "not_in_requirements"  # Package is installed but not in requirements.txt
    VERSION_MISMATCH = (
        "version_mismatch"  # Installed version doesn't match requirements
    )
    VERSION_CONFLICT = "version_conflict"  # Version conflict between pyproject.toml and requirements.txt

    def __str__(self) -> str:
        return self.value

    @classmethod
    def get_description(cls, status: "PackageStatus") -> str:
        """Get the description for a status value"""
        descriptions = {
            cls.REDUNDANT: "Package is listed in requirements.txt but is also a dependency of another package",
            cls.NORMAL: "Package is properly installed and listed in requirements.txt",
            cls.NOT_INSTALLED: "Package is listed in requirements.txt but not installed",
            cls.NOT_IN_REQUIREMENTS: "Package is installed but not listed in requirements.txt",
            cls.VERSION_MISMATCH: "Installed package version does not match requirements",
            cls.VERSION_CONFLICT: "Version conflict between pyproject.toml and requirements.txt",
        }
        return descriptions.get(status, "Unknown status")


class DependencySource(str, Enum):
    """
    Dependency source enumeration
    """

    REQUIREMENTS = "r"  # From requirements.txt
    PYPROJECT = "p"  # From pyproject.toml
    BOTH = "p+r"  # From both files

    def __str__(self) -> str:
        return self.value

    @classmethod
    def combine(cls, sources: Set["DependencySource"]) -> "DependencySource":
        """Combine multiple sources into one"""
        if len(sources) == 2:
            return cls.BOTH
        return next(iter(sources))


class DependencyInfo:
    """
    Dependency information container
    """

    def __init__(self, name: str, version_spec: str, source: DependencySource):
        self.name = name
        self._version_spec = version_spec
        self.source = source
        self._pyproject_version = None
        self._requirements_version = None

    def set_version(self, version: str, source: DependencySource):
        """Set version for specific source"""
        if source == DependencySource.PYPROJECT:
            self._pyproject_version = version
        elif source == DependencySource.REQUIREMENTS:
            self._requirements_version = version

    def _format_version_with_source(
        self, version: str, source_tag: str, color: str
    ) -> Text:
        """Format version with colored source tag"""
        # 統一移除版本約束，只保留版本號
        for constraint in [">=", "==", "<=", "!=", "~=", ">", "<"]:
            if version.startswith(constraint):
                version = version[len(constraint) :].strip()
                break

        # Create a Text object for proper color formatting
        text = Text()
        text.append(version)
        text.append(" (", style="dim")
        text.append(source_tag, style=color)
        text.append(")", style="dim")
        return text

    def format_version(self) -> Text:
        """Format version with source indicator"""
        if self.source == DependencySource.BOTH:
            # 先清理版本號
            p_version = self._clean_version(self._pyproject_version)
            r_version = self._clean_version(self._requirements_version)

            # Show both versions if they differ
            if p_version != r_version:
                r_text = self._format_version_with_source(
                    self._requirements_version, "r", "yellow"
                )
                p_text = self._format_version_with_source(
                    self._pyproject_version, "p", "cyan"
                )

                # Combine the texts
                combined = Text()
                combined.append(r_text)
                combined.append(" / ")
                combined.append(p_text)
                return combined

            # If versions are the same, show with both indicators
            return self._format_version_with_source(
                self._version_spec, "r+p", "green"
            )
        elif self.source == DependencySource.PYPROJECT:
            return self._format_version_with_source(
                self._version_spec, "p", "cyan"
            )
        else:  # REQUIREMENTS
            return self._format_version_with_source(
                self._version_spec, "r", "yellow"
            )

    def _clean_version(self, version: str) -> str:
        """Clean version string by removing constraints"""
        if version is None:
            return ""
        for constraint in [">=", "==", "<=", "!=", "~=", ">", "<"]:
            if version.startswith(constraint):
                return version[len(constraint) :].strip()
        return version

    @property
    def has_version_conflict(self) -> bool:
        """Check if there's a version conflict between sources"""
        if (
            self._pyproject_version is None
            or self._requirements_version is None
        ):
            return False

        p_version = self._clean_version(self._pyproject_version)
        r_version = self._clean_version(self._requirements_version)

        return p_version != r_version

    @property
    def version_spec(self) -> str:
        """Get version spec without source indicator"""
        if self.source == DependencySource.BOTH and self.has_version_conflict:
            return (
                self._requirements_version
            )  # 優先使用 requirements.txt 的版本
        return self._version_spec

    @version_spec.setter
    def version_spec(self, value: str):
        self._version_spec = value


class PackageAnalyzer:
    """
    Analyzer for Python package dependencies and metadata
    """

    def __init__(self, project_path: Optional[str] = None):
        """
        Initialize PackageAnalyzer with project path

        Args:
            project_path: Path to the project directory. If None, uses current directory
        """
        # Initialize VenvAnalyzer instance
        self.venv_analyzer = VenvAnalyzer(project_path)

        # Get necessary attributes from VenvAnalyzer
        self.project_path = self.venv_analyzer.project_path
        self.has_venv = self.venv_analyzer.has_venv

        # Only initialize these if we have a virtual environment
        if self.has_venv:
            self.site_packages = self.venv_analyzer.site_packages

            # Add site-packages to sys.path if not present
            if str(self.site_packages) not in sys.path:
                sys.path.insert(0, str(self.site_packages))

            # Setup importlib.metadata for compatibility
            importlib.metadata.PathDistribution.at = (
                lambda path: importlib.metadata.PathDistribution(path)
            )

        self._packages_cache = None
        self._requirements_cache = None

    def clear_cache(self):
        """Clear the package and requirements cache"""
        self._packages_cache = None
        self._requirements_cache = None

    def _parse_version_spec(self, spec: str) -> Tuple[str, str]:
        """
        Parse version specification into constraint and version

        Args:
            spec: Version specification (e.g., ">=8.0.0")

        Returns:
            Tuple of (constraint, version)
        """
        constraints = [">=", "==", "<=", "!=", "~=", ">", "<"]
        for constraint in sorted(constraints, key=len, reverse=True):
            if spec.startswith(constraint):
                version = spec[len(constraint) :].strip()
                return constraint, version
        return "", spec

    def _parse_requirements(self) -> Dict[str, DependencyInfo]:
        """
        Parse requirements.txt and pyproject.toml files and return package information

        Returns:
            Dictionary mapping package names to DependencyInfo objects
        """
        if self._requirements_cache is None:
            self._requirements_cache = {}
            sources: Dict[str, Set[DependencySource]] = {}

            # Parse requirements.txt
            req_file = self.project_path / "requirements.txt"
            if req_file.exists():
                with open(req_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            try:
                                req = Requirement(line)
                                name = self._normalize_package_name(req.name)
                                spec = (
                                    str(req.specifier) if req.specifier else ""
                                )

                                if name not in sources:
                                    sources[name] = set()
                                sources[name].add(DependencySource.REQUIREMENTS)

                                if name not in self._requirements_cache:
                                    self._requirements_cache[name] = (
                                        DependencyInfo(
                                            name=name,
                                            version_spec=spec,
                                            source=DependencySource.REQUIREMENTS,
                                        )
                                    )
                                self._requirements_cache[name].set_version(
                                    spec, DependencySource.REQUIREMENTS
                                )
                            except Exception as e:
                                print(
                                    f"Warning: Error processing requirement {line}: {e}"
                                )
                                continue

            # Parse pyproject.toml
            pyproject_file = self.project_path / "pyproject.toml"
            if pyproject_file.exists():
                try:
                    with open(pyproject_file, "r", encoding="utf-8") as f:
                        pyproject_data = tomlkit.load(f)

                    if (
                        "project" in pyproject_data
                        and "dependencies" in pyproject_data["project"]
                    ):
                        for dep in pyproject_data["project"]["dependencies"]:
                            try:
                                req = Requirement(dep)
                                name = self._normalize_package_name(req.name)
                                spec = (
                                    str(req.specifier) if req.specifier else ""
                                )

                                if name not in sources:
                                    sources[name] = set()
                                sources[name].add(DependencySource.PYPROJECT)

                                if name not in self._requirements_cache:
                                    self._requirements_cache[name] = (
                                        DependencyInfo(
                                            name=name,
                                            version_spec=spec,
                                            source=DependencySource.PYPROJECT,
                                        )
                                    )
                                self._requirements_cache[name].set_version(
                                    spec, DependencySource.PYPROJECT
                                )
                            except Exception as e:
                                print(
                                    f"Warning: Error processing dependency {dep}: {e}"
                                )
                                continue
                except Exception as e:
                    print(f"Warning: Error reading pyproject.toml: {e}")

            # Update sources for packages that appear in both files
            for name, src_set in sources.items():
                if name in self._requirements_cache:
                    self._requirements_cache[name].source = (
                        DependencySource.combine(src_set)
                    )

        return self._requirements_cache

    def _check_version_compatibility(
        self, installed_version: str, required_spec: str
    ) -> bool:
        """
        Check if installed version matches the required specification

        Args:
            installed_version: Currently installed version
            required_spec: Version specification from requirements.txt
        """
        return check_version_compatibility(installed_version, required_spec)

    @staticmethod
    def _normalize_package_name(name: str) -> str:
        """
        Normalize package name

        Args:
            name: Package name to normalize
        """
        return normalize_package_name(name)

    @staticmethod
    def _get_system_packages() -> Set[str]:
        """
        Get a set of known system packages that should be excluded from analysis
        """
        return {
            "pip",
            "setuptools",
            "wheel",
            "pkg_resources",  # Part of setuptools
            "pkg-resources",  # Debian/Ubuntu specific
            "distribute",  # Old version of setuptools
            "easy_install",  # Part of setuptools
        }

    def _should_exclude_dependency(self, requirement: str) -> bool:
        """
        Check if a dependency should be excluded from runtime dependencies

        Args:
            requirement: Original requirement string

        Returns:
            bool: True if should be excluded
        """
        if ";" not in requirement:
            return False

        _, conditions = requirement.split(";", 1)
        conditions = "".join(conditions.split())

        if "extra==" in conditions:
            extra_name = conditions.split("extra==")[1].strip("'").strip('"')
            exclude_extras = {
                "development",
                "dev",
                "test",
                "testing",
                "doc",
                "docs",
                "documentation",
                "lint",
                "linting",
                "typing",
                "check",
            }
            if extra_name in exclude_extras:
                return True

        if "sys_platform==" in conditions:
            import sys

            platform_name = (
                conditions.split("sys_platform==")[1].strip("'").strip('"')
            )
            if sys.platform != platform_name:
                return True

        return False

    def _get_package_info(
        self,
        pkg_name: str,
        installed_packages: Dict,
        requirements: Dict[str, DependencyInfo],
        all_dependencies: Set[str],
    ) -> Dict:
        """
        Get standardized package information
        """
        pkg_info = installed_packages.get(pkg_name, {})
        installed_version = pkg_info.get("installed_version")
        dep_info = requirements.get(pkg_name)

        # Format required version with source indicator
        required_version = dep_info.format_version() if dep_info else None
        version_for_check = dep_info.version_spec if dep_info else ""

        is_installed = pkg_name in installed_packages

        # Determine package status
        if not is_installed and pkg_name in requirements:
            status = PackageStatus.NOT_INSTALLED
        elif pkg_name in all_dependencies and pkg_name in requirements:
            status = PackageStatus.REDUNDANT
        elif is_installed and pkg_name not in requirements:
            status = PackageStatus.NOT_IN_REQUIREMENTS
        elif dep_info and dep_info.has_version_conflict:
            status = PackageStatus.VERSION_CONFLICT
        elif is_installed and version_for_check:
            if not self._check_version_compatibility(
                installed_version, version_for_check
            ):
                status = PackageStatus.VERSION_MISMATCH
            else:
                status = PackageStatus.NORMAL
        else:
            status = PackageStatus.NORMAL

        return {
            "name": pkg_info.get("name", pkg_name),
            "installed_version": installed_version,
            "required_version": required_version,
            "dependencies": sorted(pkg_info.get("dependencies", [])),
            "status": status.value,
        }

    def _get_package_dependencies(
        self, dist: importlib.metadata.PathDistribution, exclude_system: bool
    ) -> List[str]:
        """
        Get package dependencies from distribution

        Args:
            dist: Package distribution
            exclude_system: Whether to exclude system packages

        Returns:
            List of dependency names
        """
        system_packages = (
            self._get_system_packages() if exclude_system else set()
        )
        deps = set()

        if dist.requires:
            for req in dist.requires:
                try:
                    if self._should_exclude_dependency(req):
                        continue
                    req_obj = Requirement(req)
                    dep_name = self._normalize_package_name(req_obj.name)
                    if not exclude_system or dep_name not in system_packages:
                        deps.add(dep_name)
                except Exception as e:
                    print(f"Warning: Error processing requirement {req}: {e}")
                    continue

        return sorted(deps)

    def get_venv_info(self) -> Dict[str, Any]:
        """
        Get information about the virtual environment
        """
        return self.venv_analyzer.get_venv_info()

    def get_installed_packages(
        self, exclude_system: bool = True
    ) -> Dict[str, Dict]:
        """
        Get all installed packages and their information, sorted alphabetically
        """
        if not self.has_venv:
            return {}

        if self._packages_cache is None:
            packages_info = {}
            system_packages = (
                self._get_system_packages() if exclude_system else set()
            )

            try:
                for pattern in ["*.dist-info", "*.egg-info"]:
                    for info_dir in sorted(self.site_packages.glob(pattern)):
                        try:
                            dist = importlib.metadata.PathDistribution.at(
                                info_dir
                            )
                            original_name = dist.metadata["Name"]
                            normalized_name = self._normalize_package_name(
                                original_name
                            )
                            installed_version = dist.metadata["Version"]

                            if (
                                exclude_system
                                and normalized_name in system_packages
                            ):
                                continue

                            packages_info[normalized_name] = {
                                "name": original_name,
                                "installed_version": installed_version,
                                "dependencies": self._get_package_dependencies(
                                    dist, exclude_system
                                ),
                            }

                        except Exception as e:
                            print(
                                f"Warning: Error processing {info_dir}: {str(e)}"
                            )
                            continue

                all_dependencies = set()
                for pkg_info in packages_info.values():
                    all_dependencies.update(pkg_info["dependencies"])

                requirements = self._parse_requirements()
                for pkg_name in list(packages_info.keys()):
                    packages_info[pkg_name] = self._get_package_info(
                        pkg_name, packages_info, requirements, all_dependencies
                    )

                self._packages_cache = dict(sorted(packages_info.items()))
            except Exception as e:
                print(f"Error scanning packages: {str(e)}")
                self._packages_cache = {}

        return self._packages_cache

    def get_top_level_packages(
        self, exclude_system: bool = True
    ) -> Dict[str, Dict]:
        """
        Get packages that are either not dependencies of other packages or listed in requirements.txt

        Args:
            exclude_system: Whether to exclude system packages

        Returns:
            Dictionary containing top-level package information
        """
        if not self.has_venv:
            return {}

        installed_packages = self.get_installed_packages(
            exclude_system=exclude_system
        )
        requirements = self._parse_requirements()

        all_dependencies = set()
        for pkg_info in installed_packages.values():
            if pkg_info["dependencies"]:
                all_dependencies.update(pkg_info["dependencies"])

        top_level_pkgs = {}
        for pkg_name in set(requirements.keys()) | (
            set(installed_packages.keys()) - all_dependencies
        ):
            top_level_pkgs[pkg_name] = self._get_package_info(
                pkg_name, installed_packages, requirements, all_dependencies
            )

        return dict(sorted(top_level_pkgs.items()))

    def get_dependency_tree(
        self, exclude_system: bool = True
    ) -> Dict[str, Dict]:
        """
        Get detailed dependency tree with package status and version information

        Args:
            exclude_system: Whether to exclude system packages

        Returns:
            Dictionary containing package information and their dependencies tree
        """
        if not self.has_venv:
            return {}

        installed_packages = self.get_installed_packages(
            exclude_system=exclude_system
        )
        requirements = self._parse_requirements()
        top_level = self.get_top_level_packages(exclude_system=exclude_system)

        all_dependencies = set()
        for pkg_info in installed_packages.values():
            if pkg_info["dependencies"]:
                all_dependencies.update(pkg_info["dependencies"])

        def _build_dependency_info(
            pkg_name: str, visited: Set[str] = None
        ) -> Optional[Dict]:
            if visited is None:
                visited = set()

            if pkg_name in visited:
                return None

            visited.add(pkg_name)

            base_info = self._get_package_info(
                pkg_name, installed_packages, requirements, all_dependencies
            )

            nested_deps = {}
            for dep_name in base_info["dependencies"]:
                dep_info = _build_dependency_info(dep_name, visited.copy())
                if dep_info is not None:
                    if (
                        dep_info["installed_version"] is not None
                        or dep_info["required_version"] is not None
                    ):
                        nested_deps[dep_name] = dep_info

            base_info["dependencies"] = nested_deps
            return base_info

        result = {}
        for pkg_name in top_level.keys():
            dep_info = _build_dependency_info(pkg_name)
            if dep_info is not None:
                result[pkg_name] = dep_info

        return dict(sorted(result.items()))
