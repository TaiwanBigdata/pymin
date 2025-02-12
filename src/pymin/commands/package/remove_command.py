"""Remove packages command"""

import click
from typing import List, Dict
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
@click.argument("packages", nargs=-1, required=True)
def remove(packages: List[str]):
    """Remove packages from the virtual environment

    PACKAGES: One or more package names to remove
    """
    try:
        manager = VenvManager()

        # Check if we're in a virtual environment
        if not manager.from_env:
            print_error(
                "No virtual environment is active. Use 'pmm on' to activate one."
            )
            return

        with progress_status("Removing packages..."):
            # Remove packages from both requirements.txt and pyproject.toml
            results = manager.remove_packages(packages)

        # Display results
        console.print()

        # Track dependencies that have been shown
        shown_deps = set()

        for pkg in packages:  # 只顯示主要請求移除的套件
            if pkg not in results:
                continue

            info = results[pkg]
            if info["status"] == "removed":
                console.print(
                    f"[bold][green]{SymbolType.SUCCESS}[/green] Removed [cyan]{pkg}=={info['version']}[/cyan][/bold]"
                )

                # Show dependency information
                dep_info = info.get("dependency_info", {})

                # 已移除的依賴
                if "removable_deps" in dep_info:
                    removable_deps = sorted(dep_info["removable_deps"])
                    if removable_deps:
                        # 取得被移除依賴的版本
                        deps_with_versions = []
                        for dep in removable_deps:
                            version = (
                                manager.package_manager._get_installed_version(
                                    dep
                                )
                            )
                            deps_with_versions.append(
                                f"[cyan]{dep}=={version}[/cyan]"
                            )
                        console.print(
                            f"[dim]Removed dependencies:  {', '.join(deps_with_versions)}[/dim]"
                        )

                # 被保留的依賴
                if "kept_deps" in dep_info:
                    kept_deps = sorted(dep_info["kept_deps"])
                    if kept_deps:
                        deps_with_versions = []
                        for dep in kept_deps:
                            version = (
                                manager.package_manager._get_installed_version(
                                    dep
                                )
                            )
                            # 從 dep_info 中取得 kept_for 資訊
                            kept_for = dep_info.get(dep, {}).get("kept_for", [])
                            if kept_for:
                                dependents = sorted(kept_for)
                                deps_with_versions.append(
                                    f"[cyan]{dep}=={version}[/cyan] (required by: {', '.join(dependents)})"
                                )
                            else:
                                # 如果沒有 kept_for 資訊，可能需要重新檢查依賴關係
                                all_deps = (
                                    manager.package_manager._get_all_dependencies()
                                )
                                other_dependents = sorted(
                                    all_deps.get(dep, set())
                                )
                                if other_dependents:
                                    deps_with_versions.append(
                                        f"[cyan]{dep}=={version}[/cyan] (required by: {', '.join(other_dependents)})"
                                    )
                                else:
                                    deps_with_versions.append(
                                        f"[cyan]{dep}=={version}[/cyan]"
                                    )
                        if deps_with_versions:
                            console.print(
                                f"[dim]Kept dependencies:  {', '.join(deps_with_versions)}[/dim]"
                            )

            elif info["status"] == "not_found":
                console.print(
                    f"[yellow]{SymbolType.WARNING}[/yellow] [cyan]{pkg}[/cyan]: {info['message']}"
                )
            else:
                console.print(
                    f"[red]{SymbolType.ERROR}[/red] Failed to remove [cyan]{pkg}[/cyan]: {info.get('message', 'Unknown error')}"
                )

        console.print()

    except Exception as e:
        print_error(f"Failed to remove packages: {str(e)}")
        return
