#!/usr/bin/env python3
"""Terminal interface for 0xLog."""

import argparse
import shlex
import signal
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from .core import TimeTracker
from .exceptions import AmbiguousTaskError, TimeTrackerError


console = Console()


def format_duration(seconds: float) -> str:
    """Format seconds for display in the terminal."""
    return str(timedelta(seconds=int(seconds)))


def get_current_git_branch() -> str:
    """Return the current Git branch, or an empty string outside a repository."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def task_name_with_context(tracker: TimeTracker, name_or_alias: str) -> str:
    """Add Git context in the CLI so the reusable core stays environment-agnostic."""
    task_name = tracker.resolve_task_name(name_or_alias)
    branch = get_current_git_branch()
    if branch and "[{}]".format(branch) not in task_name:
        return "{} [{}]".format(task_name, branch)
    return task_name


def print_error(error: TimeTrackerError) -> None:
    """Render domain errors here so core exceptions remain UI-independent."""
    if isinstance(error, AmbiguousTaskError):
        console.print("[red]Multiple tasks match {!r}. Please be more specific:[/red]".format(error.query))
        for task_name in error.matches:
            console.print(" - {}".format(task_name))
        return
    console.print("[red]Error:[/red] {}".format(error))


def start_task(tracker: TimeTracker, name_or_alias: str) -> None:
    """Start a task and render the result."""
    try:
        task = tracker.start_task(task_name_with_context(tracker, name_or_alias))
    except TimeTrackerError as error:
        print_error(error)
        return
    console.print("[green]Started task:[/green] {}".format(task["task"]))


def stop_task(tracker: TimeTracker, task_name: str) -> None:
    """Stop a task and render the completed record."""
    try:
        record = tracker.stop_task(task_name)
    except TimeTrackerError as error:
        print_error(error)
        return
    console.print(
        "[green]Stopped task:[/green] {} (Logged {})".format(
            record["task"], format_duration(record["duration"])
        )
    )


def add_record(
    tracker: TimeTracker,
    name_or_alias: str,
    start_value: str,
    end_value: Optional[str] = None,
    duration_value: Optional[str] = None,
) -> None:
    """Add and render a retrospective task record."""
    try:
        record = tracker.add_record(
            task_name_with_context(tracker, name_or_alias),
            start_value,
            end_value,
            duration_value,
        )
    except TimeTrackerError as error:
        print_error(error)
        return
    console.print(
        "[green]Successfully logged past task:[/green] {} ({})".format(
            record["task"], format_duration(record["duration"])
        )
    )


def stop_all(tracker: TimeTracker) -> None:
    """Stop all active tasks and render an appropriate outcome."""
    try:
        records = tracker.stop_all()
    except TimeTrackerError as error:
        print_error(error)
        return

    if not records:
        console.print("[yellow]No ongoing tasks to stop.[/yellow]")
        return
    for record in records:
        console.print(
            "[green]Stopped task:[/green] {} (Logged {})".format(
                record["task"], format_duration(record["duration"])
            )
        )


def add_alias(tracker: TimeTracker, alias: str, task_name: str) -> None:
    """Create or reassign an alias and render its mapping."""
    try:
        mapping = tracker.add_alias(alias, task_name)
    except TimeTrackerError as error:
        print_error(error)
        return
    console.print("[green]Alias saved:[/green] {alias} -> {task}".format(**mapping))


def remove_alias(tracker: TimeTracker, alias: str) -> None:
    """Delete and render an alias mapping."""
    try:
        mapping = tracker.remove_alias(alias)
    except TimeTrackerError as error:
        print_error(error)
        return
    console.print("[green]Alias deleted:[/green] {alias} -> {task}".format(**mapping))


def show_aliases(tracker: TimeTracker) -> None:
    """Render all configured aliases and their task UUIDs."""
    aliases = tracker.get_aliases()
    if not aliases:
        console.print("[yellow]No aliases defined.[/yellow]")
        return
    table = Table(title="Task Aliases")
    table.add_column("Alias", style="cyan")
    table.add_column("Task")
    table.add_column("Task ID", style="dim")
    for mapping in aliases:
        table.add_row(mapping["alias"], mapping["task"], mapping["task_id"])
    console.print(table)


def show_status(tracker: TimeTracker) -> None:
    """Render active tasks and today's accumulated time."""
    ongoing_tasks = tracker.get_ongoing()
    if ongoing_tasks:
        table = Table(title="Ongoing Tasks")
        table.add_column("Task", style="cyan")
        table.add_column("Elapsed Time", style="magenta")
        for task in ongoing_tasks:
            table.add_row(task["task"], format_duration(task["elapsed"]))
        console.print(table)
    else:
        console.print("[yellow]No ongoing tasks.[/yellow]")
    console.print("\n[bold]Total logged today:[/bold] {}".format(format_duration(tracker.get_today_total())))


