#!/usr/bin/env python3
"""
Validate version manifest files.

Validation checks:
- YAML syntax is valid
- Semantic versioning format
- Versions in ascending order
- Severity values in allowed set (green, yellow, red)
- Country codes valid (ISO 3166-1 alpha-2)
- Location hash format (64 character hex string)
- released_at is ISO 8601 format
- Each version has at least one default matcher
"""

import sys
import yaml
import re
from pathlib import Path
from datetime import datetime

SEVERITY_VALUES = {'green', 'yellow', 'red'}
MATCHER_TYPES = {'default', 'country', 'location_hash'}

# ISO 3166-1 alpha-2 country codes (subset for validation)
VALID_COUNTRIES = {
    'US', 'GB', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'AT', 'CH',
    'PL', 'CZ', 'SK', 'HU', 'RO', 'BG', 'HR', 'SI', 'SE', 'NO',
    'DK', 'FI', 'IE', 'PT', 'GR', 'LU', 'EE', 'LV', 'LT', 'CY',
    'MT', 'IS'
}

def validate_name(name):
    """Validate name is English alphabet lowercase only."""
    if not isinstance(name, str) or not name:
        return False
    pattern = r'^[a-z]+$'
    return re.match(pattern, name) is not None


def validate_semver(version):
    """Validate semantic versioning format."""
    pattern = r'^\d+\.\d+\.\d+$'
    return re.match(pattern, version) is not None

def parse_semver(version):
    """Parse semantic version string into tuple of integers (major, minor, patch)."""
    parts = version.split('.')
    return tuple(int(part) for part in parts)

def validate_iso8601(timestamp):
    """Validate ISO 8601 timestamp format."""
    try:
        # YAML parser may already convert to datetime object
        if isinstance(timestamp, datetime):
            return True
        # Otherwise validate string format
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return True
    except (ValueError, AttributeError):
        return False

def validate_location_hash(hash_value):
    """Validate location hash is 64 character hex string."""
    pattern = r'^[a-f0-9]{64}$'
    return re.match(pattern, hash_value) is not None


def load_config(config_path='config.yml'):
    """Load and parse config.yml file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f), None
    except yaml.YAMLError as e:
        return None, f"YAML syntax error in config.yml: {e}"
    except FileNotFoundError:
        return None, "config.yml not found"
    except Exception as e:
        return None, f"Error reading config.yml: {e}"


def validate_config(config):
    """Validate config.yml structure and return expected manifest filenames."""
    errors = []
    expected_files = set()

    if not config or 'apps' not in config:
        return [], ["config.yml: missing 'apps' key"]

    apps = config['apps']
    if not isinstance(apps, list) or not apps:
        return [], ["config.yml: 'apps' must be a non-empty list"]

    for i, app in enumerate(apps):
        if not isinstance(app, dict):
            errors.append(f"config.yml: app at index {i} must be an object")
            continue

        # Validate app name
        if 'name' not in app:
            errors.append(f"config.yml: app at index {i} missing 'name'")
            continue

        app_name = app['name']
        if not validate_name(app_name):
            errors.append(f"config.yml: invalid app name '{app_name}' (must be lowercase letters only)")
            continue

        # Validate environments
        if 'environments' not in app:
            errors.append(f"config.yml: app '{app_name}' missing 'environments'")
            continue

        envs = app['environments']
        if not isinstance(envs, list) or not envs:
            errors.append(f"config.yml: app '{app_name}' environments must be a non-empty list")
            continue

        for env in envs:
            if not validate_name(env):
                errors.append(f"config.yml: invalid environment '{env}' in app '{app_name}' (must be lowercase letters only)")
                continue
            expected_files.add(f"{app_name}--{env}.yml")

    return list(expected_files), errors


def validate_manifest(filepath):
    """Validate a single manifest file."""
    errors = []

    try:
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML syntax error: {e}"]
    except Exception as e:
        return [f"Error reading file: {e}"]

    if not data or 'versions' not in data:
        return ["Missing 'versions' key"]

    versions = data['versions']
    if not versions:
        return ["No versions defined"]

    if not isinstance(versions, dict):
        return ["'versions' must be a dictionary, not a list or other type"]

    # Check versions are in ascending order
    version_list = list(versions.keys())
    valid_versions = []  # Track versions with valid format for comparison

    for version in version_list:
        # Validate semver format
        if not validate_semver(version):
            errors.append(f"Invalid semantic version format: {version}")
            continue  # Skip comparison for invalid versions


        valid_versions.append(version)

        # Check ascending order (only compare valid versions)
        if len(valid_versions) > 1:
            prev_version = valid_versions[-2]
            # Use semantic version comparison (numeric tuples) instead of string comparison
            if parse_semver(version) <= parse_semver(prev_version):
                errors.append(f"Versions not in ascending order: {prev_version} -> {version}")

    # Validate each version entry
    for version, details in versions.items():
        # Check if details is a dict
        if not isinstance(details, dict):
            errors.append(f"Version {version}: version details must be an object, not {type(details).__name__}")
            continue

        if 'released_at' not in details:
            errors.append(f"Version {version}: missing 'released_at'")
        elif not validate_iso8601(details['released_at']):
            errors.append(f"Version {version}: invalid ISO 8601 timestamp")

        if 'matchers' not in details:
            errors.append(f"Version {version}: missing 'matchers'")
            continue

        matchers = details['matchers']
        if not isinstance(matchers, list):
            errors.append(f"Version {version}: 'matchers' must be a list")
            continue

        has_default = False
        for matcher in matchers:
            if not isinstance(matcher, dict):
                errors.append(f"Version {version}: matcher must be an object, not {type(matcher).__name__}")
                continue

            matcher_type = matcher.get('matcher_type')

            if matcher_type not in MATCHER_TYPES:
                errors.append(f"Version {version}: invalid matcher_type '{matcher_type}'")
                continue

            if matcher_type == 'default':
                has_default = True

            if matcher_type == 'country':
                country = matcher.get('matcher_value')
                if not country or country not in VALID_COUNTRIES:
                    errors.append(f"Version {version}: invalid country code '{country}'")

            if matcher_type == 'location_hash':
                hash_val = matcher.get('matcher_value')
                if not hash_val or not validate_location_hash(hash_val):
                    errors.append(f"Version {version}: invalid location hash format")

            severity = matcher.get('severity')
            if severity not in SEVERITY_VALUES:
                errors.append(f"Version {version}: invalid severity '{severity}'")

        if not has_default:
            errors.append(f"Version {version}: missing default matcher")

    return errors

def main():
    """Validate all manifest files against config.yml."""
    manifests_dir = Path('manifests')

    # Load and validate config.yml
    config, config_error = load_config()
    if config_error:
        print(f"Error: {config_error}")
        sys.exit(1)

    expected_files, config_errors = validate_config(config)
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

    if all_errors:
        print("Validation failed:\n")
        for filename in sorted(all_errors.keys()):
            print(f"{filename}:")
            for error in all_errors[filename]:
                print(f"  - {error}")
        sys.exit(1)
    else:
        print("All manifest files are valid")
        sys.exit(0)

if __name__ == '__main__':
    main()

