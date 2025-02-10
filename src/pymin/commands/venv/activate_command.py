"""Virtual environment activation command"""

import click
import os
from pathlib import Path
from ...core.venv_manager import VenvManager
from ...ui.console import print_error


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
