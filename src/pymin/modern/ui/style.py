# Console styling definitions
from enum import Enum


class Colors:
    """Color definitions for console output."""

    # Primary colors
    CYAN = "cyan"
    BLUE = "blue"
    GREEN = "green"
    RED = "red"
    YELLOW = "yellow"

    # Variants
    BRIGHT_BLUE = "bright_blue"
    BRIGHT_GREEN = "bright_green"
    BRIGHT_RED = "bright_red"
    BRIGHT_YELLOW = "bright_yellow"

    # Special
    DIM = "dim"
    BOLD = "bold"


class Styles:
    """Style definitions combining colors and attributes."""

    # Status styles
    SUCCESS = f"{Colors.BRIGHT_GREEN} bold"
    ERROR = f"{Colors.BRIGHT_RED} bold"
    WARNING = Colors.YELLOW
    INFO = Colors.BLUE

    # Text styles
    BOLD = Colors.BOLD
    DIM = Colors.DIM

    # Element styles
    HEADER = f"{Colors.BRIGHT_BLUE} bold"
    LINK = Colors.BLUE
    PATH = Colors.CYAN
    VERSION = Colors.CYAN


class Symbols:
    """Unicode symbols for status indicators."""

    SUCCESS = "✓"  # Check mark
    ERROR = "✗"  # Cross mark
    WARNING = "⚠"  # Warning sign
    INFO = "ℹ"  # Info sign
    BULLET = "•"  # List bullet
    ARROW = "→"  # Arrow
    DOTS = "…"  # Ellipsis
