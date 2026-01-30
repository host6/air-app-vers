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

def validate_semver(version):
    """Validate semantic versioning format."""
    pattern = r'^\d+\.\d+\.\d+$'
    return re.match(pattern, version) is not None

def validate_iso8601(timestamp):
    """Validate ISO 8601 timestamp format."""
    try:
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False

def validate_location_hash(hash_value):
    """Validate location hash is 64 character hex string."""
    pattern = r'^[a-f0-9]{64}$'
    return re.match(pattern, hash_value) is not None

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
    
    # Check versions are in ascending order
    version_list = list(versions.keys())
    for i, version in enumerate(version_list):
        # Validate semver format
        if not validate_semver(version):
            errors.append(f"Invalid semantic version format: {version}")
        
        # Check ascending order
        if i > 0:
            prev_version = version_list[i-1]
            if version <= prev_version:
                errors.append(f"Versions not in ascending order: {prev_version} -> {version}")
    
    # Validate each version entry
    for version, details in versions.items():
        if 'released_at' not in details:
            errors.append(f"Version {version}: missing 'released_at'")
        elif not validate_iso8601(details['released_at']):
            errors.append(f"Version {version}: invalid ISO 8601 timestamp")
        
        if 'matchers' not in details:
            errors.append(f"Version {version}: missing 'matchers'")
            continue
        
        has_default = False
        for matcher in details['matchers']:
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
    """Validate all manifest files."""
    manifests_dir = Path('manifests')
    
    if not manifests_dir.exists():
        print("Error: manifests directory not found")
        sys.exit(1)
    
    all_errors = {}
    for manifest_file in manifests_dir.glob('*.yml'):
        errors = validate_manifest(manifest_file)
        if errors:
            all_errors[manifest_file.name] = errors
    
    if all_errors:
        print("Validation failed:\n")
        for filename, errors in all_errors.items():
            print(f"{filename}:")
            for error in errors:
                print(f"  - {error}")
        sys.exit(1)
    else:
        print("All manifest files are valid")
        sys.exit(0)

if __name__ == '__main__':
    main()

