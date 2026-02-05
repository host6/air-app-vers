#!/usr/bin/env python3
"""
Unit tests for manifest file validation.
"""

import unittest
import tempfile
import os
import sys
import shutil
from textwrap import dedent

# Add scripts directory to path for imports
from scripts.validate import validate_manifest


class TestValidateManifest(unittest.TestCase):
    """Test manifest file validation."""

    def setUp(self):
        """Create temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def write_manifest(self, content):
        """Helper to write a manifest file."""
        filepath = os.path.join(self.temp_dir, "test.yml")
        with open(filepath, 'w') as f:
            f.write(dedent(content))
        return filepath

    def test_manifest_validation(self):
        """Table-driven tests for manifest validation."""

        valid_hash = "5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9"

        test_cases = [
            {
                'name': 'valid_manifest',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        notes: Test version
                        matchers:
                          - matcher_type: default
                            severity: green
                      "2.0.0":
                        released_at: 2026-01-15T09:00:00Z
                        matchers:
                          - matcher_type: country
                            matcher_value: US
                            severity: yellow
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': [],
            },
            {
                'name': 'valid_manifest_all_matcher_types',
                'content': f"""
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        notes: Optional notes field
                        matchers:
                          - matcher_type: location_hash
                            matcher_value: {valid_hash}
                            severity: red
                          - matcher_type: country
                            matcher_value: US
                            severity: yellow
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': [],
            },
            {
                'name': 'semantic_version_ordering',
                'content': """
                    versions:
                      "9.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: green
                      "10.0.0":
                        released_at: 2026-01-15T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': [],
            },
            {
                'name': 'duplicate_versions_yaml_overwrites',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: green
                      "1.0.0":
                        released_at: 2026-01-15T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': [],
            },
            {
                'name': 'invalid_yaml',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: green
                          invalid yaml here: [
                """,
                'expected_errors': ['YAML syntax error'],
            },
            {
                'name': 'missing_versions_key',
                'content': """
                    other_key:
                      value: test
                """,
                'expected_errors': ["Missing 'versions' key"],
            },
            {
                'name': 'empty_file',
                'content': '',
                'expected_errors': ["Missing 'versions' key"],
            },
            {
                'name': 'empty_versions_dict',
                'content': 'versions: {}',
                'expected_errors': ['No versions defined'],
            },
            {
                'name': 'null_versions',
                'content': 'versions: null',
                'expected_errors': ['No versions defined'],
            },
            {
                'name': 'versions_is_list_not_dict',
                'content': """
                    versions:
                      - "1.0.0"
                      - "2.0.0"
                """,
                'expected_errors': ['versions'],
            },
            {
                'name': 'invalid_semver_format',
                'content': """
                    versions:
                      "1.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': ['Invalid semantic version format'],
            },
            {
                'name': 'invalid_semver_with_letters',
                'content': """
                    versions:
                      "a.b.c":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': ['Invalid semantic version format: a.b.c'],
            },
            {
                'name': 'versions_not_ascending',
                'content': """
                    versions:
                      "2.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: green
                      "1.0.0":
                        released_at: 2026-01-15T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': ['not in ascending order'],
            },
            {
                'name': 'missing_released_at',
                'content': """
                    versions:
                      "1.0.0":
                        matchers:
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': ["missing 'released_at'"],
            },
            {
                'name': 'invalid_iso8601',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: "not a timestamp"
                        matchers:
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': ['invalid ISO 8601 timestamp'],
            },
            {
                'name': 'missing_matchers',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                """,
                'expected_errors': ["missing 'matchers'"],
            },
            {
                'name': 'invalid_matcher_type',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: invalid_type
                            severity: green
                """,
                'expected_errors': ['invalid matcher_type'],
            },
            {
                'name': 'invalid_severity',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: invalid
                """,
                'expected_errors': ['invalid severity'],
            },
            {
                'name': 'missing_severity',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: default
                """,
                'expected_errors': ['invalid severity'],
            },
            {
                'name': 'invalid_country_code',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: country
                            matcher_value: XX
                            severity: green
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': ['invalid country code'],
            },
            {
                'name': 'country_matcher_missing_value',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: country
                            severity: green
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': ['invalid country code'],
            },
            {
                'name': 'invalid_location_hash',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: location_hash
                            matcher_value: "invalid"
                            severity: green
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': ['invalid location hash format'],
            },
            {
                'name': 'location_hash_missing_value',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: location_hash
                            severity: green
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': ['invalid location hash format'],
            },
            {
                'name': 'missing_default_matcher',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: country
                            matcher_value: US
                            severity: green
                """,
                'expected_errors': ['missing default matcher'],
            },
            {
                'name': 'matchers_not_a_list',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers: "not a list"
                """,
                'expected_errors': ['matchers'],
            },
            {
                'name': 'matcher_not_a_dict',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - "just a string"
                          - 123
                """,
                'expected_errors': ['matcher'],
            },
            {
                'name': 'multiple_invalid_semvers',
                'content': """
                    versions:
                      "x.y.z":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: green
                      "1.2":
                        released_at: 2026-01-15T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: green
                      "a.b.c":
                        released_at: 2026-01-20T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': [
                    'Invalid semantic version format: x.y.z',
                    'Invalid semantic version format: 1.2',
                    'Invalid semantic version format: a.b.c'
                ],
            },
            {
                'name': 'valid_then_invalid_semver',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: green
                      "invalid":
                        released_at: 2026-01-15T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': ['Invalid semantic version format: invalid'],
            },
            {
                'name': 'multiple_versions_with_errors',
                'content': """
                    versions:
                      "1.0.0":
                        released_at: 2026-01-10T09:00:00Z
                        matchers:
                          - matcher_type: default
                            severity: invalid_severity
                      "2.0.0":
                        released_at: 2026-01-15T09:00:00Z
                        matchers:
                          - matcher_type: country
                            matcher_value: XX
                            severity: green
                          - matcher_type: default
                            severity: green
                """,
                'expected_errors': ['invalid severity', 'invalid country code'],
            },
        ]

        for tc in test_cases:
            with self.subTest(name=tc['name']):
                filepath = self.write_manifest(tc['content'])
                errors = validate_manifest(filepath)

                if not tc['expected_errors']:
                    self.assertEqual(errors, [],
                                   f"Expected no errors, got: {errors}")
                else:
                    for expected in tc['expected_errors']:
                        self.assertTrue(
                            any(expected in err for err in errors),
                            f"Expected '{expected}' in errors, got: {errors}"
                        )

    def test_invalid_semver_followed_by_valid(self):
        """Test invalid version followed by valid version (no ordering error)."""
        content = """
            versions:
              "a.b.c":
                released_at: 2026-01-10T09:00:00Z
                matchers:
                  - matcher_type: default
                    severity: green
              "1.0.0":
                released_at: 2026-01-15T09:00:00Z
                matchers:
                  - matcher_type: default
                    severity: green
        """
        filepath = self.write_manifest(content)
        errors = validate_manifest(filepath)
        # Should report invalid format but not crash
        self.assertTrue(any("Invalid semantic version format: a.b.c" in err for err in errors))
        # Should not report ordering error since invalid version is skipped
        self.assertFalse(any("not in ascending order" in err for err in errors))

    def test_mixed_valid_invalid_versions_ordering(self):
        """Test that ordering check only applies to valid versions."""
        content = """
            versions:
              "1.0.0":
                released_at: 2026-01-10T09:00:00Z
                matchers:
                  - matcher_type: default
                    severity: green
              "invalid":
                released_at: 2026-01-15T09:00:00Z
                matchers:
                  - matcher_type: default
                    severity: green
              "2.0.0":
                released_at: 2026-01-20T09:00:00Z
                matchers:
                  - matcher_type: default
                    severity: green
        """
        filepath = self.write_manifest(content)
        errors = validate_manifest(filepath)
        # Should report invalid format
        self.assertTrue(any("Invalid semantic version format: invalid" in err for err in errors))
        # Should not report ordering error (1.0.0 < 2.0.0 is correct)
        self.assertFalse(any("not in ascending order" in err for err in errors))

    def test_version_details_is_not_dict(self):
        """Test manifest with versions having invalid details types."""
        content = """
            versions:
              "1.0.0": "string"
              "2.0.0": 456
              "3.0.0": null
        """
        filepath = self.write_manifest(content)
        errors = validate_manifest(filepath)
        # Should report all invalid details
        self.assertTrue(any("1.0.0" in err and "not str" in err for err in errors))
        self.assertTrue(any("2.0.0" in err and "not int" in err for err in errors))
        self.assertTrue(any("3.0.0" in err and "not NoneType" in err for err in errors))

    def test_file_not_found(self):
        """Test non-existent file returns error."""
        filepath = os.path.join(self.temp_dir, "nonexistent.yml")
        errors = validate_manifest(filepath)
        self.assertTrue(len(errors) > 0)
        self.assertTrue(any("Error reading file" in err for err in errors))

    def test_utf8_encoded_manifest(self):
        """Test manifest with UTF-8 characters is validated correctly."""
        filepath = os.path.join(self.temp_dir, "test.yml")
        content = """versions:
  "1.0.0":
    released_at: 2026-01-10T09:00:00Z
    notes: "Versión con caracteres especiales: äöü ñ 日本語"
    matchers:
      - matcher_type: default
        severity: green
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        errors = validate_manifest(filepath)
        self.assertEqual(errors, [])

    def test_released_at_dates_are_in_chronological_order(self):
        """Test error when released_at dates are not in chronological order."""
        content = """
            versions:
              "1.0.0":
                released_at: 2026-01-15T09:00:00Z
                matchers:
                  - matcher_type: default
                    severity: green
              "2.0.0":
                released_at: 2026-01-10T09:00:00Z
                matchers:
                  - matcher_type: default
                    severity: green
        """
        filepath = self.write_manifest(content)
        errors = validate_manifest(filepath)
        self.assertTrue(any("not in chronological order" in err for err in errors))

    def test_released_at_is_not_in_the_future(self):
        """Test error when released_at is in the future."""
        content = """
            versions:
              "1.0.0":
                released_at: 2099-01-10T09:00:00Z
                matchers:
                  - matcher_type: default
                    severity: green
        """
        filepath = self.write_manifest(content)
        errors = validate_manifest(filepath)
        self.assertTrue(any("in the future" in err for err in errors))

    def test_released_at_not_older_than_12_months(self):
        """Test error when released_at is older than 12 months."""
        content = """
            versions:
              "1.0.0":
                released_at: 2020-01-10T09:00:00Z
                matchers:
                  - matcher_type: default
                    severity: green
        """
        filepath = self.write_manifest(content)
        errors = validate_manifest(filepath)
        self.assertTrue(any("older than 12 months" in err for err in errors))

    def test_no_duplicate_matchers_for_same_version(self):
        """Test error when duplicate matchers exist for same version."""
        content = """
            versions:
              "1.0.0":
                released_at: 2026-01-10T09:00:00Z
                matchers:
                  - matcher_type: default
                    severity: green
                  - matcher_type: default
                    severity: yellow
        """
        filepath = self.write_manifest(content)
        errors = validate_manifest(filepath)
        self.assertTrue(any("duplicate default matchers" in err for err in errors))

    def test_no_conflicting_location_hash_matchers(self):
        """Test error when conflicting location hash matchers exist."""
        valid_hash = "5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9"
        content = f"""
            versions:
              "1.0.0":
                released_at: 2026-01-10T09:00:00Z
                matchers:
                  - matcher_type: location_hash
                    matcher_value: {valid_hash}
                    severity: green
                  - matcher_type: location_hash
                    matcher_value: {valid_hash}
                    severity: red
                  - matcher_type: default
                    severity: green
        """
        filepath = self.write_manifest(content)
        errors = validate_manifest(filepath)
        self.assertTrue(any("conflicting location hash matchers" in err for err in errors))

    def test_no_conflicting_country_matchers(self):
        """Test error when conflicting country matchers exist."""
        content = """
            versions:
              "1.0.0":
                released_at: 2026-01-10T09:00:00Z
                matchers:
                  - matcher_type: country
                    matcher_value: US
                    severity: green
                  - matcher_type: country
                    matcher_value: US
                    severity: red
                  - matcher_type: default
                    severity: green
        """
        filepath = self.write_manifest(content)
        errors = validate_manifest(filepath)
        self.assertTrue(any("conflicting country matchers" in err for err in errors))

    def test_no_extra_fields(self):
        """Test error when extra fields are present in version or matcher."""
        content = """
            versions:
              "1.0.0":
                released_at: 2026-01-10T09:00:00Z
                extra_field: should not be here
                matchers:
                  - matcher_type: default
                    severity: green
                    unknown_field: invalid
        """
        filepath = self.write_manifest(content)
        errors = validate_manifest(filepath)
        self.assertTrue(any("extra fields not allowed" in err and "extra_field" in err for err in errors))
        self.assertTrue(any("extra fields not allowed" in err and "unknown_field" in err for err in errors))


if __name__ == '__main__':
    unittest.main()
