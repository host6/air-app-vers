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
- released_at dates are in chronological order
- released_at is not in the future
- released_at not older than 12 months
- Each version has at least one default matcher
- No duplicate matchers for same version
- No conflicting location hash matchers
- No conflicting country matchers
- No extra fields
"""

import re
import yaml
from datetime import datetime, timedelta, timezone

SEVERITY_VALUES = {'green', 'yellow', 'red'}
MATCHER_TYPES = {'default', 'country', 'location_hash'}

# Allowed fields for validation
ALLOWED_VERSION_FIELDS = {'released_at', 'matchers', 'notes'}
ALLOWED_MATCHER_FIELDS = {'matcher_type', 'matcher_value', 'severity'}

# Time constraints
MAX_AGE_DAYS = 365  # 12 months

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


def parse_iso8601(timestamp):
    """Parse ISO 8601 timestamp to datetime object.

    Returns datetime object or None if parsing fails.
    """
    try:
        if isinstance(timestamp, datetime):
            # Ensure timezone-aware
            if timestamp.tzinfo is None:
                return timestamp.replace(tzinfo=timezone.utc)
            return timestamp
        # Parse string format
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


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

    # Track released_at timestamps for chronological order check
    prev_released_at = None
    prev_version_for_date = None
    now = datetime.now(timezone.utc)
    min_date = now - timedelta(days=MAX_AGE_DAYS)

    # Validate each version entry
    for version, details in versions.items():
        # Check if details is a dict
        if not isinstance(details, dict):
            errors.append(f"Version {version}: version details must be an object, not {type(details).__name__}")
            continue

        # Check for extra fields in version
        extra_fields = set(details.keys()) - ALLOWED_VERSION_FIELDS
        if extra_fields:
            errors.append(f"Version {version}: extra fields not allowed: {', '.join(sorted(extra_fields))}")

        if 'released_at' not in details:
            errors.append(f"Version {version}: missing 'released_at'")
        elif not validate_iso8601(details['released_at']):
            errors.append(f"Version {version}: invalid ISO 8601 timestamp")
        else:
            # Parse and validate released_at constraints
            released_at = parse_iso8601(details['released_at'])
            if released_at:
                # Check not in future
                if released_at > now:
                    errors.append(f"Version {version}: released_at is in the future")

                # Check not older than 12 months
                if released_at < min_date:
                    errors.append(f"Version {version}: released_at is older than 12 months")

                # Check chronological order
                if prev_released_at is not None and released_at < prev_released_at:
                    errors.append(f"Version {version}: released_at is not in chronological order (earlier than {prev_version_for_date})")

                prev_released_at = released_at
                prev_version_for_date = version

        if 'matchers' not in details:
            errors.append(f"Version {version}: missing 'matchers'")
            continue

        matchers = details['matchers']
        if not isinstance(matchers, list):
            errors.append(f"Version {version}: 'matchers' must be a list")
            continue

        has_default = False
        default_count = 0
        country_matchers = {}  # country -> severity
        location_hash_matchers = {}  # hash -> severity

        for matcher in matchers:
            if not isinstance(matcher, dict):
                errors.append(f"Version {version}: matcher must be an object, not {type(matcher).__name__}")
                continue

            # Check for extra fields in matcher
            extra_matcher_fields = set(matcher.keys()) - ALLOWED_MATCHER_FIELDS
            if extra_matcher_fields:
                errors.append(f"Version {version}: matcher has extra fields not allowed: {', '.join(sorted(extra_matcher_fields))}")

            matcher_type = matcher.get('matcher_type')

            if matcher_type not in MATCHER_TYPES:
                errors.append(f"Version {version}: invalid matcher_type '{matcher_type}'")
                continue

            if matcher_type == 'default':
                has_default = True
                default_count += 1

            if matcher_type == 'country':
                country = matcher.get('matcher_value')
                if not country or country not in VALID_COUNTRIES:
                    errors.append(f"Version {version}: invalid country code '{country}'")
                elif country in country_matchers:
                    # Check for conflicting country matchers
                    prev_severity = country_matchers[country]
                    curr_severity = matcher.get('severity')
                    if prev_severity != curr_severity:
                        errors.append(f"Version {version}: conflicting country matchers for '{country}' with different severities")
                    else:
                        errors.append(f"Version {version}: duplicate country matcher for '{country}'")
                else:
                    country_matchers[country] = matcher.get('severity')

            if matcher_type == 'location_hash':
                hash_val = matcher.get('matcher_value')
                if not hash_val or not validate_location_hash(hash_val):
                    errors.append(f"Version {version}: invalid location hash format")
                elif hash_val in location_hash_matchers:
                    # Check for conflicting location hash matchers
                    prev_severity = location_hash_matchers[hash_val]
                    curr_severity = matcher.get('severity')
                    if prev_severity != curr_severity:
                        errors.append(f"Version {version}: conflicting location hash matchers with different severities")
                    else:
                        errors.append(f"Version {version}: duplicate location hash matcher")
                else:
                    location_hash_matchers[hash_val] = matcher.get('severity')

            severity = matcher.get('severity')
            if severity not in SEVERITY_VALUES:
                errors.append(f"Version {version}: invalid severity '{severity}'")

        if not has_default:
            errors.append(f"Version {version}: missing default matcher")

        # Check for duplicate default matchers
        if default_count > 1:
            errors.append(f"Version {version}: duplicate default matchers ({default_count} found)")

    return errors

