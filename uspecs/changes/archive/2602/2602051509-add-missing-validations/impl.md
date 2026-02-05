# Implementation Plan

## Construction

- [x] update: [scripts/validate_manifest.py](../../../scripts/validate_manifest.py)
  - add: `released_at dates are in chronological order` validation
  - add: `released_at is not in the future` validation
  - add: `released_at not older than 12 months` validation
  - add: `No duplicate matchers for same version` validation
  - add: `No conflicting location hash matchers` validation
  - add: `No conflicting country matchers` validation
  - add: `No extra fields` validation
- [x] update: [scripts/test_validate_manifest.py](../../../scripts/test_validate_manifest.py)
  - add: `test_released_at_dates_are_in_chronological_order`
  - add: `test_released_at_is_not_in_the_future`
  - add: `test_released_at_not_older_than_12_months`
  - add: `test_no_duplicate_matchers_for_same_version`
  - add: `test_no_conflicting_location_hash_matchers`
  - add: `test_no_conflicting_country_matchers`
  - add: `test_no_extra_fields`
- [x] review: Run all tests to verify implementation
