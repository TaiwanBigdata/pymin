# Virtual environment management service providing environment creation and activation
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple
from rich.console import Console

console = Console()


class VenvManager:
    """Virtual environment manager"""

    def __init__(self):
        self.venv_path = Path("env")
        self.activate_script = self.venv_path / "bin" / "activate"
        if sys.platform == "win32":
            self.activate_script = self.venv_path / "Scripts" / "activate.bat"

    def create(self, path: Optional[str] = None) -> Tuple[bool, str]:
        """Create a new virtual environment"""
        if path:
            self.venv_path = Path(path)
            self.activate_script = self.venv_path / "bin" / "activate"
            if sys.platform == "win32":
                self.activate_script = (
                    self.venv_path / "Scripts" / "activate.bat"
                )

        try:
            if self.venv_path.exists():
                return (
                    False,
                    f"Virtual environment already exists at {self.venv_path}",
                )

            subprocess.run(
                [sys.executable, "-m", "venv", str(self.venv_path)], check=True
            )
            return True, f"Virtual environment created at {self.venv_path}"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to create virtual environment: {str(e)}"

    def get_activate_command(self) -> str:
        """Get the activation command for the current shell"""
        if sys.platform == "win32":
            return str(self.activate_script)
        return f"source {self.activate_script}"

    def get_deactivate_command(self) -> str:
        """Get the deactivation command"""
        return "deactivate"

    def is_active(self) -> bool:
        """Check if a virtual environment is active"""
        return "VIRTUAL_ENV" in os.environ

    def get_current_venv(self) -> Optional[str]:
        """Get the path of current active virtual environment"""
        if self.is_active():
            venv_path = os.environ.get("VIRTUAL_ENV")
            return str(Path(venv_path).resolve())
        return None
