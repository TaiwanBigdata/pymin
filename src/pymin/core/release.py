# Package release service for PyPI and Test PyPI
import os
import re
import subprocess
import click
import importlib.util
from pathlib import Path
from typing import Optional, Dict, Any
import tomllib
import requests
from packaging.version import parse, Version
from rich.prompt import Confirm
from rich.text import Text
from ..ui.console import print_error, print_warning, print_success, console


def extract_error_from_html(html_content: str) -> str:
    """Extract error message from HTML response"""
    # Try to find error message in <title> tag
    title_match = re.search(r"<title>(.*?)</title>", html_content)
    if title_match:
        return title_match.group(1).strip()

    # Try to find error message in <h1> tag
    h1_match = re.search(r"<h1>(.*?)</h1>", html_content)
    if h1_match:
        return h1_match.group(1).strip()

    return "Unknown error"


def update_version_in_pyproject(version: str) -> None:
    """Update version in pyproject.toml"""
    with open("pyproject.toml", "r", encoding="utf-8") as f:
        content = f.read()

    # Replace version line
    content = re.sub(
        r'version\s*=\s*"[^"]*"',
        f'version = "{version}"',
        content,
    )

    with open("pyproject.toml", "w", encoding="utf-8") as f:
        f.write(content)


def find_next_test_version(project_name: str, base_version: str) -> str:
    """Find next available test version number"""
    # Try to get project info from Test PyPI
    response = requests.get(f"https://test.pypi.org/pypi/{project_name}/json")

    if response.status_code == 404:
        # Project doesn't exist on Test PyPI
        return f"{base_version}.dev0"

    if response.status_code != 200:
        # Can't get version info, use dev0 as fallback
        print_warning("Unable to fetch version info from Test PyPI")
        print_warning("Using dev0 as fallback")
        return f"{base_version}.dev0"

    # Get all versions
    versions = response.json()["releases"].keys()
    dev_versions = [v for v in versions if v.startswith(f"{base_version}.dev")]

    if not dev_versions:
        return f"{base_version}.dev0"

    # Find highest dev number
    highest = -1
    for version in dev_versions:
        try:
            dev_num = int(version.split(".dev")[1])
            highest = max(highest, dev_num)
        except (ValueError, IndexError):
            continue

    return f"{base_version}.dev{highest + 1}"


