"""Fix package inconsistencies command"""

import click
from typing import Dict, List, Set, Tuple
from rich.prompt import Confirm
from ...core.venv_manager import VenvManager
from ...core.package_analyzer import (
    PackageAnalyzer,
    DependencySource,
    DependencyInfo,
)
from ...ui.console import (
    print_error,
    print_warning,
    print_success,
    console,
    progress_status,
    create_summary_panel,
)
from ...ui.style import SymbolType
from rich.text import Text
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from pathlib import Path

# Create package analyzer instance
pkg_analyzer = PackageAnalyzer()


@click.command()
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Automatically confirm all fixes",
)
@click.option(
    "-p",
    "--pyproject",
    "use_pyproject",
    is_flag=True,
    help="Use pyproject.toml instead of requirements.txt",
)
def fix(yes: bool = False, use_pyproject: bool = False):
    """Fix package inconsistencies"""
    try:
        manager = VenvManager()

        # Check if we're in a virtual environment
        if not manager.from_env:
            print_error(
                "No virtual environment is active. Use 'pmm on' to activate one."
            )
            return

        # If using pyproject.toml, validate it exists
        if use_pyproject:
            pyproject_path = Path("pyproject.toml")
            if not pyproject_path.exists():
                print_error("No pyproject.toml found in current directory")
                return

        # Get package information
        with progress_status("Analyzing packages..."):
            installed_packages = pkg_analyzer.get_installed_packages()
            top_level_packages = pkg_analyzer.get_top_level_packages()
            requirements = pkg_analyzer._parse_requirements()

        if not installed_packages and not requirements:
            print_warning("No packages found to analyze")
            return

        # Find issues to fix
        issues_found = False
        packages_to_update: List[Tuple[str, str, str]] = (
            []
        )  # name, current, required
        packages_to_install: List[str] = []  # name
        redundant_packages: List[str] = []  # name
        not_in_requirements: List[Tuple[str, str, str]] = (
            []
        )  # name, version, missing_from

        # Check packages installed but not in requirements (only top-level)
        for pkg_name, pkg_info in top_level_packages.items():
            if pkg_info["status"] == "not_in_requirements":
                # 檢查套件是否在 requirements.txt 和 pyproject.toml 中
                in_requirements = pkg_name in requirements
                has_pyproject = Path("pyproject.toml").exists()
                in_pyproject = has_pyproject and any(
                    dep.name == pkg_name
                    for dep in pkg_analyzer._parse_pyproject_dependencies()
                )

                # 根據使用的文件和存在狀況決定顯示訊息
                if use_pyproject:
                    if not in_pyproject:
                        missing_from = (
                            "both files"
                            if not in_requirements
                            else "pyproject.toml"
                        )
                        not_in_requirements.append(
                            (
                                pkg_name,
                                pkg_info["installed_version"],
                                missing_from,
                            )
                        )
                        issues_found = True
                else:
                    if not in_requirements:
                        missing_from = (
                            "both files"
                            if has_pyproject and not in_pyproject
                            else "requirements.txt"
                        )
                        not_in_requirements.append(
                            (
                                pkg_name,
                                pkg_info["installed_version"],
                                missing_from,
                            )
                        )
                        issues_found = True

        # Check version mismatches and missing packages
        for pkg_name, req_version in requirements.items():
            if pkg_name not in installed_packages:
                packages_to_install.append(pkg_name)
                issues_found = True
            else:
                installed_version = installed_packages[pkg_name][
                    "installed_version"
                ]
                # 處理 DependencyInfo 對象的版本比較
                if hasattr(req_version, "version_spec"):
                    required_clean = req_version.version_spec
                elif isinstance(req_version, Text):
                    required_clean = str(req_version)
                else:
                    required_clean = req_version.lstrip("=")

                # 檢查版本是否滿足要求
                def is_version_satisfied(
                    current: str, requirement: str
                ) -> bool:
                    # 如果要求是 >=x.x.x 格式，檢查當前版本是否大於等於要求版本
                    if requirement.startswith(">="):
                        spec = SpecifierSet(requirement)
                        return Version(current) in spec
                    # 如果要求是 ==x.x.x 格式，直接比較版本號
                    elif requirement.startswith("==") or not any(
                        requirement.startswith(op)
                        for op in [">=", "<=", "!=", "~=", ">", "<"]
                    ):
                        req_version = requirement.lstrip("=").strip()
                        return current.strip() == req_version
                    return False

                if not is_version_satisfied(installed_version, required_clean):
                    packages_to_update.append(
                        (pkg_name, installed_version, required_clean)
                    )
                    issues_found = True

        # Check redundant packages
        all_dependencies = set()
        for pkg_info in installed_packages.values():
            deps = pkg_info.get("dependencies", [])
            all_dependencies.update(deps)

        # 檢查 requirements 中的套件是否為其他套件的依賴
        for pkg_name, dep_info in requirements.items():
            if pkg_name in all_dependencies:
                # 檢查套件來源
                if isinstance(dep_info, DependencyInfo):
                    if use_pyproject:
                        # 使用 pyproject.toml 時，只檢查來自 pyproject.toml 的套件
                        if dep_info.source in [
                            DependencySource.PYPROJECT,
                            DependencySource.BOTH,
                        ]:
                            redundant_packages.append(pkg_name)
                            issues_found = True
                    else:
                        # 使用 requirements.txt 時，只檢查來自 requirements.txt 的套件
                        if dep_info.source in [
                            DependencySource.REQUIREMENTS,
                            DependencySource.BOTH,
                        ]:
                            redundant_packages.append(pkg_name)
                            issues_found = True
                else:
                    # 如果 dep_info 不是 DependencyInfo 對象，使用舊的邏輯
                    redundant_packages.append(pkg_name)
                    issues_found = True

        # 保存 pyproject.toml 的路徑
        pyproject_path = pkg_analyzer.project_path / "pyproject.toml"

        if not issues_found:
            print_success("No package inconsistencies found!")
            return

        # Display issues
        console.print("\n[cyan]Package Issues Found:[/cyan]")

        if packages_to_update:
            console.print("\n[yellow]Version Mismatches:[/yellow]")
            for name, current, required in packages_to_update:
                console.print(
                    f"  • [cyan]{name}[/cyan]: [yellow]{current}[/yellow] → [green]{required}[/green]"
                )

        if packages_to_install:
            console.print("\n[yellow]Missing Packages:[/yellow]")
            for name in packages_to_install:
                version = requirements.get(name, "")
                # 處理 DependencyInfo 對象的版本顯示
                if hasattr(version, "version_spec"):
                    version_display = version.version_spec
                elif isinstance(version, Text):
                    version_display = str(version)
                else:
                    version_display = version
                console.print(f"  • [cyan]{name}[/cyan] ({version_display})")

        if not_in_requirements:
            console.print("\n[yellow]Not in Requirements:[/yellow]")
            for name, version, missing_from in not_in_requirements:
                console.print(
                    f"  • [cyan]{name}[/cyan] ({version}) [dim](missing from {missing_from})[/dim]"
                )

        if redundant_packages:
            console.print("\n[yellow]Redundant Packages:[/yellow]")
            for name in redundant_packages:
                console.print(
                    f"  • [cyan]{name}[/cyan] (listed in requirements but also a dependency)"
                )

        # Confirm fixes
        console.print()
        if not yes and not Confirm.ask("Do you want to fix these issues?"):
            return

        # Apply fixes
        fixed_count = 0
        error_count = 0

        # Fix version mismatches
        if packages_to_update:
            with progress_status("Updating package versions..."):
                for name, _, required in packages_to_update:
                    try:
                        # 清理版本字符串，移除前導的版本約束符號
                        version_clean = str(required).lstrip("=")
                        if not any(
                            version_clean.startswith(op)
                            for op in [">=", "<=", "!=", "~=", ">", "<", "=="]
                        ):
                            version_clean = version_clean.strip()

                        # 使用自動修復安裝
                        pkg_info = manager.package_manager.auto_fix_install(
                            name, version_clean
                        )

                        if pkg_info.get("status") == "installed":
                            fixed_count += 1
                            if pkg_info.get("auto_fixed"):
                                print_warning(
                                    f"Auto-fixed [cyan]{name}[/cyan]: [yellow]{pkg_info['original_version']}[/yellow] "
                                    f"([yellow]{pkg_info['update_reason']}[/yellow]) → [green]{pkg_info['installed_version']}[/green]"
                                )
                            else:
                                print_success(
                                    f"Updated [cyan]{name}[/cyan] to version [green]{version_clean}[/green]"
                                )
                        else:
                            error_count += 1
                            print_error(
                                f"Failed to update [cyan]{name}[/cyan]: {pkg_info.get('message', 'Unknown error')}"
                            )
                            if pkg_info.get("version_info"):
                                console.print(
                                    f"[dim][yellow]Available versions:[/yellow] {pkg_info['version_info']['latest_versions']}[/dim]"
                                )
                    except Exception as e:
                        error_count += 1
                        print_error(
                            f"Failed to update [cyan]{name}[/cyan]: {str(e)}"
                        )

        # Install missing packages
        if packages_to_install:
            with progress_status("Installing missing packages..."):
                for name in packages_to_install:
                    try:
                        version = requirements.get(name, "")
                        # 處理 DependencyInfo 對象的版本清理
                        if hasattr(version, "version_spec"):
                            version_clean = version.version_spec
                        elif isinstance(version, Text):
                            version_clean = str(version)
                        else:
                            version_clean = str(version).lstrip("=")

                        # 使用自動修復安裝
                        pkg_info = manager.package_manager.auto_fix_install(
                            name, version_clean
                        )

                        if pkg_info.get("status") == "installed":
                            fixed_count += 1
                            if pkg_info.get("auto_fixed"):
                                print_warning(
                                    f"Auto-fixed [cyan]{name}[/cyan]: [yellow]{pkg_info['original_version']}[/yellow] "
                                    f"([yellow]{pkg_info['update_reason']}[/yellow]) → [green]{pkg_info['installed_version']}[/green]"
                                )
                            else:
                                print_success(
                                    f"Installed [cyan]{name}[/cyan] {version_clean if version_clean else ''}"
                                )
                        else:
                            error_count += 1
                            print_error(
                                f"Failed to install [cyan]{name}[/cyan]: {pkg_info.get('message', 'Unknown error')}"
                            )
                            if pkg_info.get("version_info"):
                                console.print(
                                    f"[dim][yellow]Available versions:[/yellow] {pkg_info['version_info']['latest_versions']}[/dim]"
                                )
                    except Exception as e:
                        error_count += 1
                        print_error(
                            f"Failed to install [cyan]{name}[/cyan]: {str(e)}"
                        )

        # Handle redundant packages
        if redundant_packages:
            with progress_status("Optimizing package dependencies..."):
                # 如果使用 pyproject.toml，先初始化 PyProjectManager
                proj_manager = None
                if use_pyproject:
                    from ...core.pyproject_manager import PyProjectManager

                    proj_manager = PyProjectManager(pyproject_path)

                for name in redundant_packages:
                    try:
                        if use_pyproject and proj_manager:
                            proj_manager.remove_dependency(name)
                        else:
                            manager.package_manager._update_requirements(
                                removed=[name]
                            )
                        fixed_count += 1
                        print_success(
                            f"Removed [cyan]{name}[/cyan] from {'pyproject.toml' if use_pyproject else 'requirements.txt'}"
                        )
                    except Exception as e:
                        error_count += 1
                        print_error(
                            f"Failed to remove [cyan]{name}[/cyan] from {'pyproject.toml' if use_pyproject else 'requirements.txt'}: {str(e)}"
                        )

        # Handle not in requirements packages
        if not_in_requirements:
            with progress_status(
                f"Adding packages to {'pyproject.toml' if use_pyproject else 'requirements.txt'}..."
            ):
                for name, version, _ in not_in_requirements:
                    try:
                        if use_pyproject:
                            # Initialize PyProjectManager
                            from ...core.pyproject_manager import (
                                PyProjectManager,
                            )

                            proj_manager = PyProjectManager(
                                Path("pyproject.toml")
                            )
                            # Add to pyproject.toml with >= constraint
                            proj_manager.add_dependency(name, version, ">=")
                            fixed_count += 1
                            print_success(
                                f"Added [cyan]{name}>={version}[/cyan] to pyproject.toml"
                            )
                        else:
                            # Add to requirements.txt with == constraint
                            manager.package_manager._update_requirements(
                                added=[f"{name}=={version}"]
                            )
                            fixed_count += 1
                            print_success(
                                f"Added [cyan]{name}=={version}[/cyan] to requirements.txt"
                            )
                    except Exception as e:
                        error_count += 1
                        print_error(
                            f"Failed to add [cyan]{name}[/cyan]: {str(e)}"
                        )

        # Show summary
        console.print()
        if fixed_count > 0 or error_count > 0:
            summary_text = Text()
            summary_text.append("Total Issues: ")
            summary_text.append(f"{fixed_count + error_count}", style="cyan")
            summary_text.append("\n\n")

            if fixed_count > 0:
                summary_text.append("• Fixed: ")
                summary_text.append(f"{fixed_count}", style="green")
                summary_text.append("\n")

            if error_count > 0:
                summary_text.append("• Failed: ")
                summary_text.append(f"{error_count}", style="red")

            console.print(create_summary_panel("Fix Summary", summary_text))
            console.print()

    except Exception as e:
        print_error(f"Failed to fix package inconsistencies: {str(e)}")
        return
