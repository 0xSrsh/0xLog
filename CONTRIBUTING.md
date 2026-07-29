# Contributing to 0xLog

Thank you for contributing. Please start by reading [CONVENTIONS.md](CONVENTIONS.md); it defines the project's architecture, typing, portability, and commit-message rules.

## Development setup

1. Fork the repository and create a branch from `main` using `feature/<name>` or `bugfix/<name>`.
2. Create and activate a virtual environment.
3. Install the project in editable mode:

   ```bash
   python -m pip install -e .
   ```

4. Run the test suite before opening a pull request:

   ```bash
   python -m unittest discover -s tests -v
   ```

## Pull requests

- Keep each pull request focused and include tests for behaviour changes.
- Keep domain logic in `src/oxlog/core.py` independent of terminal presentation.
- Use Conventional Commit messages, for example: `feat(core): add task export`.
- Update documentation when commands, configuration, or user-facing behaviour changes.
