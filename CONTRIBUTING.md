# Contributing to json-logging

Thx for wanting to help. Please read this before you open a pull request.

## Issues come first

Every pull request needs a linked issue that a maintainer has triaged. An issue
is triaged once a maintainer has added the `ready` label to it. Until then it
carries the `needs triage` label.

The flow is:

1. Search open and closed issues for the same problem or idea.
2. Open a new issue from one of the templates, with a minimal reproduction for
   bugs or a concrete use case for features.
3. Wait for a maintainer to triage it. They may ask questions, mark it as a
   duplicate, decline it, or label it `ready`.
4. Once it's `ready`, comment that you're picking it up and open a PR that says
   `Fixes #<issue>` in its description.

Pull requests without a linked `ready` issue may be closed without review, even
if the change looks fine. This keeps review time for changes the project has
agreed it wants, and it saves you from writing code that ends up declined.

A few changes don't need an issue: typo and broken link fixes, Dependabot
updates, and release PRs opened by maintainers.

## Before you open the PR

- Keep it to one bug or feature.
- Add tests for the behavior you changed.
- Add a changelog entry under `Unreleased` in `CHANGELOG.md` when users will
  notice the change.
- Run the checks described in [MAINTENANCE.md](MAINTENANCE.md#development-and-ci).

If you use an AI coding agent, point it at [AGENTS.md](AGENTS.md). The same
triage rule applies.
