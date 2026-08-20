# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Safely recreate the exact public dashboard output directory."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil


def prepare_output_directory(repository_root: Path, output_directory: str) -> Path:
    """Remove stale output without following symlinks beyond the repository."""

    root = repository_root.resolve(strict=True)
    relative_target = Path(output_directory)
    if relative_target.is_absolute() or any(
        part in {"", ".", ".."} for part in relative_target.parts
    ):
        raise ValueError("output directory must be a canonical repository-relative path")
    if relative_target.parts[0] in {".git", ".github", "actions", "schemas", "scripts", "tests"}:
        raise ValueError("output directory must not replace a protected repository area")
    lexical_target = root / relative_target
    resolved_target = lexical_target.resolve(strict=False)
    try:
        resolved_target.relative_to(root)
    except ValueError as error:
        raise ValueError("output directory resolves outside the repository") from error
    if resolved_target == root:
        raise ValueError("output directory must not be the repository root")
    if lexical_target.is_symlink():
        raise ValueError("output directory must not be a symbolic link")
    if lexical_target.exists():
        if not lexical_target.is_dir():
            raise ValueError("output directory path exists and is not a directory")
        shutil.rmtree(lexical_target)
    lexical_target.mkdir(parents=True, exist_ok=False)
    return lexical_target


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-directory", required=True)
    return parser.parse_args()


def main() -> int:
    """Prepare one output directory and report its resolved location."""

    arguments = parse_arguments()
    output = prepare_output_directory(
        arguments.repository_root,
        arguments.output_directory,
    )
    print(f"Prepared clean dashboard output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
