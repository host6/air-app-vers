#!/usr/bin/env python3
"""
Unit tests for validation script.
"""

import unittest
import tempfile
import os
import shutil
from datetime import datetime
from io import StringIO
from unittest.mock import patch
from pathlib import Path

from scripts.validate import main, get_versions_from_manifests
from scripts.validate_config import (
    validate_name,
    load_config,
    validate_config,
    REQUIRED_LOCALE,
)
from scripts.validate_manifest import (
    validate_semver,
    parse_semver,
    validate_iso8601,
    validate_location_hash,
)


class TestValidateSemver(unittest.TestCase):
    """Test semantic version validation."""

    def test_valid_versions(self):
        """Test valid semantic version formats."""
        self.assertTrue(validate_semver("1.0.0"))
        self.assertTrue(validate_semver("0.0.1"))
        self.assertTrue(validate_semver("10.20.30"))
        self.assertTrue(validate_semver("999.999.999"))

    def test_invalid_versions(self):
        """Test invalid semantic version formats."""
        self.assertFalse(validate_semver("1.0"))
        self.assertFalse(validate_semver("1"))
        self.assertFalse(validate_semver("1.0.0.0"))
        self.assertFalse(validate_semver("v1.0.0"))
        self.assertFalse(validate_semver("1.0.0-alpha"))
        self.assertFalse(validate_semver("a.b.c"))
        self.assertFalse(validate_semver(""))


class TestValidateName(unittest.TestCase):
    """Test name validation for apps and environments."""

    def test_valid_names(self):
        """Test valid lowercase letter names."""
        self.assertTrue(validate_name("pos"))
        self.assertTrue(validate_name("live"))
        self.assertTrue(validate_name("backoffice"))
        self.assertTrue(validate_name("a"))
        self.assertTrue(validate_name("staging"))

    def test_invalid_names(self):
        """Test invalid name formats."""
        self.assertFalse(validate_name(""))
        self.assertFalse(validate_name("POS"))  # uppercase
        self.assertFalse(validate_name("pos1"))  # contains number
        self.assertFalse(validate_name("pos-live"))  # contains hyphen
        self.assertFalse(validate_name("pos_live"))  # contains underscore
        self.assertFalse(validate_name("pos live"))  # contains space
        self.assertFalse(validate_name("pos.live"))  # contains dot
        self.assertFalse(validate_name(None))  # None
        self.assertFalse(validate_name(123))  # not a string


class TestLoadConfig(unittest.TestCase):
    """Test config.yml loading."""

    def setUp(self):
        """Create temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

        self.original_cwd = os.getcwd()
        self.addCleanup(os.chdir, self.original_cwd)

        os.chdir(self.temp_dir)

    def write_config(self, content):
        """Helper to write config.yml file."""
        with open('config.yml', 'w') as f:
            f.write(content)

    def test_valid_config(self):
        """Test loading valid config.yml."""
        self.write_config("""apps:
  - name: pos
    environments:
      - live
""")
        config, error = load_config()
        self.assertIsNone(error)
        self.assertIsNotNone(config)
        assert config is not None  # Type narrowing for type checker
        self.assertIn('apps', config)

    def test_config_not_found(self):
        """Test error when config.yml doesn't exist."""
        config, error = load_config()
        self.assertIsNone(config)
        self.assertIsNotNone(error)
        assert error is not None  # Type narrowing for type checker
        self.assertIn("config.yml not found", error)

    def test_invalid_yaml(self):
        """Test error on invalid YAML syntax."""
        self.write_config("apps:\n  - name: [invalid")
        config, error = load_config()
        self.assertIsNone(config)
        self.assertIsNotNone(error)
        assert error is not None  # Type narrowing for type checker
        self.assertIn("YAML syntax error", error)


