# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Exercise the actual composite scripts in complete, differently named checkouts.

This local harness substitutes only the action's env expressions. It is not a
GitHub scheduler emulator and cannot establish deployment or provider evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "actions/repository-intelligence"
REPOSITORY = "example/repository"


def git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True, capture_output=True, text=True,
        env={**os.environ, "GIT_AUTHOR_DATE": "2026-08-25T14:00:00Z",
             "GIT_COMMITTER_DATE": "2026-08-25T14:00:00Z"},
    ).stdout.strip()


def inventory(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*")) if path.is_file()}


class RepositoryIntelligencePortabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name)
        self.seed = self.workspace / "seed"
        self.seed.mkdir()
        git(self.seed, "init", "--quiet", "--initial-branch", "main")
        git(self.seed, "config", "user.name", "Fixture")
        git(self.seed, "config", "user.email", "fixture@example.test")
        (self.seed / "README.md").write_text("# Fixture\n", encoding="utf-8")
        git(self.seed, "add", "README.md")
        git(self.seed, "commit", "--quiet", "--message", "fixture")
        self.commit = git(self.seed, "rev-parse", "HEAD")
        self.generator = git(ROOT, "rev-parse", "HEAD")

    def checkout(self, relative: str) -> Path:
        path = self.workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        git(self.workspace, "clone", "--quiet", "--no-local", str(self.seed), str(path))
        git(path, "checkout", "--quiet", "--detach", self.commit)
        self.assertEqual(git(path, "rev-parse", "--is-shallow-repository"), "false")
        return path

    def run_action(
        self, checkout: Path, *, snapshot: bool = False,
        inputs: dict[str, str] | None = None,
        context: dict[str, str] | None = None,
        environment: dict[str, str] | None = None,
        metadata_only: bool = False,
    ) -> dict[str, str]:
        """Run checked-in Bash steps, binding their declared env from fixture inputs."""
        values = {
            "activity-ref": self.commit, "activity-since": "2020-01-01",
            "activity-author": "", "as-of": "", "default-branch": "",
            "max-depth": "10", "output-directory": "dist/intelligence",
            "observatory-comparison": "", "observatory-snapshot": "",
            "reports-directory": ".reports", "repository": REPOSITORY,
            "repository-visibility": "", "require-full-history": "true",
            "source-commit": self.commit, "work-directory": ".cache/intelligence",
            "excluded-paths": ".git,.cache,dist,.reports",
            "analytics-excluded-paths": ".git,.cache,dist,.reports",
        }
        if snapshot:
            source = ROOT / "tests/fixtures/repository-intelligence-site/snapshot.json"
            target = checkout / ".cache/snapshot.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            evidence = json.loads(source.read_text(encoding="utf-8").replace("1" * 40, self.commit))
            health = ROOT / "tests/fixtures/repository-intelligence-health/snapshot.json"
            evidence["views"]["health"] = json.loads(health.read_text())["views"]["health"]
            target.write_text(json.dumps(evidence, sort_keys=True) + "\n", encoding="utf-8")
            values["observatory-snapshot"] = ".cache/snapshot.json"
        values.update(inputs or {})
        expressions = {f"inputs.{key}": value for key, value in values.items()}
        expressions.update({
            "github.event.repository.default_branch": "main",
            "github.event.repository.private": "false",
            "github.event.repository.visibility": "public",
            "github.action_ref": self.generator,
            "github.action_repository": "egohygiene/relay",
            "job.workflow_ref": "", "job.workflow_repository": "", "job.workflow_sha": "",
        })
        expressions.update(context or {})
        action = (ACTION / "action.yml").read_text(encoding="utf-8")
        outputs: dict[str, str] = {}
        for index, step in enumerate(action.split("    - name: ")[1:]):
            header, script = step.split("      run: |\n", 1)
            output_path = self.workspace / f"outputs-{index}"
            output_path.write_text("", encoding="utf-8")
            env = {**os.environ, "GITHUB_WORKSPACE": str(checkout),
                   "GITHUB_ACTION_PATH": str(ACTION), "GITHUB_OUTPUT": str(output_path),
                   "GITHUB_REPOSITORY": REPOSITORY}
            env.update(environment or {})
            bindings = re.findall(r'^        (\w+): "\$\{\{ (.*?) \}\}"$', header, re.MULTILINE)
            self.assertTrue(bindings, "Harness must bind the action's declared env")
            for key, expression in bindings:
                env[key] = expressions[expression]
            subprocess.run(["bash", "--noprofile", "--norc", "-c", textwrap.dedent(script)],
                           cwd=checkout, env=env, check=True, capture_output=True, text=True)
            step_outputs = dict(line.split("=", 1) for line in output_path.read_text().splitlines())
            outputs.update(step_outputs)
            step_id = re.search(r"^      id: (\w+)$", header, re.MULTILINE)
            if step_id:
                expressions.update({f"steps.{step_id[1]}.outputs.{key}": value
                                    for key, value in step_outputs.items()})
            if metadata_only:
                break
        return outputs

    def test_complete_bundles_are_portable_across_checkout_names(self) -> None:
        first = self.checkout("runner-alpha/checkout-one")
        second = self.checkout("worktrees-beta/checkout-two")
        for snapshot in (False, True):
            with self.subTest(snapshot=snapshot):
                outputs = [self.run_action(path, snapshot=snapshot, environment={
                    "GITHUB_RUN_ID": str(100 + index), "GITHUB_RUN_ATTEMPT": str(index + 1),
                }) for index, path in enumerate((first, second))]
                bundles = [inventory(path / "dist/intelligence") for path in (first, second)]
                self.assertEqual(bundles[0].keys(), bundles[1].keys())
                for name in bundles[0]:
                    self.assertEqual(bundles[0][name], bundles[1][name], name)
                self.assertTrue({"summary.json", "dashboard/index.html", "provenance.json",
                                 "build-manifest.json"}.issubset(bundles[0]))
                self.assertEqual(outputs[0], outputs[1])
                self.assertEqual(inventory(first / ".cache/intelligence/tree"),
                                 inventory(second / ".cache/intelligence/tree"))
                tree = json.loads((first / ".cache/intelligence/tree/repo.json").read_text())
                self.assertEqual(tree["tree"]["name"], REPOSITORY)
                self.assertEqual(tree["source"]["revision"], self.commit)
                for root in (first, second):
                    public_bytes = b"\n".join(bundles[0].values())
                    for private_name in (str(root), root.name, root.parent.name, str(self.workspace)):
                        self.assertNotIn(private_name.encode(), public_bytes)
                manifest = json.loads(bundles[0]["build-manifest.json"])
                self.assertEqual(outputs[0]["bundle-digest"], manifest["bundle"]["digest"])
                self.assertEqual(outputs[0]["manifest-sha256"],
                                 "sha256:" + hashlib.sha256(bundles[0]["build-manifest.json"]).hexdigest())
                print("portability-proof: " + json.dumps({
                    "consumer_revision": self.commit,
                    "generator_revision": self.generator,
                    "snapshot": snapshot,
                    "public_file_count": len(bundles[0]),
                    "bundle_digest": outputs[0]["bundle-digest"],
                    "manifest_sha256": outputs[0]["manifest-sha256"],
                }, sort_keys=True))

    def test_distinct_source_commits_remain_identifiable(self) -> None:
        first = self.checkout("first-revision/checkout")
        original = self.commit
        first_outputs = self.run_action(first)
        (self.seed / "README.md").write_text("# Changed fixture\n", encoding="utf-8")
        git(self.seed, "add", "README.md")
        git(self.seed, "commit", "--quiet", "--message", "changed fixture")
        self.commit = git(self.seed, "rev-parse", "HEAD")
        second = self.checkout("second-revision/checkout")
        second_outputs = self.run_action(second)
        self.assertNotEqual(original, self.commit)
        self.assertEqual(first_outputs["source-commit"], original)
        self.assertEqual(second_outputs["source-commit"], self.commit)
        self.assertNotEqual(first_outputs["bundle-digest"], second_outputs["bundle-digest"])
        for path, revision in ((first, original), (second, self.commit)):
            tree = json.loads((path / ".cache/intelligence/tree/repo.json").read_text())
            self.assertEqual(tree["tree"]["name"], REPOSITORY)
            self.assertEqual(tree["source"]["revision"], revision)

    def test_identity_resolution_preserves_event_authority(self) -> None:
        checkout = self.checkout("authority/consumer")
        cases = [
            ({}, {}, {}, REPOSITORY),
            ({"repository": "EXAMPLE/REPOSITORY"}, {}, {}, REPOSITORY),
            ({"repository": "local/consumer"}, {}, {"GITHUB_REPOSITORY": ""}, "local/consumer"),
        ]
        for inputs, context, environment, expected in cases:
            with self.subTest(inputs=inputs, environment=environment):
                result = self.run_action(checkout, inputs=inputs, context=context,
                                         environment=environment, metadata_only=True)
                self.assertEqual(result["repository"], expected)

    def test_standalone_cli_requires_portable_identity(self) -> None:
        checkout = self.checkout("standalone/unnamed-checkout")
        arguments = [sys.executable, str(ACTION / "scripts/generate_repository_intelligence.py"),
                     "--repo-root", str(checkout), "--output-root", str(checkout / ".cache/tree"),
                     "--ref", self.commit]
        for explicit, workflow, expected in (
            (REPOSITORY, "", REPOSITORY),
            ("", REPOSITORY, REPOSITORY),
            ("EXAMPLE/REPOSITORY", REPOSITORY, REPOSITORY),
        ):
            with self.subTest(explicit=explicit, workflow=workflow):
                subprocess.run([*arguments, "--repository", explicit], check=True,
                               capture_output=True, text=True,
                               env={**os.environ, "GITHUB_REPOSITORY": workflow})
                tree = json.loads((checkout / ".cache/tree/tree/repo.json").read_text())
                self.assertEqual(tree["tree"]["name"], expected)
        for explicit, workflow, diagnostic in (
            ("", "", "required"), ("other/repository", REPOSITORY, "must not override"),
            ("bad", "", "owner/name"), ("owner/../name", "", "owner/name"),
            ("owner/..", "", "dot segments"), ("./name", "", "dot segments"),
            ("owner/name\n", "", "owner/name"), ("", "bad", "owner/name"),
        ):
            with self.subTest(explicit=explicit, workflow=workflow):
                result = subprocess.run([*arguments, "--repository", explicit],
                                        capture_output=True, text=True,
                                        env={**os.environ, "GITHUB_REPOSITORY": workflow})
                self.assertEqual(result.returncode, 2)
                self.assertIn(diagnostic, result.stderr)

    def test_invalid_conflicting_or_absent_identity_is_rejected(self) -> None:
        checkout = self.checkout("rejected/consumer")
        cases = [
            ({"repository": "other/repository"}, {}, "must not override"),
            ({"repository": "bad"}, {"GITHUB_REPOSITORY": ""}, "owner/name"),
            ({"repository": "../repository"}, {"GITHUB_REPOSITORY": ""}, "dot segments"),
            ({"repository": ""}, {"GITHUB_REPOSITORY": ""}, "required"),
            ({"repository-visibility": "private"}, {}, "must not override"),
        ]
        for inputs, environment, diagnostic in cases:
            with self.subTest(inputs=inputs):
                with self.assertRaises(subprocess.CalledProcessError) as failure:
                    self.run_action(checkout, inputs=inputs, environment=environment, metadata_only=True)
                self.assertIn(diagnostic, failure.exception.stderr)
                self.assertFalse((checkout / "dist/intelligence").exists())


if __name__ == "__main__":
    unittest.main()
