# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Render bounded Repository Intelligence supporting views from accepted evidence."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def load_renderer(name: str, filename: str) -> ModuleType:
    """Load one sibling renderer without changing Python's import path."""

    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Repository Intelligence renderer could not be loaded: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dependencies_renderer = load_renderer(
    "relay_repository_intelligence_dependencies_route",
    "render_repository_intelligence_dependencies_route.py",
)
work_renderer = load_renderer(
    "relay_repository_intelligence_work",
    "render_repository_intelligence_work.py",
)
releases_renderer = load_renderer(
    "relay_repository_intelligence_releases",
    "render_repository_intelligence_releases.py",
)
search_renderer = load_renderer(
    "relay_repository_intelligence_search",
    "render_repository_intelligence_search.py",
)

# Preserve the helper surface used by focused dependency tests and existing callers.
for exported_name in dir(dependencies_renderer):
    if not exported_name.startswith("__"):
        globals()[exported_name] = getattr(dependencies_renderer, exported_name)

render_dependencies_main = dependencies_renderer.main
render_work_main = work_renderer.main
render_releases_main = releases_renderer.main
render_search_main = search_renderer.main


def main() -> int:
    """Render Dependencies, Work, Releases, then Search from one accepted snapshot."""

    result = render_dependencies_main()
    if result != 0:
        return result
    result = render_work_main()
    if result != 0:
        return result
    result = render_releases_main()
    if result != 0:
        return result
    return render_search_main()


if __name__ == "__main__":
    raise SystemExit(main())
