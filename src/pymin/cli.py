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
from pathlib import Path
import shutil
import tempfile
import sys
import re

# Force color output
console = Console(force_terminal=True, color_system="auto")


def _get_shell_script_path(script_name: str) -> Path:
    """Get the path to a shell script"""
    package_dir = Path(__file__).parent
    script_path = package_dir / "shell" / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Shell script not found: {script_name}")
    return script_path


def _clean_rc_file(rc_file: str) -> None:
    """Clean up RC file by removing PyMin configuration"""
    if not os.path.exists(rc_file):
        return

    with open(rc_file, "r") as f:
        lines = f.readlines()

    # Find PyMin configuration block
    start_idx = -1
    end_idx = -1
    for i, line in enumerate(lines):
        if "# PyMin Configuration" in line:
            start_idx = i
            end_idx = i + 2  # Configuration block is 3 lines
            break

    if start_idx >= 0:
        # Remove the configuration block
        lines = lines[:start_idx] + lines[end_idx + 1 :]

        # Write back to file
        with open(rc_file, "w") as f:
            f.writelines(lines)


@click.group()
def cli():
    """PyPI Package Name Checker"""
    pass


@cli.group()
def shell():
    """Shell integration management"""
    pass


@shell.command()
def install():
    """Install shell integration"""
    try:
        script_path = _get_shell_script_path("install.sh")
        subprocess.run(
            ["bash", str(script_path)],
            check=True,
            env={**os.environ, "SHELL": "/bin/bash"},
        )
    except Exception as e:
        console.print(
            f"[red]Failed to install shell integration: {str(e)}[/red]"
        )


@shell.command()
def uninstall():
    """Uninstall shell integration"""
    try:
        pymin_home = Path.home() / ".pymin"

        # Check if we're running from ~/.pymin/bin
        current_script = Path(sys.argv[0]).resolve()
        if str(pymin_home) in str(current_script):
            console.print(
                Panel(
                    "Cannot uninstall while using PyMin commands.\n"
                    "Please use the Python module directly:\n\n"
                    "[cyan]python -m pymin shell uninstall[/cyan]",
                    title="[yellow]Warning[/yellow]",
                    width=80,
                )
            )
            return

        # Clean up RC files first
        for rc_file in [Path.home() / ".zshrc", Path.home() / ".bashrc"]:
            if rc_file.exists():
                if rc_file.is_symlink():
                    real_path = rc_file.resolve()
                    with open(real_path) as f:
                        content = f.read()
                    # Remove PyMin configuration block and extra newlines
                    new_content = (
                        re.sub(
                            r"\n*# PyMin Configuration\n[^\n]+\n[^\n]+\n*",
                            "\n",
                            content,
                        ).rstrip()
                        + "\n"
                    )  # Ensure single newline at end
                    with open(real_path, "w") as f:
                        f.write(new_content)
                    console.print(
                        f"Removed PyMin configuration from: {real_path} (via symlink {rc_file})"
                    )
                else:
                    with open(rc_file) as f:
                        content = f.read()
                    # Remove PyMin configuration block and extra newlines
                    new_content = (
                        re.sub(
                            r"\n*# PyMin Configuration\n[^\n]+\n[^\n]+\n*",
                            "\n",
                            content,
                        ).rstrip()
                        + "\n"
                    )  # Ensure single newline at end
                    with open(rc_file, "w") as f:
                        f.write(new_content)
                    console.print(
                        f"Removed PyMin configuration from: {rc_file}"
                    )

        # Then remove PyMin directory
        if pymin_home.exists():
            shutil.rmtree(str(pymin_home))
            console.print(f"Removed PyMin directory: {pymin_home}")

        console.print("\nPyMin shell integration uninstalled successfully!")
        console.print("Please restart your shell or source your RC file.")

    except Exception as e:
        console.print(
            f"[red]Failed to uninstall shell integration: {str(e)}[/red]"
        )


@cli.command()
@click.option(
    "--path", "-p", help="Path to create virtual environment", default="env"
)
def venv(path):
    """Create a new virtual environment"""
    manager = VenvManager()
    success, message = manager.create(path)
    if success:
        console.print(Panel(Text(message, style="green"), width=80))
        # Show activation command
        console.print("\nTo activate the virtual environment, run:")
        console.print(f"[cyan]pm activate[/cyan]")
    else:
        console.print(Panel(Text(message, style="red"), width=80))


@cli.command()
@click.option("--path", "-p", help="Path to virtual environment", default="env")
def activate(path):
    """Activate virtual environment"""
    console.print(
        Panel(
            Text.assemble(
                "This command must be run through shell integration.\n",
                "Please install shell integration first:\n\n",
                "[cyan]pm shell install[/cyan]",
            ),
            title="Shell Integration Required",
            width=80,
        )
    )


@cli.command()
def deactivate():
    """Deactivate virtual environment"""
    console.print(
        Panel(
            Text.assemble(
                "This command must be run through shell integration.\n",
                "Please install shell integration first:\n\n",
                "[cyan]pm shell install[/cyan]",
            ),
            title="Shell Integration Required",
            width=80,
        )
    )


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
        width=80,
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


if __name__ == "__main__":
    cli()
