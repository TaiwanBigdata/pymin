"""Fix package inconsistencies command"""

import click
from typing import Dict, List, Set, Tuple
from rich.prompt import Confirm
from ...core.venv_manager import VenvManager
from ...core.package_analyzer import (
    PackageAnalyzer,
    DependencySource,
    DependencyInfo,
    PackageStatus,
)
from ...ui.console import (
    print_error,
    print_warning,
    print_success,
    console,
    progress_status,
    create_summary_panel,
    print_info,
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
def fix(yes: bool = False):
    """Fix package inconsistencies"""
    try:
        manager = VenvManager()

        # Check if we're in a virtual environment
        if not manager.from_env:
            print_error(
                "No virtual environment is active. Use 'pmm on' to activate one."
            )
            return

        # Determine which configuration file to use
        use_pyproject, reason = pkg_analyzer.determine_config_source()
        print_info(reason)

        # Get package information
        with progress_status("Analyzing packages..."):
            installed_packages = pkg_analyzer.get_installed_packages()
            requirements = pkg_analyzer._parse_requirements()

        if not installed_packages and not requirements:
            print_warning("No packages found to analyze")
            return

        # Find issues to fix using the new abstraction
        inconsistencies = pkg_analyzer.get_package_inconsistencies(
            installed_packages, requirements, use_pyproject
        )

        # Check if any issues were found
        issues_found = any(pkgs for pkgs in inconsistencies.values())
        if not issues_found:
            print_success("No package inconsistencies found!")
            return

        # Convert inconsistencies to the format expected by the fix logic
        packages_to_update = []
        packages_to_install = []
        redundant_packages = []
        not_in_requirements = []

        # Process version mismatches
        for pkg_name, version_spec in inconsistencies[
            PackageStatus.VERSION_MISMATCH
        ]:
            # 如果套件是冗餘的，跳過版本更新
            if pkg_name in inconsistencies[PackageStatus.REDUNDANT]:
                continue

            installed_version = installed_packages[pkg_name][
                "installed_version"
            ]
            packages_to_update.append(
                (pkg_name, installed_version, version_spec)
            )

        # Process missing packages
        # 同樣跳過冗餘套件
        packages_to_install.extend(
            [
                pkg_name
                for pkg_name in inconsistencies[PackageStatus.NOT_INSTALLED]
                if pkg_name not in inconsistencies[PackageStatus.REDUNDANT]
            ]
        )

        # Process redundant packages
        redundant_packages.extend(inconsistencies[PackageStatus.REDUNDANT])

        # Process not in requirements
        for pkg_name in inconsistencies[PackageStatus.NOT_IN_REQUIREMENTS]:
            version = installed_packages[pkg_name]["installed_version"]
            # 根據使用的文件和存在狀況決定顯示訊息
            if use_pyproject:
                missing_from = "pyproject.toml"
            else:
                missing_from = "requirements.txt"
            not_in_requirements.append((pkg_name, version, missing_from))

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

                    proj_manager = PyProjectManager(
                        pkg_analyzer.project_path / "pyproject.toml"
                    )

                for name in redundant_packages:
                    try:
                        # 獲取完整的套件資訊（包含 extras）
                        pkg_info = requirements.get(name)
                        pkg_name_with_extras = (
                            pkg_info.version_spec.split("==")[0].split(">=")[0]
                            if pkg_info and pkg_info.extras
                            else name
                        )

                        # 同時從兩個文件中移除冗餘套件
                        if use_pyproject and proj_manager:
                            # 先檢查套件是否在 pyproject.toml 中
                            deps = proj_manager.get_dependencies()
                            if name in deps:
                                proj_manager.remove_dependency(name)

                        # 檢查並從 requirements.txt 中移除
                        if Path("requirements.txt").exists():
                            manager.package_manager._update_requirements(
                                removed=[pkg_name_with_extras]
                            )

                        fixed_count += 1
                        if use_pyproject and proj_manager and name in deps:
                            print_success(
                                f"Removed [cyan]{pkg_name_with_extras}[/cyan] from both pyproject.toml and requirements.txt"
                            )
                        else:
                            print_success(
                                f"Removed [cyan]{pkg_name_with_extras}[/cyan] from requirements.txt"
                            )
                    except Exception as e:
                        error_count += 1
                        print_error(
                            f"Failed to remove [cyan]{name}[/cyan]: {str(e)}"
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
