"""Virtual environment deactivation command"""

import click
import os
from ...core.venv_manager import VenvManager
from ...ui.console import print_error


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
