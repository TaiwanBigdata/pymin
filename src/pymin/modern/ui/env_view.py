"""Environment information display formatting and rendering"""

import json
from rich.table import Table
from typing import Dict, Any, List
from .style import StyleType as style
from .console import display_panel, console
from .formatting import Text
import pathlib


def create_env_info_panel(env_info: Dict[str, Any]) -> Text:
    """Create environment information panel content"""
    # Retrieve information
    env_status = env_info["environment_status"]
    system_info = env_info["system"]
    current_env = env_status["current_environment"]

    # Create base content with system information
    content = (
        Text()
        # System Information section
        .append_header("System Information", top_margin=False)
        .append_field_with_path(
            "Python",
            system_info["python"]["version"],
            system_info["python"]["executable"],
        )
        .append_field_with_path(
            "Pip", system_info["pip"]["version"], system_info["pip"]["path"]
        )
        .append_field_with_path(
            "OS",
            f"{system_info['platform']['os']} {system_info['platform']['os_version']}",
            system_info["platform"]["build"],
        )
        .append_field_with_path(
            "Architecture",
            system_info["platform"]["processor"],
            system_info["platform"]["native_arch"],
            path_style="white",
        )
        .append_field(
            "Kernel",
            f"{system_info['platform']['system']} {system_info['platform']['release']}",
        )
    )

    # Add Virtual Environment section
    content.append_header("Virtual Environment Status")

    # Add Active Environment info
    content.append_field("Active Environment", "", label_style="dim")
    if env_status["active_environment"]["has_venv"]:
        content.append_env_info(env_status["active_environment"])
    else:
        content.append("\n  None")

    # Add Current Directory info
    if current_env["has_venv"]:
        (
            content.append_header("Current Directory", style="dim")
            .append_env_info(current_env)
            .append_field(
                "Status",
                "✓ Active" if current_env["is_active"] else "⚠ Inactive",
                value_style=(
                    "green bold" if current_env["is_active"] else "yellow bold"
                ),
                prefix="  ",
            )
        )
    else:
        (
            content.append_header("Current Directory", style="dim")
            .append("\n  No virtual environment", style="yellow")
            .append("\n  Run: ", style="dim")
            .append("pmm venv", style="cyan")
            .append(" to create one", style="dim")
        )

    return content


def display_environment_info(env_info: Dict[str, Any]) -> None:
    """Display formatted environment information"""
    if not env_info.get("environment_status"):
        console.print(
            "[yellow]No virtual environment information available.[/yellow]"
        )
        return

    display_panel("Environment Information", create_env_info_panel(env_info))
