# Security Policy

## Supported Versions

Security fixes are provided for the latest released version of DatasetLint. Before the first tagged public release, security fixes target `main`.

## Reporting A Vulnerability

Please report suspected security issues privately by opening a GitHub security advisory for the repository:

https://github.com/gagandeepreehal/datasetlint/security/advisories/new

If GitHub advisories are unavailable, open a public issue asking for a private security contact, but do not include exploit details in that issue.

Reports should include:

- affected DatasetLint version or commit
- Python version and operating system
- install method
- minimal reproduction or affected input shape
- expected impact
- any known workaround

## Dataset Privacy

Do not post sensitive datasets publicly. Redact:

- private file paths
- dataset names that identify customers, sites, robots, or people
- GPS coordinates or map details that should not be public
- tokens, credentials, cloud paths, and internal URLs
- images, labels, or logs that contain private information

Prefer a tiny synthetic repro that preserves the failing folder structure, CSV columns, timestamps, or metadata shape.

## Scope

DatasetLint is a local file validation tool. Security issues most likely involve unsafe file handling, confusing report output that leaks sensitive paths, dependency vulnerabilities, or denial-of-service behavior on malformed inputs.
