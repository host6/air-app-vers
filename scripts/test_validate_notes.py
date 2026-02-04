#!/usr/bin/env python3
"""
Unit tests for notes validation functions.
"""

import unittest
import tempfile
import os
import shutil
from pathlib import Path

from scripts.validate_notes import (
    validate_notes_filename,
    validate_notes_file,
)


class TestValidateNotesFilename(unittest.TestCase):
    """Test notes filename validation."""

    def test_valid_filenames(self):
        """Test valid notes filenames."""
        app_name, version = validate_notes_filename("pos--1.0.0.yml")
        self.assertEqual(app_name, "pos")
        self.assertEqual(version, "1.0.0")

        app_name, version = validate_notes_filename("backoffice--10.20.30.yml")
        self.assertEqual(app_name, "backoffice")
        self.assertEqual(version, "10.20.30")

    def test_invalid_filenames(self):
        """Test invalid notes filenames."""
        # Missing version
        app_name, version = validate_notes_filename("pos.yml")
        self.assertIsNone(app_name)
        self.assertIsNone(version)

        # Invalid separator
        app_name, version = validate_notes_filename("pos-1.0.0.yml")
        self.assertIsNone(app_name)
        self.assertIsNone(version)

        # Uppercase app name
        app_name, version = validate_notes_filename("POS--1.0.0.yml")
        self.assertIsNone(app_name)
        self.assertIsNone(version)

        # Invalid version format
        app_name, version = validate_notes_filename("pos--1.0.yml")
        self.assertIsNone(app_name)
        self.assertIsNone(version)


class TestValidateNotesFile(unittest.TestCase):
    """Test notes file content validation."""

    def setUp(self):
        """Create temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def write_notes(self, content):
        """Helper to write a notes file."""
        filepath = os.path.join(self.temp_dir, "test--1.0.0.yml")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return Path(filepath)

    def test_valid_notes_file(self):
        """Test valid notes file."""
        content = """locales:
  - name: en-en
    notes: Test release notes
  - name: nl-NL
    notes: Test release notes in Dutch
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en', 'nl-NL', 'de-DE'})
        self.assertEqual(errors, [])

    def test_missing_locales_key(self):
        """Test error when locales key is missing."""
        content = """notes: Test"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en'})
        self.assertTrue(any("Missing 'locales'" in e for e in errors))

    def test_empty_locales_list(self):
        """Test error when locales list is empty."""
        content = """locales: []
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en'})
        self.assertTrue(any("At least one locale entry is required" in e for e in errors))

    def test_missing_required_locale(self):
        """Test error when required locale (en-en) is missing."""
        content = """locales:
  - name: nl-NL
    notes: Test notes in Dutch
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en', 'nl-NL'})
        self.assertTrue(any("Missing required locale 'en-en'" in e for e in errors))

    def test_undefined_locale(self):
        """Test error when locale is not defined in config."""
        content = """locales:
  - name: en-en
    notes: Test notes
  - name: fr-FR
    notes: Notes in French
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en', 'nl-NL'})
        self.assertTrue(any("not defined in config.yml" in e for e in errors))

    def test_notes_too_long(self):
        """Test error when notes exceed max length."""
        long_notes = "x" * 501
        content = f"""locales:
  - name: en-en
    notes: {long_notes}
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en'})
        self.assertTrue(any("exceeds" in e and "characters" in e for e in errors))

    def test_empty_notes(self):
        """Test error when notes field is empty."""
        content = """locales:
  - name: en-en
    notes: ""
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en'})
        self.assertTrue(any("cannot be empty" in e for e in errors))

    def test_invalid_yaml(self):
        """Test error when notes file has invalid YAML syntax."""
        content = """locales:
  - name: [invalid
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en'})
        self.assertTrue(any("YAML syntax error" in e for e in errors))

    def test_duplicate_locale(self):
        """Test error when same locale appears multiple times."""
        content = """locales:
  - name: en-en
    notes: First entry
  - name: en-en
    notes: Duplicate entry
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en'})
        self.assertTrue(any("Duplicate locale entry" in e for e in errors))

    def test_locales_not_a_list(self):
        """Test error when locales is not a list."""
        content = """locales:
  en-en: Test notes
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en'})
        self.assertTrue(any("'locales' must be a list" in e for e in errors))

    def test_locale_entry_not_an_object(self):
        """Test error when locale entry is not an object."""
        content = """locales:
  - en-en
  - nl-NL
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en', 'nl-NL'})
        self.assertTrue(any("must be an object" in e for e in errors))

    def test_locale_entry_missing_name(self):
        """Test error when locale entry is missing 'name' field."""
        content = """locales:
  - notes: Test notes without name
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en'})
        self.assertTrue(any("missing 'name' field" in e for e in errors))

    def test_locale_name_not_a_string(self):
        """Test error when locale 'name' is not a string."""
        content = """locales:
  - name: 123
    notes: Test notes
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en'})
        self.assertTrue(any("'name' must be a string" in e for e in errors))

    def test_locale_missing_notes_field(self):
        """Test error when locale entry is missing 'notes' field."""
        content = """locales:
  - name: en-en
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en'})
        self.assertTrue(any("missing 'notes' field" in e for e in errors))

    def test_locale_notes_not_a_string(self):
        """Test error when locale 'notes' is not a string."""
        content = """locales:
  - name: en-en
    notes: 123
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en'})
        self.assertTrue(any("'notes' must be a string" in e for e in errors))

    def test_utf8_encoded_notes(self):
        """Test notes file with UTF-8 characters is validated correctly."""
        content = """locales:
  - name: en-en
    notes: "Release notes with special characters: äöü ñ 日本語 émojis 🎉"
"""
        filepath = self.write_notes(content)
        errors = validate_notes_file(filepath, {'en-en'})
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()

