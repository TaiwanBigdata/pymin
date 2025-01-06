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
from .utils import get_current_shell, get_environment_display_name
from rich.markup import escape

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
    venv_path = Path(name)

    # Check if virtual environment already exists
    if venv_path.exists() and venv_path.is_dir():
        if Confirm.ask(
            f"\n[yellow]Virtual environment '{name}' already exists. Do you want to rebuild it?[/yellow]"
        ):
            # Deactivate if current environment is active
            if os.environ.get("VIRTUAL_ENV") == str(venv_path.absolute()):
                shell, shell_name = get_current_shell()
                deactivate_cmd = (
                    f"source {venv_path}/bin/activate && deactivate"
                )
                subprocess.run([shell, "-c", deactivate_cmd])

            # Remove existing virtual environment
            import shutil

            shutil.rmtree(venv_path)
            console.print(
                f"[green]✓ Removed existing environment: {name}[/green]"
            )
        else:
            console.print("[yellow]Operation cancelled.[/yellow]")
            return

    manager = VenvManager()
    success, message = manager.create_venv(name)

    if success:
        venv_info = manager.get_venv_info(name)
        text = Text.assemble(
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
        )
        panel = Panel.fit(
            text,
            title="Virtual Environment Creation Results",
            title_align="left",
            border_style="bright_blue",
        )
        console.print(panel)

        # Prepare to activate virtual environment
        activate_script = venv_path / "bin" / "activate"
        shell, shell_name = get_current_shell()

        # Check if requirements.txt exists
        if Path("requirements.txt").exists():
            if Confirm.ask(
                "\n[yellow]Found requirements.txt. Do you want to install the dependencies?[/yellow]"
            ):
                # Activate virtual environment and upgrade pip
                subprocess.run(
                    [
                        shell,
                        "-c",
                        f"source {activate_script} && pip install --upgrade pip",
                    ],
                    check=True,
                )

                # Install packages in virtual environment
                os.environ["VIRTUAL_ENV"] = str(venv_path)
                os.environ["PATH"] = f"{venv_path}/bin:{os.environ['PATH']}"
                package_manager = PackageManager()
                with open("requirements.txt") as f:
                    packages = [
                        line.strip()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    ]
                for package in packages:
                    if "==" in package:
                        name, version = package.split("==")
                        package_manager.add(name, version)
                    else:
                        package_manager.add(package)

        # Activate virtual environment
        os.execl(
            shell,
            shell_name,
            "-c",
            f"source {activate_script} && exec {shell_name}",
        )
    else:
        text = Text.assemble(
            ("Status: ", "dim"),
            ("✗ Failed", "red"),
            "\n",
            ("Error: ", "dim"),
            (message, "red"),
        )
        panel = Panel.fit(
            text,
            title="Virtual Environment Creation Error",
            title_align="left",
            border_style="red",
        )
        console.print(panel)


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

    console.print(
        f"[yellow]Switching environment:[/yellow]\n"
        f"  From: {current_status}\n"
        f"  To:   [cyan]{venv_display}{project_name}[/cyan]"
    )
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

    console.print(
        f"[yellow]Deactivating environment:[/yellow]\n"
        f"  From: [cyan]{venv_display}{project_name}[/cyan]\n"
        f"  To:   No active environment"
    )
    shell, shell_name = get_current_shell()

    # If virtual environment folder doesn't exist, directly execute python -m venv deactivate
    if not current_venv.exists():
        os.execl(
            shell,
            shell_name,
            "-c",
            f"unset VIRTUAL_ENV && unset PYTHONHOME && export PATH=$(echo $PATH | tr ':' '\n' | grep -v {current_venv}/bin | tr '\n' ':' | sed 's/:$//') && exec {shell_name}",
        )
        return

    # If virtual environment folder exists, use the original method
    deactivate_script = current_venv / "bin" / "activate"
    os.execl(
        shell,
        shell_name,
        "-c",
        f"source {deactivate_script} && deactivate && exec {shell_name}",
    )


@cli.command()
@click.argument("packages", nargs=-1, required=True)
@click.option(
    "--version",
    "-v",
    help="Specific version to install (only works with single package)",
)
def add(packages, version: Optional[str]):
    """Add packages to requirements.txt and install them"""
    manager = PackageManager()
    if version and len(packages) > 1:
        console.print(
            "[yellow]Warning: Version option is ignored when installing multiple packages[/yellow]"
        )
        version = None
    for package in packages:
        manager.add(package, version)


@cli.command()
@click.argument("packages", nargs=-1, required=True)
@click.option(
    "-y",
    is_flag=True,
    help="Automatically confirm all prompts",
)
def remove(packages, y: bool):
    """Remove packages from requirements.txt and uninstall them"""
    manager = PackageManager()
    for package in packages:
        manager.remove(package, auto_confirm=y)


# Add 'rm' as an alias for 'remove'
cli.add_command(remove, "rm")

# Add 'env' as an alias for 'venv'
cli.add_command(venv, "env")


@cli.command(name="list")
@click.option("-a", "--all", is_flag=True, help="List all installed packages")
@click.option("-t", "--tree", is_flag=True, help="Show dependency tree")
def list_packages(all, tree):
    """List installed packages and their dependencies"""
    pm = PackageManager()
    pm.list_packages(show_all=all, show_deps=tree)


