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
    parse_requirement_string,
    validate_version,
    VALID_CONSTRAINTS,
)


class PackageStatus(str, Enum):
    """
    Package status enumeration
    Inherits from str to make it JSON serializable and human-readable
    """

    REDUNDANT = (
        "redundant"  # Package is in requirements.txt but is also a dependency
    )
    DUPLICATE = "duplicate"  # Package is defined multiple times
    VERSION_MISMATCH = (
        "version_mismatch"  # Installed version doesn't match requirements
    )
    NOT_INSTALLED = (
        "not_installed"  # Package is in requirements.txt but not installed
    )
    NOT_IN_REQUIREMENTS = "not_in_requirements"  # Package is installed but not in requirements.txt
    NORMAL = "normal"  # Package is properly installed and listed

    def __str__(self) -> str:
        return self.value

    @classmethod
    def get_description(cls, status: "PackageStatus") -> str:
        """Get the description for a status value"""
        descriptions = {
            cls.REDUNDANT: "Package is listed in requirements.txt but is also a dependency of another package",
            cls.DUPLICATE: "Package is defined multiple times in the same file",
            cls.VERSION_MISMATCH: "Installed package version does not match requirements",
            cls.NOT_INSTALLED: "Package is listed in requirements.txt but not installed",
            cls.NOT_IN_REQUIREMENTS: "Package is installed but not listed in requirements.txt",
            cls.NORMAL: "Package is properly installed and listed in requirements.txt",
        }
        return descriptions.get(status, "Unknown status")

    @staticmethod
    def get_priority(status: str) -> int:
        """Get priority value for status ordering (lower number = higher priority)"""
        priorities = {
            "redundant": 1,  # 冗餘（最嚴重，影響依賴結構）
            "duplicate": 2,  # 重複定義（次嚴重，可能導致版本衝突）
            "version_mismatch": 3,  # 版本不匹配（重要但不如結構性問題嚴重）
            "not_installed": 4,  # 未安裝（可以輕易修復）
            "not_in_requirements": 5,  # 未在需求文件中（次要問題）
            "normal": 6,  # 正常
        }
        return priorities.get(str(status).lower(), 99)  # 未知狀態給予最低優先級

    @classmethod
    def get_fix_order(cls) -> List["PackageStatus"]:
        """Get list of statuses in fix priority order (excluding NORMAL)"""
        # 獲取所有非 NORMAL 的狀態
        statuses = [status for status in cls if status != cls.NORMAL]
        # 根據優先級排序
        return sorted(statuses, key=lambda s: cls.get_priority(s))


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
    Stores both original name and normalized id for package identification
    """

    def __init__(self, name: str, version_spec: str, source: DependencySource):
        self.name = name  # 原始名稱（保留大小寫）
        self.id = normalize_package_name(name)  # 標準化 ID（用於比較和查找）
        self._version_spec = version_spec
        self.source = source
        self.versions: Dict[DependencySource, str] = {}
        self.extras: Optional[Set[str]] = None

    def set_version(self, version: str, source: DependencySource):
        """Set version for specific source"""
        self.versions[source] = version

    @property
    def version_spec(self) -> str:
        if self.extras:
            extras_str = f"[{','.join(sorted(self.extras))}]"
            return f"{self.name}{extras_str}{self._version_spec}"
        return self._version_spec

    @version_spec.setter
    def version_spec(self, value: str):
        self._version_spec = value

    def get_version_info(self) -> Dict[str, Dict[str, str]]:
        """
        Get version information for each source

        Returns:
            Dict with format:
            {
                "pyproject": {"constraint": ">=", "version": "1.0.0"},
                "requirements": {"constraint": "==", "version": "1.0.0"}
            }
        """
        result = {}

        for source, version in self.versions.items():
            if version:
                try:
                    constraint, _ = parse_requirement_string(version)
                    result[source.value] = {
                        "constraint": constraint,
                        "version": version,
                    }
                except ValueError:
                    result[source.value] = {
                        "constraint": "",
                        "version": version,
                    }

        return result

    def _format_version_with_source(
        self, version: str, source_tag: str, color: str
    ) -> Text:
        """Format version with colored source tag"""
        # 統一移除版本約束，只保留版本號
        for constraint in VALID_CONSTRAINTS:
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
            p_version = self._clean_version(
                self.versions.get(DependencySource.PYPROJECT)
            )
            r_version = self._clean_version(
                self.versions.get(DependencySource.REQUIREMENTS)
            )

            # Show both versions if they differ
            if p_version != r_version:
                r_text = self._format_version_with_source(
                    r_version, "r", "yellow"
                )
                p_text = self._format_version_with_source(
                    p_version, "p", "cyan"
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
        for constraint in VALID_CONSTRAINTS:
            if version.startswith(constraint):
                return version[len(constraint) :].strip()
        return version


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

    def determine_config_source(self) -> Tuple[bool, str]:
        """
        Determine which configuration file to use based on project state.

        Returns:
            Tuple[bool, str]: (use_pyproject, reason)
            - use_pyproject: True if should use pyproject.toml, False for requirements.txt
            - reason: A string explaining why this choice was made
        """
        pyproject_exists = (self.project_path / "pyproject.toml").exists()
        requirements_exists = (self.project_path / "requirements.txt").exists()

        if pyproject_exists and requirements_exists:
            return (
                True,
                "Using pyproject.toml (both files exist, preferring pyproject.toml)",
            )
        elif pyproject_exists:
            return True, "Using pyproject.toml (only pyproject.toml exists)"
        elif requirements_exists:
            return (
                False,
                "Using requirements.txt (only requirements.txt exists)",
            )
        else:
            return (
                False,
                "Using requirements.txt (no configuration files exist, will create requirements.txt)",
            )

    def clear_cache(self):
        """Clear the package and requirements cache"""
        self._packages_cache = None
        self._requirements_cache = None

    def _parse_requirements(self) -> Dict[str, DependencyInfo]:
        """
        Parse requirements.txt and pyproject.toml files and return package information
        Always keeps the last occurrence of a package when case variants exist

        Returns:
            Dictionary mapping package IDs to DependencyInfo objects
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
                                name, extras, constraint, version = (
                                    parse_requirement_string(line)
                                )
                                if name is None:
                                    continue

                                pkg_id = normalize_package_name(name)
                                spec = (
                                    f"{constraint}{version}"
                                    if constraint and version
                                    else ""
                                )

                                # 總是使用最新的名稱和版本
                                dep_info = DependencyInfo(
                                    name=name,
                                    version_spec=spec,
                                    source=DependencySource.REQUIREMENTS,
                                )
                                if extras:
                                    dep_info.extras = extras

                                # 更新或添加新的套件資訊
                                self._requirements_cache[pkg_id] = dep_info
                                if pkg_id not in sources:
                                    sources[pkg_id] = set()
                                sources[pkg_id].add(
                                    DependencySource.REQUIREMENTS
                                )
                                dep_info.set_version(
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
                                name, extras, constraint, version = (
                                    parse_requirement_string(dep)
                                )
                                if name is None:
                                    continue

                                pkg_id = normalize_package_name(name)
                                spec = (
                                    f"{constraint}{version}"
                                    if constraint and version
                                    else ""
                                )

                                if pkg_id not in sources:
                                    sources[pkg_id] = set()
                                sources[pkg_id].add(DependencySource.PYPROJECT)

                                if pkg_id not in self._requirements_cache:
                                    dep_info = DependencyInfo(
                                        name=name,
                                        version_spec=spec,
                                        source=DependencySource.PYPROJECT,
                                    )
                                    if extras:
                                        dep_info.extras = extras
                                    self._requirements_cache[pkg_id] = dep_info
                                else:
                                    # 更新現有條目的版本
                                    self._requirements_cache[
                                        pkg_id
                                    ].version_spec = spec
                                self._requirements_cache[pkg_id].set_version(
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
            for pkg_id, src_set in sources.items():
                if pkg_id in self._requirements_cache:
                    self._requirements_cache[pkg_id].source = (
                        DependencySource.combine(src_set)
                    )

        return self._requirements_cache

    def _parse_pyproject_dependencies(self) -> List[DependencyInfo]:
        """
        Parse dependencies from pyproject.toml

        Returns:
            List of DependencyInfo objects
        """
        pyproject_file = self.project_path / "pyproject.toml"
        dependencies = []

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
                            spec = str(req.specifier) if req.specifier else ""
                            dependencies.append(
                                DependencyInfo(
                                    name=name,
                                    version_spec=spec,
                                    source=DependencySource.PYPROJECT,
                                )
                            )
                        except Exception as e:
                            print(
                                f"Warning: Error processing dependency {dep}: {e}"
                            )
                            continue
            except Exception as e:
                print(f"Warning: Error reading pyproject.toml: {e}")

        return dependencies

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
        pkg_id: str,
        installed_packages: Dict,
        requirements: Dict[str, DependencyInfo],
        all_dependencies: Set[str],
    ) -> Dict:
        """Get standardized package information using package ID"""
        pkg_info = installed_packages.get(pkg_id, {})
        installed_version = pkg_info.get("installed_version")
        dep_info = requirements.get(pkg_id)

        # 使用原始名稱進行顯示，但用 ID 進行邏輯判斷
        display_name = pkg_info.get(
            "name", dep_info.name if dep_info else pkg_id
        )

        # Format required version with source indicator
        required_version = dep_info.format_version() if dep_info else None
        version_for_check = dep_info.version_spec if dep_info else ""

        # Get extras from DependencyInfo
        extras = None
        if dep_info and hasattr(dep_info, "extras"):
            extras = dep_info.extras

        is_installed = pkg_id in installed_packages

        # 檢查是否有重複定義
        duplicates = []
        if dep_info:
            # 檢查 requirements.txt
            req_file = self.project_path / "requirements.txt"
            if req_file.exists():
                versions = []
                with open(req_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            try:
                                name, _, constraint, version = (
                                    parse_requirement_string(line)
                                )
                                if (
                                    name
                                    and normalize_package_name(name) == pkg_id
                                ):
                                    versions.append(
                                        f"{constraint}{version}"
                                        if constraint and version
                                        else ""
                                    )
                            except Exception:
                                continue
                if len(versions) > 1:
                    duplicates = versions

            # 檢查 pyproject.toml
            if not duplicates:  # 如果在 requirements.txt 中沒有重複
                pyproject_file = self.project_path / "pyproject.toml"
                if pyproject_file.exists():
                    try:
                        with open(pyproject_file, "r", encoding="utf-8") as f:
                            pyproject_data = tomlkit.load(f)
                            if (
                                "project" in pyproject_data
                                and "dependencies" in pyproject_data["project"]
                            ):
                                versions = []
                                for dep in pyproject_data["project"][
                                    "dependencies"
                                ]:
                                    try:
                                        name, _, constraint, version = (
                                            parse_requirement_string(dep)
                                        )
                                        if (
                                            name
                                            and normalize_package_name(name)
                                            == pkg_id
                                        ):
                                            versions.append(
                                                f"{constraint}{version}"
                                                if constraint and version
                                                else ""
                                            )
                                    except Exception:
                                        continue
                                if len(versions) > 1:
                                    duplicates = versions
                    except Exception:
                        pass

        # Determine package status
        statuses = set()

        # Check for duplicate definitions
        if duplicates:
            statuses.add(PackageStatus.DUPLICATE)

        # Check for missing packages
        if not is_installed and pkg_id in requirements:
            statuses.add(PackageStatus.NOT_INSTALLED)

        # Check for redundant packages
        if pkg_id in all_dependencies and pkg_id in requirements:
            statuses.add(PackageStatus.REDUNDANT)

        # Check for unlisted packages
        if is_installed and pkg_id not in requirements:
            statuses.add(PackageStatus.NOT_IN_REQUIREMENTS)

        # Check for version mismatches
        if is_installed and version_for_check:
            if not self._check_version_compatibility(
                installed_version, version_for_check
            ):
                statuses.add(PackageStatus.VERSION_MISMATCH)

        # If no issues found, mark as normal
        if not statuses:
            statuses.add(PackageStatus.NORMAL)

        return {
            "name": display_name,
            "id": pkg_id,
            "installed_version": installed_version,
            "required_version": required_version,
            "extras": extras,
            "dependencies": sorted(pkg_info.get("dependencies", [])),
            "statuses": statuses,  # Return set of statuses
            "status": min(
                statuses, key=PackageStatus.get_priority
            ).value,  # For backwards compatibility
            "redundant": pkg_id in all_dependencies and pkg_id in requirements,
            "duplicates": duplicates,  # Keep duplicate version info
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

        Returns:
            Dictionary mapping package IDs to package information
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
                            normalized_id = self._normalize_package_name(
                                original_name
                            )
                            installed_version = dist.metadata["Version"]

                            if (
                                exclude_system
                                and normalized_id in system_packages
                            ):
                                continue

                            packages_info[normalized_id] = {
                                "name": original_name,
                                "id": normalized_id,  # 添加 ID 到套件信息中
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
                    all_dependencies.update(
                        self._normalize_package_name(dep)
                        for dep in pkg_info["dependencies"]
                    )

                requirements = self._parse_requirements()
                for pkg_id in list(packages_info.keys()):
                    packages_info[pkg_id] = self._get_package_info(
                        pkg_id, packages_info, requirements, all_dependencies
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

    def get_package_inconsistencies(
        self,
        installed_packages: Dict,
        requirements: Dict[str, DependencyInfo],
        use_pyproject: bool,
    ) -> Dict[PackageStatus, List[str]]:
        """
        Get all package inconsistencies grouped by their status.

        Args:
            installed_packages: Dictionary of installed packages
            requirements: Dictionary of required packages
            use_pyproject: Whether using pyproject.toml as source

        Returns:
            Dict mapping PackageStatus to list of package names
        """
        inconsistencies = {
            PackageStatus.REDUNDANT: [],
            PackageStatus.NOT_INSTALLED: [],
            PackageStatus.NOT_IN_REQUIREMENTS: [],
            PackageStatus.VERSION_MISMATCH: [],
            PackageStatus.DUPLICATE: [],  # 新增重複套件的列表
        }

        # 追蹤套件在每個文件中的出現次數
        req_duplicates: Dict[str, List[str]] = {}  # pkg_id -> [versions]
        proj_duplicates: Dict[str, List[str]] = {}  # pkg_id -> [versions]

        # Parse requirements.txt
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            with open(req_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        try:
                            name, extras, constraint, version = (
                                parse_requirement_string(line)
                            )
                            if name is None:
                                continue
                            pkg_id = normalize_package_name(name)
                            if pkg_id not in req_duplicates:
                                req_duplicates[pkg_id] = []
                            req_duplicates[pkg_id].append(
                                f"{constraint}{version}"
                                if constraint and version
                                else ""
                            )
                        except Exception:
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
                                name, extras, constraint, version = (
                                    parse_requirement_string(dep)
                                )
                                if name is None:
                                    continue
                                pkg_id = normalize_package_name(name)
                                if pkg_id not in proj_duplicates:
                                    proj_duplicates[pkg_id] = []
                                proj_duplicates[pkg_id].append(
                                    f"{constraint}{version}"
                                    if constraint and version
                                    else ""
                                )
                            except Exception:
                                continue
            except Exception:
                pass

        # 檢查重複定義
        if use_pyproject:
            duplicates = proj_duplicates
        else:
            duplicates = req_duplicates

        for pkg_id, versions in duplicates.items():
            if len(versions) > 1:
                # 找到對應的原始名稱
                dep_info = requirements.get(pkg_id)
                if dep_info:
                    inconsistencies[PackageStatus.DUPLICATE].append(
                        (dep_info.name, versions)
                    )
                    # 檢查最終版本（最後一個）是否與安裝版本相容
                    if pkg_id in installed_packages:
                        installed_version = installed_packages[pkg_id][
                            "installed_version"
                        ]
                        final_version = versions[-1]
                        if not self._check_version_compatibility(
                            installed_version, final_version
                        ):
                            # 只在這裡添加版本不符，後面的檢查會跳過已經處理過的重複定義套件
                            inconsistencies[
                                PackageStatus.VERSION_MISMATCH
                            ].append((dep_info.name, final_version))

        # 收集所有依賴關係（包含子依賴和孫依賴），使用標準化的 ID
        all_dependencies_ids = set()
        for pkg_info in installed_packages.values():
            deps = pkg_info.get("dependencies", [])
            # 標準化所有依賴的 ID
            deps_ids = {self._normalize_package_name(dep) for dep in deps}
            all_dependencies_ids.update(deps_ids)
            # 遞迴收集子依賴的依賴
            for dep in deps:
                dep_id = self._normalize_package_name(dep)
                if dep_id in installed_packages:
                    subdeps = installed_packages[dep_id].get("dependencies", [])
                    all_dependencies_ids.update(
                        self._normalize_package_name(subdep)
                        for subdep in subdeps
                    )

        # 先檢查冗餘套件，使用標準化的 ID 進行比較
        for pkg_id, dep_info in requirements.items():
            normalized_id = self._normalize_package_name(dep_info.name)
            if normalized_id in all_dependencies_ids:
                # 使用原始名稱添加到結果中
                inconsistencies[PackageStatus.REDUNDANT].append(dep_info.name)

        # 檢查 requirements 中的套件
        for pkg_id, dep_info in requirements.items():
            normalized_id = self._normalize_package_name(dep_info.name)
            # 如果是冗餘套件，跳過其他檢查
            if dep_info.name in inconsistencies[PackageStatus.REDUNDANT]:
                continue

            # 檢查是否已安裝，使用標準化的 ID 進行比較
            if normalized_id not in installed_packages:
                inconsistencies[PackageStatus.NOT_INSTALLED].append(
                    dep_info.name
                )
                continue

            # 檢查版本是否匹配（跳過已經處理過的重複定義套件）
            if normalized_id not in duplicates:
                installed_version = installed_packages[normalized_id][
                    "installed_version"
                ]

                # 根據來源選擇正確的版本規範
                if use_pyproject:
                    # 如果使用 pyproject.toml，優先使用其版本規範
                    version_for_check = dep_info.versions.get(
                        DependencySource.PYPROJECT, ""
                    )
                    # 如果套件不在 pyproject.toml 中，才使用 requirements.txt 的版本
                    if not version_for_check:
                        version_for_check = dep_info.versions.get(
                            DependencySource.REQUIREMENTS, ""
                        )
                else:
                    # 如果使用 requirements.txt，使用其版本規範
                    version_for_check = dep_info.versions.get(
                        DependencySource.REQUIREMENTS, ""
                    )

                if version_for_check and not self._check_version_compatibility(
                    installed_version, version_for_check
                ):
                    # 將版本規範資訊一併儲存，以便後續顯示
                    inconsistencies[PackageStatus.VERSION_MISMATCH].append(
                        (dep_info.name, version_for_check)
                    )

        # 檢查已安裝但不在 requirements 中的套件
        for pkg_id, pkg_info in installed_packages.items():
            normalized_id = self._normalize_package_name(pkg_id)
            # 檢查是否在 requirements 中（使用標準化的 ID）
            if not any(
                self._normalize_package_name(req.name) == normalized_id
                for req in requirements.values()
            ):
                # 檢查是否是其他套件的依賴
                if normalized_id not in all_dependencies_ids:
                    inconsistencies[PackageStatus.NOT_IN_REQUIREMENTS].append(
                        pkg_info.get("name", pkg_id)
                    )

        # 對每個列表進行排序以保持穩定的輸出順序
        for status in inconsistencies:
            if (
                status == PackageStatus.VERSION_MISMATCH
                or status == PackageStatus.DUPLICATE
            ):
                # 對於包含元組的列表，使用第一個元素（套件名稱）進行排序
                inconsistencies[status].sort(key=lambda x: x[0].lower())
            else:
                # 對於純字符串列表，直接使用小寫進行排序
                inconsistencies[status].sort(key=str.lower)

        return inconsistencies
