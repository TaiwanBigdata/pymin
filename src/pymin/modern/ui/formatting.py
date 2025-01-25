"""Text formatting patterns for UI components"""

from rich.text import Text as RichText
from typing import Optional, Dict, Any


class Text(RichText):
    """Enhanced Text class with formatting methods"""

    def append_header(
        self,
        content: str,
        style: str = "white bold",
        top_margin: bool = True,
        add_newline: bool = True,
    ) -> "Text":
        """Append a header to the Text object

        Args:
            content: The header content
            style: Style for the header (default: white bold)
            top_margin: Whether to add a newline before the header (default: True)
            add_newline: Whether to add a newline after the header (default: True)

        Returns:
            self for method chaining
        """
        if top_margin:
            self.append("\n")
        self.append(content, style=style)
        if add_newline:
            self.append("\n")
        return self

    def append_field(
        self,
        label: str,
        value: str,
        *,  # Force keyword arguments
        note: Optional[str] = None,
        label_style: str = "dim",
        value_style: str = "cyan",
        note_style: str = "dim",
        indent: int = 0,
        note_format: str = " ({note})",
        align: bool = False,
        min_label_width: Optional[int] = None,
        add_newline: bool = True,
    ) -> "Text":
        """Append a field with optional alignment and note

        Args:
            label: The field label
            value: The field value
            note: Optional note to display (replaces path)
            label_style: Style for the label (default: dim)
            value_style: Style for the value (default: cyan)
            note_style: Style for the note (default: dim)
            indent: Number of indentation levels (default: 0)
            note_format: Format string for the note (default: " ({note})")
            align: Whether to align the values (default: False)
            min_label_width: Minimum width for label alignment (default: None)
            add_newline: Whether to add a newline after the field (default: True)

        Returns:
            self for method chaining
        """
        # Calculate indentation
        indent_str = " " * (indent * 2)

        # Handle alignment
        if align:
            # Update maximum label width
            label_width = len(label)
            if min_label_width:
                label_width = max(label_width, min_label_width)
            self._max_label_width = max(self._max_label_width, label_width)

            # Format label with alignment
            formatted_label = f"{indent_str}{label:<{self._max_label_width}}"
        else:
            formatted_label = f"{indent_str}{label}:"

        # Append label
        self.append(formatted_label, style=label_style)
        self.append(" ")

        # Append value
        self.append(value, style=value_style)

        # Append note if provided
        if note:
            self.append(note_format.format(note=note), style=note_style)

        # Add newline if requested
        if add_newline:
            self.append("\n")

        return self

    def append_field_with_path(
        self,
        label: str,
        value: str,
        path: str,
        value_style: str = "cyan",
        path_style: str = "dim",
        label_style: str = "dim",
        indent: int = 0,
    ) -> "Text":
        """Append a labeled field with path to the Text object

        Args:
            label: The field label
            value: The field value
            path: The path to display in parentheses
            value_style: Style for the value (default: cyan)
            path_style: Style for the path and parentheses (default: dim)
            label_style: Style for the label (default: dim)
            indent: Number of indentation levels (default: 0)

        Returns:
            self for method chaining
        """
        self.append_field(
            label,
            value,
            value_style=value_style,
            label_style=label_style,
            indent=indent,
        )
        self.append(" (", style=path_style)
        self.append(path, style=path_style)
        self.append(")", style=path_style)
        return self

    def append_value_with_extra(
        self,
        value: str,
        extra: str,
        value_style: str = "cyan",
        extra_style: str = "dim",
    ) -> "Text":
        """Append a value with extra information in parentheses

        Args:
            value: The main value
            extra: Extra information to display in parentheses
            value_style: Style for the value (default: cyan)
            extra_style: Style for the extra info and parentheses (default: dim)

        Returns:
            self for method chaining
        """
        self.append(value, style=value_style)
        self.append(" (", style=extra_style)
        self.append(extra, style=extra_style)
        self.append(")", style=extra_style)
        return self

    def append_env_info(
        self,
        env_data: Dict[str, Any],
        *,  # Force keyword arguments
        indent: int = 0,
        name_style: str = "cyan",
        path_style: str = "cyan",
        label_style: str = "dim",
    ) -> "Text":
        """Append environment information to the Text object"""
        if not env_data["has_venv"]:
            self.append("\n  None")
            return self

        project_name, env_name = env_data["name"].split("(")
        env_name = env_name.rstrip(")")

        # Add Name field
        self.append_field(
            "Name",
            project_name,
            note=env_name,
            label_style=label_style,
            value_style=name_style,
            note_style=label_style,
            indent=indent,
        )

        # Add Path field
        self.append_field(
            "Path",
            env_data["path"],
            label_style=label_style,
            value_style=path_style,
            indent=indent,
        )

        return self
