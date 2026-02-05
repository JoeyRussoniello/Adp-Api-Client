#!/usr/bin/env python3
"""Generate a consolidated monofile notebook from src/adpapi modules."""

import json
from pathlib import Path
from typing import List, Set, Tuple

import yaml


def extract_imports(code: str) -> Tuple[List[str], str]:
    """Extract imports from code and return (imports, code_without_imports)."""
    lines = code.split('\n')
    imports = []
    code_lines = []
    in_imports = True
    
    for line in lines:
        # Check if this is an import or from-import line
        if line.strip().startswith('import ') or line.strip().startswith('from '):
            imports.append(line)
        elif in_imports and line.strip() == '':
            # Empty line after imports, still part of import block
            continue
        else:
            in_imports = False
            code_lines.append(line)
    
    # Join the remaining code, removing leading empty lines
    remaining_code = '\n'.join(code_lines).lstrip('\n')
    
    return imports, remaining_code


def remove_package_imports(imports: List[str]) -> List[str]:
    """Remove imports starting with 'adpapi.'"""
    filtered = []
    for imp in imports:
        if 'from adpapi.' not in imp and 'import adpapi.' not in imp:
            filtered.append(imp)
    return filtered


def consolidate_imports(imports: List[str]) -> List[str]:
    """Remove duplicate imports while preserving order."""
    seen: Set[str] = set()
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
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config


def read_python_files(src_dir: Path, module_order: List[str]) -> dict:
    """Read all Python files from src/adpapi directory in specified order."""
    files = {}
    
    # Read files in the specified order
    for module in module_order:
        py_file = src_dir / module
        if py_file.exists():
            with open(py_file, 'r') as f:
                files[module] = f.read()
    
    return files


def generate_notebook(all_imports: List[str], files: dict) -> dict:
    """Generate notebook structure with consolidated imports and file contents."""
    cells = []
    
    # Add imports cell
    if all_imports:
        import_code = '\n'.join(all_imports)
        cells.append({
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": import_code.split('\n')
        })
    
    # Add file contents
    for filename, content in files.items():
        # Add markdown header for file
        file_header = f"## {filename[:-3]}"  # Remove .py extension
        cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": [file_header]
        })
        
        # Extract and clean content
        file_imports, file_code = extract_imports(content)
        
        # Add code cell with file content (imports already consolidated at top)
        if file_code.strip():
            cells.append({
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": file_code.strip().split('\n')
            })
    
    # Create notebook structure
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.11.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 2
    }
    
    return notebook


def main():
    """Main function to generate monofile."""
    # Define paths
    project_root = Path(__file__).parent.parent
    src_dir = project_root / 'src' / 'adpapi'
    config_file = Path(__file__).parent / 'config.yaml'
    output_file = project_root / 'monofile.ipynb'
    
    # Load configuration
    print(f"Loading configuration from: {config_file}")
    config = load_config(config_file)
    module_order = config.get('module_order', [])
    
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
    for filename, content in files.items():
        file_imports, _ = extract_imports(content)
        all_imports.extend(file_imports)
    
    # Clean and consolidate imports
    all_imports = remove_package_imports(all_imports)
    all_imports = consolidate_imports(all_imports)
    
    print(f"Consolidated to {len(all_imports)} unique imports")
    
    # Generate notebook
    notebook = generate_notebook(all_imports, files)
    
    # Write notebook
    with open(output_file, 'w') as f:
        json.dump(notebook, f, indent=1)
    
    print(f"Generated monofile: {output_file}")

if __name__ == '__main__':
    main()
