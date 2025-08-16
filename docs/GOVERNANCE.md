---
title: Project Governance
---

[← Back to docs index](./_index.md)

# Project Governance

This document defines the governance model for the trading platform
repository.  It establishes branch protection rules, pull request
procedures, and ownership guidelines to ensure a consistent and
high‑quality contribution process.

## Branch Protection

The repository enforces branch protection on the `main` branch to
prevent unreviewed or untested code from being merged.  The following
rules are recommended for GitHub configuration:

* **Require pull request reviews** – All changes to `main` must
  go through a pull request (PR) approved by at least one maintainer.
* **Enforce status checks** – CI must run and pass (tests, linting and
  coverage) before the PR can be merged.
* **Require signed commits** – To maintain integrity, commits must be
  signed by the author (GPG or S/MIME).
* **Restrict force pushes and deletions** – Only administrators may
  force push or delete protected branches.

For detailed instructions on setting branch protection in GitHub, refer
to the [GitHub Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-branch-protection-rules).

### Verifying Branch Protection

After configuring branch protection rules in GitHub, maintainers should
verify that the settings are in effect.  You can do this by navigating
to **Settings → Branches** and ensuring that the required status
checks and review approvals are enabled for `main`.  Additionally,
create a test pull request and confirm that merging is blocked until
the CI jobs pass and a maintainer reviews the PR.  Document any
changes to branch protection in `CHANGELOG.md`.

## Pull Request Workflow

1. **Fork and branch** – Contributors should create feature branches
   from `main` or fork the repository before making changes.
2. **Write tests and docs** – All new features or bug fixes must
   include corresponding tests and documentation updates.
3. **Submit a PR** – Open a pull request targeting `main`.  Include a
   concise description, link to any relevant issues, and attach
   screenshots or logs if applicable.
4. **Review and iterate** – A maintainer reviews the PR, requests
   changes if necessary, and approves when ready.  CI must pass before
   merging.
5. **Merge and clean up** – Once approved, the maintainer merges the
   PR via a merge commit or squash.  Delete the feature branch when
   appropriate.

## Ownership & Roles

* **Maintainers** – Core team members responsible for reviewing PRs,
  maintaining CI, and guiding project direction.  They have write
  access to the repository.
* **Contributors** – Anyone submitting PRs.  They are encouraged to
  follow the contribution guidelines and respect the review process.
* **Security contacts** – Maintainers who handle vulnerability
  disclosures.  See `SECURITY.md` for contact information.

## Conflict Resolution

Disagreements should be resolved through constructive discussion.
If consensus cannot be reached, maintainers will decide by majority
vote.  Escalate unresolved issues to the project leads or
security contacts as appropriate.