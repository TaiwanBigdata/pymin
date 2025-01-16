# Modern command line interface
from pathlib import Path
from typing import Optional
import click

from .modern.core import (
    PackageManager,
    VenvManager,
    RequirementsManager,
    DependencyAnalyzer,
    PackageError,
    EnvironmentError,
    RequirementsError,
)
from .modern.ui import console


# Shared command options
def venv_options(f):
    """Common virtual environment options."""
    f = click.option(
        "--venv",
        "-v",
        help="Virtual environment name",
        type=str,
        required=False,
    )(f)
    return f


def project_options(f):
    """Common project options."""
    f = click.option(
        "--project",
        "-p",
        help="Project directory",
        type=click.Path(exists=True, file_okay=False, resolve_path=True),
        default=".",
    )(f)
    return f


# Main command group
@click.group()
def pmm():
    """Modern Python package management tool."""
    pass


# Package management commands
@pmm.command()
@click.argument("package")
@click.option("--version", "-v", help="Package version")
@click.option(
    "--upgrade/--no-upgrade",
    default=False,
    help="Upgrade if installed",
)
@venv_options
@project_options
def add(
    package: str,
    version: Optional[str],
    upgrade: bool,
    venv: Optional[str],
    project: str,
):
    """Add a package."""
    try:
        project_path = Path(project)
        manager = PackageManager(
            venv_path=project_path / venv if venv else None
        )
        manager.install(package, version=version, upgrade=upgrade)
    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@pmm.command()
@click.argument("package")
@venv_options
@project_options
def remove(package: str, venv: Optional[str], project: str):
    """Remove a package."""
    try:
        project_path = Path(project)
        manager = PackageManager(
            venv_path=project_path / venv if venv else None
        )
        manager.uninstall(package)
    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@pmm.command()
@venv_options
@project_options
def update(venv: Optional[str], project: str):
    """Update all packages."""
    try:
        project_path = Path(project)
        manager = PackageManager(
            venv_path=project_path / venv if venv else None
        )

        # Get outdated packages
        updates = manager.check_updates()
        if not updates:
            console.info("All packages are up to date")
            return

        # Update each package
        for package in updates:
            try:
                console.start_status(f"Updating {package}...")
                manager.upgrade(package)
                console.success(f"Updated {package}")
            except Exception as e:
                console.warning(f"Failed to update {package}", str(e))
            finally:
                console.stop_status()

    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@pmm.command()
@venv_options
@project_options
def fix(venv: Optional[str], project: str):
    """Fix package inconsistencies."""
    try:
        project_path = Path(project)
        manager = PackageManager(
            venv_path=project_path / venv if venv else None
        )

        # Check for conflicts
        analyzer = DependencyAnalyzer(
            venv_path=project_path / venv if venv else None
        )
        conflicts = analyzer.check_conflicts()

        if not conflicts:
            console.success("No package inconsistencies found")
            return

        # Try to fix each conflict
        fixed = []
        failed = []

        for pkg, req, has in conflicts:
            try:
                console.start_status(f"Fixing {pkg}...")
                manager.upgrade(pkg)
                fixed.append(pkg)
                console.success(f"Fixed {pkg}")
            except Exception as e:
                failed.append((pkg, str(e)))
                console.warning(f"Failed to fix {pkg}", str(e))
            finally:
                console.stop_status()

        # Show summary
        if fixed:
            console.success(f"Fixed {len(fixed)} package(s)")
        if failed:
            console.warning(
                f"Failed to fix {len(failed)} package(s)",
                "Some packages could not be fixed automatically",
            )

    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@pmm.command()
@venv_options
@project_options
def list(venv: Optional[str], project: str):
    """List installed packages."""
    try:
        project_path = Path(project)
        manager = PackageManager(
            venv_path=project_path / venv if venv else None
        )
        packages = manager.list_installed()

        if not packages:
            console.info("No packages installed")
            return

        table = console.create_table(
            "Installed Packages",
            show_header=True,
        )
        table.add_column("Package")
        table.add_column("Version")

        for name, version in sorted(packages.items()):
            table.add_row(name, version)

        console.print(table)

    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@pmm.command()
@venv_options
@project_options
def outdated(venv: Optional[str], project: str):
    """Check for outdated packages."""
    try:
        project_path = Path(project)
        manager = PackageManager(
            venv_path=project_path / venv if venv else None
        )
        updates = manager.check_updates()

        if not updates:
            console.info("All packages are up to date")
            return

        table = console.create_table(
            "Outdated Packages",
            show_header=True,
        )
        table.add_column("Package")
        table.add_column("Current")
        table.add_column("Latest")

        for name, (current, latest) in sorted(updates.items()):
            table.add_row(name, current, latest)

        console.print(table)

    except Exception as e:
        console.error(str(e))
        raise click.Abort()


