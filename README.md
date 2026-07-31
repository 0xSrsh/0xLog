# 0xLog: Terminal Time Tracker

[![PyPI](https://img.shields.io/pypi/v/0xlog-cli.svg)](https://pypi.org/project/0xlog-cli/)
[![Python](https://img.shields.io/pypi/pyversions/0xlog-cli.svg)](https://pypi.org/project/0xlog-cli/)
[![License: MIT](https://img.shields.io/pypi/l/0xlog-cli.svg)](https://github.com/0xSrsh/0xLog/blob/main/LICENSE)
[![CI](https://github.com/0xSrsh/0xLog/actions/workflows/ci.yml/badge.svg)](https://github.com/0xSrsh/0xLog/actions/workflows/ci.yml)

`0xLog` is a lightweight, terminal-based time tracking tool designed to stay out of your way. It operates seamlessly alongside your development workflow, featuring an interactive TUI, Git branch awareness, and file-based syncing.

## Installation

The package is published on PyPI as [`0xlog-cli`](https://pypi.org/project/0xlog-cli/).

`0xLog` is a command-line application, so the recommended way to install it is with a tool that gives it an isolated environment and still puts `0xlog` on your `PATH`:

```bash
pipx install 0xlog-cli
# Or, if you use uv:
uv tool install 0xlog-cli
```

This also avoids the `externally-managed-environment` error (PEP 668) that recent Debian, Ubuntu, and Fedora releases raise when you `pip install` into the system Python.

Inside a virtual environment, plain pip works as well:

```bash
python -m pip install 0xlog-cli
```

To upgrade later:

```bash
pipx upgrade 0xlog-cli
```

For local development, clone the repository and install it in editable mode:

```bash
python -m pip install -e .
```

---

## Basic Usage

### Starting a Task

You can start a task using the `start` command, or skip the command entirely for even faster logging.

```bash
0xlog start "Writing tests for xbut"
# Or the shorthand version:
0xlog "Writing tests for xbut"

```

### Stopping a Task

Stop a specific task by name, or stop everything at once (useful before shutting down).

```bash
0xlog stop "Writing tests for xbut"
0xlog stopall

```

---

## ⚡ Git Workflow Integration

`0xLog` is context-aware. If you start a task while inside a Git repository, it automatically detects your current branch and appends it to your task name.

**Example:**
If you are inside the `Narsil/backend` directory on the `feature/jwt-auth` branch:

```bash
0xlog start "Updating middleware"

```

*What gets logged:* `Updating middleware [feature/jwt-auth]`

### Smart Task Stopping

Because typing out the full branch name every time you stop a task is tedious, the `stop` command uses **smart partial matching**. You only need to type enough of the task name to uniquely identify it.

```bash
# This will successfully find and stop "Updating middleware [feature/jwt-auth]"
0xlog stop "Updating middleware"

```

*(If multiple running tasks match your input, `0xLog` will list them and ask you to be more specific.)*

---

## Task Aliases

If you find yourself typing the same long task names repeatedly, create an alias to speed things up.

```bash
# Create the alias
0xlog alias code-review "Reviewing pull requests"

# Use the alias
0xlog start code-review

```

List all configured aliases and the UUID of the task each one points to:

```bash
0xlog alias
```

Reusing an alias name reassigns it to the supplied task:

```bash
0xlog alias code-review "Review customer feedback"
```

Delete an alias when it is no longer useful:

```bash
0xlog alias --delete code-review
```

Aliases are references to tasks, not separate tasks. Starting or adding time with either a task name or one of its aliases keeps the same task UUID.

---

## Adding retrospective tasks

Use start time and duration to add a task:

```bash
0xlog add "Reviewed PRs" --start "10 am" --duration "20m"
# Shorthand:
0xlog add "Reviewed PRs" -s "10 am" -d "20m"
```

Or use start time and end time:
```bash
0xlog add "Client Call" --start "10 am" --end "10:49"
# Shorthand:
0xlog add "Client Call" -s "10:00" -e "10:49"
```
The time parser is highly flexible and will accept formats like 10am, 10 am, 10:00, 14:30, 02:30 pm, etc. The duration parser understands strings like 20m, 20 minutes, 1h 30m, and 1.5h.

---

## Monitoring & Reports

Keep track of your active time and daily productivity without leaving the terminal.

* **`0xlog status`**
Displays all currently running tasks and your total logged time for the current day.
* **`0xlog recent`**
Prints a list of your 10 most recently tracked tasks so you can easily copy/paste them to resume work.
* **`0xlog report`**
Generates a summarized daily timesheet, aggregating all the time spent on each task today.

---

## Interactive TUI Mode

If you prefer a live dashboard that you can keep open in a dedicated terminal pane, simply run the command with no arguments:

```bash
0xlog

```

This launches a live-updating view of your ongoing tasks.

* The dashboard updates every second.
* You can type commands directly into the prompt at the bottom (e.g., `start "Deploying xbut"`, `stopall`, `report`).
* Type `quit` or `q` to exit.
* **Graceful Shutdown:** If you leave the TUI running and shut down your computer, the script intercepts the system termination signal and automatically runs `stopall` to ensure your timers are accurately halted.

---

## Data & Syncing

All your data is stored in a single, human-readable JSON file located at:
`~/.0xlog.json`

Each task has a stable UUID. 0xLog stores that ID with every historical and ongoing record, so repeated use of an existing task name or alias is always associated with the same task. Existing data files are migrated automatically the next time they are loaded.

**To sync your timers across multiple machines:**
Simply place this file in a synced folder (like Dropbox, Google Drive, or a private Git repo) and create a symlink to your home directory on each machine:

**Linux/macOS:**

```bash
ln -s /path/to/synced/folder/.0xlog.json ~/.0xlog.json

```

**Windows (Run as Administrator):**

```cmd
mklink %USERPROFILE%\.0xlog.json "C:\path\to\synced\folder\.0xlog.json"

```

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](https://github.com/0xSrsh/0xLog/blob/main/CONTRIBUTING.md) and [CONVENTIONS.md](https://github.com/0xSrsh/0xLog/blob/main/CONVENTIONS.md) before opening a pull request.

## Security

Please follow the private reporting process in [SECURITY.md](https://github.com/0xSrsh/0xLog/blob/main/SECURITY.md) for suspected vulnerabilities.

## Code of Conduct

Participation in this project is governed by the [Code of Conduct](https://github.com/0xSrsh/0xLog/blob/main/CODE_OF_CONDUCT.md).

## License

0xLog is released under the [MIT License](https://github.com/0xSrsh/0xLog/blob/main/LICENSE).
