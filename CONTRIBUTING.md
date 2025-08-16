# Contributing to the Trading Platform

Thank you for your interest in contributing to this project!  We
appreciate community support and welcome contributions of code, tests,
documentation and ideas.  This guide outlines the steps to follow
when proposing changes.

## Getting Started

1. **Read the [Governance](docs/GOVERNANCE.md) and [Security](docs/SECURITY.md)
   guidelines** to understand the rules and expectations for
   contributions.
2. **Set up your development environment** by cloning the repository
   and installing dependencies listed in `workers/requirements.txt`.
   Offline execution is supported; see `scripts/README.md` for
   offline commands.
3. **Choose an issue or propose your own** – Look through existing
   issues or open a new one to discuss your idea before implementing.

## Making Changes

* **Branch from `main`** – Create a descriptive feature branch (e.g.
  `feat/add-garch-forecast`) based off the latest `main`.
* **Follow the coding conventions** – Use Black and Ruff for
  formatting.  Run tests with `pytest -q` and ensure coverage is
  generated.
* **Write tests and documentation** – Every new feature should have
  appropriate unit and/or integration tests and documentation
  updates.  See `tests/README.md` for guidance.
* **Commit logically** – Make small, focused commits with clear
  messages.  If possible, sign your commits.

## Opening a Pull Request

1. **Push your branch** to your fork or the main repository.
2. **Open a pull request** targeting `main`.  Follow the PR template
   provided in `.github/PULL_REQUEST_TEMPLATE.md`.  Summarise your
   changes, link related issues and mention any follow‑ups required.
3. **Address feedback** – A maintainer will review your PR, leaving
   comments or requesting changes.  Respond promptly and update your
   branch as needed.  All CI checks must pass before merging.

We appreciate your contribution and will do our best to help you
navigate the process.  For urgent security issues, please refer to
`SECURITY.md` for disclosure guidelines.