# Concepts

A dataset check is a deterministic function that reads a loaded dataset context
and returns findings with a severity, location, and message.

An adapter turns an input path into the folder-oriented context DatasetLint can
check. The folder adapter is supported in v0; other robotics formats are
detection-only until small fixtures and parsers are available.

Severity levels:

- `error`: likely blocks reliable use of the dataset.
- `warning`: suspicious and worth review.
- `info`: descriptive context.
