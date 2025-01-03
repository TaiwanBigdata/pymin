# Command-line interface providing PyPI package name validation and search functionality
import click
import os
import subprocess
from rich.console import Console
from rich.prompt import Confirm
from .check import PackageNameChecker
from .search import PackageSearcher
from .venv import VenvManager
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.layout import Layout
from rich.style import Style
from pathlib import Path
import sys

# Force color output
console = Console(force_terminal=True, color_system="auto")


def create_status_table(title: str, rows: list[tuple[str, str, str]]) -> Table:
    """Create a status table with consistent styling"""
    table = Table(
        title=title,
        show_header=False,
        box=None,
        padding=(0, 2),
        collapse_padding=True,
        expand=False,
        title_justify="left",
    )

    table.add_column("Key", style="dim")
    table.add_column("Value", style="bold")
    table.add_column("Status", justify="right")

    for row in rows:
        table.add_row(*row)

    return table


@click.group()
def cli():
    """[cyan]PyMin[/cyan] CLI tool for PyPI package management

    \b
    Core Commands:
      check       Check package name availability on PyPI
      search      Search for similar package names
      venv        Create a virtual environment

    \b
    Environment:
      activate    Show virtual environment activation command
      deactivate  Show virtual environment deactivation command
      info        Show environment information
    """
    pass


@cli.command()
@click.argument("name")
def check(name):
    """Check package name availability"""
    checker = PackageNameChecker()
    result = checker.check_availability(name)
    checker.display_result(result)


@cli.command()
@click.argument("name")
@click.option(
    "--threshold",
    "-t",
    default=0.8,
    help="Similarity threshold (0.0-1.0)",
    type=float,
)
def search(name: str, threshold: float):
    """Search for similar package names on PyPI"""
    searcher = PackageSearcher(similarity_threshold=threshold)
    results = searcher.search_similar(name)

    if not results:
        console.print("[yellow]No similar packages found.[/yellow]")
        return

    table = Table(
        title=Text.assemble(
            "Similar Packages to '",
            (name, "cyan"),
            "'",
        ),
        show_header=True,
        header_style="bold magenta",
        expand=False,
        title_justify="left",
    )

    table.add_column("Package Name", style="cyan")
    table.add_column("Similarity", justify="center")
    table.add_column("PyPI URL", style="blue")

    for pkg_name, similarity in results:
        url = searcher.get_package_url(pkg_name)
        table.add_row(
            pkg_name, f"{similarity:.2%}", f"[link={url}]{url}[/link]"
        )

    console.print("\n")  # Add empty line
    console.print(table)
    console.print(
        "\n[dim]Tip: Click on package names or URLs to open in browser[/dim]"
    )


@cli.command()
@click.argument("name", default="env")
def venv(name):
    """Create a virtual environment with specified name"""
    manager = VenvManager()
    success, message = manager.create_venv(name)

    if success:
        venv_info = manager.get_venv_info(name)
        text = Text.assemble(
            "\n",
            ("Virtual Environment: ", "dim"),
            (name, "cyan"),
            "\n",
            ("Python Version: ", "dim"),
            (venv_info["python_version"], "cyan"),
            "\n",
            ("Pip Version: ", "dim"),
            (venv_info["pip_version"], "cyan"),
            "\n",
            ("Location: ", "dim"),
            (str(venv_info["location"]), "cyan"),
            "\n",
            ("Status: ", "dim"),
            ("✓ Created", "green"),
            "\n",
            "\n",
            ("Next Steps", "bold white"),
            (":\n", "dim"),
            ("1. ", "dim"),
            ("source ", "cyan"),
            (f"{name}/bin/activate", "cyan"),
            "\n",
            ("2. ", "dim"),
            ("pip install -r requirements.txt", "cyan"),
            " (if exists)",
            "\n",
        )
        panel = Panel.fit(
            text,
            title="Virtual Environment Creation Results",
            title_align="left",
            border_style="bright_blue",
        )
    else:
        text = Text.assemble(
            "\n",
            ("Status: ", "dim"),
            ("✗ Failed", "red"),
            "\n",
            ("Error: ", "dim"),
            (message, "red"),
            "\n",
        )
        panel = Panel.fit(
            text,
            title="Virtual Environment Creation Error",
            title_align="left",
            border_style="red",
        )

    console.print("\n")
    console.print(panel)
    console.print("\n")


