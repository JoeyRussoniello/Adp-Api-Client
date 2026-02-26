#!/usr/bin/env python3
"""Generate a consolidated monofile notebook from src/adpapi modules."""

import json
import sys
import tomllib
from pathlib import Path

import yaml


def extract_package_version() -> str:
    """Extract the package version from pyproject.toml"""
    pyproject = Path('pyproject.toml')
    with open(pyproject, 'rb') as f:
        data = tomllib.load(f)
    version = data.get('project').get('version')
    if version is None:
        raise ValueError('Expect project version in pyproject.toml')
    return version

def extract_imports(code: str) -> tuple[list[str], str]:
    """Extract imports from code and return (imports, code_without_imports).

    Handles multi-line imports (parenthesized) and skips module docstrings
    that appear before imports.
    """
    lines = code.split("\n")
    imports: list[str] = []
    code_lines: list[str] = []
    in_preamble = True  # Before/during imports (docstrings, blanks, imports)
    in_multiline_import = False
    multiline_parts: list[str] = []
    in_docstring = False
    docstring_delim = ""

    for line in lines:
        stripped = line.strip()

        # Handle multi-line docstring skipping (module-level docstrings)
        if in_docstring:
            if docstring_delim in stripped:
                in_docstring = False
            continue

        # Handle continuation of a multi-line import
        if in_multiline_import:
            multiline_parts.append(line)
            if ")" in stripped:
                imports.append("\n".join(multiline_parts))
                multiline_parts = []
                in_multiline_import = False
            continue

        # While still in the preamble (before real code)
        if in_preamble:
            if stripped.startswith("import ") or stripped.startswith("from "):
                # Start of an import — could be multi-line
                if "(" in stripped and ")" not in stripped:
                    in_multiline_import = True
                    multiline_parts = [line]
                else:
                    imports.append(line)
            elif stripped == "" or stripped.startswith("#"):
                # Blank lines and comments in preamble — skip
                continue
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                delim = stripped[:3]
                # Check if docstring opens and closes on same line
                if stripped.count(delim) >= 2:
                    # Single-line docstring — skip it
                    continue
                else:
                    # Multi-line docstring — skip until closing delimiter
                    in_docstring = True
                    docstring_delim = delim
                    continue
            else:
                in_preamble = False
                code_lines.append(line)
        else:
            code_lines.append(line)

    # Join the remaining code, removing leading empty lines
    remaining_code = "\n".join(code_lines).lstrip("\n")

    return imports, remaining_code


def remove_package_imports(imports: list[str]) -> list[str]:
    """Remove imports starting with 'adpapi.'"""
    filtered = []
    for imp in imports:
        if "from adpapi." not in imp and "import adpapi." not in imp:
            filtered.append(imp)
    return filtered


def consolidate_imports(imports: list[str]) -> list[str]:
    """Remove duplicate imports while preserving order."""
    seen: set[str] = set()
    consolidated = []
    for imp in imports:
        if imp.strip() not in seen:
            seen.add(imp.strip())
            consolidated.append(imp)
    return consolidated


def load_config(config_file: Path) -> dict:
    """Load configuration from YAML file."""
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    with open(config_file) as f:
        config = yaml.safe_load(f)
    return config


def read_python_files(src_dir: Path, module_order: list[str]) -> dict:
    """Read all Python files from src/adpapi directory in specified order."""
    files = {}

    # Read files in the specified order
    for module in module_order:
        py_file = src_dir / module
        if py_file.exists():
            with open(py_file) as f:
                files[module] = f.read()

    return files


def _split_source(code: str) -> list[str]:
    """Split code into notebook source lines with trailing newlines (except the last)."""
    lines = code.split("\n")
    return [line + "\n" for line in lines[:-1]] + [lines[-1]]


def generate_notebook(all_imports: list[str], files: dict, version: str) -> dict:
    """Generate notebook structure with consolidated imports and file contents."""
    cells = [{
        'cell_type': 'markdown',
        'metadata': {},
        'source': [f'## `adpapi` v{version}']
    }]

    # Add imports cell
    if all_imports:
        import_code = "\n".join(all_imports)
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": _split_source(import_code),
            }
        )

    # Add file contents
    for filename, content in files.items():
        # Add markdown header for file
        file_header = f"## {filename[:-3]}"  # Remove .py extension
        cells.append({"cell_type": "markdown", "metadata": {}, "source": [file_header]})

        # Extract and clean content
        file_imports, file_code = extract_imports(content)

        # Add code cell with file content (imports already consolidated at top)
        if file_code.strip():
            cells.append(
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": _split_source(file_code.strip()),
                }
            )

    # Create notebook structure
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 2,
    }

    return notebook

def lint_notebook(notebook_file: Path):
    """Lint the generated notebook using ruff."""
    import subprocess

    print(f"Linting notebook: {notebook_file}")
    try:
        subprocess.run(
            ['ruff', 'format', str(notebook_file.absolute())],
            capture_output=True,
            text = True,
            check = True,
        )
        print('Formatted notebook successfully.')
        subprocess.run(
            ["ruff", "check", '--fix', '--unsafe-fixes', str(notebook_file.absolute())],
            capture_output=True,
            text=True,
            check=True,
        )
        print("Linting passed with no issues.")
    except subprocess.CalledProcessError as e:
        print("Linting issues found:")
        print(f'Command: {e.cmd}')
        print(e.stdout)
        print(e.stderr)
        sys.exit(1)

def main():
    """Main function to generate monofile."""
    # Define paths
    package_version = extract_package_version()
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src" / "adpapi"
    config_file = Path(__file__).parent / "config.yaml"
    output_file = project_root / "monofile.ipynb"

    # Load configuration
    print(f"Loading configuration from: {config_file}")
    config = load_config(config_file)
    module_order = config.get("module_order", [])

    if not module_order:
        print("No module_order specified in config.yaml")
        return

    print(f"Reading Python files from: {src_dir}")

    # Read all Python files in specified order
    files = read_python_files(src_dir, module_order)
    if not files:
        print("No Python files found in src/adpapi")
        return

    print(f"Found {len(files)} Python files: {', '.join(files.keys())}")

    # Collect all imports
    all_imports = []
    for _, content in files.items():
        file_imports, _ = extract_imports(content)
        all_imports.extend(file_imports)

    # Clean and consolidate imports
    all_imports = remove_package_imports(all_imports)
    all_imports = consolidate_imports(all_imports)

    print(f"Consolidated to {len(all_imports)} unique imports")

    # Generate notebook
    notebook = generate_notebook(all_imports, files, package_version)

    # Write notebook
    with open(output_file, "w") as f:
        json.dump(notebook, f, indent=1)

    print(f"Generated monofile: {output_file}")
    lint_notebook(output_file)

if __name__ == "__main__":
    main()