class TestValidateConfig(unittest.TestCase):
    """Test config.yml structure validation."""

    def test_valid_config(self):
        """Test valid config structure."""
        config = {
            'apps': [
                {'name': 'pos', 'environments': ['live', 'staging']},
                {'name': 'backoffice', 'environments': ['live']}
            ],
            'locales': ['en-en', 'nl-NL', 'de-DE']
        }
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertEqual(errors, [])
        self.assertIn('pos--live.yml', expected_files)
        self.assertIn('pos--staging.yml', expected_files)
        self.assertIn('backoffice--live.yml', expected_files)
        self.assertEqual(len(expected_files), 3)
        self.assertIn('pos', app_names)
        self.assertIn('backoffice', app_names)
        self.assertIn('en-en', locales)
        self.assertIn('nl-NL', locales)

    def test_missing_apps_key(self):
        """Test error when apps key is missing."""
        config = {}
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertEqual(expected_files, [])
        self.assertIn("config.yml: missing 'apps' key", errors)

    def test_empty_apps_list(self):
        """Test error when apps list is empty."""
        config = {'apps': []}
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertEqual(expected_files, [])
        self.assertIn("config.yml: 'apps' must be a non-empty list", errors)

    def test_missing_app_name(self):
        """Test error when app is missing name."""
        config = {'apps': [{'environments': ['live']}], 'locales': ['en-en']}
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertTrue(any("missing 'name'" in e for e in errors))

    def test_missing_environments(self):
        """Test error when app is missing environments."""
        config = {'apps': [{'name': 'pos'}], 'locales': ['en-en']}
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertTrue(any("missing 'environments'" in e for e in errors))

    def test_empty_environments_list(self):
        """Test error when environments list is empty."""
        config = {'apps': [{'name': 'pos', 'environments': []}], 'locales': ['en-en']}
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertTrue(any("must be a non-empty list" in e for e in errors))

    def test_none_config(self):
        """Test error when config is None."""
        expected_files, app_names, locales, errors = validate_config(None)
        self.assertEqual(expected_files, [])
        self.assertIn("config.yml: missing 'apps' key", errors)

    def test_apps_not_a_list(self):
        """Test error when apps is not a list."""
        config = {'apps': "not a list"}
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertEqual(expected_files, [])
        self.assertIn("config.yml: 'apps' must be a non-empty list", errors)

    def test_app_not_a_dict(self):
        """Test error when app entry is not a dict."""
        config = {'apps': ["string", 123], 'locales': ['en-en']}
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertTrue(any("must be an object" in e for e in errors))

    def test_environments_not_a_list(self):
        """Test error when environments is not a list."""
        config = {'apps': [{'name': 'pos', 'environments': "not a list"}], 'locales': ['en-en']}
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertTrue(any("must be a non-empty list" in e for e in errors))

    def test_missing_locales_key(self):
        """Test error when locales key is missing."""
        config = {'apps': [{'name': 'pos', 'environments': ['live']}]}
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertIn("config.yml: missing 'locales' key", errors)

    def test_missing_required_locale(self):
        """Test error when required locale (en-en) is missing."""
        config = {
            'apps': [{'name': 'pos', 'environments': ['live']}],
            'locales': ['nl-NL', 'de-DE']
        }
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertTrue(any(f"missing required locale '{REQUIRED_LOCALE}'" in e for e in errors))

    def test_locales_not_a_list(self):
        """Test error when locales is not a list."""
        config = {
            'apps': [{'name': 'pos', 'environments': ['live']}],
            'locales': 'en-en'
        }
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertTrue(any("'locales' must be a non-empty list" in e for e in errors))

    def test_invalid_locale_entry(self):
        """Test error when locale entry is invalid (not a non-empty string)."""
        config = {
            'apps': [{'name': 'pos', 'environments': ['live']}],
            'locales': ['en-en', '', 123]
        }
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertTrue(any("invalid locale" in e for e in errors))

    def test_duplicate_app_names(self):
        """Test error when duplicate app names exist."""
        config = {
            'apps': [
                {'name': 'pos', 'environments': ['live']},
                {'name': 'pos', 'environments': ['staging']}
            ],
            'locales': ['en-en']
        }
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertTrue(any("duplicate app name 'pos'" in e for e in errors))

    def test_duplicate_environment_names(self):
        """Test error when duplicate environment names exist within same app."""
        config = {
            'apps': [
                {'name': 'pos', 'environments': ['live', 'staging', 'live']}
            ],
            'locales': ['en-en']
        }
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertTrue(any("duplicate environment 'live' in app 'pos'" in e for e in errors))

    def test_duplicate_locale_names(self):
        """Test error when duplicate locale names exist."""
        config = {
            'apps': [{'name': 'pos', 'environments': ['live']}],
            'locales': ['en-en', 'nl-NL', 'en-en']
        }
        expected_files, app_names, locales, errors = validate_config(config)
        self.assertTrue(any("duplicate locale 'en-en'" in e for e in errors))