# Virtual environment commands
@pmm.group()
def venv():
    """Virtual environment commands."""
    pass


@venv.command()
@click.argument("name")
@click.option(
    "--system-packages/--no-system-packages",
    default=False,
    help="Allow access to system packages",
)
@click.option(
    "--clear/--no-clear",
    default=False,
    help="Delete environment if it exists",
)
@click.option(
    "--upgrade-deps/--no-upgrade-deps",
    default=True,
    help="Upgrade base packages",
)
@project_options
def create(
    name: str,
    system_packages: bool,
    clear: bool,
    upgrade_deps: bool,
    project: str,
):
    """Create a virtual environment."""
    try:
        project_path = Path(project)
        manager = VenvManager(project_path)
        manager.create(
            name,
            system_site_packages=system_packages,
            clear=clear,
            upgrade_deps=upgrade_deps,
        )
    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@venv.command()
@click.argument("name")
@project_options
def remove(name: str, project: str):
    """Remove a virtual environment."""
    try:
        if not console.confirm(
            f"Are you sure you want to remove environment '{name}'?"
        ):
            return

        project_path = Path(project)
        manager = VenvManager(project_path)
        manager.remove(name)
    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@venv.command()
@project_options
def list(project: str):
    """List virtual environments."""
    try:
        project_path = Path(project)
        manager = VenvManager(project_path)
        environments = manager.list_environments()

        if not environments:
            console.info("No virtual environments found")
            return

        table = console.create_table(
            "Virtual Environments",
            show_header=True,
        )
        table.add_column("Name")
        table.add_column("Path")

        for name, path in sorted(environments.items()):
            table.add_row(name, str(path))

        console.print(table)

    except Exception as e:
        console.error(str(e))
        raise click.Abort()


# Requirements commands
@pmm.group()
def req():
    """Requirements management commands."""
    pass


@req.command()
@click.argument("package")
@click.option("--version", "-v", help="Package version")
@project_options
def add(package: str, version: Optional[str], project: str):
    """Add package to requirements."""
    try:
        project_path = Path(project)
        manager = RequirementsManager(project_path)
        manager.add_package(package, version=version)
        console.success(f"Added {package} to requirements.txt")
    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@req.command()
@click.argument("package")
@project_options
def remove(package: str, project: str):
    """Remove package from requirements."""
    try:
        project_path = Path(project)
        manager = RequirementsManager(project_path)
        if manager.remove_package(package):
            console.success(f"Removed {package} from requirements.txt")
        else:
            console.warning(f"Package {package} not found in requirements.txt")
    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@req.command()
@project_options
def list(project: str):
    """List requirements."""
    try:
        project_path = Path(project)
        manager = RequirementsManager(project_path)
        packages = manager.parse()

        if not packages:
            console.info("No requirements found")
            return

        table = console.create_table(
            "Requirements",
            show_header=True,
        )
        table.add_column("Package")
        table.add_column("Version")

        for name, version in sorted(packages.items()):
            table.add_row(name, version or "-")

        console.print(table)

    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@req.command()
@project_options
def check(project: str):
    """Validate requirements file."""
    try:
        project_path = Path(project)
        manager = RequirementsManager(project_path)
        if manager.validate():
            console.success("Requirements file is valid")
    except Exception as e:
        console.error(str(e))
        raise click.Abort()


# Dependency analysis commands
@pmm.group()
def dep():
    """Dependency analysis commands."""
    pass


@dep.command()
@click.argument("package")
@click.option(
    "--recursive/--no-recursive",
    default=False,
    help="Show recursive dependencies",
)
@click.option(
    "--versions/--no-versions",
    default=False,
    help="Show version constraints",
)
@venv_options
@project_options
def deps(
    package: str,
    recursive: bool,
    versions: bool,
    venv: Optional[str],
    project: str,
):
    """Show package dependencies."""
    try:
        project_path = Path(project)
        analyzer = DependencyAnalyzer(
            venv_path=project_path / venv if venv else None
        )
        dependencies = analyzer.get_dependencies(
            package,
            recursive=recursive,
            include_versions=versions,
        )

        if not dependencies:
            console.info(f"No dependencies found for {package}")
            return

        table = console.create_table(
            f"Dependencies for {package}",
            show_header=True,
        )
        table.add_column("Package")
        table.add_column("Dependencies")

        for pkg, deps in sorted(dependencies.items()):
            table.add_row(pkg, "\n".join(sorted(deps)) if deps else "-")

        console.print(table)

    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@dep.command()
