---
title: Branch Protection and Pull Request Workflow
---

[← Back to docs index](./_index.md)

# Branch Protection and PR Workflow

This document outlines recommended policies for protecting the main branch
and ensuring high‑quality contributions via pull requests.  These
guidelines are optional but strongly encouraged for teams deploying the
trading platform in collaborative environments.

## Branch Protection Rules

At a minimum, we recommend enabling the following protections on your
primary branch (e.g. `main` or `master`):

1. **Require pull requests before merging** – Direct pushes to the
   protected branch should be disallowed.  All changes must go through
   a pull request.
2. **Require status checks to pass before merging** – Ensure that the CI
   pipeline (unit tests, integration tests, linting and coverage)
   completes successfully.  Failing checks should block the merge.
3. **Require at least one code review** – A designated reviewer or
   code owner must approve each pull request.  Consider requiring
   multiple approvals for critical components.
4. **Restrict who can push** – Limit merge rights to a trusted group
   (e.g. release managers or maintainers).  Use GitHub roles or teams
   for fine‑grained control.
5. **Signed commits** – Optionally require signed commits to ensure
   authenticity.

These rules can be configured via GitHub’s repository settings under
Branch protection rules.  See GitHub’s documentation for step‑by‑step
instructions.

## Pull Request Workflow

To ensure consistent code quality and maintainability, follow this
workflow when submitting changes:

1. **Fork and branch** – Create a feature branch off `main`.  Use
   descriptive names like `feature/volatility-calibration` or
   `bugfix/slack-retries`.
2. **Write tests** – Implement unit and integration tests alongside
   your code changes.  Tests should live under `trading_platform/tests`.
3. **Update documentation** – If your change affects behaviour or
   configuration, update the relevant documentation in `docs/` and the
   environment examples in `env/`.
4. **Run pre-commit checks** – If you have the pre‑commit hooks
   installed (`pre-commit install`), run `pre-commit run --all-files`
   locally to catch linting and formatting issues.
5. **Open a pull request** – Target the `main` branch.  Fill out the
   pull request template and describe the change, motivation, and any
   related issues.
6. **Address feedback** – Incorporate reviewer comments and push
   additional commits to your branch.  CI will re‑run automatically.
7. **Merge** – Once approvals and checks are complete, merge using
   “Squash and merge” or “Rebase and merge” to maintain a clean
   history.

Following these guidelines helps maintain stability and traceability in
the codebase.