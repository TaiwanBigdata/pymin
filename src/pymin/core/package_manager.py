"""Package management for virtual environments"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from ..ui.console import progress_status, print_error, console, print_warning
from rich.text import Text
from rich.tree import Tree
from rich.style import Style
from .package_analyzer import PackageAnalyzer
from packaging import version
import re
import requests


class PackageManager:
    """Package management for virtual environments"""

    def __init__(self, venv_path: Path):
        """Initialize package manager

        Args:
            venv_path: Path to the virtual environment
        """
        self.venv_path = venv_path
        self.requirements_path = Path("requirements.txt")
        self._pip_path = self._get_pip_path()

        # Initialize package analyzer with project root directory
        self.package_analyzer = PackageAnalyzer()

    def _check_pip_upgrade(self, stderr: str) -> None:
        """Check if pip needs upgrade and handle it

        Args:
            stderr: Error output from pip
        """
        if "new version of pip available" in stderr.lower():
            try:
                # Get current and latest version
                current_version = None
                latest_version = None
                for line in stderr.split("\n"):
                    if "new release" in line.lower():
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == "->":
                                current_version = parts[i - 1]
                                latest_version = parts[i + 1]
                                break

                if current_version and latest_version:
                    console.print(
                        f"[yellow]⚠ A new version of pip is available: {current_version} -> {latest_version}[/yellow]"
                    )
                    console.print(
                        "[dim]To update, run: pip install --upgrade pip[/dim]"
                    )
            except Exception:
                pass

    def _build_dependency_tree(
        self,
        name: str,
        version: str,
        deps: List[str],
        visited: Optional[Set[str]] = None,
    ) -> Tree:
        """Build a rich Tree structure for package dependencies"""
        if visited is None:
            visited = set()

        # Create tree node
        tree = Tree(
            Text.assemble(
                (name, "cyan"),
                ("==", "dim"),
                (version, "cyan"),
            )
        )

        # Add dependencies
        if deps:
            visited.add(name)
            for dep in sorted(deps):
                if dep not in visited:
                    dep_version = self._get_installed_version(dep)
                    dep_deps = self._check_dependencies(dep)
                    dep_tree = self._build_dependency_tree(
                        dep, dep_version, dep_deps, visited
                    )
                    tree.add(dep_tree)

        return tree

    def _update_dependency_files(
        self, *, added: List[str] = None, removed: List[str] = None
    ) -> None:
        """Update all dependency files (requirements.txt and pyproject.toml)

        Args:
            added: List of packages that were added
            removed: List of packages that were removed
        """
        # Update requirements.txt
        if added:
            self._update_requirements(added=added)
        if removed:
            self._update_requirements(removed=removed)

        # Update pyproject.toml if exists
        pyproject_path = Path("pyproject.toml")
        if pyproject_path.exists():
            from .pyproject_manager import PyProjectManager

            proj_manager = PyProjectManager(pyproject_path)

            if added:
                for pkg_spec in added:
                    try:
                        # Parse package spec (e.g., "package==1.0.0" or "package")
                        if "==" in pkg_spec:
                            pkg_name, version = pkg_spec.split("==")
                        else:
                            pkg_name = pkg_spec
                            # Get installed version
                            version = self._get_installed_version(pkg_name)

                        if version:
                            proj_manager.add_dependency(pkg_name, version, ">=")
                    except Exception as e:
                        print_warning(
                            f"Warning: Failed to add {pkg_name} to pyproject.toml: {str(e)}"
                        )

            if removed:
                for pkg_name in removed:
                    try:
                        proj_manager.remove_dependency(pkg_name)
                    except Exception as e:
                        print_warning(
                            f"Warning: Failed to remove {pkg_name} from pyproject.toml: {str(e)}"
                        )

    def add_packages(
        self,
        packages: List[str],
        *,
        dev: bool = False,
        editable: bool = False,
        no_deps: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        """Add packages to the virtual environment

        Args:
            packages: List of packages to add
            dev: Whether to install as development dependency
            editable: Whether to install in editable mode
            no_deps: Whether to skip installing package dependencies

        Returns:
            Dict with installation results for each package
        """
        results = {}
        successfully_added = []

        # Parse package specifications
        package_specs = [self._parse_package_spec(pkg) for pkg in packages]

        for pkg_name, pkg_version in package_specs:
            try:
                # Install package
                cmd = [str(self._pip_path), "install"]
                if editable:
                    cmd.append("-e")
                if no_deps:
                    cmd.append("--no-deps")

                # Construct package spec
                pkg_spec = (
                    f"{pkg_name}=={pkg_version}" if pkg_version else pkg_name
                )
                cmd.append(pkg_spec)

                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                if process.returncode == 0:
                    # Get installed version and dependencies
                    self.package_analyzer.clear_cache()
                    packages_after = (
                        self.package_analyzer.get_installed_packages()
                    )

                    # Try to find the package with case-insensitive matching
                    pkg_name_lower = pkg_name.lower()
                    matching_pkg = None
                    for installed_pkg, info in packages_after.items():
                        if installed_pkg.lower() == pkg_name_lower:
                            matching_pkg = installed_pkg
                            pkg_info = info
                            break

                    if matching_pkg:
                        version = pkg_info["installed_version"]
                        successfully_added.append(f"{matching_pkg}=={version}")
                        results[matching_pkg] = {
                            "status": "installed",
                            "version": version,
                            "dependencies": sorted(pkg_info["dependencies"]),
                            "new_dependencies": sorted(
                                pkg_info["dependencies"]
                            ),
                        }
                else:
                    # Extract version information from pip's error output
                    error_output = (
                        process.stderr if process.stderr else "Unknown error"
                    )
                    version_info = {}

                    # Try to get available versions from error message
                    if (
                        "Could not find a version that satisfies the requirement"
                        in error_output
                    ):
                        try:
                            # Extract versions from error message
                            versions = []
                            for line in error_output.split("\n"):
                                if "from versions:" in line:
                                    versions_str = line.split(
                                        "from versions:", 1
                                    )[1].strip()
                                    versions = [
                                        v.strip()
                                        for v in versions_str.strip("()").split(
                                            ","
                                        )
                                    ]
                                    break

                            if versions:
                                version_info["latest_versions"] = ", ".join(
                                    f"[cyan]{v}[/cyan]"
                                    for v in versions[-3:][::-1]
                                )
                                version_info["similar_versions"] = ", ".join(
                                    f"[cyan]{v}[/cyan]"
                                    for v in versions[-6:-3][::-1]
                                )
                        except Exception:
                            # If parsing fails, try to get from PyPI
                            try:
                                response = requests.get(
                                    f"https://pypi.org/pypi/{pkg_name}/json"
                                )
                                if response.status_code == 200:
                                    data = response.json()
                                    versions = sorted(
                                        data["releases"].keys(), reverse=True
                                    )
                                    version_info["latest_versions"] = ", ".join(
                                        f"[cyan]{v}[/cyan]"
                                        for v in versions[:3]
                                    )
                                    version_info["similar_versions"] = (
                                        ", ".join(
                                            f"[cyan]{v}[/cyan]"
                                            for v in versions[3:6]
                                        )
                                    )
                            except Exception:
                                pass

                    results[pkg_name] = {
                        "status": "error",
                        "message": error_output,
                        "version_info": version_info,
                    }
            except Exception as e:
                results[pkg_name] = {
                    "status": "error",
                    "message": str(e),
                }

        # Update dependency files only after successful installations
        if successfully_added:
            self._update_dependency_files(added=successfully_added)

        return results

    def remove_packages(
        self,
        packages: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """Remove packages from the virtual environment

        Args:
            packages: List of packages to remove

        Returns:
            Dict with removal results for each package
        """
        results = {}
        successfully_removed = []

        for pkg in packages:
            try:
                # Get version before uninstalling
                version = self._get_installed_version(pkg)
                if not version:
                    results[pkg] = {
                        "status": "not_found",
                        "message": "Package not installed",
                    }
                    continue

                # Uninstall package
                cmd = [str(self._pip_path), "uninstall", "-y", pkg]
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                if process.returncode == 0:
                    successfully_removed.append(pkg)
                    results[pkg] = {
                        "status": "removed",
                        "version": version,  # Use the version we got earlier
                    }
                else:
                    results[pkg] = {
                        "status": "error",
                        "message": (
                            process.stderr
                            if process.stderr
                            else "Unknown error"
                        ),
                    }
            except Exception as e:
                results[pkg] = {
                    "status": "error",
                    "message": str(e),
                }

        # Update dependency files only after successful removals
        if successfully_removed:
            self._update_dependency_files(removed=successfully_removed)

        return results

    def _parse_package_spec(self, spec: str) -> Tuple[str, Optional[str]]:
        """Parse package specification into name and version"""
        if "==" in spec:
            name, version = spec.split("==")
            return name.strip(), version.strip()
        return spec.strip(), None

    def _get_installed_packages(self) -> Dict[str, Dict[str, Any]]:
        """Get installed packages and their information

        Returns:
            Dict mapping package names to their information
        """
        return self.package_analyzer.get_installed_packages()

    def _get_all_dependencies(self) -> Dict[str, Set[str]]:
        """Get all packages and their dependents

        Returns:
            Dict mapping package names to sets of packages that depend on them
        """
        packages = self._get_installed_packages()
        dependents = {}

        # Build dependency map
        for pkg_name, pkg_info in packages.items():
            for dep in pkg_info["dependencies"]:
                if dep not in dependents:
                    dependents[dep] = set()
                dependents[dep].add(pkg_name)

        return dependents

    def _get_installed_version(self, package: str) -> Optional[str]:
        """Get installed version of a package

        Args:
            package: Package name

        Returns:
            Version string if installed, None otherwise
        """
        packages = self.package_analyzer.get_installed_packages()
        if package in packages:
            return packages[package]["installed_version"]
        return None

    def _check_conflicts(
        self,
        package_specs: List[Tuple[str, Optional[str]]],
        existing: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Check for version conflicts"""
        conflicts = []
        for name, version in package_specs:
            if name in existing and version and existing[name] != version:
                conflicts.append(
                    {
                        "package": name,
                        "requested": version,
                        "installed": existing[name],
                    }
                )
        return conflicts

    def _check_dependencies(self, package: str) -> List[str]:
        """Get dependencies of a package

        Args:
            package: Package name

        Returns:
            List of dependency names
        """
        packages = self.package_analyzer.get_installed_packages()
        if package in packages:
            return packages[package]["dependencies"]
        return []

    def _is_dependency(self, package: str) -> Tuple[bool, List[str]]:
        """Check if package is a dependency of other packages

        Args:
            package: Package name to check

        Returns:
            Tuple of (is_dependency, list_of_dependent_packages)
        """
        packages = self.package_analyzer.get_installed_packages()
        dependents = []

        for pkg_name, pkg_info in packages.items():
            if pkg_name != package and package in pkg_info["dependencies"]:
                dependents.append(pkg_name)

        return bool(dependents), dependents

    def _update_requirements(
        self,
        added: Optional[List[str]] = None,
        removed: Optional[List[str]] = None,
        dev: bool = False,
    ) -> None:
        """Update requirements.txt file"""
        try:
            # Read existing requirements
            requirements = []
            if self.requirements_path.exists():
                with open(self.requirements_path) as f:
                    requirements = [line.strip() for line in f if line.strip()]

            # Remove packages
            if removed:
                requirements = [
                    r
                    for r in requirements
                    if not any(r.startswith(f"{pkg}==") for pkg in removed)
                ]

            # Add packages
            if added:
                # First remove any existing versions of the packages we're adding
                for pkg_spec in added:
                    pkg_name = pkg_spec.split("==")[0]
                    requirements = [
                        r
                        for r in requirements
                        if not r.startswith(f"{pkg_name}==")
                    ]
                # Then add the new versions
                requirements.extend(added)

            # Write back
            with open(self.requirements_path, "w") as f:
                f.write("\n".join(sorted(requirements)) + "\n")
        except Exception as e:
            raise RuntimeError(f"Failed to update requirements.txt: {str(e)}")

    def _get_pip_path(self) -> Path:
        """Get path to pip executable"""
        if sys.platform == "win32":
            pip_path = self.venv_path / "Scripts" / "pip.exe"
        else:
            pip_path = self.venv_path / "bin" / "pip"

        if not pip_path.exists():
            raise RuntimeError(f"pip not found at {pip_path}")

        return pip_path

    def _get_pip_versions(
        self, stderr: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Extract current and latest pip versions from stderr"""
        current_version = None
        latest_version = None
        for line in stderr.split("\n"):
            if "new release" in line.lower():
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "->":
                        current_version = parts[i - 1]
                        latest_version = parts[i + 1]
                        break
        return current_version, latest_version

    def auto_fix_install(
        self,
        package_name: str,
        version: Optional[str] = None,
        *,
        dev: bool = False,
        editable: bool = False,
        no_deps: bool = False,
    ) -> Dict[str, Any]:
        """
        Install a package with automatic version fixing if needed.

        Args:
            package_name: Name of the package to install
            version: Optional version specification
            dev: Whether to install as development dependency
            editable: Whether to install in editable mode
            no_deps: Whether to skip installing package dependencies

        Returns:
            Dict containing installation results with status and additional info
        """
        # 清理並格式化版本字符串
        if version:
            version = str(version).strip()
            # 如果版本字符串不包含版本約束符號，添加 ==
            if not any(
                version.startswith(op)
                for op in [">=", "<=", "!=", "~=", ">", "<", "=="]
            ):
                version = version.lstrip("=").strip()
                package_spec = f"{package_name}=={version}"
            else:
                package_spec = f"{package_name}{version}"
        else:
            package_spec = package_name

        # 嘗試安裝
        results = self.add_packages(
            [package_spec],
            dev=dev,
            editable=editable,
            no_deps=no_deps,
        )

        pkg_info = results.get(package_name, {})

        # 如果安裝失敗，檢查是否需要自動修復
        if pkg_info.get("status") != "installed":
            error_msg = pkg_info.get("message", "")
            version_info = pkg_info.get("version_info", {})

            # 檢查是否為版本相關錯誤
            if (
                "Version not found" in error_msg
                or "No matching distribution" in error_msg
                or "Could not find a version that satisfies the requirement"
                in error_msg
            ) and version_info:
                # 獲取最新版本
                latest_version = (
                    version_info["latest_versions"]
                    .split(",")[0]
                    .strip()
                    .replace("[cyan]", "")
                    .replace("[/cyan]", "")
                    .replace(" (latest)", "")
                )

                # 分析更新原因
                if (
                    "Python version" in error_msg
                    or "requires Python" in error_msg
                ):
                    update_reason = "Python compatibility issue"
                elif "dependency conflict" in error_msg:
                    update_reason = "Dependency conflict"
                elif (
                    "not found" in error_msg
                    or "No matching distribution" in error_msg
                ):
                    update_reason = "Version not found"
                else:
                    update_reason = "Installation failed"

                # 使用最新版本重試
                retry_results = self.add_packages(
                    [f"{package_name}=={latest_version}"],
                    dev=dev,
                    editable=editable,
                    no_deps=no_deps,
                )

                retry_info = retry_results.get(package_name, {})
                if retry_info.get("status") == "installed":
                    retry_info["auto_fixed"] = True
                    retry_info["original_version"] = version
                    retry_info["update_reason"] = update_reason
                    retry_info["installed_version"] = latest_version
                    return retry_info

                # 如果重試也失敗，返回重試的錯誤信息
                return retry_info

        return pkg_info


def _get_pre_release_type_value(pre_type: str) -> int:
    """Get numeric value for pre-release type for ordering"""
    pre_type_order = {"a": 0, "b": 1, "rc": 2}
    return pre_type_order.get(pre_type, 3)


def get_version_distance(ver_str: str, target_str: str) -> float:
    """Calculate distance between two version strings with improved handling of pre-releases"""
    # Parse versions using packaging.version
    ver = version.parse(ver_str)
    target = version.parse(target_str)

    # Get release components
    ver_release = ver.release
    target_release = target.release

    # Pad with zeros to make same length
    max_len = max(len(ver_release), len(target_release))
    ver_parts = list(ver_release) + [0] * (max_len - len(ver_release))
    target_parts = list(target_release) + [0] * (max_len - len(target_release))

    # Calculate weighted distance for release parts
    distance = 0
    for i, (a, b) in enumerate(zip(ver_parts, target_parts)):
        weight = 10 ** (max_len - i - 1)
        distance += abs(a - b) * weight

    # Add pre-release penalty
    pre_release_penalty = 0
    if ver.is_prerelease or target.is_prerelease:
        # Penalize pre-releases but still keep them close to their release version
        pre_release_penalty = 0.5

        # If both are pre-releases, reduce penalty and compare their order
        if ver.is_prerelease and target.is_prerelease:
            pre_release_penalty = 0.25
            # Compare pre-release parts
            if ver.pre and target.pre:
                pre_type_diff = abs(
                    _get_pre_release_type_value(ver.pre[0])
                    - _get_pre_release_type_value(target.pre[0])
                )
                pre_num_diff = abs(ver.pre[1] - target.pre[1])
                pre_release_penalty += (
                    pre_type_diff + pre_num_diff * 0.1
                ) * 0.25

    return distance + pre_release_penalty
