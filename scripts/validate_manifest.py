#!/usr/bin/env python3
"""
Manifest file validation functions.

Validation checks for manifests:
- YAML syntax is valid
- Semantic versioning format
- Versions in ascending order
- Severity values in allowed set (green, yellow, red)
- Country codes valid (ISO 3166-1 alpha-2)
- Location hash format (64 character hex string)
- released_at is ISO 8601 format
- Each version has at least one default matcher
"""

import re
import yaml
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


def validate_manifest(filepath):
    """Validate a single manifest file."""
    errors = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
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

