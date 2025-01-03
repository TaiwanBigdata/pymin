# CLI environment management service
import os
import subprocess
import sys
import venv
import tomllib
from pathlib import Path
from typing import Optional, Tuple, Dict
from rich.console import Console

console = Console()


class VenvManager:
    """CLI environment manager"""

    def __init__(self):
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check if required dependencies are installed"""
        try:
            # 檢查必要的依賴是否安裝
            import click
            import rich
            import requests
            import packaging
            import pandas
        except ImportError as e:
            console.print(f"[red]Missing dependency: {str(e)}[/red]")
            raise

    def create(self, name: str) -> Tuple[bool, str]:
        """Create a new project environment"""
        try:
            # 建立專案目錄
            project_path = Path(name)
            if project_path.exists():
                return False, f"Project directory '{name}' already exists"

            project_path.mkdir(parents=True)

            # 建立基本檔案結構
            (project_path / "src").mkdir()
            (project_path / "tests").mkdir()
            (project_path / "docs").mkdir()

            # 建立 pyproject.toml
            self._create_pyproject_toml(project_path, name)

            return True, f"Project environment created at {project_path}"
        except Exception as e:
            return False, f"Failed to create project: {str(e)}"

    def _create_pyproject_toml(self, project_path: Path, name: str) -> None:
        """Create pyproject.toml with CLI registration"""
        content = f"""[build-system]
requires = ["setuptools>=61.0.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{name}"
version = "0.1.0"
description = "A CLI tool"
requires-python = ">=3.8"
dependencies = [
    "click>=8.0.0",
    "rich>=10.0.0",
]

[project.scripts]
{name} = "{name}.cli:cli"

[tool.setuptools]
package-dir = {{ "" = "src" }}
packages = ["{name}"]
"""
        with open(project_path / "pyproject.toml", "w") as f:
            f.write(content)

    def create_venv(self, name: str) -> Tuple[bool, str]:
        """Create a virtual environment with specified name"""
        try:
            venv_path = Path(name)

            # Check if directory already exists
            if venv_path.exists():
                return False, f"Directory '{name}' already exists"

            # Create virtual environment
            venv.create(venv_path, with_pip=True)

            return True, f"Virtual environment created at {venv_path}"
        except Exception as e:
            return False, f"Failed to create virtual environment: {str(e)}"

    def get_python_version(self) -> str:
        """Get the Python version"""
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def get_project_info(self):
        """Get project information from pyproject.toml"""
        try:
            with open("pyproject.toml", "rb") as f:
                data = tomllib.load(f)
                project = data.get("project", {})
                return {
                    "name": project.get("name", ""),
                    "version": project.get("version", ""),
                    "description": project.get("description", ""),
                    "requires_python": project.get("requires-python", ""),
                    "build_backend": data.get("build-system", {}).get(
                        "build-backend", ""
                    ),
                    "scripts": project.get("scripts", {}),
                }
        except FileNotFoundError:
            return None

    def get_environment_info(self) -> dict:
        """Get current environment information"""
        platform_name = {
            "darwin": "macOS",
            "linux": "Linux",
            "win32": "Windows",
        }.get(sys.platform, sys.platform)

        # Get CPU architecture
        arch = subprocess.check_output(["uname", "-m"], text=True).strip()

        # Get pip version
        pip_version = subprocess.check_output(
            ["pip", "--version"], text=True
        ).split()[1]

        # Check pip for updates (using pip list --outdated)
        pip_update = None
        try:
            output = subprocess.check_output(
                ["pip", "list", "--outdated", "--format=json"],
                text=True,
            )
            import json

            outdated = json.loads(output)
            for pkg in outdated:
                if pkg["name"] == "pip":
                    pip_update = pkg["latest_version"]
                    break
        except:
            pass

        info = {
            "python_version": self.get_python_version(),
            "platform": f"{platform_name} ({arch})",
            "pip_location": subprocess.getoutput("which pip"),
            "pip_version": pip_version,
            "pip_update": pip_update,
            "virtual_env": os.environ.get("VIRTUAL_ENV"),
            "user_scripts": Path.home() / ".local/bin",
            "working_dir": str(Path.cwd()),
        }

        # Add project info if available
        project_info = self.get_project_info()
        if project_info:
            info["project"] = project_info

        return info

    def get_venv_info(self, name: str) -> dict:
        """Get virtual environment information"""
        venv_path = Path(name).absolute()
        python_path = venv_path / "bin" / "python"

        # Get Python version
        python_version = (
            subprocess.check_output(
                [str(python_path), "-V"],
                text=True,
            )
            .strip()
            .replace("Python ", "")
        )

        # Get pip version
        pip_version = subprocess.check_output(
            [str(venv_path / "bin" / "pip"), "-V"],
            text=True,
        ).split()[1]

        return {
            "python_version": python_version,
            "pip_version": pip_version,
            "location": venv_path,
        }
