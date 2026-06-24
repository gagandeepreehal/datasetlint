## Summary

Describe the change and the user-facing behavior.

## Verification

```bash
pytest
ruff check .
ruff format --check .
mypy datasetlint
```

## Checklist

- [ ] Added or updated tests for behavior changes.
- [ ] Updated docs, examples, or schema files when public behavior changed.
- [ ] Kept runtime dependencies lightweight and offline-friendly.
