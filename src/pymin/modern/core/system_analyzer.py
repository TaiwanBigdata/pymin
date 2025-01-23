import json
import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List


class SystemAnalyzer:
    """
    A comprehensive system environment detector that provides information about
    Python installations and platform details
    """

    def __init__(self):
        """Initialize detector with environment variables and platform checks"""
        self.env_vars = os.environ.copy()
        self.is_windows = sys.platform.startswith("win")
        self.current_venv = os.path.dirname(os.path.dirname(sys.executable))

    def _run_shell_command(self, command: str) -> str:
        """Execute shell command and return output"""
        shell = os.environ.get("SHELL", "/bin/zsh")
        cmd = f"{shell} -i -c '{command}'"
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                env=dict(os.environ, PATH=os.environ.get("PATH", "")),
            )
            return result.stdout.strip()
        except subprocess.SubprocessError:
            return ""

    def _is_venv_path(self, path: str) -> bool:
        """
        Check if path is any virtual environment path (venv/poetry)
        """
        normalized_path = os.path.normpath(path)
        venv_patterns = [
            "/venv/",
            "/env/",
            "/venv",
            "/env",
            "/.venv/",
            "/.venv",
            "/poetry/virtualenvs/",
        ]
        return any(pattern in normalized_path for pattern in venv_patterns)

    def get_python_info(self) -> Dict[str, Any]:
        """Get Python installations excluding current virtual environment"""
        paths_output = self._run_shell_command("which -a python3")
        python_paths = [
            p
            for p in paths_output.splitlines()
            if p.strip() and not self._is_venv_path(p)
        ]

        if not python_paths:
            return {
                "python": {
                    "path": "not found",
                    "base_prefix": "unknown",
                    "version": "unknown",
                },
                "pip": {"version": "unknown", "path": "not found"},
            }

        python_path = python_paths[0]
        python_version = self._run_shell_command(
            f"{python_path} --version"
        ).split()[1]

        # Get Python base prefix
        base_prefix_cmd = (
            f'{python_path} -c "import sys; print(sys.base_prefix)"'
        )
        base_prefix = self._run_shell_command(base_prefix_cmd)

        # Get pip info
        pip_paths = [
            p
            for p in self._run_shell_command("which -a pip3").splitlines()
            if p.strip() and not self._is_venv_path(p)
        ]
        pip_path = pip_paths[0] if pip_paths else "not found"
        pip_version = (
            self._run_shell_command(f"{pip_path} --version").split()[1]
            if pip_paths
            else "unknown"
        )

        return {
            "python": {
                "path": python_path,
                "base_prefix": base_prefix,
                "version": python_version,
            },
            "pip": {"version": pip_version, "path": pip_path},
        }

    def _get_darwin_platform_info(self) -> Dict[str, Any]:
        """
        Get detailed Darwin/macOS platform information

        Returns:
            Dictionary containing macOS specific details
        """

        def _run_command(command: list, timeout: int = 3) -> str:
            """Helper function to run command with error handling"""
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=timeout
                )
                return result.stdout.strip() if result.returncode == 0 else ""
            except subprocess.SubprocessError:
                return ""

        # Get system information
        hw_model = _run_command(["sysctl", "-n", "hw.model"])
        arch = _run_command(["uname", "-m"])
        os_version = _run_command(["sw_vers", "-productVersion"])
        build_version = _run_command(["sw_vers", "-buildVersion"])

        # Get processor information
        cpu_brand = _run_command(["sysctl", "-n", "machdep.cpu.brand_string"])
        if not cpu_brand and arch == "arm64":
            cpu_brand = "Apple Silicon"

        # Check Rosetta 2
        is_rosetta = False
        if arch == "x86_64":
            rosetta_check = _run_command(
                ["sysctl", "-n", "sysctl.proc_translated"]
            )
            is_rosetta = rosetta_check == "1"
            if not is_rosetta and cpu_brand:
                is_rosetta = "Apple" in cpu_brand

        return {
            "system": "Darwin",
            "os": "macOS",
            "os_version": os_version or platform.mac_ver()[0],
            "release": platform.release(),
            "machine": arch or platform.machine(),
            "model": hw_model or "Unknown",
            "processor": cpu_brand
            or platform.processor()
            or platform.machine(),
            "build_version": build_version,
            "is_rosetta": is_rosetta,
        }

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about system environment

        Returns:
            Dictionary containing Python, pip and platform information
        """
        # Get Python and pip information
        python_info = self.get_python_info()

        # Get platform specific information
        if sys.platform == "darwin":
            platform_info = self._get_darwin_platform_info()
        else:
            platform_info = {
                "system": platform.system(),
                "os": platform.system(),
                "os_version": platform.version(),
                "release": platform.release(),
                "machine": platform.machine(),
                "processor": platform.processor() or platform.machine(),
                "build_version": "",
                "is_rosetta": False,
            }

        return {**python_info, "platform": platform_info}
