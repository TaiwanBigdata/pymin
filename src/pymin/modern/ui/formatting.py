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
    ) -> "Text":
        """Append a header to the Text object

        Args:
            content: The header content
            style: Style for the header (default: white bold)
            top_margin: Whether to add a newline before the header (default: True)

        Returns:
            self for method chaining
        """
        if top_margin:
            self.append("\n\n")
        self.append(content, style=style)
        return self

    def append_field(
        self,
        label: str,
        value: str,
        value_style: str = "cyan",
        label_style: str = "dim",
        prefix: str = "",
    ) -> "Text":
        """Append a labeled field to the Text object

        Args:
            label: The field label
            value: The field value
            value_style: Style for the value (default: cyan)
            label_style: Style for the label (default: dim)
            prefix: Optional prefix for indentation

        Returns:
            self for method chaining
        """
        self.append(f"\n{prefix}{label}: ", style=label_style)
        self.append(value, style=value_style)
        return self

    def append_field_with_path(
        self,
        label: str,
        value: str,
        path: str,
        value_style: str = "cyan",
        path_style: str = "dim",
        label_style: str = "dim",
        prefix: str = "",
    ) -> "Text":
        """Append a labeled field with path to the Text object

        Args:
            label: The field label
            value: The field value
            path: The path to display in parentheses
            value_style: Style for the value (default: cyan)
            path_style: Style for the path and parentheses (default: dim)
            label_style: Style for the label (default: dim)
            prefix: Optional prefix for indentation

        Returns:
            self for method chaining
        """
        self.append_field(label, value, value_style, label_style, prefix)
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
        prefix: str = "",
        name_style: str = "cyan",
        path_style: str = "cyan",
        label_style: str = "dim",
    ) -> "Text":
        """Append environment information to the Text object"""
        if not env_data["has_venv"]:
            self.append(f"\n{prefix}None" if prefix else "\n  None")
            return self

        project_name, env_name = env_data["name"].split("(")
        env_name = env_name.rstrip(")")

        # Add Name field
        self.append(
            f"\n{prefix}Name: " if prefix else "\n  Name: ", style=label_style
        )
        self.append(project_name, style=name_style)
        self.append(" (", style=label_style)
        self.append(env_name, style=label_style)
        self.append(")", style=label_style)

        # Add Path field
        self.append(
            f"\n{prefix}Path: " if prefix else "\n  Path: ", style=label_style
        )
        self.append(env_data["path"], style=path_style)

        return self
