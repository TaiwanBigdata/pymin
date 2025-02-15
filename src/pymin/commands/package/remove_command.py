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

        # 先顯示主要移除的套件
        for pkg in packages:
            if pkg not in results:
                continue

            info = results[pkg]
            if info["status"] == "removed":
                console.print(
                    f"[bold][green]{SymbolType.SUCCESS}[/green] Removed [cyan]{pkg}=={info['version']}[/cyan][/bold]"
                )

                # 顯示這個套件特有的依賴
                removable_deps = info.get("removable_deps", {})
                if removable_deps:
                    deps_str = ", ".join(
                        f"[cyan]{dep}=={version}[/cyan]"
                        for dep, version in sorted(removable_deps.items())
                    )
                    console.print(
                        f"[dim]Removed dependencies:  {deps_str}[/dim]"
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
