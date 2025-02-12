"""Command-line interface for PyPI package management"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from pathlib import Path
import os
import sys
import tomllib
from .core.package_analyzer import PackageAnalyzer
from .commands.venv.info_command import info
from .commands.venv.activate_command import activate
from .commands.venv.deactivate_command import deactivate
from .commands.venv.venv_command import venv
from .commands.package import add, remove, list, update, fix
from .commands.pypi.check_command import check
from .commands.pypi.search_command import search
from .commands.pypi.release_command import release
from .ui.console import (
    create_package_table,
    create_dependency_tree,
    print_error,
    print_warning,
    print_success,
    print_info,
    print_table,
    create_package_summary,
    create_summary_panel,
    print_tips,
)
from .ui.style import DEFAULT_PANEL, PanelConfig, StyleType
from typing import Union, List, Dict
from .core.version_checker import check_for_updates

console = Console(force_terminal=True, color_system="auto")

# Create package analyzer instance
pkg_analyzer = PackageAnalyzer()

# Get version from pyproject.toml
try:
    with open(
        Path(__file__).parent.parent.parent / "pyproject.toml", "rb"
    ) as f:
        __version__ = tomllib.load(f)["project"]["version"]
except Exception:
    __version__ = "unknown"

# Check for updates before anything else
check_for_updates()


class CliGroup(click.Group):
    """Command group with custom help formatting"""

    def format_help(self, ctx, formatter):
        """Format help message with styling"""
        console.print(
            Panel.fit(
                "\n".join(
                    [
                        "[bold blue]Environment Management:[/bold blue]",
                        f"  [cyan]info[/cyan]        [dim]Show environment information[/dim]",
                        f"  [cyan]venv[/cyan]        [dim]Create and activate a virtual environment[/dim] (alias: [cyan]env[/cyan])",
                        f"  [cyan]activate[/cyan]    [dim]Activate the virtual environment (defaults to current directory's env)[/dim] (alias: [cyan]on[/cyan])",
                        f"  [cyan]deactivate[/cyan]  [dim]Deactivate the current virtual environment[/dim] (alias: [cyan]off[/cyan])",
                        "",
                        "[bold blue]Package Management:[/bold blue]",
                        f"  [cyan]list[/cyan]        [dim]List installed packages and their dependencies[/dim] ([cyan]-a[/cyan]: all, [cyan]-t[/cyan]: tree) (alias: [cyan]ls[/cyan])",
                        f"  [cyan]add[/cyan]         [dim]Add or Update packages to requirements.txt or pyproject.toml[/dim] ([cyan]-p[/cyan]: use pyproject.toml)",
                        f"  [cyan]remove[/cyan]      [dim]Remove packages from requirements.txt and uninstall them[/dim] (alias: [cyan]rm[/cyan])",
                        f"  [cyan]update[/cyan]      [dim]Update packages to their latest versions[/dim] ([cyan]-a[/cyan]: all, [cyan]--check[/cyan]: check only) (alias: [cyan]up[/cyan])",
                        f"  [cyan]fix[/cyan]         [dim]Fix package inconsistencies[/dim] ([cyan]-p[/cyan]: use pyproject.toml)",
                        "",
                        "[bold blue]PyPI Integration:[/bold blue]",
                        f"  [cyan]check[/cyan]       [dim]Check package name availability[/dim]",
                        f"  [cyan]search[/cyan]      [dim]Search for similar package names on PyPI[/dim] ([cyan]-t[/cyan]: threshold)",
                        f"  [cyan]release[/cyan]     [dim]Build and publish package to PyPI or Test PyPI[/dim] ([cyan]--test[/cyan]: to Test PyPI)",
                        "",
                        "[bold blue]Global Options:[/bold blue]",
                        f"  [cyan]--version[/cyan]   [dim]Show version number[/dim] ([cyan]alias: -V, -v[/cyan])",
                    ]
                ),
                title="PyMin - CLI tool for PyPI package management",
                title_align=DEFAULT_PANEL.title_align,
                border_style=DEFAULT_PANEL.border_style,
                padding=(2, 2),
            )
        )


@click.group(cls=CliGroup, chain=True)
@click.option(
    "--version",
    "-v",
    "-V",
    is_flag=True,
    help="Show version number",
    is_eager=True,
    callback=lambda ctx, param, value: value
    and (console.print(f"pymin {__version__}") or ctx.exit()),
)
def cli(version: bool = False):
    """PyMin - PyPI Package Management Tool"""
    pass


# Register environment commands
cli.add_command(info)
cli.add_command(activate)
cli.add_command(deactivate)
cli.add_command(venv)

# Register package management commands
cli.add_command(add)
cli.add_command(remove)
cli.add_command(list)
cli.add_command(update)
cli.add_command(fix)

# Register PyPI integration commands
cli.add_command(check)
cli.add_command(search)
cli.add_command(release)

# Register command aliases
cli.add_command(activate, name="on")
cli.add_command(deactivate, name="off")
cli.add_command(venv, name="env")
cli.add_command(list, name="ls")
cli.add_command(remove, name="rm")
cli.add_command(update, name="up")


if __name__ == "__main__":
    cli()
