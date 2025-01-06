# PyMin

### pymin (0.0.4)

PyMin embodies Python's minimalist philosophy: a focused tool that does one thing exceptionally well. The name reflects our commitment to minimalism - minimal configuration, minimal complexity, but maximum effectiveness in Python development workflow.

Just as Python emphasizes readability and simplicity, PyMin provides a clean, intuitive interface for package management and development environment setup. No unnecessary features, no complex configurations - just straightforward, reliable development tools.

The name "PyMin" carries dual meanings:

**In English: "Py" (Python) + "Min" (Minimal/Minimalist)**
- Represents our commitment to minimalist design and focused functionality
- Follows Python's "Simple is better than complex" philosophy

**In Taiwanese: "歹命" (Pháiⁿ-miā)**
- A humorous reference to the common challenges in Python development
- Reflects developers' daily struggles with environment setup and package management
- Turns development pain points into a playful and helpful tool

This duality in naming captures both our design philosophy and the real-world problems we're solving, while adding a touch of Taiwanese developer humor to the Python ecosystem.

A CLI tool for PyPI package management, providing package name validation, virtual environment management, and project information display with rich output formatting.

#### Demo
![Demo](https://raw.githubusercontent.com/TaiwanBigdata/pymin/main/docs/images/demo.gif)

#### Environment Information
![Environment Information](https://raw.githubusercontent.com/TaiwanBigdata/pymin/main/docs/images/env_info.png)


# Features

## Core Features

1. Package Management
   - Smart dependency handling with tree visualization (`pm list -t`)
   - Intelligent package removal with unused dependency cleanup (`pm rm`)
   - Automatic requirements.txt synchronization (`pm fix`)
   - Version mismatch detection and resolution
   - Bulk package operations support
   - One-command package updates (`pm update`/`pm up`)

2. Project Validation
   - Real-time PyPI name availability check (`pm check`)
   - PEP 503 naming convention validation
   - Similar package name detection
   - Project metadata verification

3. Environment Management
   - Virtual environment creation and reset (`pm venv`)
   - One-command environment activation/deactivation (`pm activate`/`pm deactivate`)
   - Cross-platform compatibility
   - Automatic dependency installation

4. Developer Experience
   - Beautiful tree-style dependency visualization
   - Color-coded status indicators
   - Progress tracking with real-time feedback
   - Minimal configuration required


# Installation

## Quick Start

Install via pipx:
```bash
$ pipx install pymin
```

### System Requirements
| Component | Requirement                |
|-----------|----------------------------|
| Python    | >=3.8 |
| OS        | Platform independent       |


# Usage

## Command Interface

The CLI provides two command interfaces:

| Command | Description                       |
|---------|----------------------------------|
| pm      | Main command (recommended)        |
| pymin   | Alternative full name            |

### Available Commands

| Command    | Description                                |
|------------|--------------------------------------------|
| check      | Check package name availability on PyPI    |
| search     | Search for similar package names           |
| venv (env) | Create or reset virtual environment        |
| activate   | Activate virtual environment               |
| deactivate | Deactivate virtual environment             |
| info       | Show environment information               |
| add        | Add packages to requirements.txt           |
| remove (rm)| Remove packages and unused dependencies    |
| list       | List installed packages with dependencies  |
| fix        | Fix package inconsistencies                |
| update (up)| Update packages to latest versions         |

### Command Examples

#### Package Management
```bash
# Add packages
$ pm add fastapi
$ pm add fastapi==0.100.0    # Specific version
$ pm add fastapi sqlalchemy  # Multiple packages

# Remove packages (with unused dependencies)
$ pm rm fastapi
$ pm rm -y fastapi  # Auto confirm

# List packages
$ pm list          # Show main packages
$ pm list -a       # Show all installed packages with their versions (same as `pip list` command)
$ pm list -t       # Show dependency tree with version status (✓ ≠ ✗ △)

# Fix inconsistencies
$ pm fix           # Check and fix requirements.txt

# Update packages
$ pm update        # Update all packages to latest versions
$ pm up -y         # Update with auto-confirm
```

#### Environment Management
```bash
# Create virtual environment
$ pm venv          # Create with default name 'env'
$ pm venv my_env   # Create with custom name
$ pm env           # Alias for venv

# Activate/Deactivate
$ pm activate
$ pm deactivate

# Show environment info
$ pm info
```

#### Project Validation
```bash
# Check package name
$ pm check my-package-name
┌─ PyPI Package Name Check Results ─┐
│ Package Name: my-package-name     │
│ Normalized Name: my-package-name  │
│ Valid Format: ✓                   │
│ Available: ✓                      │
│ Message: Package name available!  │
└───────────────────────────────────┘

# Search similar names
$ pm search fastapi           # Default similarity (80%)
$ pm search fastapi -t 0.85   # Custom threshold
```


# License

This project is licensed under the MIT License.


# Project Structure

```
pymin/
├── src/
│   └── pymin/
│       ├── __main__.py    # Allow direct execution of the package
│       ├── check.py       # Package name validation service with PyPI availability checking and security analysis
│       ├── cli.py         # Command-line interface providing PyPI package name validation and search functionality
│       ├── package.py     # Package management functionality providing dependency handling and requirements.txt management
│       ├── search.py      # Package name similarity search service with PyPI integration
│       ├── security.py    # Security service for package name typosquatting detection and analysis
│       ├── similarity.py  # String similarity analysis service for package name comparison
│       ├── utils.py       # Utility functions for package name normalization and string manipulation
│       ├── validators.py  # Package name validation service implementing PyPI naming conventions
│       └── venv.py        # CLI environment management service
├── LICENSE
├── pyproject.toml
├── readgen.toml
└── README.md
```


---
> This document was automatically generated by [ReadGen](https://github.com/TaiwanBigdata/readgen).