class TestParseSemver(unittest.TestCase):
    """Test semantic version parsing."""

    def test_parse_versions(self):
        """Test parsing version strings to tuples."""
        self.assertEqual(parse_semver("1.0.0"), (1, 0, 0))
        self.assertEqual(parse_semver("10.20.30"), (10, 20, 30))
        self.assertEqual(parse_semver("0.0.1"), (0, 0, 1))

    def test_version_comparison(self):
        """Test that parsed versions compare correctly."""
        self.assertLess(parse_semver("1.0.0"), parse_semver("2.0.0"))
        self.assertLess(parse_semver("1.0.0"), parse_semver("1.1.0"))
        self.assertLess(parse_semver("1.0.0"), parse_semver("1.0.1"))
        self.assertLess(parse_semver("9.0.0"), parse_semver("10.0.0"))
        self.assertEqual(parse_semver("1.0.0"), parse_semver("1.0.0"))


class TestValidateISO8601(unittest.TestCase):
    """Test ISO 8601 timestamp validation."""

    def test_valid_timestamps(self):
        """Test valid ISO 8601 timestamps."""
        self.assertTrue(validate_iso8601("2026-01-10T09:00:00Z"))
        self.assertTrue(validate_iso8601("2026-01-10T09:00:00+00:00"))
        self.assertTrue(validate_iso8601("2026-01-10T09:00:00"))

    def test_datetime_objects(self):
        """Test that datetime objects are accepted."""
        dt = datetime(2026, 1, 10, 9, 0, 0)
        self.assertTrue(validate_iso8601(dt))

    def test_invalid_timestamps(self):
        """Test invalid timestamp formats."""
        # Note: datetime.fromisoformat() accepts date-only strings, so we test truly invalid formats
        self.assertFalse(validate_iso8601("invalid"))
        self.assertFalse(validate_iso8601(""))
        self.assertFalse(validate_iso8601(123))
        self.assertFalse(validate_iso8601("not-a-date"))


class TestValidateLocationHash(unittest.TestCase):
    """Test location hash validation."""

    def test_valid_hashes(self):
        """Test valid 64-character hex hashes."""
        valid_hash = "5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9"
        self.assertTrue(validate_location_hash(valid_hash))
        self.assertTrue(validate_location_hash("a" * 64))
        self.assertTrue(validate_location_hash("0" * 64))

    def test_invalid_hashes(self):
        """Test invalid hash formats."""
        self.assertFalse(validate_location_hash("abc"))  # Too short
        self.assertFalse(validate_location_hash("a" * 63))  # 63 chars
        self.assertFalse(validate_location_hash("a" * 65))  # 65 chars
        self.assertFalse(validate_location_hash("G" * 64))  # Invalid hex char
        self.assertFalse(validate_location_hash("ABCD" * 16))  # Uppercase
        self.assertFalse(validate_location_hash(""))


