# Maintainers

This project welcomes contributors and maintainers. The people listed here help
keep `json-logging` reliable, compatible with supported web frameworks, and
responsive to users.

| Person | Responsibility | Focus |
| --- | --- | --- |
| **Bob T.** ([@bobbui](https://github.com/bobbui)) | Original author and project steward | Project direction, original implementation, release coordination |
| **Udit Agrawal** ([@suppagoddo](https://github.com/suppagoddo)) | Repository maintainer / GitHub collaborator | Test infrastructure, CI reliability, issue triage, and technical reviews |

## How maintenance works

- Open an issue for a reproducible defect or an enhancement proposal.
- Open a focused pull request with tests and a description of behavioral changes.
- Prefer independent review for nontrivial changes, especially changes affecting
  JSON output, correlation IDs, supported frameworks, or packaging.
- For the detailed contribution, review, and release process, read
  [MAINTENANCE.md](MAINTENANCE.md).
- Coding agents and contributors should also follow [AGENTS.md](AGENTS.md).

## Release permissions and attribution

Being listed as a repository maintainer does **not** confer PyPI publishing
permissions. PyPI project roles are managed separately by the existing PyPI
project owner. GitHub repository access and package publishing credentials must
not be conflated.

Bob's original authorship is preserved. Changes to distribution metadata,
additional author/maintainer credit, and PyPI project roles require an explicit
decision by the project owner and should reflect actual contributions and
responsibilities.

## Previous work

- [PR #121](https://github.com/bobbui/json-logging-python/pull/121):
  smoke-test startup reliability, polling deadlines, and process cleanup
  (Udit Agrawal).
