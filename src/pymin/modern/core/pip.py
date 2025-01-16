# Pip operations and utilities
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import subprocess
import sys

from .exceptions import PipError


class PipWrapper:
    """Wrapper for pip command line interface."""

    def __init__(self, python_path: Optional[str] = None):
        """
        Initialize pip wrapper.

        Args:
            python_path: Optional path to Python executable
        """
        self.python_path = python_path or sys.executable

    def run(self, *args: str, capture_output: bool = True) -> Tuple[str, str]:
        """
        Run pip command with given arguments.

        Args:
            *args: Command arguments
            capture_output: Whether to capture command output

        Returns:
            Tuple of (stdout, stderr) if capture_output is True

        Raises:
            PipError: If command fails
        """
        cmd = [self.python_path, "-m", "pip", *args]
        env = {"PIP_DISABLE_PIP_VERSION_CHECK": "1"}

        try:
            if capture_output:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                )
                stdout, stderr = process.communicate()
            else:
                process = subprocess.Popen(cmd, env=env)
                process.wait()
                stdout = stderr = ""

            if process.returncode != 0:
                raise PipError(
                    f"Pip command failed: {' '.join(cmd)}",
                    details=stderr.strip() if capture_output else None,
                )

            return stdout.strip(), stderr.strip()

        except Exception as e:
            if isinstance(e, PipError):
                raise
            raise PipError(
                f"Failed to run pip command: {' '.join(cmd)}",
                details=str(e),
            )

    def install(
        self,
        package: str,
        version: Optional[str] = None,
        upgrade: bool = False,
        editable: bool = False,
        requirements: bool = False,
        no_deps: bool = False,
        pre: bool = False,
    ) -> None:
        """
        Install a package.

        Args:
            package: Package name or requirements file path
            version: Optional version constraint
            upgrade: Whether to upgrade existing package
            editable: Whether to install in editable mode
            requirements: Whether package is a requirements file
            no_deps: Whether to skip dependencies
            pre: Whether to include pre-release versions

        Raises:
            PipError: If installation fails
        """
        args = ["install"]

        if upgrade:
            args.append("--upgrade")
        if editable:
            args.append("-e")
        if requirements:
            args.append("-r")
        if no_deps:
            args.append("--no-deps")
        if pre:
            args.append("--pre")

        if version and not requirements:
            package = f"{package}=={version}"

        args.append(package)
        self.run(*args)

    def uninstall(self, package: str, yes: bool = True) -> None:
        """
        Uninstall a package.

        Args:
            package: Package name
            yes: Whether to skip confirmation

        Raises:
            PipError: If uninstallation fails
        """
        args = ["uninstall"]
        if yes:
            args.append("-y")
        args.append(package)
        self.run(*args)

    def list_packages(self, outdated: bool = False) -> List[Dict]:
        """
        List installed packages.

        Args:
            outdated: Whether to list only outdated packages

        Returns:
            List of package information dictionaries

        Raises:
            PipError: If listing fails
        """
        args = ["list", "--format=json"]
        if outdated:
            args.append("--outdated")

        stdout, _ = self.run(*args)
        return json.loads(stdout)

    def show(self, package: str) -> Dict[str, str]:
        """
        Show package information.

        Args:
            package: Package name

        Returns:
            Dictionary of package information

        Raises:
            PipError: If getting info fails
        """
        stdout, _ = self.run("show", package)
        info = {}

        for line in stdout.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip().lower()] = value.strip()

        return info

    def check(self) -> None:
        """
        Verify installed packages have compatible dependencies.

        Raises:
            PipError: If verification fails
        """
        self.run("check")

    def config(self, *options: str) -> Optional[str]:
        """
        Get/set pip configuration options.

        Args:
            *options: Configuration options

        Returns:
            Configuration value if getting a single option

        Raises:
            PipError: If configuration fails
        """
        stdout, _ = self.run("config", *options)
        return stdout if stdout else None

    def cache_info(self) -> Dict[str, int]:
        """
        Get information about pip cache.

        Returns:
            Dictionary with cache statistics

        Raises:
            PipError: If getting cache info fails
        """
        stdout, _ = self.run("cache", "info")
        info = {}

        for line in stdout.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                try:
                    info[key.strip().lower()] = int(value.strip())
                except ValueError:
                    info[key.strip().lower()] = value.strip()

        return info

    def cache_clear(self) -> None:
        """
        Clear pip cache.

        Raises:
            PipError: If clearing cache fails
        """
        self.run("cache", "purge")

    def download(
        self,
        package: str,
        version: Optional[str] = None,
        dest: Optional[Path] = None,
    ) -> None:
        """
        Download package without installing.

        Args:
            package: Package name
            version: Optional version constraint
            dest: Optional destination directory

        Raises:
            PipError: If download fails
        """
        args = ["download"]

        if version:
            package = f"{package}=={version}"
        if dest:
            args.extend(["--dest", str(dest)])

        args.append(package)
        self.run(*args)
