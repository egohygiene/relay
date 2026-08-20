# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any
import xml.etree.ElementTree as ET

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

DEFAULT_EXCLUDED_PATHS = [
    ".git",
    ".staging",
    ".cache",
    ".venv",
    ".reports",
    ".site",
    "docs/generated",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "coverage",
    "__pycache__",
]

TREE_SCHEMA = "egohygiene.repository-tree/v1"
TREE_SCHEMA_VERSION = 1

Node = dict[str, Any]
GitEntry = tuple[str, str]


def positive_integer(raw_value: str) -> int:
    value = int(raw_value)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate commit-scoped repository intelligence tree artifacts."
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--max-depth", type=positive_integer, default=10)
    parser.add_argument(
        "--excluded-paths",
        default=",".join(DEFAULT_EXCLUDED_PATHS),
        help="Comma-separated repository-relative paths to exclude.",
    )
    return parser.parse_args()


def normalize_excluded_paths(raw_paths: str) -> list[str]:
    excluded: list[str] = []

    for raw_path in raw_paths.split(","):
        candidate = raw_path.strip().strip("/")

        if candidate:
            excluded.append(candidate)

    return excluded


def is_excluded_path(relative_path: str, excluded_paths: Iterable[str]) -> bool:
    parts = Path(relative_path).parts

    for excluded_path in excluded_paths:
        if "/" not in excluded_path and excluded_path in parts:
            return True
        if relative_path == excluded_path or relative_path.startswith(f"{excluded_path}/"):
            return True

    return False


def run_git(repo_root: Path, arguments: Sequence[str]) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def resolve_revision(repo_root: Path, revision: str) -> str:
    return (
        run_git(repo_root, ["rev-parse", "--verify", f"{revision}^{{commit}}"])
        .decode("utf-8")
        .strip()
    )


def source_committed_at(repo_root: Path, revision: str) -> str:
    return (
        run_git(repo_root, ["show", "--no-patch", "--format=%cI", revision]).decode("utf-8").strip()
    )


def list_git_entries(repo_root: Path, revision: str) -> list[GitEntry]:
    output = run_git(repo_root, ["ls-tree", "-r", "-z", "--full-tree", revision])
    entries: list[GitEntry] = []

    for raw_record in output.split(b"\0"):
        if not raw_record:
            continue
        metadata, raw_path = raw_record.split(b"\t", maxsplit=1)
        mode = metadata.split(b" ", maxsplit=1)[0].decode("ascii")
        entries.append((raw_path.decode("utf-8", errors="surrogateescape"), mode))

    return entries


def entry_type(mode: str) -> str:
    if mode == "120000":
        return "symlink"
    if mode == "160000":
        return "submodule"
    return "file"


def new_directory(name: str, path: str) -> Node:
    return {
        "name": name,
        "path": path,
        "type": "directory",
        "children": [],
    }


def child_by_name(node: Node, name: str) -> Node | None:
    return next((child for child in node["children"] if child["name"] == name), None)


def add_entry(root: Node, relative_path: str, mode: str, max_depth: int) -> None:
    parts = Path(relative_path).parts
    current = root

    for index, part in enumerate(parts, start=1):
        if index > max_depth:
            current["truncated"] = True
            return

        path = Path(*parts[:index]).as_posix()
        is_leaf = index == len(parts)
        existing = child_by_name(current, part)

        if existing is not None:
            current = existing
            continue

        child = (
            {"name": part, "path": path, "type": entry_type(mode)}
            if is_leaf
            else new_directory(part, path)
        )
        current["children"].append(child)
        current = child


def sort_and_annotate(node: Node) -> dict[str, int]:
    if node["type"] != "directory":
        return {
            "directories": 0,
            "files": int(node["type"] == "file"),
            "symlinks": int(node["type"] == "symlink"),
            "submodules": int(node["type"] == "submodule"),
        }

    node["children"].sort(
        key=lambda child: (
            child["type"] != "directory",
            child["name"].casefold(),
            child["name"],
        )
    )
    counts = {"directories": 0, "files": 0, "symlinks": 0, "submodules": 0}

    for child in node["children"]:
        if child["type"] == "directory":
            counts["directories"] += 1
        child_counts = sort_and_annotate(child)
        for key, value in child_counts.items():
            counts[key] += value

    node["descendants"] = counts
    return counts


def build_tree(
    repository_name: str,
    entries: Iterable[GitEntry],
    excluded_paths: Iterable[str],
    max_depth: int,
) -> Node:
    root = new_directory(repository_name, ".")

    for relative_path, mode in entries:
        if is_excluded_path(relative_path, excluded_paths):
            continue
        add_entry(root, relative_path, mode, max_depth)

    sort_and_annotate(root)
    return root


def node_label(node: Node) -> str:
    suffix = "/" if node["type"] == "directory" else ""
    return f"{node['name']}{suffix}"


def render_ascii_tree(node: Node) -> str:
    lines = [node_label(node)]

    def walk(children: list[Node], prefix: str) -> None:
        for index, child in enumerate(children):
            is_last = index == len(children) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{node_label(child)}")

            if child.get("type") == "directory":
                nested_prefix = f"{prefix}{'    ' if is_last else '│   '}"
                nested_children = list(child.get("children", []))

                if child.get("truncated"):
                    lines.append(f"{nested_prefix}└── …")
                    continue

                walk(nested_children, nested_prefix)

    walk(list(node.get("children", [])), "")
    return "\n".join(lines) + "\n"


