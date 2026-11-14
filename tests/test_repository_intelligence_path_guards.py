# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Exercise the actual action's pre-Git path checks without collection or writes."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "actions/repository-intelligence"


class RepositoryIntelligencePathGuardTests(unittest.TestCase):
    def run_guard(self, overrides: dict[str, str] | None = None):
        action = (ACTION / "action.yml").read_text(encoding="utf-8")
        metadata = action.split("      id: metadata\n", 1)[1]
        header, body = metadata.split("      run: |\n", 1)
        script = textwrap.dedent(body.split("    - name: ", 1)[0])
        # Stop before source Git resolution. No clone, collector, renderer or
        # publication behavior is executed by this focused regression.
        script, separator, _ = script.partition('source_commit="${INPUT_SOURCE_COMMIT}"')
        self.assertTrue(separator, "actual metadata pre-Git boundary must remain explicit")
        self.assertNotIn("$(git ", script)
        self.assertNotRegex(script, r"(?m)^\s*git\s")
        names = re.findall(r"^        (\w+):", header, re.MULTILINE)
        environment = {name: "" for name in names}
        environment.update({
            "PATH": os.defpath,
            "LC_ALL": "C",
            "GITHUB_ACTION_PATH": str(ACTION),
            "INPUT_COLLECT_ADRS": "false",
            "INPUT_COLLECT_ROADMAP": "false",
            "INPUT_COLLECT_JOURNEY": "false",
            "INPUT_COLLECT_DEPENDENCIES": "false",
            "INPUT_SEARCH_ATTRIBUTION": "false",
            "INPUT_JOURNEY_MAXIMUM_COMMITS": "256",
            "INPUT_ADR_POLICY_OWNER": "false",
            "INPUT_ADR_KNOWN_EXTERNAL_DECISIONS": "[]",
            "INPUT_OUTPUT_DIRECTORY": ".site/producers/intelligence",
            "INPUT_WORK_DIRECTORY": ".cache/repository-intelligence",
            "INPUT_REPORTS_DIRECTORY": ".reports",
            "INPUT_MAX_DEPTH": "10",
            "INPUT_REQUIRE_FULL_HISTORY": "true",
        })
        environment.update(overrides or {})
        with tempfile.TemporaryDirectory(prefix="relay-path-guard-") as directory:
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-c", script],
                cwd=directory, env=environment, capture_output=True, text=True,
                check=False, timeout=10,
            )
            self.assertEqual(list(Path(directory).iterdir()), [], "metadata guards must not write")
        return result

    def test_default_literal_directories_do_not_attempt_path_commands(self):
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "", "valid paths must not produce attempted-command errors")

    def test_literal_hidden_names_and_segment_prefix_siblings_are_allowed(self):
        for values in [
            {"INPUT_OUTPUT_DIRECTORY": "dist.v1/intelligence", "INPUT_WORK_DIRECTORY": ".cache/work"},
            {"INPUT_OUTPUT_DIRECTORY": "out", "INPUT_WORK_DIRECTORY": "out-private", "INPUT_REPORTS_DIRECTORY": "out-reports"},
            {"INPUT_OUTPUT_DIRECTORY": "...output/data", "INPUT_WORK_DIRECTORY": "_private/..cache"},
        ]:
            with self.subTest(values=values):
                result = self.run_guard(values)
                self.assertEqual((result.returncode, result.stderr), (0, ""))

    def test_dot_parent_and_noncanonical_segments_are_refused_for_each_managed_path(self):
        for key in ("INPUT_OUTPUT_DIRECTORY", "INPUT_WORK_DIRECTORY", "INPUT_REPORTS_DIRECTORY"):
            for value in (".", "..", "./out", "../out", "a/./b", "a/../b", "a/.", "a/..", "a//b", "out/", "/out", ""):
                with self.subTest(key=key, value=value):
                    result = self.run_guard({key: value})
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("canonical, literal repository-relative path", result.stderr)
                    self.assertNotIn("No such file or directory", result.stderr)

    def test_nonliteral_metacharacters_and_controls_are_refused_without_execution(self):
        for value in ("out with spaces", "out$(touch marker)", "out;touch marker", "out`touch marker`", "out*", "out?", "out\nnext", "out\tpart", "out\\part"):
            with self.subTest(value=value):
                result = self.run_guard({"INPUT_OUTPUT_DIRECTORY": value})
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("canonical, literal repository-relative path", result.stderr)
                self.assertNotIn("command not found", result.stderr)

    def test_private_paths_cannot_equal_contain_or_be_contained_by_public_output(self):
        for key in ("INPUT_WORK_DIRECTORY", "INPUT_REPORTS_DIRECTORY"):
            for private, public in (("out", "out"), ("out/private", "out"), ("out", "out/public")):
                with self.subTest(key=key, private=private, public=public):
                    result = self.run_guard({key: private, "INPUT_OUTPUT_DIRECTORY": public})
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("must not overlap", result.stderr)

    def test_optional_input_paths_use_the_same_canonical_guard(self):
        for key in ("INPUT_SOURCE_CAPTURES", "INPUT_OBSERVATORY_SNAPSHOT", "INPUT_OBSERVATORY_COMPARISON", "INPUT_OBSERVATORY_HYGIENE"):
            with self.subTest(key=key):
                result = self.run_guard({key: "a/../private.json", "INPUT_AS_OF": "2026-11-13T00:00:00Z"})
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("canonical, literal repository-relative path", result.stderr)

    def test_protected_source_areas_remain_refused(self):
        for key in ("INPUT_OUTPUT_DIRECTORY", "INPUT_WORK_DIRECTORY"):
            for value in (".git", ".github/output", "actions/build", "schemas/generated", "scripts/output", "tests/output"):
                with self.subTest(key=key, value=value):
                    result = self.run_guard({key: value})
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("protected repository area", result.stderr)


if __name__ == "__main__":
    unittest.main()
