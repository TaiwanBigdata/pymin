from abc import ABC, abstractmethod
from typing import Dict, Any, List, TypedDict
import platform
import subprocess
import sys
import os
import json
import re
from pathlib import Path


class Platform(TypedDict):
    system: str  # System name (Darwin/Windows/Linux)
    os: str  # OS name (macOS/Windows 11/Ubuntu)
    os_version: str  # OS version
    arch: str  # Current architecture
    native_arch: str  # Native architecture
    model: str  # Hardware model
    processor: str  # CPU info
    release: str  # Kernel release version
    build: str  # Build number
    is_emulated: bool


class SystemInfo(TypedDict):
    platform: Platform
    python: Dict[str, str]
    pip: Dict[str, str]


class CommandRunner:
    @staticmethod
    def run_shell(command: str, shell: str = "/bin/zsh") -> str:
        try:
            result = subprocess.run(
                f"{shell} -i -c '{command}'",
                shell=True,
                capture_output=True,
                text=True,
                env=dict(os.environ, PATH=os.environ.get("PATH", "")),
            )
            return result.stdout.strip()
        except subprocess.SubprocessError:
            return ""

    @staticmethod
    def run_command(command: List[str], timeout: float = 1.0) -> str:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            return ""


class PythonInfo:
    def __init__(self):
        self.current_venv = os.path.dirname(os.path.dirname(sys.executable))

    def _is_venv_path(self, path: str) -> bool:
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

    def get_info(self) -> Dict[str, Dict[str, str]]:
        paths_output = CommandRunner.run_shell("which -a python3")
        python_paths = [
            p
            for p in paths_output.splitlines()
            if p.strip() and not self._is_venv_path(p)
        ]

        if not python_paths:
            return {
                "python": {
                    "executable": "not found",
                    "base_prefix": "unknown",
                    "version": "unknown",
                },
                "pip": {"version": "unknown", "path": "not found"},
            }

        python_path = python_paths[0]
        python_version = CommandRunner.run_shell(
            f"{python_path} --version"
        ).split()[1]
        base_prefix = CommandRunner.run_shell(
            f'{python_path} -c "import sys; print(sys.base_prefix)"'
        )

        pip_paths = [
            p
            for p in CommandRunner.run_shell("which -a pip3").splitlines()
            if p.strip() and not self._is_venv_path(p)
        ]
        pip_path = pip_paths[0] if pip_paths else "not found"
        pip_version = (
            CommandRunner.run_shell(f"{pip_path} --version").split()[1]
            if pip_paths
            else "unknown"
        )

        return {
            "python": {
                "executable": python_path,
                "base_prefix": base_prefix,
                "version": python_version,
            },
            "pip": {"version": pip_version, "path": pip_path},
        }


class PlatformDetector(ABC):
    @abstractmethod
    def get_info(self) -> Platform:
        pass


class DarwinDetector(PlatformDetector):
    class Command:
        ARCH = ["sysctl", "-n", "hw.optional.arm64"]
        CURRENT_ARCH = ["uname", "-m"]
        ROSETTA = ["sysctl", "-n", "sysctl.proc_translated"]
        MODEL = ["sysctl", "-n", "hw.model"]
        OS_VERSION = ["sw_vers", "-productVersion"]
        BUILD = ["sw_vers", "-buildVersion"]
        CPU = ["sysctl", "-n", "machdep.cpu.brand_string"]
        DARWIN_VERSION = ["uname", "-r"]

    def get_info(self) -> Platform:
        is_arm64 = CommandRunner.run_command(self.Command.ARCH) == "1"
        current_arch = CommandRunner.run_command(self.Command.CURRENT_ARCH)
        is_rosetta = (
            CommandRunner.run_command(self.Command.ROSETTA) == "1"
            if current_arch == "x86_64"
            else False
        )
        darwin_version = CommandRunner.run_command(self.Command.DARWIN_VERSION)

        return Platform(
            system="Darwin",
            os="macOS",
            os_version=CommandRunner.run_command(self.Command.OS_VERSION),
            arch=current_arch,
            native_arch="arm64" if is_arm64 else current_arch,
            model=CommandRunner.run_command(self.Command.MODEL),
            processor=CommandRunner.run_command(self.Command.CPU),
            release=darwin_version,
            build=CommandRunner.run_command(self.Command.BUILD),
            is_emulated=is_rosetta,
        )


class WindowsDetector(PlatformDetector):
    def get_info(self) -> Platform:
        win_ver = platform.win32_ver()
        os_version = platform.version()
        return Platform(
            system="Windows",
            os=f"Windows {win_ver[0]}",
            os_version=os_version,
            arch=platform.machine(),
            native_arch=platform.machine(),
            model=platform.machine(),
            processor=platform.processor(),
            release=os_version,
            build=os_version,
            is_emulated=False,
        )


class LinuxDetector(PlatformDetector):
    def get_info(self) -> Platform:
        kernel_release = platform.release()
        os_version = self._get_os_version()
        return Platform(
            system="Linux",
            os=self._get_distro(),
            os_version=os_version,
            arch=platform.machine(),
            native_arch=platform.machine(),
            model=platform.machine(),
            processor=self._get_cpu_info(),
            release=kernel_release,
            build=os_version,
            is_emulated=False,
        )

    def _get_distro(self) -> str:
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=")[1].strip().strip('"')
        except (OSError, IndexError):
            return "Linux"
        return "Linux"

    def _get_os_version(self) -> str:
        try:
            with open("/etc/os-release") as f:
                version_id = ""
                build_id = ""
                for line in f:
                    if line.startswith("VERSION_ID="):
                        version_id = line.split("=")[1].strip().strip('"')
                    elif line.startswith("BUILD_ID="):
                        build_id = line.split("=")[1].strip().strip('"')
                return build_id if build_id else version_id
        except (OSError, IndexError):
            return platform.version()
        return platform.version()

    def _get_cpu_info(self) -> str:
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":")[1].strip()
        except (OSError, IndexError):
            return platform.processor()
        return platform.processor()


class SystemAnalyzer:
    def __init__(self):
        self.python_info = PythonInfo()
        if sys.platform.startswith("darwin"):
            self.platform_detector = DarwinDetector()
        elif sys.platform.startswith("win"):
            self.platform_detector = WindowsDetector()
        else:
            self.platform_detector = LinuxDetector()

    def get_system_info(self) -> SystemInfo:
        platform_info = self.platform_detector.get_info()
        python_data = self.python_info.get_info()

        return SystemInfo(
            platform=platform_info,
            python=python_data["python"],
            pip=python_data["pip"],
        )
