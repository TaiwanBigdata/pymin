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
from .version_utils import normalize_package_name, parse_requirement_string
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
        package_specs = [parse_requirement_string(pkg) for pkg in packages]

        for pkg_name, pkg_extras, pkg_constraint, pkg_version in package_specs:
            try:
                # Install package
                cmd = [str(self._pip_path), "install"]
                if editable:
                    cmd.append("-e")
                if no_deps:
                    cmd.append("--no-deps")

                # Construct package spec with extras if present
                if pkg_extras:
                    extras_str = f"[{','.join(sorted(pkg_extras))}]"
                    pkg_spec = f"{pkg_name}{extras_str}"
                else:
                    pkg_spec = pkg_name

                if pkg_version:
                    pkg_spec = f"{pkg_spec}=={pkg_version}"

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

    def get_packages_to_remove(self, package_names: List[str]) -> Set[str]:
        """
        取得可以安全移除的套件集合。
        一個套件可以被移除，如果它只被目標套件所依賴。

        Args:
            package_names: 要移除的套件名稱列表

        Returns:
            可以安全移除的套件名稱集合
        """
        # 初始化集合
        packages_to_remove = set(package_names)
        checked_packages = set()
        dependency_tree = self.package_analyzer.get_dependency_tree()

        def build_dependency_maps() -> (
            Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]
        ):
            """
            建立兩個映射：
            1. used_by_map: 誰使用了這個套件 (反向依賴)
            2. depends_on_map: 這個套件依賴哪些套件 (正向依賴)
            """
            used_by_map = {}  # pkg -> set of pkgs that use it
            depends_on_map = {}  # pkg -> set of pkgs it depends on
            visited = set()  # 用來追蹤已處理的套件

            def build_maps(
                pkg_name: str, deps_info: Dict, chain: Set[str] = None
            ):
                if chain is None:
                    chain = set()
                if pkg_name in chain:  # 避免循環依賴
                    return
                if pkg_name in visited:  # 避免重複處理
                    return

                chain.add(pkg_name)
                visited.add(pkg_name)  # 標記為已處理

                deps = deps_info.get("dependencies", {})
                for dep_name, dep_info in deps.items():
                    # 記錄誰使用了這個依賴
                    if dep_name not in used_by_map:
                        used_by_map[dep_name] = set()
                    used_by_map[dep_name].add(pkg_name)

                    # 記錄這個套件依賴誰
                    if pkg_name not in depends_on_map:
                        depends_on_map[pkg_name] = set()
                    depends_on_map[pkg_name].add(dep_name)

                    # 遞迴處理這個依賴的依賴
                    if dep_name not in visited:
                        build_maps(
                            dep_name, dep_info, chain.copy()
                        )  # 使用 chain 的副本

                chain.remove(pkg_name)  # 移除當前套件,回溯時使用

            # 從頂層套件開始建立映射
            for pkg_name, pkg_info in dependency_tree.items():
                if pkg_name not in visited:
                    build_maps(pkg_name, pkg_info, set())

            return used_by_map, depends_on_map

        def is_safe_to_remove(
            pkg: str, used_by_map: Dict[str, Set[str]], chain: Set[str] = None
        ) -> bool:
            """
            判斷一個套件是否可以安全移除：
            1. 如果沒有人使用它，可以移除
            2. 如果使用它的套件都在移除列表中，可以移除
            """
            if chain is None:
                chain = set()

            # 避免循環依賴
            if pkg in chain:
                return False

            # 取得所有使用這個套件的套件
            users = used_by_map.get(pkg, set())

            # 如果沒有人使用，可以移除
            if not users:
                return True

            # 檢查所有使用者是否都在移除列表中或可以被移除
            chain.add(pkg)
            for user in users:
                if user not in packages_to_remove and user not in chain:
                    if not is_safe_to_remove(user, used_by_map, chain):
                        chain.remove(pkg)
                        return False
            chain.remove(pkg)

            return True

        def get_all_dependencies(
            pkg: str, deps_map: Dict[str, Set[str]], visited: Set[str] = None
        ) -> Set[str]:
            """
            取得一個套件的所有依賴（包含間接依賴）
            """
            if visited is None:
                visited = set()
            if pkg in visited:
                return set()

            visited.add(pkg)
            deps = deps_map.get(pkg, set())
            all_deps = deps.copy()

            for dep in deps:
                if dep not in visited:
                    all_deps.update(
                        get_all_dependencies(dep, deps_map, visited)
                    )

            return all_deps

        # 建立依賴映射
        used_by_map, depends_on_map = build_dependency_maps()

        # 檢查每個要移除的套件
        for pkg in package_names:
            if pkg not in checked_packages:
                # 檢查這個套件是否可以安全移除
                if is_safe_to_remove(pkg, used_by_map):
                    # 取得這個套件的所有依賴
                    deps = get_all_dependencies(pkg, depends_on_map)
                    # 檢查每個依賴是否也可以安全移除
                    for dep in deps:
                        if is_safe_to_remove(dep, used_by_map):
                            packages_to_remove.add(dep)
                checked_packages.add(pkg)

        return packages_to_remove

    def remove_packages(
        self,
        packages: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        移除套件及其不再需要的依賴

        Args:
            packages: 要移除的套件列表

        Returns:
            移除結果的字典
        """
        results = {}
        dependency_tree = self.package_analyzer.get_dependency_tree()

        # 取得所有可以安全移除的套件
        packages_to_remove = self.get_packages_to_remove(packages)

        # 對於每個要移除的套件
        for pkg_name in packages:
            pkg_info = dependency_tree.get(pkg_name, {})
            if not pkg_info:
                results[pkg_name] = {
                    "status": "not_found",
                    "message": f"Package {pkg_name} is not installed",
                }
                continue

            try:
                # 執行 pip uninstall
                process = subprocess.run(
                    [str(self._pip_path), "uninstall", "-y", pkg_name],
                    capture_output=True,
                    text=True,
                )

                if process.returncode == 0:
                    # 收集依賴資訊
                    removable_deps = set()
                    kept_deps = {}

                    # 檢查每個依賴
                    for dep_name, dep_info in pkg_info.get(
                        "dependencies", {}
                    ).items():
                        if dep_name in packages_to_remove:
                            removable_deps.add(dep_name)
                        else:
                            # 找出為什麼這個依賴被保留
                            kept_for = set()
                            for top_pkg, top_info in dependency_tree.items():
                                if top_pkg == pkg_name:
                                    continue

                                def find_dep_in_tree(deps_info: Dict) -> bool:
                                    if not deps_info:
                                        return False
                                    if dep_name in deps_info.get(
                                        "dependencies", {}
                                    ):
                                        return True
                                    for d_info in deps_info.get(
                                        "dependencies", {}
                                    ).values():
                                        if find_dep_in_tree(d_info):
                                            return True
                                    return False

                                if find_dep_in_tree(top_info):
                                    kept_for.add(top_pkg)

                            if kept_for:
                                kept_deps[dep_name] = {
                                    "kept_for": sorted(kept_for)
                                }

                    results[pkg_name] = {
                        "status": "removed",
                        "version": pkg_info.get("installed_version"),
                        "dependency_info": {
                            "removable_deps": removable_deps,
                            "kept_deps": kept_deps,
                        },
                    }

                    # 移除可移除的依賴
                    for dep in removable_deps:
                        if dep not in results:  # 避免重複移除
                            try:
                                subprocess.run(
                                    [
                                        str(self._pip_path),
                                        "uninstall",
                                        "-y",
                                        dep,
                                    ],
                                    capture_output=True,
                                    text=True,
                                )
                            except Exception as e:
                                print(
                                    f"Warning: Failed to remove dependency {dep}: {str(e)}"
                                )

                else:
                    results[pkg_name] = {
                        "status": "error",
                        "message": process.stderr,
                    }

            except Exception as e:
                results[pkg_name] = {
                    "status": "error",
                    "message": str(e),
                }

        # 更新 requirements.txt
        self._update_requirements(removed=list(packages_to_remove))

        return results

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
                    if not any(
                        normalize_package_name(r.split("==")[0])
                        == normalize_package_name(pkg)
                        for pkg in removed
                    )
                ]

            # Add packages
            if added:
                # 先移除要新增的套件的舊版本（使用正規化名稱比較）
                for pkg_spec in added:
                    pkg_name = pkg_spec.split("==")[0]
                    normalized_name = normalize_package_name(pkg_name)
                    requirements = [
                        r
                        for r in requirements
                        if normalize_package_name(r.split("==")[0])
                        != normalized_name
                    ]

                # 取得已安裝套件的原始名稱
                installed_packages = (
                    self.package_analyzer.get_installed_packages()
                )
                new_requirements = []

                for pkg_spec in added:
                    pkg_name, version = pkg_spec.split("==")
                    normalized_name = normalize_package_name(pkg_name)

                    # 如果套件已安裝，使用其原始名稱
                    if normalized_name in installed_packages:
                        original_name = installed_packages[normalized_name][
                            "name"
                        ]
                        new_requirements.append(f"{original_name}=={version}")
                    else:
                        # 如果尚未安裝，使用提供的名稱
                        new_requirements.append(pkg_spec)

                # 加入新的套件規格（使用原始名稱）
                requirements.extend(new_requirements)

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
