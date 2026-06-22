## Summary

Describe the change and why it is needed.

## Checklist

- [ ] Tests added or updated
- [ ] Docs updated for user-facing changes
- [ ] Examples updated if behavior is user-facing
- [ ] No undocumented CLI/API behavior changes
- [ ] No overclaiming of unsupported adapters, formats, or report outputs
- [ ] CLI/API behavior verified locally
- [ ] Backwards compatibility considered for public fields, config keys, and commands

## Verification

```bash
pytest
ruff check .
mypy datasetlint
mkdocs build --strict
```
