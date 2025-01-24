"""Environment management commands implementation"""

import click
from ..core.venv_manager import VenvManager
from ..ui.env_view import display_environment_info
from rich.console import Console
from pathlib import Path
import os
import sys
from ..ui.console import (
    print_success,
    print_error,
    print_info,
    progress_status,
    console,
)


@click.command()
def info():
    """Show environment information"""
    try:
        with progress_status("Getting environment information...") as status:
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
        shell, shell_name, shell_command = manager._prepare_activation(
            venv_path
        )
        if shell_command:
            os.execl(shell, shell_name, "-c", shell_command)
    except Exception as e:
        print_error(f"Error: {str(e)}")


@click.command()
def deactivate():
    """Deactivate virtual environment"""
    try:
        manager = VenvManager()
        shell, shell_name, shell_command = manager._prepare_deactivation()
        if shell_command:
            os.execl(shell, shell_name, "-c", shell_command)
    except Exception as e:
        print_error(f"Error: {str(e)}")
