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
from .modern.commands.env_command import info, activate, deactivate
from .modern.ui.console import (
    create_package_table,
    create_dependency_tree,
    print_error,
    print_warning,
    print_success,
    print_info,
    print_table,
    create_package_summary,
    create_summary_panel,
    create_fix_tip,
)
from typing import Union, List, Dict

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

# Register commands
cli.add_command(info)
cli.add_command(activate)
cli.add_command(deactivate)

# Register command aliases
cli.add_command(activate, "on")
cli.add_command(deactivate, "off")


def should_show_fix_tip(packages: Union[List[Dict], Dict[str, Dict]]) -> bool:
    """Check if there are any non-normal package statuses in top-level packages"""
    if isinstance(packages, dict):
        return any(
            pkg.get("status") not in [None, "normal"]
            for pkg in packages.values()
            if not pkg.get("is_dependency")
        )
    return any(
        pkg.get("status") not in [None, "normal"]
        for pkg in packages
        if not pkg.get("is_dependency")
    )


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
            summary_content = create_package_summary(
                packages, mode="dependency_tree"
            )
            console.print(
                create_summary_panel("Package Summary", summary_content)
            )

            # Show fix tip if needed
            if should_show_fix_tip(packages):
                console.print()
                create_fix_tip()

        else:
            # Get package data
            if show_all:
                packages = pkg_analyzer.get_installed_packages()
                title = "All Installed Packages"
                mode = "all_installed"
                # Get top level packages for dimming check
                top_level_packages = pkg_analyzer.get_top_level_packages()
            else:
                packages = pkg_analyzer.get_top_level_packages()
                title = "Top Level Packages"
                mode = "top_level"

            if not packages:
                print_warning("No installed packages found")
                return

            # Get all dependencies for redundancy check
            all_packages = pkg_analyzer.get_installed_packages()
            all_dependencies = set()
            requirements = pkg_analyzer._parse_requirements()
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

                # Check if package is redundant (in requirements.txt and is a dependency)
                if name in requirements and name in all_dependencies:
                    package_data["redundant"] = True
                    package_data["status"] = "redundant"
                # Check if package is missing (in requirements.txt but not installed)
                elif name in requirements and not package_data.get(
                    "installed_version"
                ):
                    package_data["status"] = "missing"

                # Mark if package is not top-level (for dimming in display)
                if show_all and name not in top_level_packages:
                    package_data["is_dependency"] = True

                rows.append([package_data])

            # Create and display table
            table = create_package_table(
                title,
                ["Package Name", "Required", "Installed", "Status"],
                rows,
            )
            print_table(table)

            # Display summary
            summary_content = create_package_summary(packages, mode=mode)
            console.print(
                create_summary_panel("Package Summary", summary_content)
            )
            console.print("\n")

            # Show fix tip if needed
            if should_show_fix_tip(packages):
                create_fix_tip()

    except Exception as e:
        print_error(f"Error: {str(e)}")
        return


if __name__ == "__main__":
    cli()
