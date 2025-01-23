"""Environment information display formatting and rendering"""

import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from typing import Dict, Any, List
from .style import StyleType as style, SymbolType
import pathlib

console = Console()


def create_env_info_panel(env_info: Dict[str, Any]) -> Panel:
    """Create a panel displaying environment information"""

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
    system_info_display = [
        f"[dim]Python:[/dim] [cyan]{system_python['version']}[/cyan] [dim]({system_python['executable']})[/dim]",
        f"[dim]Pip:[/dim] [cyan]{system_pip['version']}[/cyan] [dim]({system_pip['path']})[/dim]",
        f"[dim]OS:[/dim] [cyan]{platform_info['os']} {platform_info['os_version']}[/cyan] ({platform_info['build']})",
        f"[dim]Architecture:[/dim] [cyan]{platform_info['processor']}[/cyan] ({platform_info['native_arch']})",
        f"[dim]Kernel:[/dim] [cyan]{platform_info['system']} {platform_info['release']}[/cyan]",
    ]

    # Initialize environment status information list
    env_status_info = []

    # Display active environment information
    env_status_info.append("[dim]Active Environment:[/dim]")
    if active_env["has_venv"]:
        # Extract project name and environment name from the full name
        project_name, env_name = active_env["name"].split("(")
        env_status_info.extend(
            [
                f"  [dim]Name:[/dim] [cyan]{project_name}[/cyan][dim]({env_name}[/dim]",
                f"  [dim]Path:[/dim] [cyan]{active_env['path']}[/cyan]",
            ]
        )
    else:
        env_status_info.append("  None")

    # Display current directory environment information
    env_status_info.append("\n[dim]Current Directory:[/dim]")
    if current_env["has_venv"]:
        status = (
            f"[green bold]{SymbolType.SUCCESS} Active[/green bold]"
            if current_env["is_active"]
            else f"[yellow bold]{SymbolType.WARNING} Inactive[/yellow bold]"
        )
        # Extract project name and environment name from the full name
        project_name, env_name = current_env["name"].split("(")
        env_status_info.extend(
            [
                f"  [dim]Name:[/dim] [cyan]{project_name}[/cyan][dim]({env_name}[/dim]",
                f"  [dim]Path:[/dim] [cyan]{current_env['path']}[/cyan]",
                f"  [dim]Status:[/dim] {status}",
            ]
        )
    else:
        env_status_info.append("  [yellow]No virtual environment[/yellow]")
        env_status_info.append(
            "  [dim]Run:[/dim] [cyan]pmm venv[/cyan] [dim]to create one[/dim]"
        )

    # Combine all sections into final display content
    content = (
        "[white bold]System Information[/white bold]\n"
        + "\n".join(system_info_display)
        + "\n\n[white bold]Virtual Environment Status[/white bold]\n"
        + "\n".join(env_status_info)
    )

    return Panel.fit(
        content,
        title="Environment Information",
        title_align="left",
        border_style="blue",
        padding=(1, 2),
    )


def display_environment_info(env_info: Dict[str, Any]) -> None:
    """Display formatted environment information"""
    # Check for the presence of environment status information
    if not env_info.get("environment_status"):
        console.print(
            "\n[yellow]No virtual environment information available.[/yellow]"
        )
        return

    # Display the formatted environment information panel
    console.print("\n")
    console.print(create_env_info_panel(env_info))
    console.print("\n")
