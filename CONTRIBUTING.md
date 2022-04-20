# Contributing

## Helpful Commands

```sh
poetry run flake8 .  # Run linter
poetry run black .  # Run formatter
poetry run isort .  # Run import formatter
poetry run mypy -p censys.cloud_connectors  # Run type checker
pre-commit run --all-files  # Run pre-commit hooks (lint, type check, etc.)
poetry run pytest  # Run tests
poetry run pytest --cov --cov-report html  # Run tests with coverage report
```

## Committing

This repository currently uses the `rebase` workflow for Merge Requests. This means
that merge messages are _not_ created when requests are merged.

Every commit in the merge request **must** be treated as a stand-alone, autonomous
change. If this is not the case, consider using the squash feature before
merging.

### Commit Messages

Search is now using
[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
to structure its commit messages, in the event we want to automatically
generate changelogs in the future.

Commit messages should always be written as if to complete the follow sentence:

> If applied, this commit will... < Insert Commit Message Here >

#### Type

- `fix`: A bug fix.
- `feat`: A new feature or component.
- `improve`: A code code that is neither a new feature nor a bug fix but improves
  functionality.
- `refactor`: A code change that is niether a new feature nor
  a bug fix but does not change the current functionality of the code.
- `chore`: A repeatable action such as static code generation.
- `docs`: Changes to documentation.
- `style`: Changes that do not change the meaning of the code such as black or isort.
- `test`: Changes to tests.

> type: \<commit message>

Finally, there is a `build` type which has its own set of scopes. See below.

#### Scope

The scope should be the name of an area of Search. While this is certainly not
an exhaustive list, please consider using an existing scope before adding a
new one.

Scopes are not required, but they help keep commits succinct and autonomous.

- `cc`: Changes to the Cloud Connectors.
  - `cc-azure`: Changes to the Azure Cloud Connectors.
  - `cc-gcp`: Changes to the GCP Cloud Connectors.
- `cli`: Changes to the CLI.
  - `cli-config`: Changes to the CLI config.
  - `cli-scan`: Changes to the CLI scan.
- `docs`: Changes to the documentation.

> type(scope): \<commit message>

#### Build Type and Scopes

The `build` type is used to represent changes to the build system or repository itself.
The following scopes are recommended for use with the build commit type:

- `ci`
- `chart`
- `container`
- `deps`

## VSCode Config

Please note that there is a sample vscode `settings.json` and `extensions.json`
files in the `.vscode` directory.

Features inlcuded in the extensions:

- Use pytest as a test runner
- `.toml`, `.yaml`, `.env` file extension support
- View all todos
- Automatically generate docsstrings
- Spell check
- Docker and Kubernetes support

## FAQs

### Rebasing merge conflicts when there was a new package added to poetry

Incase of `poetry.lock` merge conflicts

1. Accept all incoming changes (to maintain toml validity)

2. Rewrite the lockfile from `pyproject.toml`

```sh
poetry lock --no-update
```