class TestValidation(unittest.TestCase):
    """Integration tests for validate.py."""

    def setUp(self):
        """Create temporary directory with manifests and notes subdirectories."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

        self.manifests_dir = os.path.join(self.temp_dir, 'manifests')
        os.makedirs(self.manifests_dir)

        self.notes_dir = os.path.join(self.temp_dir, 'notes')
        os.makedirs(self.notes_dir)

        self.original_cwd = os.getcwd()
        self.addCleanup(os.chdir, self.original_cwd)

    def write_manifest(self, filename, content):
        """Helper to write a manifest file in manifests/ directory."""
        filepath = os.path.join(self.manifests_dir, filename)
        with open(filepath, 'w') as f:
            f.write(content)
        return filepath

    def write_notes(self, filename, content):
        """Helper to write a notes file in notes/ directory."""
        filepath = os.path.join(self.notes_dir, filename)
        with open(filepath, 'w') as f:
            f.write(content)
        return filepath

    def write_config(self, content):
        """Helper to write config.yml file."""
        filepath = os.path.join(self.temp_dir, 'config.yml')
        with open(filepath, 'w') as f:
            f.write(content)
        return filepath

    def run_main(self):
        """Run main() and capture output and exit code."""
        os.chdir(self.temp_dir)
        captured_output = StringIO()

        with patch('sys.stdout', captured_output):
            with self.assertRaises(SystemExit) as cm:
                main()

        return cm.exception.code, captured_output.getvalue()

    def test_main_with_valid_manifests_and_notes(self):
        """Test main() with valid manifest and notes files."""
        config = """apps:
  - name: appone
    environments:
      - envone
  - name: apptwo
    environments:
      - envtwo
locales:
  - en-en
  - nl-NL
"""
        self.write_config(config)

        manifest_content = """versions:
  "1.0.0":
    released_at: 2026-01-10T09:00:00Z
    matchers:
      - matcher_type: default
        severity: green
"""
        self.write_manifest("appone--envone.yml", manifest_content)
        self.write_manifest("apptwo--envtwo.yml", manifest_content)

        notes_content = """locales:
  - name: en-en
    notes: Test release notes
"""
        self.write_notes("appone--1.0.0.yml", notes_content)
        self.write_notes("apptwo--1.0.0.yml", notes_content)

        exit_code, output = self.run_main()
        self.assertEqual(exit_code, 0)
        self.assertIn("All manifest and notes files are valid", output)

    def test_main_with_invalid_manifest(self):
        """Test main() with one invalid manifest."""
        config = """apps:
  - name: valid
    environments:
      - env
  - name: invalid
    environments:
      - env
locales:
  - en-en
"""
        self.write_config(config)

        valid_content = """versions:
  "1.0.0":
    released_at: 2026-01-10T09:00:00Z
    matchers:
      - matcher_type: default
        severity: green
"""
        invalid_content = """versions:
  "1.0.0":
    released_at: 2026-01-10T09:00:00Z
    matchers:
      - matcher_type: default
        severity: invalid_severity
"""
        self.write_manifest("valid--env.yml", valid_content)
        self.write_manifest("invalid--env.yml", invalid_content)

        # Write notes files for cross-validation
        notes_content = """locales:
  - name: en-en
    notes: Test release notes
"""
        self.write_notes("valid--1.0.0.yml", notes_content)
        self.write_notes("invalid--1.0.0.yml", notes_content)

        exit_code, output = self.run_main()
        self.assertEqual(exit_code, 1)
        self.assertIn("Validation failed", output)
        self.assertIn("invalid--env.yml", output)
        self.assertIn("invalid severity", output)

    def test_main_with_multiple_errors(self):
        """Test main() with multiple manifest files having errors."""
        config = """apps:
  - name: errorone
    environments:
      - env
  - name: errortwo
    environments:
      - env
locales:
  - en-en
"""
        self.write_config(config)

        error1_content = """versions:
  "1.0":
    released_at: 2026-01-10T09:00:00Z
    matchers:
      - matcher_type: default
        severity: green
"""
        error2_content = """versions:
  "1.0.0":
    released_at: invalid_timestamp
    matchers:
      - matcher_type: default
        severity: green