@cli.command()
def info():
    """Show environment information"""
    manager = VenvManager()
    info = manager.get_environment_info()

    text = Text()
    text.append("\n")

    # System Information
    text.append("System Information", "bold white")
    text.append("\n")
    text.append("  Python Version: ", "dim")
    text.append(str(info["python_version"]), "cyan")
    text.append("\n")
    text.append("  Platform: ", "dim")
    text.append(str(info["platform"]), "cyan")
    text.append("\n")
    text.append("  Working Directory: ", "dim")
    text.append(str(info["working_dir"]), "cyan")
    text.append("\n")
    text.append("  Pip: ", "dim")
    text.append(
        f"{str(info['pip_version'])} at {str(info['pip_location'])}", "cyan"
    )

    # Show pip update if available
    if info.get("pip_update"):
        text.append(" (", "dim")
        text.append(f"update available: {str(info['pip_update'])}", "yellow")
        text.append(")", "dim")

    text.append("\n")
    text.append("  User Scripts: ", "dim")
    text.append(str(info["user_scripts"]), "cyan")
    text.append("\n")

    # Project info if available
    if "project" in info:
        project = info["project"]
        text.append("\n")
        text.append("Project Information", "bold white")
        text.append("\n")
        text.append("  Name: ", "dim")
        text.append(str(project["name"]), "green")
        text.append("\n")
        text.append("  Version: ", "dim")
        text.append(str(project["version"]), "green")
        text.append("\n")
        text.append("  Description: ", "dim")
        text.append(str(project["description"]), "green")
        text.append("\n")
        text.append("  Python Required: ", "dim")
        text.append(str(project["requires_python"]), "green")
        text.append("\n")
        text.append("  Build Backend: ", "dim")
        text.append(str(project["build_backend"]), "green")
        text.append("\n")

        # Show CLI commands if available
        if "scripts" in project:
            text.append("  Commands:", "dim")
            text.append("\n")
            for cmd_name, cmd_path in sorted(project["scripts"].items()):
                text.append("    ", "dim")
                text.append(cmd_name, "cyan")
                text.append("  ", "dim")
                text.append(cmd_path, "green")
                text.append("\n")

        # Show dependencies count if available
        if project.get("dependencies"):
            deps_count = len(project["dependencies"])
            text.append("  Dependencies: ", "dim")
            text.append(f"{deps_count} packages", "green")
            text.append("\n")

    # Virtual environment info
    text.append("\n")
    text.append("Virtual Environment", "bold white")
    text.append("\n")

    # Show active virtual environment if any
    if info["virtual_env"]:
        active_venv_path = Path(info["virtual_env"])
        text.append("  Active Environment:", "dim")
        text.append("\n")
        text.append("    Name: ", "dim")
        text.append(active_venv_path.name, "cyan")
        text.append("\n")
        text.append("    Path: ", "dim")
        text.append(str(active_venv_path), "cyan")
        text.append("\n")

    # Show current directory virtual environment status
    text.append("  Current Directory:", "dim")
    text.append("\n")

    current_venv = Path("env")
    if current_venv.exists() and current_venv.is_dir():
        text.append("    Name: ", "dim")
        text.append("env", "cyan")
        text.append("\n")
        text.append("    Path: ", "dim")
        text.append(str(current_venv.absolute()), "cyan")
        text.append("\n")
        text.append("    Status: ", "dim")
        if info["virtual_env"] and Path(info["virtual_env"]).samefile(
            current_venv
        ):
            text.append("✓ Active", "green")
        else:
            text.append("Not Active", "yellow")
    else:
        text.append("    Status: ", "dim")
        text.append("Not Found", "yellow")
    text.append("\n")

    panel = Panel.fit(
        text,
        title="Environment Information",
        title_align="left",
        border_style="bright_blue",
    )

    console.print("\n")
    console.print(panel)
    console.print("\n")


@cli.command()
def activate():
    """Show virtual environment activation command"""
    if not Path("env").exists():
        console.print("[red]Error: Virtual environment 'env' not found.[/red]")
        console.print(
            "[yellow]Tip: Run 'pm init' first to create a project with virtual environment.[/yellow]"
        )
        return

    activate_cmd = str(Path("env/bin/activate"))
    text = Text.assemble(
        "\n",
        ("Copy and run this command:\n", "dim"),
        "\n",
        (f"source {activate_cmd}", "cyan bold"),
        "\n",
        "\n",
        ("Or use this shortcut:\n", "dim"),
        ("\n. env/bin/activate", "cyan"),
        "\n",
    )
    panel = Panel.fit(
        text,
        title="Virtual Environment Activation",
        title_align="left",
        border_style="bright_blue",
    )
    console.print("\n")
    console.print(panel)
    console.print("\n")


@cli.command()
def deactivate():
    """Show virtual environment deactivation command"""
    if not os.environ.get("VIRTUAL_ENV"):
        console.print("[red]Error: No active virtual environment found.[/red]")
        return

    text = Text.assemble(
        "\n",
        ("Run this command:\n", "dim"),
        "\n",
        ("deactivate", "cyan bold"),
        "\n",
    )
    panel = Panel.fit(
        text,
        title="Virtual Environment Deactivation",
        title_align="left",
        border_style="bright_blue",
    )
    console.print("\n")
    console.print(panel)
    console.print("\n")


if __name__ == "__main__":
    cli()
