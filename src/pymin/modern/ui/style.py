"""Style definitions for consistent UI appearance"""

from rich.style import Style
from rich.theme import Theme

# Color constants
COLORS = {
    "success": "green",
    "error": "red",
    "warning": "yellow",
    "info": "blue",
    "highlight": "cyan",
    "dim": "bright_black",
}

# Style definitions
STYLES = {
    # Title styles
    "title": Style(color="cyan", bold=True),
    "subtitle": Style(color="blue", bold=True),
    # Status styles
    "success": Style(color="green", bold=True),
    "error": Style(color="red", bold=True),
    "warning": Style(color="yellow"),
    "info": Style(color="blue"),
    # Package status styles
    "normal": Style(color="green"),
    "redundant": Style(color="yellow"),
    "not_installed": Style(color="red"),
    "not_in_requirements": Style(color="blue"),
    "version_mismatch": Style(color="red"),
    # Package related styles
    "package_name": Style(color="cyan"),
    "package_version": Style(color="bright_black"),
    "package_dependency": Style(dim=True),
    # Environment related styles
    "venv_active": Style(color="green", bold=True),
    "venv_inactive": Style(color="yellow"),
    "venv_path": Style(color="blue"),
    "env_name": Style(color="green"),
    "env_path": Style(color="bright_black"),
    # Other styles
    "highlight": Style(color="cyan"),
    "dim": Style(dim=True),
    "url": Style(color="blue", underline=True),
}

# Status symbols
SYMBOLS = {
    "success": "✓",
    "error": "✗",
    "warning": "⚠",
    "info": "ℹ",
    # Package status symbols
    "normal": "✓",
    "redundant": "⚠",
    "not_installed": "✗",
    "not_in_requirements": "△",
    "version_mismatch": "≠",
    "arrow": "→",
    "bullet": "•",
    "tree_branch": "├──",
    "tree_last": "└──",
    "tree_vertical": "│",
}

# Theme definition
THEME = Theme(
    {
        "success": f"bold {COLORS['success']}",
        "error": f"bold {COLORS['error']}",
        "warning": COLORS["warning"],
        "info": COLORS["info"],
        "highlight": COLORS["highlight"],
        "dim": COLORS["dim"],
    }
)


def get_status_symbol(status: str) -> str:
    """Get status symbol for given status"""
    return SYMBOLS.get(status, "•")


def get_style(style_name: str) -> Style:
    """Get style for given style name"""
    return STYLES.get(style_name, Style())