@click.argument("package")
@venv_options
@project_options
def rdeps(package: str, venv: Optional[str], project: str):
    """Show reverse dependencies."""
    try:
        project_path = Path(project)
        analyzer = DependencyAnalyzer(
            venv_path=project_path / venv if venv else None
        )
        dependencies = analyzer.find_reverse_dependencies(package)

        if not dependencies:
            console.info(f"No packages depend on {package}")
            return

        table = console.create_table(
            f"Reverse Dependencies for {package}",
            show_header=True,
        )
        table.add_column("Package")
        table.add_column("Dependent Packages")

        for pkg, deps in sorted(dependencies.items()):
            table.add_row(pkg, "\n".join(sorted(deps)) if deps else "-")

        console.print(table)

    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@dep.command()
@venv_options
@project_options
def conflicts(venv: Optional[str], project: str):
    """Check for dependency conflicts."""
    try:
        project_path = Path(project)
        analyzer = DependencyAnalyzer(
            venv_path=project_path / venv if venv else None
        )
        conflicts = analyzer.check_conflicts()

        if not conflicts:
            console.success("No dependency conflicts found")
            return

        table = console.create_table(
            "Dependency Conflicts",
            show_header=True,
        )
        table.add_column("Package")
        table.add_column("Requires")
        table.add_column("Has")

        for pkg, req, has in sorted(conflicts):
            table.add_row(pkg, req, has)

        console.print(table)
        console.warning(
            f"Found {len(conflicts)} dependency conflicts",
            "These conflicts may cause issues",
        )

    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@dep.command()
@click.argument("package")
@venv_options
@project_options
def impact(package: str, venv: Optional[str], project: str):
    """Analyze impact of removing a package."""
    try:
        project_path = Path(project)
        analyzer = DependencyAnalyzer(
            venv_path=project_path / venv if venv else None
        )
        analysis = analyzer.analyze_impact(package)

        if analysis["safe_to_remove"]:
            console.success(f"Safe to remove {package}")
            return

        console.warning(
            f"Removing {package} will affect other packages",
            "The following packages depend on it:",
        )

        if analysis["direct_dependents"]:
            table = console.create_table(
                "Direct Dependents",
                show_header=True,
            )
            table.add_column("Package")
            for pkg in analysis["direct_dependents"]:
                table.add_row(pkg)
            console.print(table)

        if analysis["indirect_dependents"]:
            table = console.create_table(
                "Indirect Dependents",
                show_header=True,
            )
            table.add_column("Package")
            for pkg in analysis["indirect_dependents"]:
                table.add_row(pkg)
            console.print(table)

    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@dep.command()
@venv_options
@project_options
def cycles(venv: Optional[str], project: str):
    """Find dependency cycles."""
    try:
        project_path = Path(project)
        analyzer = DependencyAnalyzer(
            venv_path=project_path / venv if venv else None
        )
        cycles = analyzer.find_cycles()

        if not cycles:
            console.success("No dependency cycles found")
            return

        table = console.create_table(
            "Dependency Cycles",
            show_header=True,
        )
        table.add_column("Cycle")

        for cycle in cycles:
            table.add_row(" -> ".join(cycle))

        console.print(table)
        console.warning(
            f"Found {len(cycles)} dependency cycles",
            "Cycles may cause installation and upgrade issues",
        )

    except Exception as e:
        console.error(str(e))
        raise click.Abort()


@dep.command()
@click.argument("package")
@click.option(
    "--depth",
    "-d",
    type=int,
    help="Maximum depth to show",
)
@click.option(
    "--no-versions",
    is_flag=True,
    help="Don't show version constraints",
)
@venv_options
@project_options
def tree(
    package: str,
    depth: Optional[int],
    no_versions: bool,
    venv: Optional[str],
    project: str,
):
    """Show dependency tree."""
    try:
        project_path = Path(project)
        analyzer = DependencyAnalyzer(
            venv_path=project_path / venv if venv else None
        )

        # Build and format tree
        tree = analyzer.build_dependency_tree(
            package,
            max_depth=depth,
            include_versions=not no_versions,
        )

        # Create title panel
        title = f"Dependency Tree for {package}"
        if depth is not None:
            title += f" (max depth: {depth})"

        panel = console.create_panel(
            analyzer.format_tree(tree),
            title=title,
        )
        console.print(panel)

    except Exception as e:
        console.error(str(e))
        raise click.Abort()


if __name__ == "__main__":
    pmm()

# Export the main command as cli for entry point
cli = pmm
