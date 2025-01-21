"""Modern command-line interface for PyPI package management"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from pathlib import Path
import os
import sys
from typing import Optional
from .modern.core.package_analyzer import PackageAnalyzer
from .modern.ui.console import (
    create_package_table,
    create_dependency_tree,
    print_error,
    print_warning,
)

console = Console(force_terminal=True, color_system="auto")

# Create package analyzer instance
pkg_analyzer = PackageAnalyzer()


def format_help_message(ctx, formatter):
    """Format help message with modern styling"""
    categories = {
        "Environment": ["info", "venv", "activate", "deactivate"],
        "Package": ["list", "add", "remove", "update", "fix"],
        "PyPI": ["check", "search", "release"],
    }

    content = Text()
    for category, cmd_names in categories.items():
        content.append("\n")
        content.append(category, style="bold blue")
        content.append(":\n")

        for cmd_name in cmd_names:
            if cmd_name not in ctx.command.commands:
                continue

            cmd = ctx.command.commands[cmd_name]
            if cmd.hidden:
                continue

            content.append("  ")
            content.append(cmd_name, style="dim")
            padding = 12 - len(cmd_name)
            content.append(" " * padding)

            help_text = cmd.help or ""
            content.append(Text(help_text, style="cyan"))

            # Add parameter info or alias info
            extra_info = []
            if cmd_name == "list":
                extra_info.append("(-a: all, -t: tree)")
            elif cmd_name == "release":
                extra_info.append("(--test: Test PyPI)")
            elif cmd_name == "search":
                extra_info.append("(-t: threshold)")
            elif cmd_name in [
                "remove",
                "update",
                "venv",
                "activate",
                "deactivate",
            ]:
                aliases = {
                    "remove": "rm",
                    "update": "up",
                    "venv": "env",
                    "activate": "on",
                    "deactivate": "off",
                }
                extra_info.append(f"(alias: {aliases[cmd_name]})")

            if extra_info:
                content.append(" ")
                content.append(Text(" ".join(extra_info), style="green"))

            content.append("\n")

    # Create title
    title_text = Text()
    title_text.append("PyMin Modern", style="bold cyan")
    title_text.append(" - ", style="dim")
    title_text.append("Modern PyPI Package Management Tool", style="cyan")

    # Add global options
    content.append("\n")
    content.append("Global Options", style="bold blue")
    content.append(":\n")
    content.append("  --version", style="dim")
    padding = 12 - len("--version")
    content.append(" " * padding)
    content.append("Show version number", style="cyan")
    content.append(" ")
    content.append("(alias: -V, -v)", style="green")
    content.append("\n")

    console.print(
        Panel.fit(
            content,
            title=title_text,
            border_style="blue",
            padding=(1, 2),
            title_align="left",
        )
    )


class ModernGroup(click.Group):
    """Modern command group with custom help formatting"""

    def format_help(self, ctx, formatter):
        self.format_commands(ctx, formatter)


@click.group(cls=ModernGroup)
@click.option(
    "--version",
    "-v",
    "-V",
    is_flag=True,
    help="Show version number",
    is_eager=True,
    callback=lambda ctx, param, value: value
    and (console.print("pymin-modern 0.1.0") or ctx.exit()),
)
def cli(version: bool = False):
    """PyMin Modern - Modern PyPI Package Management Tool"""
    pass


cli.format_commands = format_help_message


@cli.command()
@click.option("-a", "--all", is_flag=True, help="Show all installed packages")
@click.option("-t", "--tree", is_flag=True, help="Show dependency tree")
def list(all: bool, tree: bool):
    """List installed packages and their dependencies"""
    if not Path(os.environ.get("VIRTUAL_ENV", "")).exists():
        print_error("No active virtual environment found")
        return

    try:
        if tree:
            # Show dependency tree
            packages = pkg_analyzer.get_dependency_tree()
            if not packages:
                print_warning("No installed packages found")
                return

            # Create and display dependency tree
            tree_view = create_dependency_tree(packages)
            console.print("\n")
            console.print(tree_view)
            console.print("\n")

            # Calculate statistics
            total_packages = len(packages)
            direct_deps = sum(
                1 for pkg in packages.values() if "dependencies" in pkg
            )
            total_deps = sum(
                len(pkg.get("dependencies", {})) for pkg in packages.values()
            )

            # Show summary
            console.print("Summary:")
            console.print(f"  • Total Packages: {total_packages}")
            console.print(f"  • Not in requirements.txt (△): {total_packages}")
            console.print(
                f"  • Total Dependencies: {total_deps} (Direct: {direct_deps})"
            )
            console.print("\n")
            console.print("Tip: Run pm fix to resolve package inconsistencies")
            console.print("\n")

        else:
            # Get package data
            if all:
                packages = pkg_analyzer.get_installed_packages()
                title = "All Installed Packages"
            else:
                packages = pkg_analyzer.get_top_level_packages()
                title = "Top Level Packages"

            if not packages:
                print_warning("No installed packages found")
                return

            # Prepare table data
            headers = ["Package Name", "Version"]
            rows = [
                [name, version] for name, version in sorted(packages.items())
            ]
            styles = ["package_name", "package_version"] * len(rows)

            # Create and display table
            table = create_package_table(title, headers, rows, styles)
            console.print("\n")
            console.print(table)
            console.print("\n")

            # Show statistics
            console.print(f"Total: [cyan]{len(packages)}[/cyan] packages")
            console.print("\n")

    except Exception as e:
        print_error(f"Error: {str(e)}")
        return


if __name__ == "__main__":
    cli()
