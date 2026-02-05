---
registered_at: 2026-02-05T08:29:48Z
change_id: 2602051129-add-missing-validations
baseline: 5a261cc73822635691444878f2827887227dd514
archived_at: 2026-02-05T15:09:33Z
---

# Change request: Add missing manifest validation checks

## Why

A comprehensive review of existing tests revealed that 7 validation requirements for manifest files are not implemented. These missing validations could allow invalid manifest configurations to pass validation, potentially causing issues in production.

## What

Implement the following missing validation checks for manifest files:

Date/time validations:

- `released_at dates are in chronological order` (newer versions have later dates)
- `released_at is not in the future`
- `released_at not older than 12 months`

Matcher conflict validations:

- `No duplicate matchers for same version` (e.g., two default matchers)
- `No conflicting location hash matchers` (same hash with different severities)
- `No conflicting country matchers` (same country with different severities)

Schema validation:

- `No extra fields`

Semantic versioning enhancement (optional, needs clarification):

- `Semantic versioning format` with prerelease (e.g., "2.0.0-rc.2") - current regex `^\d+\.\d+\.\d+$` rejects these
