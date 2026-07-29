# 0xLog Project Conventions

To ensure the codebase remains maintainable, cross-platform, and ready for future expansion into web and mobile clients, all contributors must follow these conventions.

## 1. Commit Messages
We strictly follow [Conventional Commits](https://www.conventionalcommits.org/). This allows us to auto-generate changelogs and trace history easily.

**Format:** `type(scope): description`

**Types:**
* `feat`: A new feature (e.g., `feat(core): add time parsing for manual records`)
* `fix`: A bug fix (e.g., `fix(cli): resolve crash on exit`)
* `refactor`: Code changes that neither fix a bug nor add a feature
* `docs`: Documentation updates (README, CONVENTIONS)
* `chore`: Maintenance tasks (updates to dependencies, `.gitignore`)

## 2. Architecture & Separation of Concerns
This project is currently a CLI, but the roadmap includes a cloud backend (Django REST Framework) and a mobile companion app (Flutter). 

To future-proof the codebase:
* **`core.py` (Domain Logic):** Must remain 100% independent of the terminal. It should never use `print()`, `sys.exit()`, or `rich`. It manages data, calculations, and state. It should raise custom Python exceptions when things go wrong.
* **`cli.py` (Presentation Layer):** Handles all terminal interactions, argument parsing, and `rich` UI elements. It catches exceptions raised by `core.py` and displays them as formatted terminal messages.

## 3. Code Style & Typing
* **Strict Typing:** All function signatures must include Python type hints. This project is optimized for strict type-checking in Pylance.
  * *Good:* `def start_task(self, name_or_alias: str) -> None:`
  * *Bad:* `def start_task(self, name_or_alias):`
* **Docstrings:** Use docstrings for classes and complex methods to explain *why* something is done, not just *what* it does.

## 4. Cross-Platform Compatibility
0xLog must run flawlessly on both Windows and Linux environments.
* Never hardcode file paths using forward or backward slashes. Use `os.path.join()` or `pathlib`.
* Always use `os.path.expanduser("~")` to resolve the user's home directory across different operating systems.
* Ensure OS-specific signals (like `SIGTERM` vs `SIGINT` handling) are wrapped in platform checks (e.g., `sys.platform != "win32"`).

## 5. Branching Strategy
* **`main`**: The stable branch. Direct commits are restricted.
* **`feature/<name>`**: For new features (e.g., `feature/git-detection`).
* **`bugfix/<name>`**: For bug fixes (e.g., `bugfix/duration-parsing`).
* All changes must be submitted via Pull Requests and reviewed before merging.