def show_recent(tracker: TimeTracker, limit: int = 10) -> None:
    """Render recently completed unique task names."""
    recent_tasks = tracker.get_recent_tasks(limit)
    if not recent_tasks:
        console.print("[yellow]No recent tasks found.[/yellow]")
        return
    console.print("[bold]Recent Tasks:[/bold]")
    for task_name in recent_tasks:
        console.print("- {}".format(task_name))


def show_report(tracker: TimeTracker) -> None:
    """Render today's completed task totals."""
    report = tracker.get_daily_report()
    if not report:
        console.print("[yellow]No tasks completed today yet.[/yellow]")
        return

    table = Table(title="Daily Report: {}".format(datetime.now().strftime("%Y-%m-%d")))
    table.add_column("Task", style="cyan")
    table.add_column("Total Time", justify="right", style="green")
    for task_name, duration in report.items():
        table.add_row(task_name, format_duration(duration))
    console.print(table)
    console.print("[bold]Total for today:[/bold] {}".format(format_duration(sum(report.values()))))


def run_tui(tracker: TimeTracker) -> None:
    """Run the interactive terminal dashboard."""
    def generate_dashboard() -> Panel:
        table = Table(box=None, expand=True)
        table.add_column("Ongoing Task", style="cyan")
        table.add_column("Time", justify="right", style="magenta")
        for task in tracker.get_ongoing():
            table.add_row(task["task"], format_duration(task["elapsed"]))
        return Panel(
            table,
            title="[bold]0xLog TUI[/bold]",
            subtitle="Commands: start, stop, add, alias, stopall, report, quit",
            border_style="green",
        )

    def handle_shutdown(signum: int, frame: Any) -> None:
        stop_all(tracker)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, handle_shutdown)

    console.clear()
    with Live(generate_dashboard(), refresh_per_second=1, screen=False) as live:
        while True:
            try:
                command_input = input("\n0xLog> ").strip()
                if not command_input:
                    continue
                if not handle_tui_command(tracker, command_input):
                    break
                live.update(generate_dashboard())
            except EOFError:
                break


def handle_tui_command(tracker: TimeTracker, command_input: str) -> bool:
    """Execute one TUI command and return whether the session should continue."""
    try:
        tokens = shlex.split(command_input)
    except ValueError as error:
        console.print("[red]Input error:[/red] {}".format(error))
        return True
    if not tokens:
        return True

    command, command_args = tokens[0].lower(), tokens[1:]
    if command in ("quit", "exit", "q"):
        return False
    if command == "start" and command_args:
        start_task(tracker, " ".join(command_args))
    elif command == "stop" and command_args:
        stop_task(tracker, " ".join(command_args))
    elif command == "stopall":
        stop_all(tracker)
    elif command == "report":
        show_report(tracker)
    elif command == "add":
        handle_tui_add(tracker, command_args)
    elif command == "alias":
        handle_tui_alias(tracker, command_args)
    else:
        console.print("[red]Unknown command.[/red]")
    return True


