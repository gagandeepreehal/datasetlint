# Reports

JSON reports include:

- dataset path and generation timestamp
- DatasetLint version
- dataset summary and fingerprint
- adapter metadata
- config used
- checks run
- issues and findings
- severity counts and check stats

Generate one with:

```bash
datasetlint report examples/minimal_dataset --out report.json
```

The JSON schema is committed at `schemas/report.schema.json`.