@cli.command()
@click.option(
    "-y",
    is_flag=True,
    help="Automatically confirm all prompts",
)
def update(y: bool):
    """Update all packages to their latest versions"""
    manager = PackageManager()
    manager.update_all(auto_confirm=y)


# Add 'up' as an alias for 'update'
cli.add_command(update, "up")


@cli.command()
@click.option(
    "-y",
    is_flag=True,
    help="Automatically confirm all prompts",
)
def fix(y: bool):
    """Fix package inconsistencies"""
    pm = PackageManager()
    pm.fix_packages(auto_confirm=y)


@cli.command()
def release():
    """Build and publish package to PyPI"""
    if not Path("pyproject.toml").exists():
        console.print("[red]No pyproject.toml found in current directory[/red]")
        return

    # Check if twine and build are installed
    required_packages = ["twine", "build"]
    need_install = []
    for pkg in required_packages:
        try:
            __import__(pkg)
        except ImportError:
            need_install.append(pkg)

    # Install required packages
    if need_install:
        console.print("[blue]Installing required packages...[/blue]")
        for pkg in need_install:
            with console.status(
                f"[blue]Installing [cyan]{pkg}[/cyan]...[/blue]",
                spinner="dots",
            ) as status:
                process = subprocess.run(
                    ["pip", "install", pkg],
                    capture_output=True,
                    text=True,
                )
                if process.returncode != 0:
                    console.print(f"[red]Failed to install {pkg}:[/red]")
                    console.print(f"[red]{process.stderr}[/red]")
                    return
                console.print(f"[green]✓ Installed {pkg}[/green]")

    # Remove existing dist directory
    if Path("dist").exists():
        import shutil

        shutil.rmtree("dist")
        console.print("[green]✓ Removed existing dist directory[/green]")

    # Build package
    console.print("\n[blue]Building package...[/blue]")
    with console.status("[blue]Building...[/blue]", spinner="dots") as status:
        process = subprocess.run(
            ["pyproject-build"],
            capture_output=True,
            text=True,
        )
        if process.returncode != 0:
            console.print("[red]Build failed:[/red]")
            console.print(f"[red]{process.stderr}[/red]")
            return
        console.print("[green]✓ Package built successfully[/green]")

    # Upload to PyPI
    console.print("\n[blue]Uploading to PyPI...[/blue]")
    result = subprocess.run(
        ["twine", "upload", "--disable-progress-bar", "dist/*"],
        capture_output=True,
        text=True,
        env={"PYTHONIOENCODING": "utf-8", **os.environ},
    )
    if result.returncode == 0:
        console.print("[green]✓ Package published successfully[/green]")
    else:
        console.print("[red]✗ Upload failed[/red]")
        error_msg = result.stderr or result.stdout

        from rich.text import Text

        # Extract and format error messages
        error_lines = error_msg.splitlines()
        upload_info_shown = False
        for line in error_lines:
            if not line.startswith(("[2K", "[?25")):  # Skip progress bar lines
                if line.strip():
                    # Convert ANSI to plain text
                    clean_line = Text.from_ansi(line.strip()).plain
                    if "Uploading" in clean_line and not upload_info_shown:
                        if "legacy" in clean_line:
                            continue  # Skip the legacy URL line
                        pkg_name = clean_line.split()[-1]
                        console.print(
                            f"[blue]Uploading [cyan]{pkg_name}[/cyan][/blue]"
                        )
                        upload_info_shown = True
                    elif (
                        "HTTPError:" in clean_line
                        or "File already exists" in clean_line
                    ):
                        console.print(f"[red]{clean_line}[/red]")
                    elif not any(
                        skip in clean_line
                        for skip in ["Uploading", "WARNING", "ERROR"]
                    ):
                        console.print(clean_line)

        # Show solution based on error type
        console.print()  # Add empty line before solution
        if "File already exists" in error_msg:
            console.print(
                "[yellow]Solution: Update the version number in [cyan]pyproject.toml[/cyan][/yellow]"
            )
        elif "Invalid credentials" in error_msg:
            console.print(
                "[yellow]Solution: Check your PyPI credentials in [cyan]~/.pypirc[/cyan] or set [cyan]TWINE_USERNAME[/cyan] and [cyan]TWINE_PASSWORD[/cyan][/yellow]"
            )
        elif "400 Bad Request" in error_msg:
            console.print(
                "[yellow]Solution: Check your package metadata in [cyan]pyproject.toml[/cyan][/yellow]"
            )
        elif "403 Forbidden" in error_msg:
            console.print(
                "[yellow]Solution: Verify your upload permissions for this package on PyPI[/yellow]"
            )
        return

    # Clean up temporary packages
    if need_install:
        console.print("\n[blue]Cleaning up temporary packages...[/blue]")
        for pkg in need_install:
            with console.status(
                f"[blue]Removing [cyan]{pkg}[/cyan]...[/blue]",
                spinner="dots",
            ) as status:
                process = subprocess.run(
                    ["pip", "uninstall", "-y", pkg],
                    capture_output=True,
                    text=True,
                )
                if process.returncode == 0:
                    console.print(f"[green]✓ Removed {pkg}[/green]")
                else:
                    console.print(
                        f"[yellow]Warning: Failed to remove {pkg}[/yellow]"
                    )


if __name__ == "__main__":
    cli()