def handle_tui_add(tracker: TimeTracker, tokens: Iterable[str]) -> None:
    """Parse and execute the TUI's compact ``add`` command."""
    parser = argparse.ArgumentParser(prog="add", add_help=False)
    parser.add_argument("task")
    parser.add_argument("--start", "-s", required=True)
    timing_group = parser.add_mutually_exclusive_group(required=True)
    timing_group.add_argument("--end", "-e")
    timing_group.add_argument("--duration", "-d")
    try:
        arguments = parser.parse_args(list(tokens))
    except SystemExit:
        console.print("[red]Invalid add command. Use: add TASK -s TIME (-e TIME | -d DURATION)[/red]")
        return
    add_record(tracker, arguments.task, arguments.start, arguments.end, arguments.duration)


def handle_tui_alias(tracker: TimeTracker, tokens: Iterable[str]) -> None:
    """Handle ``alias``, ``alias delete NAME``, and ``alias NAME TASK`` in the TUI."""
    arguments = list(tokens)
    if not arguments:
        show_aliases(tracker)
    elif arguments[0] == "delete" and len(arguments) == 2:
        remove_alias(tracker, arguments[1])
    elif len(arguments) == 2:
        add_alias(tracker, arguments[0], arguments[1])
    else:
        console.print("[red]Usage: alias [delete ALIAS | ALIAS TASK][/red]")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description="0xLog: A lightweight CLI time tracker.")
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="Start a task")
    start_parser.add_argument("task", help="Task name or alias")

    stop_parser = subparsers.add_parser("stop", help="Stop a task")
    stop_parser.add_argument("task", help="Task name")

    add_parser = subparsers.add_parser("add", help="Manually add a completed task")
    add_parser.add_argument("task", help="Task name or alias")
    add_parser.add_argument("--start", "-s", required=True, help="Start time (for example, '10 am')")
    timing_group = add_parser.add_mutually_exclusive_group(required=True)
    timing_group.add_argument("--end", "-e", help="End time (for example, '10:49')")
    timing_group.add_argument("--duration", "-d", help="Duration (for example, '20m')")

    subparsers.add_parser("stopall", help="Stop all ongoing tasks")
    subparsers.add_parser("status", help="Show ongoing tasks and today's total")
    subparsers.add_parser("recent", help="Show recent task titles")
    subparsers.add_parser("report", help="Show daily report")

    alias_parser = subparsers.add_parser("alias", help="List, create, reassign, or delete task aliases")
    alias_parser.add_argument("alias", nargs="?", help="Alias name")
    alias_parser.add_argument("task", nargs="?", help="Task name for the alias")
    alias_parser.add_argument("--delete", action="store_true", help="Delete the specified alias")
    return parser


def main() -> None:
    """Run the 0xLog command-line application."""
    try:
        tracker = TimeTracker()
    except TimeTrackerError as error:
        print_error(error)
        return

    if len(sys.argv) == 1:
        run_tui(tracker)
        return
    if len(sys.argv) == 2 and sys.argv[1] not in {
        "status", "stopall", "recent", "report", "alias", "add", "-h", "--help"
    }:
        start_task(tracker, sys.argv[1])
        return

    arguments = build_parser().parse_args()
    command_handlers = {
        "start": lambda: start_task(tracker, arguments.task),
        "stop": lambda: stop_task(tracker, arguments.task),
        "add": lambda: add_record(tracker, arguments.task, arguments.start, arguments.end, arguments.duration),
        "stopall": lambda: stop_all(tracker),
        "status": lambda: show_status(tracker),
        "recent": lambda: show_recent(tracker),
        "report": lambda: show_report(tracker),
        "alias": lambda: handle_alias_command(tracker, arguments),
    }
    handler = command_handlers.get(arguments.command)
    if handler:
        handler()


def handle_alias_command(tracker: TimeTracker, arguments: argparse.Namespace) -> None:
    """Dispatch the CLI alias actions while preserving the original set syntax."""
    if arguments.delete:
        if arguments.alias and arguments.task is None:
            remove_alias(tracker, arguments.alias)
        else:
            console.print("[red]Usage: 0xlog alias --delete ALIAS[/red]")
    elif arguments.alias is None:
        show_aliases(tracker)
    elif arguments.task is None:
        console.print("[red]Usage: 0xlog alias ALIAS TASK[/red]")
    else:
        add_alias(tracker, arguments.alias, arguments.task)


if __name__ == "__main__":
    main()
