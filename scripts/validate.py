#!/usr/bin/env python3
"""
Validate version manifest files and notes files.

Cross-validation:
- For each version in any manifest file, a corresponding notes file exists (notes/{app}--{version}.yml)
- For each notes file, the version is referenced in at least one manifest file
- All notes files use only apps defined in config.yml
- All manifest files use only apps and environments defined in config.yml
"""

import sys
import yaml
from pathlib import Path

from validate_manifest import validate_manifest
from validate_notes import validate_notes_filename, validate_notes_file
from validate_config import load_config, validate_config


def get_versions_from_manifests(manifests_dir):
    """Extract all versions from all manifest files.

    Returns:
        dict: {app_name: set of versions}
    """
    app_versions = {}

    for manifest_file in manifests_dir.glob('*.yml'):
        # Parse app name from filename (e.g., pos--live.yml -> pos)
        filename = manifest_file.name
        if '--' not in filename:
            continue
        app_name = filename.split('--')[0]

        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            if data and 'versions' in data and isinstance(data['versions'], dict):
                if app_name not in app_versions:
                    app_versions[app_name] = set()
                app_versions[app_name].update(data['versions'].keys())
        except Exception as e:
            raise RuntimeError(f"Error reading manifest file {manifest_file}: {e}") from e

    return app_versions


def main():
    """Validate all manifest files and notes files against config.yml."""
    manifests_dir = Path('manifests')
    notes_dir = Path('notes')

    # Load and validate config.yml
    config, config_error = load_config()
    if config_error:
        print(f"Error: {config_error}")
        sys.exit(1)

    expected_files, app_names, locales, config_errors = validate_config(config)
    if config_errors:
        print("Validation failed:\n")
        print("config.yml:")
        for error in config_errors:
            print(f"  - {error}")
        sys.exit(1)

    if not manifests_dir.exists():
        print("Error: manifests directory not found")
        sys.exit(1)

    # Get actual manifest files
    actual_files = {f.name for f in manifests_dir.glob('*.yml')}
    expected_set = set(expected_files)

    all_errors = {}

    # Check for orphan files (in manifests/ but not in config)
    orphan_files = actual_files - expected_set
    for orphan in orphan_files:
        all_errors[orphan] = ["Manifest file not defined in config.yml"]

    # Check for missing files (in config but not in manifests/)
    missing_files = expected_set - actual_files
    for missing in missing_files:
        all_errors[missing] = ["Missing manifest file (defined in config.yml but file not found)"]

    # Validate each manifest file that exists and is expected
    valid_files = actual_files & expected_set
    for filename in valid_files:
        manifest_file = manifests_dir / filename
        errors = validate_manifest(manifest_file)
        if errors:
            all_errors[filename] = errors

    # Get all versions from manifests for cross-validation
    app_versions = get_versions_from_manifests(manifests_dir)

    # Validate notes files
    if notes_dir.exists():
        actual_notes = {f.name for f in notes_dir.glob('*.yml')}
        notes_app_versions = {}  # Track {app: set of versions} from notes files

        for notes_filename in actual_notes:
            app_name, version = validate_notes_filename(notes_filename)

            if app_name is None:
                all_errors[f"notes/{notes_filename}"] = [
                    f"Invalid filename format (expected {{app}}--{{version}}.yml)"
                ]
                continue

            # Check app exists in config
            if app_name not in app_names:
                all_errors[f"notes/{notes_filename}"] = [
                    f"App '{app_name}' not defined in config.yml"
                ]
                continue

            # Track notes versions for cross-validation
            if app_name not in notes_app_versions:
                notes_app_versions[app_name] = set()
            notes_app_versions[app_name].add(version)

            # Validate notes file content
            notes_file = notes_dir / notes_filename
            errors = validate_notes_file(notes_file, locales)
            if errors:
                all_errors[f"notes/{notes_filename}"] = errors

        # Cross-validation: check each manifest version has a notes file
        for app_name, versions in app_versions.items():
            notes_versions = notes_app_versions.get(app_name, set())
            for version in versions:
                if version not in notes_versions:
                    error_key = f"notes/{app_name}--{version}.yml"
                    if error_key not in all_errors:
                        all_errors[error_key] = []
                    all_errors[error_key].append(
                        f"Missing notes file for version {version} (referenced in manifest)"
                    )

        # Cross-validation: check each notes file version is in at least one manifest
        for app_name, versions in notes_app_versions.items():
            manifest_versions = app_versions.get(app_name, set())
            for version in versions:
                if version not in manifest_versions:
                    error_key = f"notes/{app_name}--{version}.yml"
                    if error_key not in all_errors:
                        all_errors[error_key] = []
                    all_errors[error_key].append(
                        f"Version {version} not referenced in any manifest file"
                    )

    if all_errors:
        print("Validation failed:\n")
        for filename in sorted(all_errors.keys()):
            print(f"{filename}:")
            for error in all_errors[filename]:
                print(f"  - {error}")
        sys.exit(1)
    else:
        print("All manifest and notes files are valid")
        sys.exit(0)

if __name__ == '__main__':
    main()

