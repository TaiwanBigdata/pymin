"""Fix package inconsistencies command"""

import click
from typing import Dict, List, Set, Tuple
from rich.prompt import Confirm
from ...core.venv_manager import VenvManager
from ...core.package_analyzer import PackageAnalyzer
from ...ui.console import (
    print_error,
    print_warning,
    print_success,
    console,
    progress_status,
)
from ...ui.style import SymbolType

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

        # Get package information
        with progress_status("Analyzing packages..."):
            installed_packages = pkg_analyzer.get_installed_packages()
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

        # Check version mismatches and missing packages
        for pkg_name, req_version in requirements.items():
            if pkg_name not in installed_packages:
                packages_to_install.append(pkg_name)
                issues_found = True
            else:
                installed_version = installed_packages[pkg_name][
                    "installed_version"
                ]
                # 移除版本字串開頭的 '==' 再比較
                required_clean = req_version.lstrip("=")
                if installed_version != required_clean:
                    packages_to_update.append(
                        (pkg_name, installed_version, required_clean)
                    )
                    issues_found = True

        # Check redundant packages
        all_dependencies = set()
        for pkg_info in installed_packages.values():
            deps = pkg_info.get("dependencies", [])
            all_dependencies.update(deps)

        for pkg_name in requirements:
            if pkg_name in all_dependencies:
                redundant_packages.append(pkg_name)
                issues_found = True

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
                version = requirements.get(name, "latest")
                console.print(f"  • [cyan]{name}[/cyan] ({version})")

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
                        results = manager.add_packages([f"{name}=={required}"])
                        pkg_info = results.get(name, {})
                        if pkg_info.get("status") == "installed":
                            fixed_count += 1
                            print_success(
                                f"Updated [cyan]{name}[/cyan] to version [green]{required}[/green]"
                            )
                        else:
                            error_count += 1
                            print_error(
                                f"Failed to update [cyan]{name}[/cyan]: {pkg_info.get('message', 'Unknown error')}"
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
                        # 移除版本字串開頭的 == 再組合
                        version_clean = version.lstrip("=")
                        package_spec = (
                            f"{name}=={version_clean}"
                            if version_clean
                            else name
                        )
                        results = manager.add_packages([package_spec])
                        pkg_info = results.get(name, {})

                        if pkg_info.get("status") == "installed":
                            fixed_count += 1
                            print_success(
                                f"Installed [cyan]{name}[/cyan] {version_clean if version_clean else ''}"
                            )
                        else:
                            error_msg = pkg_info.get("message", "Unknown error")
                            version_info = pkg_info.get("version_info", {})

                            # 檢查是否為版本相關錯誤
                            if (
                                "Version not found" in error_msg
                                and version_info
                            ):
                                # 嘗試安裝最新版本
                                latest_version = (
                                    version_info["latest_versions"]
                                    .split(",")[0]
                                    .strip()
                                    .replace("[cyan]", "")
                                    .replace("[/cyan]", "")
                                    .replace(" (latest)", "")
                                )

                                # 分析更新原因
                                update_reason = (
                                    "Python compatibility issue"
                                    if "Python version" in error_msg
                                    or "requires Python" in error_msg
                                    else (
                                        "Version not found"
                                        if "not found" in error_msg
                                        else "Installation failed"
                                    )
                                )

                                # 使用最新版本重試
                                console.print(
                                    f"[yellow]Trying latest version {latest_version}...[/yellow]"
                                )
                                retry_results = manager.add_packages(
                                    [f"{name}=={latest_version}"]
                                )

                                # 檢查重試結果
                                retry_info = retry_results.get(name, {})
                                if retry_info.get("status") == "installed":
                                    fixed_count += 1
                                    print_warning(
                                        f"Auto-fixed [cyan]{name}[/cyan]: [yellow]{version_clean}[/yellow] ([yellow]{update_reason}[/yellow]) → [green]{latest_version}[/green]"
                                    )
                                else:
                                    error_count += 1
                                    print_error(
                                        f"Failed to install [cyan]{name}[/cyan] (latest version also failed)"
                                    )
                                    if version_info:
                                        console.print(
                                            f"[dim][yellow]Available versions:[/yellow] {version_info['latest_versions']}[/dim]"
                                        )
                            else:
                                error_count += 1
                                print_error(
                                    f"Failed to install [cyan]{name}[/cyan]: {error_msg}"
                                )
                    except Exception as e:
                        error_count += 1
                        print_error(
                            f"Failed to install [cyan]{name}[/cyan]: {str(e)}"
                        )

        # Handle redundant packages
        if redundant_packages:
            with progress_status("Optimizing package dependencies..."):
                for name in redundant_packages:
                    if yes or Confirm.ask(
                        f"Remove [cyan]{name}[/cyan] from requirements.txt?"
                    ):
                        try:
                            manager.package_manager._update_requirements(
                                removed=[name]
                            )
                            fixed_count += 1
                            print_success(
                                f"Removed [cyan]{name}[/cyan] from requirements.txt"
                            )
                        except Exception as e:
                            error_count += 1
                            print_error(
                                f"Failed to remove [cyan]{name}[/cyan] from requirements.txt: {str(e)}"
                            )

        # Show summary
        console.print()
        if fixed_count > 0:
            print_success(f"Successfully fixed {fixed_count} issue(s)")
        if error_count > 0:
            print_error(f"Failed to fix {error_count} issue(s)")

    except Exception as e:
        print_error(f"Failed to fix package inconsistencies: {str(e)}")
        return
