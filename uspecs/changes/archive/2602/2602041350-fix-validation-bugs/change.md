---
registered_at: 2026-02-04T13:37:47Z
change_id: 2602041715-fix-validation-bugs
baseline: 065f56374ca4dce84df6fdf01fd2e0d452d3f63f
archived_at: 2026-02-04T13:50:14Z
---

# Change request: Fix validation bugs and improve error reporting

## Why

Several validation issues were identified that could lead to silent failures or missed configuration errors:
- Exception suppressed in validate.py making debugging difficult
- YAML files not opened with UTF-8 encoding causing potential encoding issues
- Duplicate app names, environment names, and locale names are silently ignored instead of being reported as errors

## What

Fix the following issues:

- `validate.py`: Don't suppress exception in `get_versions_from_manifests()` (line 44)
- All modules: Use `encoding='utf-8'` when opening YAML files
- `validate_config.py`: Detect and report duplicate app names
- `validate_config.py`: Detect and report duplicate environment names within same app
- `validate_config.py`: Detect and report duplicate locale names
