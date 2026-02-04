# Implementation plan: Fix validation bugs and improve error reporting

## Construction

- [x] update: [scripts/validate.py](../../scripts/validate.py)
  - fix: Don't suppress exception in `get_versions_from_manifests()` - re-raise RuntimeError
  - fix: Add `encoding='utf-8'` to `open()` call

- [x] update: [scripts/validate_config.py](../../scripts/validate_config.py)
  - fix: Add `encoding='utf-8'` to `open()` call in `load_config()`
  - fix: Detect and report duplicate app names
  - fix: Detect and report duplicate environment names within same app
  - fix: Detect and report duplicate locale names

- [x] update: [scripts/validate_manifest.py](../../scripts/validate_manifest.py)
  - fix: Add `encoding='utf-8'` to `open()` call

- [x] update: [scripts/test_validate.py](../../scripts/test_validate.py)
  - add: Test for duplicate app names detection
  - add: Test for duplicate environment names detection
  - add: Test for duplicate locale names detection
  - add: Test for `get_versions_from_manifests()` error handling

- [x] update: [scripts/test_validate_manifest.py](../../scripts/test_validate_manifest.py)
  - add: Test for UTF-8 encoded manifest file validation

- [x] update: [scripts/test_validate_notes.py](../../scripts/test_validate_notes.py)
  - add: Test for UTF-8 encoded notes file validation
  - fix: Add `encoding='utf-8'` to `write_notes()` helper

- [x] review: Run tests and verify all fixes work correctly
  - `python -m unittest discover scripts -v` - 70 tests passing
