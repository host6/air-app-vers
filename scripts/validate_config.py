#!/usr/bin/env python3
"""
Config file validation functions.

Validation checks for config.yml:
- YAML syntax is valid
- 'apps' key exists and is a non-empty list
- Each app has a valid name (lowercase letters only)
- No duplicate app names
- Each app has a non-empty environments list
- Each environment name is valid (lowercase letters only)
- No duplicate environment names within same app
- 'locales' key exists and is a non-empty list
- Each locale is a non-empty string
- No duplicate locale names
- en-en locale is present in locales list (required for fallback)
"""

import re
import yaml

# Required locale for fallback
REQUIRED_LOCALE = 'en-en'


def validate_name(name):
    """Validate name is English alphabet lowercase only."""
    if not isinstance(name, str) or not name:
        return False
    pattern = r'^[a-z]+$'
    return re.match(pattern, name) is not None


def load_config(config_path='config.yml'):
    """Load and parse config.yml file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f), None
    except yaml.YAMLError as e:
        return None, f"YAML syntax error in config.yml: {e}"
    except FileNotFoundError:
        return None, "config.yml not found"
    except Exception as e:
        return None, f"Error reading config.yml: {e}"


def validate_config(config):
    """Validate config.yml structure and return expected manifest filenames, app names, and locales.

    Returns:
        tuple: (expected_manifest_files, app_names, locales, errors)
    """
    errors = []
    expected_files = set()
    app_names = set()
    locales = set()

    if not config or 'apps' not in config:
        return [], set(), set(), ["config.yml: missing 'apps' key"]

    apps = config['apps']
    if not isinstance(apps, list) or not apps:
        return [], set(), set(), ["config.yml: 'apps' must be a non-empty list"]

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

        # Check for duplicate app names
        if app_name in app_names:
            errors.append(f"config.yml: duplicate app name '{app_name}'")
            continue

        app_names.add(app_name)

        # Validate environments
        if 'environments' not in app:
            errors.append(f"config.yml: app '{app_name}' missing 'environments'")
            continue

        envs = app['environments']
        if not isinstance(envs, list) or not envs:
            errors.append(f"config.yml: app '{app_name}' environments must be a non-empty list")
            continue

        seen_envs = set()
        for env in envs:
            if not validate_name(env):
                errors.append(f"config.yml: invalid environment '{env}' in app '{app_name}' (must be lowercase letters only)")
                continue
            # Check for duplicate environment names within same app
            if env in seen_envs:
                errors.append(f"config.yml: duplicate environment '{env}' in app '{app_name}'")
                continue
            seen_envs.add(env)
            expected_files.add(f"{app_name}--{env}.yml")

    # Validate locales
    if 'locales' not in config:
        errors.append("config.yml: missing 'locales' key")
    else:
        config_locales = config['locales']
        if not isinstance(config_locales, list) or not config_locales:
            errors.append("config.yml: 'locales' must be a non-empty list")
        else:
            for locale in config_locales:
                if not isinstance(locale, str) or not locale:
                    errors.append(f"config.yml: invalid locale '{locale}' (must be a non-empty string)")
                else:
                    # Check for duplicate locale names
                    if locale in locales:
                        errors.append(f"config.yml: duplicate locale '{locale}'")
                    else:
                        locales.add(locale)

            # Check that required locale is present
            if REQUIRED_LOCALE not in locales:
                errors.append(f"config.yml: missing required locale '{REQUIRED_LOCALE}'")

    return list(expected_files), app_names, locales, errors

