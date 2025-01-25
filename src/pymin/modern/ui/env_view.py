"""Environment information display formatting and rendering"""

import json
from rich.table import Table
from rich.text import Text
from typing import Dict, Any, List
from .style import StyleType as style, SymbolType
from .console import display_panel, console
import pathlib


def create_env_info_panel(env_info: Dict[str, Any]) -> Text:
    """Create environment information panel content"""

    # Retrieve environment status information
    env_status = env_info["environment_status"]
    current_env = env_status["current_environment"]
    active_env = env_status["active_environment"]

    # Retrieve system information
    system_info = env_info["system"]
    system_python = system_info["python"]
    system_pip = system_info["pip"]
    platform_info = system_info["platform"]

    # Format system information section
    content = Text()
    content.append("System Information", style="white bold")

    # Add Python info
    content.append("\nPython: ", style="dim")
    content.append(system_python["version"], style="cyan")
    content.append(" (", style="dim")
    content.append(system_python["executable"], style="dim")
    content.append(")", style="dim")

    # Add Pip info
    content.append("\nPip: ", style="dim")
    content.append(system_pip["version"], style="cyan")
    content.append(" (", style="dim")
    content.append(system_pip["path"], style="dim")
    content.append(")", style="dim")

    # Add OS info
    content.append("\nOS: ", style="dim")
    content.append(
        f"{platform_info['os']} {platform_info['os_version']}", style="cyan"
    )
    content.append(f" ({platform_info['build']})")

    # Add Architecture info
    content.append("\nArchitecture: ", style="dim")
    content.append(platform_info["processor"], style="cyan")
    content.append(f" ({platform_info['native_arch']})", style="white")

    # Add Kernel info
    content.append("\nKernel: ", style="dim")
    content.append(
        f"{platform_info['system']} {platform_info['release']}", style="cyan"
    )

    # Add Virtual Environment Status section
    content.append("\n\nVirtual Environment Status", style="white bold")

    # Add Active Environment info
    content.append("\nActive Environment:", style="dim")
    if active_env["has_venv"]:
        project_name, env_name = active_env["name"].split("(")
        env_name = env_name.rstrip(")")  # Remove trailing parenthesis
        content.append("\n  Name: ", style="dim")
        content.append(project_name, style="cyan")
        content.append(" (", style="dim")
        content.append(env_name, style="dim")
        content.append(")", style="dim")
        content.append("\n  Path: ", style="dim")
        content.append(active_env["path"], style="cyan")
    else:
        content.append("\n  None")

    # Add Current Directory info
    content.append("\n\nCurrent Directory:", style="dim")
    if current_env["has_venv"]:
        project_name, env_name = current_env["name"].split("(")
        env_name = env_name.rstrip(")")  # Remove trailing parenthesis
        content.append("\n  Name: ", style="dim")
        content.append(project_name, style="cyan")
        content.append(" (", style="dim")
        content.append(env_name, style="dim")
        content.append(")", style="dim")
        content.append("\n  Path: ", style="dim")
        content.append(current_env["path"], style="cyan")
        content.append("\n  Status: ", style="dim")
        if current_env["is_active"]:
            content.append("✓ Active", style="green bold")
        else:
            content.append("⚠ Inactive", style="yellow bold")
    else:
        content.append("\n  No virtual environment", style="yellow")
        content.append("\n  Run: ", style="dim")
        content.append("pmm venv", style="cyan")
        content.append(" to create one", style="dim")

    return content


def display_environment_info(env_info: Dict[str, Any]) -> None:
    """Display formatted environment information"""
    # Check for the presence of environment status information
    if not env_info.get("environment_status"):
        console.print(
            "[yellow]No virtual environment information available.[/yellow]"
        )
        return

    # Display the formatted environment information panel
    display_panel("Environment Information", create_env_info_panel(env_info))
