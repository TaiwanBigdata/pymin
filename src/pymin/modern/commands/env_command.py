"""Environment management commands implementation"""

import click
from ..core.venv_manager import VenvManager
from ..ui.env_view import display_environment_info
from rich.console import Console
from rich.status import Status
from pathlib import Path
import os
import sys

console = Console()


@click.command()
def info():
    """Show environment information"""
    try:
        with Status(
            "[cyan]Getting environment information...[/cyan]", console=console
        ) as status:
            manager = VenvManager()
            env_info = manager.get_environment_info()
        display_environment_info(env_info)
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")


@click.command()
@click.argument("venv_path", required=False, type=click.Path())
def activate(venv_path: str = None):
    """Activate virtual environment"""
    try:
        manager = VenvManager()
        if venv_path:
            venv_path = Path(venv_path)

        # Show status message
        print_info("Activating virtual environment...")

        # Activate the environment (this will replace the current shell)
        manager.activate_environment(venv_path)
    except Exception as e:
        print_error(f"Error: {str(e)}")


@click.command()
def deactivate():
    """Deactivate virtual environment"""
    try:
        manager = VenvManager()

        # Show status message
        print_info("Deactivating virtual environment...")

        # Deactivate the environment (this will replace the current shell)
        manager.deactivate_environment()
    except Exception as e:
        print_error(f"Error: {str(e)}")


# Add missing imports
from ..ui.console import print_success, print_error, print_info