class PackageReleaser:
    """Handle package release to PyPI or Test PyPI"""

    def __init__(self):
        self.pyproject_path = Path("pyproject.toml")
        self.need_install = []  # Track packages that need to be installed

    def _check_requirements(self) -> bool:
        """Check if all requirements are met"""
        if not self.pyproject_path.exists():
            print_error("No pyproject.toml found in current directory")
            return False
        return True

    def _install_dependencies(self) -> bool:
        """Install required packages for release"""
        required_packages = ["twine", "build"]
        self.need_install = []

        for pkg in required_packages:
            if importlib.util.find_spec(pkg) is None:
                self.need_install.append(pkg)

        if self.need_install:
            console.print("[blue]Installing required packages...[/blue]")
            for pkg in self.need_install:
                with console.status(
                    f"[blue]Installing [cyan]{pkg}[/cyan]...[/blue]",
                    spinner="dots",
                ) as status:
                    process = subprocess.run(
                        ["pip", "install", pkg],
                        capture_output=True,
                        text=True,
                    )
                    if process.returncode != 0:
                        print_error(f"Failed to install {pkg}:")
                        print_error(process.stderr)
                        return False
                    print_success(f"Installed {pkg}")

        return True

    def _build_package(self) -> bool:
        """Build package distributions"""
        # Remove existing dist directory
        if Path("dist").exists():
            import shutil

            shutil.rmtree("dist")
            print_success("Removed existing dist directory")

        # Build package
        console.print("\n[blue]Building package...[/blue]")
        with console.status(
            "[blue]Building...[/blue]", spinner="dots"
        ) as status:
            process = subprocess.run(
                ["python", "-m", "build"],
                capture_output=True,
                text=True,
            )
            if process.returncode != 0:
                print_error("Build failed:")
                print_error(process.stderr)
                return False
            print_success("Package built successfully")

        return True

    def _handle_credentials(self, test: bool) -> bool:
        """Handle PyPI credentials"""
        pypirc_path = Path.home() / ".pypirc"
        has_credentials = False

        if pypirc_path.exists():
            with open(pypirc_path) as f:
                content = f.read()
                section = "testpypi" if test else "pypi"
                has_credentials = (
                    f"[{section}]" in content and "password =" in content
                )

        if not has_credentials:
            target = "Test PyPI" if test else "PyPI"
            print_warning(f"No saved credentials found for {target}")

            if Confirm.ask(
                "Would you like to save your credentials for future use?"
            ):
                token = click.prompt("Enter your API token", hide_input=True)

                # Create or update .pypirc
                if pypirc_path.exists():
                    with open(pypirc_path) as f:
                        current_config = f.read()

                    # Parse existing config
                    sections = {}
                    current_section = None
                    for line in current_config.splitlines():
                        line = line.strip()
                        if line.startswith("[") and line.endswith("]"):
                            current_section = line[1:-1]
                            sections[current_section] = []
                        elif line and current_section:
                            sections[current_section].append(line)

                    # Update the target section
                    section = "testpypi" if test else "pypi"
                    sections[section] = [
                        "username = __token__",
                        f"password = {token}",
                    ]

                    # Reconstruct the config
                    config = []
                    for section_name, lines in sections.items():
                        config.append(f"[{section_name}]")
                        config.extend(lines)
                        config.append("")  # Empty line between sections
                    config = "\n".join(config)
                else:
                    # Create new config with only the required section
                    section = "testpypi" if test else "pypi"
                    config = f"""[{section}]
username = __token__
password = {token}
"""

                # Write the config file
                with open(pypirc_path, "w") as f:
                    f.write(config.strip() + "\n")
                os.chmod(pypirc_path, 0o600)  # Set secure permissions
                print_success(f"Credentials saved to {pypirc_path}")

        return True

    def _upload_package(self, test: bool) -> bool:
        """Upload package to PyPI or Test PyPI"""
        repo_flag = "--repository testpypi" if test else "--repository pypi"
        target = "Test PyPI" if test else "PyPI"

        console.print(f"\n[blue]Uploading to {target}...[/blue]")
        try:
            result = subprocess.run(
                f"twine upload {repo_flag} --verbose --disable-progress-bar dist/*",
                shell=True,
                capture_output=True,
                text=True,
                env={"PYTHONIOENCODING": "utf-8", **os.environ},
            )
        except Exception as e:
            print_error("Upload failed:")
            print_error(str(e))
            return False

        if result.returncode == 0:
            print_success(f"Package published successfully to {target}")
            return True

        print_error(f"Upload to {target} failed")
        self._handle_upload_error(result.stderr or result.stdout, test)
        return False

    def _handle_upload_error(self, error_msg: str, test: bool) -> None:
        """Handle upload error messages"""
        error_lines = error_msg.splitlines()
        upload_info_shown = False
        has_error_details = False
        shown_messages = set()

        for line in error_lines:
            if not line.startswith(("[2K", "[?25")):  # Skip progress bar lines
                if line.strip():
                    # Skip HTML content and entity references
                    if (
                        any(
                            html_tag in line.lower()
                            for html_tag in [
                                "<html",
                                "</html>",
                                "<head",
                                "</head>",
                                "<body",
                                "</body>",
                                "<title",
                                "</title>",
                                "<h1",
                                "</h1>",
                                "<br",
                            ]
                        )
                        or "&#" in line
                        or "&quot;" in line
                        or "See http" in line
                    ):
                        continue

                    # Convert ANSI to plain text and clean up
                    clean_line = Text.from_ansi(line.strip()).plain

                    # Skip INFO lines in verbose output
                    if clean_line.startswith(("INFO", "See http")):
                        continue

                    # Skip lines with hash values
                    if any(
                        pattern in clean_line
                        for pattern in [
                            "blake2_256 hash",
                            "with hash",
                            "). See",
                        ]
                    ):
                        continue

                    # Handle version conflict errors
                    version_conflict_patterns = [
                        "File already exists",
                        "already exists",
                        "filename has already been used",
                        "filename is already registered",
                    ]

                    if (
                        any(
                            pattern in clean_line
                            for pattern in version_conflict_patterns
                        )
                        and "File already exists" not in shown_messages
                    ):
                        has_error_details = True
                        shown_messages.add("File already exists")
                        # Read current version from pyproject.toml
                        with open("pyproject.toml", "rb") as f:
                            current_version = tomllib.load(f)["project"][
                                "version"
                            ]

                        print_warning(
                            "\nThis version has already been uploaded."
                        )
                        console.print(
                            "1. Update the version number in pyproject.toml"
                        )
                        if test:
                            console.print(
                                "2. For testing, you can append [cyan].dev0[/cyan] to version"
                            )
                            console.print(
                                f"   Example: {current_version} -> {current_version}[cyan].dev0[/cyan]"
                            )
                        else:
                            console.print(
                                f"   Current version: {current_version}"
                            )
                        continue

                    if "Uploading" in clean_line and not upload_info_shown:
                        if "legacy" in clean_line:
                            continue  # Skip the legacy URL line
                        pkg_name = clean_line.split()[-1]
                        if pkg_name not in shown_messages:
                            console.print(
                                f"[blue]Uploading [cyan]{pkg_name}[/cyan][/blue]"
                            )
                            shown_messages.add(pkg_name)
                            upload_info_shown = True
                    elif (
                        "HTTPError:" in clean_line
                        or "Bad Request" in clean_line
                    ):
                        if (
                            "400 Bad Request" in clean_line
                            and "Upload rejected by server"
                            not in shown_messages
                        ):
                            has_error_details = True
                            shown_messages.add("Upload rejected by server")
                            print_error("Upload rejected by server")

                            # Extract error message from HTML response
                            if "<html>" in error_msg:
                                error_detail = extract_error_from_html(
                                    error_msg
                                )
                                print_error("Error Details:")
                                print_error(error_detail)
                            else:
                                # PyPI returns plain text error messages
                                # Extract error message after the HTTP status
                                error_lines = error_msg.splitlines()
                                for line in error_lines:
                                    if "HTTPError:" in line:
                                        # Skip the line with HTTPError and get the next non-empty line
                                        continue
                                    if line.strip() and not line.startswith(
                                        ("INFO", "WARNING")
                                    ):
                                        print_error("Error Details:")
                                        print_error(line.strip())
                                        break

                            # Check common issues
                            if not test:
                                print_warning("Please verify:")
                                console.print(
                                    "1. Package name is registered on PyPI"
                                )
                                console.print(
                                    "2. You have the correct permissions"
                                )
                                console.print("3. Version number is unique")
                            else:
                                print_error("HTTP Error:")
                                print_error(clean_line)
                        elif (
                            "403 Forbidden" in clean_line
                            and "Authentication failed" not in shown_messages
                        ):
                            has_error_details = True
                            shown_messages.add("Authentication failed")
                            print_error("Authentication failed")
                            print_warning("Please check:")
                            if test:
                                console.print(
                                    "1. Create an account at Test PyPI:"
                                )
                                console.print(
                                    "[blue]https://test.pypi.org/account/register/[/blue]"
                                )
                                console.print("2. Generate a token at:")
                                console.print(
                                    "[blue]https://test.pypi.org/manage/account/#api-tokens[/blue]"
                                )
                                console.print(
                                    "3. Make sure you're using a Test PyPI token (not PyPI)"
                                )
                            else:
                                console.print(
                                    "1. Your API token is correct for PyPI"
                                )
                                console.print("2. Token has upload permissions")
                    elif not any(
                        skip in clean_line
                        for skip in [
                            "Uploading",
                            "WARNING",
                            "ERROR",
                            "See https://",
                            "information.",
                        ]
                    ):
                        if "error: " in clean_line.lower():
                            if clean_line not in shown_messages:
                                print_error(clean_line)
                                shown_messages.add(clean_line)
                        elif clean_line not in shown_messages:
                            console.print(clean_line)
                            shown_messages.add(clean_line)

        if not has_error_details:
            print_warning("\nAdditional troubleshooting:")
            if test:
                console.print(
                    "1. Register at Test PyPI: [blue link=https://test.pypi.org/account/register/]https://test.pypi.org/account/register/[/blue]"
                )
                console.print(
                    "2. Create a project: [blue link=https://test.pypi.org/manage/projects/]https://test.pypi.org/manage/projects/[/blue]"
                )
            console.print("3. Check your PyPI account status")
            console.print("4. Verify package metadata in pyproject.toml")

    def _cleanup_temp_packages(self) -> None:
        """Clean up temporarily installed packages"""
        if self.need_install:
            console.print("\n[blue]Cleaning up temporary packages...[/blue]")

            # 使用 VenvManager 來深度移除套件
            from ..core.venv_manager import VenvManager

            manager = VenvManager()

            # 移除臨時安裝的套件
            results = manager.remove_packages(self.need_install)

            # 只顯示主要套件的移除結果
            for pkg_name in self.need_install:
                info = results.get(pkg_name, {})
                if info["status"] == "removed":
                    print_success(f"Removed {pkg_name}")
                elif info["status"] == "error":
                    print_warning(
                        f"Warning: Failed to remove {pkg_name}: {info.get('message', 'Unknown error')}"
                    )
                elif info["status"] == "not_found":
                    print_warning(f"Warning: Package {pkg_name} was not found")

    def release(self, test: bool = False) -> bool:
        """
        Release package to PyPI or Test PyPI

        Args:
            test: Whether to publish to Test PyPI instead of PyPI

        Returns:
            bool: True if release was successful, False otherwise
        """
        if not self._check_requirements():
            return False

        if not self._install_dependencies():
            return False

        try:
            # First build
            if not self._build_package():
                return False

            # Read project info
            with open("pyproject.toml", "rb") as f:
                pyproject = tomllib.load(f)
                project_name = pyproject["project"]["name"]
                original_version = pyproject["project"]["version"]

            # Check credentials before proceeding
            if not self._handle_credentials(test):
                return False

            # For Test PyPI, use temporary test version
            if test:
                try:
                    test_version = find_next_test_version(
                        project_name, original_version
                    )
                    console.print(
                        f"\n[blue]Using temporary version [cyan]{test_version}[/cyan] for Test PyPI...[/blue]"
                    )
                    update_version_in_pyproject(test_version)

                    # Rebuild package with new version
                    console.print(
                        "\n[blue]Rebuilding package with test version...[/blue]"
                    )
                    if not self._build_package():
                        update_version_in_pyproject(original_version)
                        return False
                except Exception as e:
                    print_error("Failed to update version number:")
                    print_error(str(e))
                    update_version_in_pyproject(original_version)
                    return False

            success = self._upload_package(test)

            # Clean up
            if Path("dist").exists():
                import shutil

                shutil.rmtree("dist")
                print_success("Cleaned up dist directory")

            # Restore original version for Test PyPI
            if test:
                update_version_in_pyproject(original_version)
                print_success(
                    f"Restored original version [cyan]{original_version}[/cyan]"
                )

            if success:
                # Display success information
                version_for_url = test_version if test else original_version
                if test:
                    web_url = f"https://test.pypi.org/project/{project_name}/{version_for_url}"
                    install_url = "https://test.pypi.org/simple/"
                else:
                    web_url = f"https://pypi.org/project/{project_name}/{version_for_url}"
                    install_url = "https://pypi.org/simple/"

                console.print(f"\n[cyan]Project Information:[/cyan]")
                console.print(
                    f"  • Name: [bold cyan]{project_name}[/bold cyan]"
                )
                console.print(
                    f"  • Version: [bold cyan]{original_version}[/bold cyan]"
                )
                if test:
                    console.print(
                        f"  • Test Version: [bold cyan]{test_version}[/bold cyan]"
                    )
                console.print(
                    f"  • URL: [link={web_url}][blue]{web_url}[/blue][/link]"
                )

                if test:
                    console.print(
                        "\n[yellow]To install from Test PyPI:[/yellow]"
                    )
                    console.print(
                        f"[cyan]pip install -i {install_url} {project_name}=={test_version}[/cyan]"
                    )
                else:
                    console.print("\n[yellow]To install:[/yellow]")
                    console.print(
                        f"[cyan]pip install {project_name}=={original_version}[/cyan]"
                    )

            return success
        finally:
            # Always clean up temporary packages
            self._cleanup_temp_packages()
