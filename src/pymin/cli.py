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
from .package import PackageManager
from typing import Optional
from .utils import get_current_shell

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


def get_environment_display_name(venv_path: Path) -> str:
    """Get a display name for the virtual environment"""
    if venv_path.name in ["env", "venv"]:
        return f"({venv_path.name}) "
    return ""


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
      activate    Activate virtual environment
      deactivate  Deactivate virtual environment
      info        Show environment information

    \b
    Package Management:
      add         Add package to requirements.txt
      remove      Remove package from requirements.txt
      list        List all packages in requirements.txt
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
@click.argument("name", default="env")
def activate(name):
    """Activate the virtual environment"""
    venv_path = Path(name)
    activate_script = venv_path / "bin" / "activate"

    if not venv_path.exists():
        console.print(
            f"[red]Virtual environment '{name}' does not exist.[/red]"
        )
        return

    if not activate_script.exists():
        console.print(f"[red]Activation script not found in '{name}'.[/red]")
        return

    # Get current project name (directory name)
    project_name = Path.cwd().name
    venv_display = get_environment_display_name(venv_path)

    current_status = "No active environment"
    if "VIRTUAL_ENV" in os.environ:
        current_venv = Path(os.environ["VIRTUAL_ENV"])
        current_status = f"[cyan]{get_environment_display_name(current_venv)}{Path(current_venv).parent.name}[/cyan]"

    if Confirm.ask(
        f"[yellow]Switch environment?[/yellow]\n"
        f"  From: {current_status}\n"
        f"  To:   [cyan]{venv_display}{project_name}[/cyan]"
    ):
        console.print(f"[green]Activating virtual environment: {name}[/green]")
        shell, shell_name = get_current_shell()
        os.execl(
            shell,
            shell_name,
            "-c",
            f"source {activate_script} && exec {shell_name}",
        )


@cli.command()
def deactivate():
    """Deactivate the current virtual environment"""
    if "VIRTUAL_ENV" not in os.environ:
        console.print("[yellow]No active virtual environment found.[/yellow]")
        return

    current_venv = Path(os.environ["VIRTUAL_ENV"])
    project_name = current_venv.parent.name
    venv_display = get_environment_display_name(current_venv)

    if Confirm.ask(
        f"[yellow]Deactivate environment?[/yellow]\n"
        f"  From: [cyan]{venv_display}{project_name}[/cyan]\n"
        f"  To:   No active environment"
    ):
        console.print("[green]Deactivating virtual environment...[/green]")
        shell, shell_name = get_current_shell()
        deactivate_script = current_venv / "bin" / "activate"
        os.execl(
            shell,
            shell_name,
            "-c",
            f"source {deactivate_script} && deactivate && exec {shell_name}",
        )


@cli.command()
@click.argument("package")
@click.option("--version", "-v", help="Specific version to install")
def add(package: str, version: Optional[str]):
    """Add a package to requirements.txt and install it"""
    manager = PackageManager()
    manager.add(package, version)


@cli.command()
@click.argument("package")
def remove(package: str):
    """Remove a package from requirements.txt and uninstall it"""
    manager = PackageManager()
    manager.remove(package)


@cli.command(name="list")
@click.option("-a", "--all", is_flag=True, help="List all installed packages")
@click.option("-t", "--tree", is_flag=True, help="Show dependency tree")
@click.option("--fix", is_flag=True, help="Fix package inconsistencies")
@click.option(
    "-f",
    "--auto-fix",
    is_flag=True,
    help="Automatically fix package inconsistencies without confirmation",
)
def list_packages(all, tree, fix, auto_fix):
    """List installed packages and their dependencies"""
    pm = PackageManager()
    pm.list_packages(show_all=all, show_deps=tree, fix=fix, auto_fix=auto_fix)


if __name__ == "__main__":
    cli()
