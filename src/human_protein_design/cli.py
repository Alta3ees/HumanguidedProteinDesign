"""Reusable terminal interaction helpers for Human-Guided Protein Design.

The CLI layer deliberately owns terminal-specific browsing and validation so
scientific/archive code stays independent from user-interface details. A future
web frontend can replace these interactions without changing the archive model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence, TypeVar


T = TypeVar("T")


def ask_text(prompt: str, *, required: bool = True, default: str | None = None) -> str:
    """Ask for text, repeating until a required value is supplied."""
    while True:
        suffix = f" [{default}]" if default is not None else ""
        value = input(f"{prompt}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return ""
        print("Input is required.")


def ask_choice(prompt: str, options: dict[str, T], *, default: str | None = None) -> T:
    """Ask for one keyed option until a valid choice is entered."""
    while True:
        suffix = f" [{default}]" if default is not None else ""
        choice = input(f"{prompt}{suffix}: ").strip() or (default or "")
        if choice in options:
            return options[choice]
        print("Choose one of: " + ", ".join(options))


def ask_yes_no(prompt: str, *, default: bool | None = None) -> bool:
    """Ask a yes/no question."""
    default_key = "y" if default is True else "n" if default is False else None
    return ask_choice(prompt, {"y": True, "n": False}, default=default_key)


def ask_int(
    prompt: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
    allow_quit: bool = False,
) -> int | None:
    """Ask for an integer with optional bounds; return None for q when enabled."""
    while True:
        raw = input(f"{prompt}: ").strip()
        if allow_quit and raw.lower() == "q":
            return None
        try:
            value = int(raw)
        except ValueError:
            print("Enter a valid integer" + (" or 'q'." if allow_quit else "."))
            continue
        if minimum is not None and value < minimum:
            print(f"Value must be at least {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Value must be at most {maximum}.")
            continue
        return value


def ask_float(
    prompt: str,
    *,
    required: bool = False,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    """Ask for a floating-point value with optional bounds."""
    while True:
        raw = input(f"{prompt}: ").strip()
        if not raw and not required:
            return None
        try:
            value = float(raw)
        except ValueError:
            print("Enter a valid number.")
            continue
        if minimum is not None and value < minimum:
            print(f"Value must be at least {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Value must be at most {maximum}.")
            continue
        return value


def choose_item(
    items: Sequence[T],
    prompt: str,
    *,
    label: Callable[[T], str] = str,
    allow_none: bool = False,
    none_label: str = "None",
) -> T | None:
    """Choose an item from a numbered terminal list."""
    if not items:
        if allow_none:
            return None
        raise ValueError("No items are available for selection.")

    while True:
        print()
        if allow_none:
            print(f"  0. {none_label}")
        for index, item in enumerate(items, start=1):
            print(f"  {index}. {label(item)}")

        raw = input(f"{prompt}: ").strip()
        try:
            index = int(raw)
        except ValueError:
            print("Enter a valid number.")
            continue

        if allow_none and index == 0:
            return None
        if 1 <= index <= len(items):
            return items[index - 1]
        print("Selection outside range.")


def choose_directory(
    root: Path,
    prompt: str,
    *,
    require_file: str | None = None,
    allow_manual: bool = True,
) -> Path:
    """Browse directories under root, with an optional manual-path fallback."""
    root = root.expanduser()

    while True:
        directories = []
        if root.is_dir():
            directories = sorted(
                path for path in root.iterdir()
                if path.is_dir() and (require_file is None or (path / require_file).is_file())
            )

        print(f"\n{prompt}")
        for index, path in enumerate(directories, start=1):
            print(f"  {index}. {path.name}")

        next_index = len(directories) + 1
        if allow_manual:
            print(f"  {next_index}. Enter path manually")
            cancel_index = next_index + 1
        else:
            cancel_index = next_index
        print(f"  {cancel_index}. Cancel")

        raw = input("Choose: ").strip()
        try:
            choice = int(raw)
        except ValueError:
            print("Enter a valid number.")
            continue

        if 1 <= choice <= len(directories):
            return directories[choice - 1]

        if allow_manual and choice == next_index:
            manual = Path(input("Path: ").strip()).expanduser()
            if not manual.is_dir():
                print(f"Directory not found: {manual}")
                continue
            if require_file is not None and not (manual / require_file).is_file():
                print(f"Required file not found: {manual / require_file}")
                continue
            return manual

        if choice == cancel_index:
            raise SystemExit("Cancelled.")

        print("Selection outside range.")


def choose_project(projects_root: Path = Path("data/projects")) -> Path:
    """Choose an existing HGD project directory."""
    return choose_directory(
        projects_root,
        "Available projects",
        require_file="design_archive.json",
    )


def choose_file(
    root: Path,
    prompt: str,
    *,
    allowed_suffixes: set[str] | None = None,
    recursive: bool = False,
    required: bool = True,
) -> Path | None:
    """Browse files beneath root, with manual-path and cancel options."""
    root = root.expanduser()
    suffixes = {suffix.lower() for suffix in allowed_suffixes} if allowed_suffixes else None

    def valid(path: Path) -> bool:
        return path.is_file() and (suffixes is None or path.suffix.lower() in suffixes)

    while True:
        candidates: list[Path] = []
        if root.is_dir():
            iterator = root.rglob("*") if recursive else root.iterdir()
            candidates = sorted(path for path in iterator if valid(path))

        print(f"\n{prompt}")
        if not candidates:
            print(f"  (no matching files in {root})")
        for index, path in enumerate(candidates, start=1):
            try:
                display = path.relative_to(root)
            except ValueError:
                display = path
            print(f"  {index}. {display}")

        manual_index = len(candidates) + 1
        print(f"  {manual_index}. Enter path manually")
        none_index = manual_index + 1 if not required else None
        if none_index is not None:
            print(f"  {none_index}. None / skip")
        cancel_index = (none_index + 1) if none_index is not None else (manual_index + 1)
        print(f"  {cancel_index}. Cancel")

        raw = input("Choose: ").strip()
        try:
            choice = int(raw)
        except ValueError:
            print("Enter a valid number.")
            continue

        if 1 <= choice <= len(candidates):
            return candidates[choice - 1]

        if choice == manual_index:
            manual = Path(input("Path: ").strip()).expanduser()
            if not valid(manual):
                print("File not found or unsupported file type.")
                continue
            return manual

        if none_index is not None and choice == none_index:
            return None
        if choice == cancel_index:
            raise SystemExit("Cancelled.")

        print("Selection outside range.")


def choose_files(
    root: Path,
    prompt: str,
    *,
    allowed_suffixes: set[str] | None = None,
) -> list[Path]:
    """Repeatedly browse for files until the user chooses to stop."""
    files: list[Path] = []
    while True:
        path = choose_file(
            root,
            prompt,
            allowed_suffixes=allowed_suffixes,
            recursive=True,
            required=False,
        )
        if path is None:
            return files
        if path not in files:
            files.append(path)
        if not ask_yes_no("Attach another file?", default=False):
            return files