"""
        self.write_manifest("errorone--env.yml", error1_content)
        self.write_manifest("errortwo--env.yml", error2_content)

        exit_code, output = self.run_main()
        self.assertEqual(exit_code, 1)
        self.assertIn("Validation failed", output)
        self.assertIn("errorone--env.yml", output)
        self.assertIn("errortwo--env.yml", output)
        self.assertIn("Invalid semantic version format", output)
        self.assertIn("invalid ISO 8601 timestamp", output)

    def test_main_manifests_directory_not_found(self):
        """Test main() when manifests directory doesn't exist."""
        config = """apps:
  - name: app
    environments:
      - env
locales:
  - en-en
"""
        self.write_config(config)

        # Remove the manifests directory
        shutil.rmtree(self.manifests_dir)

        exit_code, output = self.run_main()
        self.assertEqual(exit_code, 1)
        self.assertIn("manifests directory not found", output)

    def test_main_with_empty_manifests_directory(self):
        """Test main() with empty manifests directory and empty config."""
        config = """apps: []
"""
        self.write_config(config)
        # Don't write any manifest files

        exit_code, output = self.run_main()
        self.assertEqual(exit_code, 1)
        self.assertIn("'apps' must be a non-empty list", output)

    def test_main_orphan_manifest_file(self):
        """Test main() detects manifest file not defined in config."""
        config = """apps:
  - name: pos
    environments:
      - live
locales:
  - en-en
"""
        self.write_config(config)

        content = """versions:
  "1.0.0":
    released_at: 2026-01-10T09:00:00Z
    matchers:
      - matcher_type: default
        severity: green
"""
        self.write_manifest("pos--live.yml", content)
        self.write_manifest("unknown--app.yml", content)  # orphan file

        exit_code, output = self.run_main()
        self.assertEqual(exit_code, 1)
        self.assertIn("Validation failed", output)
        self.assertIn("unknown--app.yml", output)
        self.assertIn("not defined in config.yml", output)

    def test_main_orphan_manifest_file_unknown_environment(self):
        """Test main() detects manifest file with environment not defined in config."""
        config = """apps:
  - name: pos
    environments:
      - live
locales:
  - en-en
"""
        self.write_config(config)

        content = """versions:
  "1.0.0":
    released_at: 2026-01-10T09:00:00Z
    matchers:
      - matcher_type: default
        severity: green
"""
        self.write_manifest("pos--live.yml", content)
        self.write_manifest("pos--staging.yml", content)  # unknown environment

        notes_content = """locales:
  - name: en-en
    notes: Test release notes
"""
        self.write_notes("pos--1.0.0.yml", notes_content)

        exit_code, output = self.run_main()
        self.assertEqual(exit_code, 1)
        self.assertIn("Validation failed", output)
        self.assertIn("pos--staging.yml", output)
        self.assertIn("not defined in config.yml", output)

    def test_main_orphan_notes_file(self):
        """Test main() detects notes file with app not defined in config."""
        config = """apps:
  - name: pos
    environments:
      - live
locales:
  - en-en
"""
        self.write_config(config)

        manifest_content = """versions:
  "1.0.0":
    released_at: 2026-01-10T09:00:00Z
    matchers:
      - matcher_type: default
        severity: green
"""
        self.write_manifest("pos--live.yml", manifest_content)

        notes_content = """locales:
  - name: en-en
    notes: Test release notes
"""
        self.write_notes("pos--1.0.0.yml", notes_content)
        self.write_notes("unknown--1.0.0.yml", notes_content)  # orphan notes file

        exit_code, output = self.run_main()
        self.assertEqual(exit_code, 1)
        self.assertIn("Validation failed", output)
        self.assertIn("unknown--1.0.0.yml", output)
        self.assertIn("App 'unknown' not defined in config.yml", output)

    def test_main_invalid_notes_filename_format(self):
        """Test main() detects notes file with invalid filename format."""
        config = """apps:
  - name: pos
    environments:
      - live
locales:
  - en-en
"""
        self.write_config(config)

        manifest_content = """versions:
  "1.0.0":
    released_at: 2026-01-10T09:00:00Z
    matchers:
      - matcher_type: default
        severity: green
"""
        self.write_manifest("pos--live.yml", manifest_content)

        notes_content = """locales:
  - name: en-en
    notes: Test release notes
"""
        self.write_notes("pos--1.0.0.yml", notes_content)
        self.write_notes("invalid-filename.yml", notes_content)  # invalid format

        exit_code, output = self.run_main()
        self.assertEqual(exit_code, 1)
        self.assertIn("Validation failed", output)
        self.assertIn("invalid-filename.yml", output)
        self.assertIn("Invalid filename format", output)

    def test_main_missing_notes_file_for_version(self):
        """Test main() detects missing notes file for version in manifest."""
        config = """apps:
  - name: pos
    environments:
      - live
locales:
  - en-en
"""
        self.write_config(config)

        manifest_content = """versions:
  "1.0.0":
    released_at: 2026-01-10T09:00:00Z
    matchers:
      - matcher_type: default
        severity: green
  "2.0.0":
    released_at: 2026-01-15T09:00:00Z
    matchers:
      - matcher_type: default
        severity: green
"""
        self.write_manifest("pos--live.yml", manifest_content)

        notes_content = """locales:
  - name: en-en
    notes: Test release notes
"""
        self.write_notes("pos--1.0.0.yml", notes_content)
        # pos--2.0.0.yml is missing

        exit_code, output = self.run_main()
        self.assertEqual(exit_code, 1)
        self.assertIn("Validation failed", output)
        self.assertIn("pos--2.0.0.yml", output)
        self.assertIn("Missing notes file for version 2.0.0", output)

    def test_main_unreferenced_notes_version(self):
        """Test main() detects notes file version not referenced in any manifest."""
        config = """apps:
  - name: pos
    environments:
      - live
locales:
  - en-en
"""
        self.write_config(config)

        manifest_content = """versions:
  "1.0.0":
    released_at: 2026-01-10T09:00:00Z
    matchers:
      - matcher_type: default
        severity: green
"""
        self.write_manifest("pos--live.yml", manifest_content)

        notes_content = """locales:
  - name: en-en
    notes: Test release notes
"""
        self.write_notes("pos--1.0.0.yml", notes_content)
        self.write_notes("pos--9.9.9.yml", notes_content)  # version not in any manifest

        exit_code, output = self.run_main()
        self.assertEqual(exit_code, 1)
        self.assertIn("Validation failed", output)
        self.assertIn("pos--9.9.9.yml", output)
        self.assertIn("Version 9.9.9 not referenced in any manifest file", output)

    def test_main_missing_manifest_file(self):
        """Test main() detects missing manifest file defined in config."""
        config = """apps:
  - name: pos
    environments:
      - live
      - staging
locales:
  - en-en
"""
        self.write_config(config)

        content = """versions:
  "1.0.0":
    released_at: 2026-01-10T09:00:00Z
    matchers:
      - matcher_type: default
        severity: green
"""
        self.write_manifest("pos--live.yml", content)
        # pos--staging.yml is missing

        exit_code, output = self.run_main()
        self.assertEqual(exit_code, 1)
        self.assertIn("Validation failed", output)
        self.assertIn("pos--staging.yml", output)
        self.assertIn("Missing manifest file", output)

    def test_main_invalid_app_name_in_config(self):
        """Test main() detects invalid app name in config."""
        config = """apps:
  - name: POS
    environments:
      - live
locales:
  - en-en
"""
        self.write_config(config)

        exit_code, output = self.run_main()
        self.assertEqual(exit_code, 1)
        self.assertIn("invalid app name 'POS'", output)

    def test_main_invalid_environment_name_in_config(self):
        """Test main() detects invalid environment name in config."""
        config = """apps:
  - name: pos
    environments:
      - LIVE
locales:
  - en-en
"""
        self.write_config(config)

        exit_code, output = self.run_main()
        self.assertEqual(exit_code, 1)
        self.assertIn("invalid environment 'LIVE'", output)


class TestGetVersionsFromManifests(unittest.TestCase):
    """Test get_versions_from_manifests function."""

    def setUp(self):
        """Create temporary directory with manifests subdirectory."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        self.manifests_dir = os.path.join(self.temp_dir, 'manifests')
        os.makedirs(self.manifests_dir)

    def write_manifest(self, filename, content):
        """Helper to write a manifest file."""
        filepath = os.path.join(self.manifests_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

    def test_file_read_error_raises_exception(self):
        """Test that file read errors are not suppressed."""
        # Create a manifest file that will cause a read error
        manifest_path = os.path.join(self.manifests_dir, 'pos--live.yml')
        os.makedirs(manifest_path)  # Create directory instead of file to cause error

        with self.assertRaises(RuntimeError) as cm:
            get_versions_from_manifests(Path(self.manifests_dir))

        self.assertIn("Error reading manifest file", str(cm.exception))


if __name__ == '__main__':
    unittest.main()
