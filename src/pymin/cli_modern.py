"""Modern command-line interface for PyPI package management"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from pathlib import Path
import os
import sys
from .modern.core.package_analyzer import PackageAnalyzer
from .modern.ui.console import (
    create_package_table,
    create_dependency_tree,
    create_status_panel,
    print_error,
    print_warning,
    print_success,
    print_info,
    print_table,
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
@click.option(
    "-a", "--all", "show_all", is_flag=True, help="Show all installed packages"
)
@click.option(
    "-t", "--tree", "show_tree", is_flag=True, help="Show dependency tree"
)
def list(show_all: bool, show_tree: bool):
    """List installed packages"""
    try:
        if show_tree:
            # Get dependency tree
            packages = pkg_analyzer.get_dependency_tree()
            if not packages:
                print_warning("No installed packages found")
                return

            # Create and display dependency tree
            tree_table = create_dependency_tree(packages)
            print_table(tree_table)

            # Display summary
            total_packages = len(packages)
            total_deps = sum(
                len(pkg.get("dependencies", {})) for pkg in packages.values()
            )
            direct_deps = sum(
                1 for pkg in packages.values() if pkg.get("dependencies")
            )

            summary = Panel.fit(
                "\n".join(
                    [
                        f"  • Total Packages: {total_packages}",
                        f"  • Total Dependencies: {total_deps} (Direct: {direct_deps})",
                    ]
                ),
                title="Summary",
                border_style="bright_blue",
                padding=(1, 2),
            )
            console.print(summary)
            console.print("\n")
            print_info("Run pm fix to resolve package inconsistencies")

        else:
            # Get package data
            if show_all:
                packages = pkg_analyzer.get_installed_packages()
                title = "All Installed Packages"
            else:
                packages = pkg_analyzer.get_top_level_packages()
                title = "Top Level Packages"

            if not packages:
                print_warning("No installed packages found")
                return

            # Get all dependencies for redundancy check
            all_packages = pkg_analyzer.get_installed_packages()
            all_dependencies = set()
            for pkg_info in all_packages.values():
                deps = pkg_info.get("dependencies", [])
                all_dependencies.update(deps)

            # Convert package data to table rows
            rows = []
            for name, data in sorted(packages.items()):
                # Handle both dictionary and string (version) formats
                if isinstance(data, dict):
                    package_data = data
                else:
                    package_data = {
                        "name": name,
                        "installed_version": data,
                        "required_version": "",
                    }

                # Check if package is redundant
                if name in all_dependencies:
                    package_data["redundant"] = True
                    package_data["status"] = "redundant"

                rows.append([package_data])

            # Create and display table
            table = create_package_table(
                title,
                ["Package Name", "Required", "Installed", "Status"],
                rows,
            )
            print_table(table)

            # Show statistics
            console.print(f"Total: [cyan]{len(packages)}[/cyan] packages")
            console.print("\n")

    except Exception as e:
        print_error(f"Error: {str(e)}")
        return


if __name__ == "__main__":
    cli()
