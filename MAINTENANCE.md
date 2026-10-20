# Maintenance guide

This guide documents a practical process for maintaining `json-logging`.
The canonical maintainer list is [MAINTAINERS.md](MAINTAINERS.md), and coding
agents should follow [AGENTS.md](AGENTS.md).

## Issue triage

1. Search existing open and closed issues before creating a duplicate.
2. Request a minimal reproduction, Python and framework versions, relevant
   configuration, and expected versus actual behavior.
3. Classify the impact: correctness, compatibility, performance, security,
   documentation, or support question.
4. Verify the behavior against the current `master` branch and the latest
   published package when the distinction matters.
5. Link related issues and explain workarounds. Do not close unresolved
   behavior without clear evidence or the appropriate project decision.

For correlation ID defects, test synchronous and asynchronous handlers,
requests with and without a correlation header, and behavior across concurrent
requests. Do not rely on the request's presence in a Python call stack when
running in a different thread.

## Pull-request review

- Keep changes small and reviewable, with a linked issue when useful.
- Include reproduction steps for fixes, targeted tests, and compatibility
  notes. State what was *not* tested.
- Confirm no unintentional changes to log schema, correlation IDs, HTTP
  instrumentation, supported frameworks, or process-global initialization.
- Review hot-path allocations, concurrency, cleanup, dependency changes, and
  timeouts where relevant.
- Run unit tests, relevant framework tests, and the blocking Flake8 check.
  Let CI finish on the final commit before merging.
- Have a project maintainer review changes independently when practical;
  do not treat an AI review or green CI alone as sign-off for high-risk work.
- Add a changelog entry when a change affects library users.

## Development and CI

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r test-requirements.txt
python -m pytest --ignore=tests/smoketests -q
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

The GitHub Actions workflow `.github/workflows/code_quality.yml` runs
unit tests on Python 3.9–3.14, lint, and separate smoke tests on Python 3.9 and 3.14 for FastAPI,
Flask, Quart, and Sanic. The shared smoke-test runner starts an example
service on localhost:5000; that port must be available for local runs.

## Release process and permissions

**A merged PR does not automatically publish a PyPI release.** The repository
currently documents manual wheel/source builds and Twine uploads in
[dev.md](dev.md). The code-quality workflow does not publish distributions.

Only a person authorized on the PyPI project should perform a release.
Repository Write permission does not imply PyPI ownership or a PyPI Maintainer
role. Changing this policy or adding a release workflow requires project-owner
approval. Prefer protected environments and PyPI Trusted Publishing for future
automation, rather than checking secrets or API tokens into the repository.

### Release checklist

1. Agree on the scope, release version, and who will publish.
2. Review merged changes, supported-version compatibility, and any outstanding
   blockers or security concerns.
3. Update the version in `setup.py` and document user-facing changes in
   `CHANGELOG.md`.
4. Run the unit suite, lint, relevant smoke tests, and the full CI matrix on the
   final release commit. Inspect packaging metadata and included files.
5. Build fresh artifacts in a clean environment:

   ```bash
   python -m pip install --upgrade build twine
   python -m build
   python -m twine check dist/*
   ```

6. Have the designated PyPI publisher upload the approved artifacts using
   authorized credentials or an approved Trusted Publishing workflow. Do not
   publish automatically from a normal documentation or bug-fix PR.
7. Create and push the corresponding Git tag / GitHub release according to the
   agreed sequence; verify the tag, source, published version and artifacts
   all match. The exact tag naming convention should be consistent with prior
   releases.
8. Confirm the published release on PyPI, test installation in a clean
   environment, and announce the changes.

The package version and attribution metadata must be updated deliberately
and accurately, with approval from the people responsible for publishing.
PyPI account roles and distribution author/maintainer metadata are distinct;
changing a repository maintainer listing does not change either automatically.

## Maintenance records

Use GitHub issues, PRs, reviews, discussions, and release notes as the public
source of truth for maintenance work. Contributors may keep a private log of
decisions and links, but private personal records should not be committed
to the repository.
