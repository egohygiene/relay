# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Validate Repository Intelligence paths and safely recreate generated output."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil

PROTECTED_WRITABLE_AREAS = {".git", ".github", "actions", "schemas", "scripts", "tests"}


def canonical_relative_directory(value: str, label: str) -> Path:
    """Validate one literal repository-relative directory path."""

    relative = Path(value)
    if (
        not value
        or relative.is_absolute()
        or "\\" in value
        or relative.as_posix() != value
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ValueError(f"{label} must be a canonical repository-relative path")
    return relative


def resolve_inside_repository(repository_root: Path, relative: Path, label: str) -> Path:
    """Resolve one path while rejecting every symbolic-link component."""

    root = repository_root.resolve(strict=True)
    lexical = root / relative
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"{label} must not contain symbolic-link components")
    resolved = lexical.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} resolves outside the repository") from error
    if resolved == root:
        raise ValueError(f"{label} must not be the repository root")
    return lexical


def paths_overlap(first: Path, second: Path) -> bool:
    """Return whether two canonical relative paths are equal or nested."""

    return first == second or first in second.parents or second in first.parents


def validate_directory_layout(
    repository_root: Path,
    output_directory: str,
    work_directory: str,
    reports_directory: str,
) -> dict[str, Path]:
    """Validate generated, private, and evidence paths before any action mutation."""

    root = repository_root.resolve(strict=True)
    relative_paths = {
        "output-directory": canonical_relative_directory(
            output_directory,
            "output-directory",
        ),
        "work-directory": canonical_relative_directory(work_directory, "work-directory"),
        "reports-directory": canonical_relative_directory(
            reports_directory,
            "reports-directory",
        ),
    }
    for label in ("output-directory", "work-directory"):
        if relative_paths[label].parts[0] in PROTECTED_WRITABLE_AREAS:
            raise ValueError(f"{label} must not replace a protected repository area")
    output = relative_paths["output-directory"]
    work = relative_paths["work-directory"]
    reports = relative_paths["reports-directory"]
    if output.name != "intelligence":
        raise ValueError("output-directory must end with the intelligence subtree")
    if paths_overlap(output, work):
        raise ValueError("output-directory and work-directory must not overlap")
    if paths_overlap(output, reports):
        raise ValueError("output-directory and reports-directory must not overlap")
    site_root = output.parent
    if site_root == Path("."):
        raise ValueError(
            "output-directory must identify a subtree within a site composition root"
        )
    for label, relative in (
        ("work-directory", work),
        ("reports-directory", reports),
    ):
        if relative == site_root or site_root in relative.parents:
            raise ValueError(f"{label} must remain outside the site composition root")
    if reports == work or reports in work.parents:
        raise ValueError("work-directory must not be nested inside reports-directory")
    managed_work_paths = tuple(
        work / child for child in ("activity", "analytics", "tree", "visualization")
    )
    if any(paths_overlap(reports, managed) for managed in managed_work_paths):
        raise ValueError("reports-directory must not overlap managed work paths")
    resolved = {
        label: resolve_inside_repository(root, relative, label)
        for label, relative in relative_paths.items()
    }
    for child in ("activity", "analytics", "tree", "visualization"):
        resolve_inside_repository(
            root,
            relative_paths["work-directory"] / child,
            f"work-directory/{child}",
        )
    for producer in ("osv", "megalinter", "scorecard"):
        resolve_inside_repository(
            root,
            relative_paths["reports-directory"] / producer / "summary.json",
            f"reports-directory/{producer}/summary.json",
        )
    return resolved


def prepare_output_directory(repository_root: Path, output_directory: str) -> Path:
    """Remove stale output without following symlinks elsewhere in the repository."""

    root = repository_root.resolve(strict=True)
    relative_target = canonical_relative_directory(output_directory, "output directory")
    if relative_target.parts[0] in PROTECTED_WRITABLE_AREAS:
        raise ValueError("output directory must not replace a protected repository area")
    lexical_target = resolve_inside_repository(root, relative_target, "output directory")
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
    parser.add_argument("--work-directory")
    parser.add_argument("--reports-directory")
    parser.add_argument("--validate-layout-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Validate a layout or prepare one exact generated output directory."""

    arguments = parse_arguments()
    if arguments.validate_layout_only:
        if not arguments.work_directory or not arguments.reports_directory:
            raise SystemExit(
                "--validate-layout-only requires --work-directory and --reports-directory"
            )
        validate_directory_layout(
            arguments.repository_root,
            arguments.output_directory,
            arguments.work_directory,
            arguments.reports_directory,
        )
        print("Validated Repository Intelligence directory separation")
        return 0
    output = prepare_output_directory(
        arguments.repository_root,
        arguments.output_directory,
    )
    print(f"Prepared clean dashboard output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