def append_xml(parent: ET.Element, node: Node) -> None:
    element_name = "directory" if node["type"] == "directory" else node["type"]
    element = ET.SubElement(
        parent,
        element_name,
        {"name": str(node["name"]), "path": str(node["path"])},
    )

    if node.get("truncated"):
        element.set("truncated", "true")

    for child in list(node.get("children", [])):
        append_xml(element, child)


def render_xml(tree: Node) -> str:
    root = ET.Element(
        "repository",
        {"name": str(tree["name"]), "path": str(tree["path"])},
    )

    for child in list(tree.get("children", [])):
        append_xml(root, child)

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def render_html(ascii_tree: str, repository_name: str) -> str:
    escaped_tree = html.escape(ascii_tree)
    escaped_name = html.escape(repository_name)
    return f"""<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{escaped_name} Repository Structure</title>
    <style>
      body {{
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", \"Courier New\", monospace;
        margin: 2rem;
        line-height: 1.5;
      }}

      pre {{
        overflow-x: auto;
        white-space: pre;
      }}
    </style>
  </head>
  <body>
    <h1>Repository Structure</h1>
    <pre>{escaped_tree}</pre>
  </body>
</html>
"""


def render_markdown(ascii_tree: str) -> str:
    return "# Repository Structure\n\n```text\n" + ascii_tree + "```\n"


def render_svg(tree: Node) -> str:
    top_level_children = list(tree.get("children", []))
    preview_items = [node_label(child) for child in top_level_children[:6]]
    preview_text = " • ".join(preview_items) if preview_items else "Repository is empty."
    width = 960
    height = 220
    escaped_preview = html.escape(preview_text)
    escaped_name = html.escape(str(tree["name"]))
    escaped_count = html.escape(str(len(top_level_children)))

    return f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\" role=\"img\" aria-labelledby=\"title desc\">
  <title id=\"title\">{escaped_name} repository visualization</title>
  <desc id=\"desc\">Deterministic repository visualization generated from the top-level repository tree.</desc>
  <rect width=\"{width}\" height=\"{height}\" rx=\"16\" ry=\"16\" fill=\"#0f172a\" />
  <text x=\"32\" y=\"64\" fill=\"#e2e8f0\" font-family=\"Arial, sans-serif\" font-size=\"30\" font-weight=\"700\">{escaped_name}</text>
  <text x=\"32\" y=\"104\" fill=\"#94a3b8\" font-family=\"Arial, sans-serif\" font-size=\"20\">Top-level entries: {escaped_count}</text>
  <text x=\"32\" y=\"148\" fill=\"#cbd5e1\" font-family=\"Arial, sans-serif\" font-size=\"18\">{escaped_preview}</text>
  <text x=\"32\" y=\"188\" fill=\"#64748b\" font-family=\"Arial, sans-serif\" font-size=\"16\">Generated locally without a third-party rendering service.</text>
</svg>
"""


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def tree_contract(tree: Node, revision: str, ref: str, committed_at: str) -> Node:
    return {
        "schema": TREE_SCHEMA,
        "schema_version": TREE_SCHEMA_VERSION,
        "source": {
            "revision": revision,
            "ref": ref,
            "committed_at": committed_at,
        },
        "tree": tree,
    }


def write_outputs(
    output_root: Path,
    tree: Node,
    revision: str,
    ref: str,
    committed_at: str,
) -> None:
    tree_output_dir = output_root / "tree"
    visualization_output_dir = output_root / "visualization"
    tree_output_dir.mkdir(parents=True, exist_ok=True)
    visualization_output_dir.mkdir(parents=True, exist_ok=True)

    ascii_tree = render_ascii_tree(tree)

    atomic_write_text(tree_output_dir / "repo.tree", ascii_tree)
    atomic_write_text(tree_output_dir / "repo.md", render_markdown(ascii_tree))
    atomic_write_text(
        tree_output_dir / "repo.json",
        json.dumps(
            tree_contract(
                tree=tree,
                revision=revision,
                ref=ref,
                committed_at=committed_at,
            ),
            indent=2,
        )
        + "\n",
    )
    atomic_write_text(tree_output_dir / "repo.xml", render_xml(tree) + "\n")
    atomic_write_text(
        tree_output_dir / "repo.html",
        render_html(ascii_tree, str(tree["name"])),
    )
    atomic_write_text(visualization_output_dir / "repository.svg", render_svg(tree))


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_root = Path(args.output_root).resolve()
    if not repo_root.is_dir():
        raise SystemExit(f"Repository root is not a directory: {repo_root}")
    try:
        output_root.relative_to(repo_root)
    except ValueError as error:
        raise SystemExit(f"Output root must be inside the repository: {output_root}") from error

    excluded_paths = normalize_excluded_paths(args.excluded_paths)
    revision = resolve_revision(repo_root, args.ref)
    committed_at = source_committed_at(repo_root, revision)
    tree = build_tree(
        repository_name=repo_root.name,
        entries=list_git_entries(repo_root, revision),
        excluded_paths=excluded_paths,
        max_depth=args.max_depth,
    )
    write_outputs(
        output_root=output_root,
        tree=tree,
        revision=revision,
        ref=args.ref,
        committed_at=committed_at,
    )


if __name__ == "__main__":
    main()
