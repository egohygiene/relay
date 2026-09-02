# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Contract, safety, and integration tests for repository label automation."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT / "actions/repository-labels/scripts/repository_labels.py"
)
SPEC = importlib.util.spec_from_file_location("repository_labels", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
labels = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(labels)


class LabelFixture:
    """Build one isolated canonical contract and representative repository."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.lock = root / "lock.json"
        self.catalog = root / "catalog.json"
        self.assignments = root / "assignments.json"
        self.config = root / "config.json"
        self.observed = root / "observed.json"
        self.event = root / "event.json"
        self.changed = root / "changed.json"
        self.available = root / "available.json"
        self.comments = root / "comments.json"
        self.path_defaults = (
            ROOT
            / "actions/repository-labels/contracts/path-labels.organization-v1.json"
        )
        self.plan = root / "plan.json"
        self.repository = "egohygiene/example"
        self._write_contract()
        self.write_config()
        self.write_event()

    @staticmethod
    def write(path: Path, value: object) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

    @staticmethod
    def label(name: str, color: str = "123456", description: str | None = None) -> dict[str, str]:
        return {
            "name": name,
            "color": color,
            "description": description or f"Canonical {name}",
        }

    def _write_contract(self) -> None:
        catalog = {
            "schema_version": 1,
            "catalog_version": "1.0.0",
            "owner": "egohygiene/.github",
            "defaults": {"required": True, "removal_policy": "retain"},
            "universal": [
                {**self.label("ready", "0e8a16"), "category": "status"},
                {**self.label("area:automation", "0369a1"), "category": "area"},
                {
                    **self.label("area:developer-experience", "7c5c1e"),
                    "category": "area",
                },
                {**self.label("area:security", "b91c1c"), "category": "area"},
                {
                    **self.label("type:documentation", "64748b"),
                    "category": "type",
                },
            ],
            "overlays": [
                {
                    "id": "engineering",
                    "labels": [
                        self.label("📄 documentation", "64748b"),
                        self.label("📦 package", "0369a1"),
                        self.label("⚙️ infra", "274472"),
                    ],
                }
            ],
        }
        assignment = {
            "schema_version": 1,
            "catalog_version": "1.0.0",
            "repositories": [
                {
                    "repository": self.repository,
                    "include_universal": True,
                    "overlays": ["engineering"],
                    "additional_labels": [
                        self.label("size/xs", "d4c5f9"),
                        self.label("size/s", "c5def5"),
                        self.label("size/m", "bfdadc"),
                        self.label("size/l", "fbca04"),
                        self.label("size/xl", "d93f0b"),
                    ],
                }
            ],
        }
        self.write(self.catalog, catalog)
        self.write(self.assignments, assignment)
        lock = {
            "schema": labels.LOCK_SCHEMA,
            "repository": "egohygiene/.github",
            "revision": "a" * 40,
            "catalog": {
                "path": ".github/labels/catalog.v1.json",
                "sha256": labels.digest_file(self.catalog),
            },
            "assignments": {
                "path": ".github/labels/repositories.v1.json",
                "sha256": labels.digest_file(self.assignments),
            },
        }
        self.write(self.lock, lock)
        desired = labels.desired_labels(self.repository, catalog, assignment)
        self.write(self.available, desired)
        self.write(self.observed, desired)

    def write_config(
        self,
        *,
        missing_label: str = "error",
        maintainer_behavior: str = "error",
        retire: list[str] | None = None,
    ) -> None:
        self.write(
            self.config,
            {
                "schema": labels.CONFIG_SCHEMA,
                "sync": {"retire_labels": retire or []},
                "pull_requests": {
                    "path_labels": {
                        "enabled": True,
                        "preset": "none",
                        "missing_label": missing_label,
                        "rules": [
                            {
                                "label": "📄 documentation",
                                "paths": ["**/*.md", "docs/**"],
                            },
                            {"label": "📦 package", "paths": ["actions/**"]},
                            {"label": "⚙️ infra", "paths": [".github/**"]},
                        ],
                    },
                    "size_labels": {
                        "enabled": True,
                        "thresholds": [
                            {"label": "size/xs", "max_changes": 9},
                            {"label": "size/s", "max_changes": 49},
                            {"label": "size/m", "max_changes": 249},
                            {"label": "size/l", "max_changes": 999},
                            {"label": "size/xl", "max_changes": None},
                        ],
                    },
                    "welcome": {
                        "enabled": True,
                        "message": "Welcome to the project!",
                    },
                    "maintainer_edits": {
                        "required_for_forks": True,
                        "behavior": maintainer_behavior,
                    },
                },
            },
        )

    def write_event(
        self,
        *,
        action: str = "opened",
        association: str = "FIRST_TIME_CONTRIBUTOR",
        author_type: str = "User",
        author_login: str = "contributor",
        fork: bool = False,
        maintainer_can_modify: bool = True,
        current_labels: list[dict[str, str]] | None = None,
    ) -> None:
        self.write(
            self.event,
            {
                "action": action,
                "number": 7,
                "repository": {"full_name": self.repository},
                "pull_request": {
                    "number": 7,
                    "author_association": association,
                    "maintainer_can_modify": maintainer_can_modify,
                    "labels": current_labels or [],
                    "user": {"login": author_login, "type": author_type},
                    "base": {"sha": "b" * 40},
                    "head": {
                        "sha": "c" * 40,
                        "repo": {
                            "full_name": (
                                "external/example" if fork else self.repository
                            )
                        },
                    },
                },
            },
        )
        self.write(
            self.changed,
            [
                {"filename": "README.md", "additions": 5, "deletions": 1},
                {"filename": "actions/tool/action.yml", "additions": 20, "deletions": 0},
            ],
        )
        self.write(self.comments, [])

    def sync_arguments(self) -> argparse.Namespace:
        return argparse.Namespace(
            lock=self.lock,
            catalog=self.catalog,
            assignments=self.assignments,
            config=self.config,
            repository=self.repository,
            observed_labels=self.observed,
        )

    def pr_arguments(self) -> argparse.Namespace:
        return argparse.Namespace(
            lock=self.lock,
            catalog=self.catalog,
            assignments=self.assignments,
            config=self.config,
            repository=self.repository,
            event=self.event,
            changed_files=self.changed,
            available_labels=self.available,
            comments=self.comments,
            path_defaults=self.path_defaults,
            run_id="1234",
        )


class RepositoryLabelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = LabelFixture(Path(self.temporary.name))

    def test_lock_rejects_changed_canonical_bytes(self) -> None:
        self.fixture.catalog.write_text(self.fixture.catalog.read_text() + "\n")
        with self.assertRaisesRegex(labels.ContractError, "immutable lock"):
            labels.plan_sync(self.fixture.sync_arguments())

    def test_sync_plan_creates_updates_and_preserves_unmanaged_labels(self) -> None:
        observed = json.loads(self.fixture.observed.read_text())
        observed = [item for item in observed if item["name"] != "size/xs"]
        next(item for item in observed if item["name"] == "ready")["color"] = "ffffff"
        observed.append(self.fixture.label("manual/local", "abcdef"))
        self.fixture.write(self.fixture.observed, observed)

        plan = labels.plan_sync(self.fixture.sync_arguments())

        self.assertEqual([item["name"] for item in plan["operations"]["create"]], ["size/xs"])
        self.assertEqual([item["name"] for item in plan["operations"]["update"]], ["ready"])
        self.assertEqual(plan["operations"]["delete"], [])
        self.assertNotIn("manual/local", json.dumps(plan))
        labels.verify_plan(plan, labels.SYNC_PLAN_SCHEMA)

    def test_deletion_requires_explicit_retirement_and_apply_authority(self) -> None:
        observed = json.loads(self.fixture.observed.read_text())
        observed.append(self.fixture.label("legacy", "abcdef"))
        self.fixture.write(self.fixture.observed, observed)
        self.fixture.write_config(retire=["legacy"])
        plan = labels.plan_sync(self.fixture.sync_arguments())
        self.fixture.write(self.fixture.plan, plan)
        arguments = argparse.Namespace(
            plan=self.fixture.plan,
            repository=self.fixture.repository,
            allow_deletions=False,
        )
        with self.assertRaisesRegex(labels.ContractError, "authority was not granted"):
            labels.apply_sync(arguments)

    def test_sync_apply_uses_the_github_label_rename_contract(self) -> None:
        observed = json.loads(self.fixture.observed.read_text())
        next(item for item in observed if item["name"] == "ready")["color"] = "ffffff"
        self.fixture.write(self.fixture.observed, observed)
        plan = labels.plan_sync(self.fixture.sync_arguments())
        self.fixture.write(self.fixture.plan, plan)
        arguments = argparse.Namespace(
            plan=self.fixture.plan,
            repository=self.fixture.repository,
            allow_deletions=False,
        )

        with mock.patch.object(labels, "gh_api") as api:
            labels.apply_sync(arguments)

        api.assert_called_once_with(
            "PATCH",
            "repos/egohygiene/example/labels/ready",
            {
                "new_name": "ready",
                "color": "0e8a16",
                "description": "Canonical ready",
            },
        )

    def test_overlapping_paths_select_multiple_labels_and_one_size(self) -> None:
        plan = labels.plan_pull_request(self.fixture.pr_arguments())

        self.assertEqual(
            plan["operations"]["add_labels"],
            ["size/s", "📄 documentation", "📦 package"],
        )
        self.assertEqual(plan["changed_lines"], 26)
        self.assertEqual(len(plan["operations"]["comments"]), 1)
        self.assertFalse(plan["blocking"])
        labels.verify_plan(plan, labels.PR_PLAN_SCHEMA)

    def test_shared_path_profile_allows_repository_additions_and_overrides(self) -> None:
        config = json.loads(self.fixture.config.read_text())
        path_labels = config["pull_requests"]["path_labels"]
        path_labels["preset"] = "organization-v1"
        path_labels["rules"].append(
            {"label": "type:documentation", "paths": ["guides/**"]}
        )
        self.fixture.write(self.fixture.config, config)
        self.fixture.write(
            self.fixture.changed,
            [
                {
                    "filename": ".github/workflows/validate.yml",
                    "additions": 2,
                    "deletions": 0,
                },
                {"filename": "README.md", "additions": 1, "deletions": 0},
            ],
        )

        plan = labels.plan_pull_request(self.fixture.pr_arguments())

        self.assertIn("area:automation", plan["operations"]["add_labels"])
        self.assertIn("⚙️ infra", plan["operations"]["add_labels"])
        self.assertIn("📄 documentation", plan["operations"]["add_labels"])
        self.assertNotIn("type:documentation", plan["operations"]["add_labels"])
        self.assertEqual(
            plan["path_label_profile"]["profile"], "organization-v1"
        )

    def test_only_managed_labels_are_removed(self) -> None:
        current = [
            self.fixture.label("manual/local", "abcdef"),
            self.fixture.label("size/xl", "d93f0b"),
            self.fixture.label("⚙️ infra", "274472"),
        ]
        self.fixture.write_event(current_labels=current)
        plan = labels.plan_pull_request(self.fixture.pr_arguments())

        self.assertEqual(plan["operations"]["remove_labels"], ["size/xl", "⚙️ infra"])
        self.assertNotIn("manual/local", plan["operations"]["remove_labels"])

    def test_fork_without_maintainer_edits_blocks_and_is_idempotent(self) -> None:
        self.fixture.write_event(fork=True, maintainer_can_modify=False)
        first = labels.plan_pull_request(self.fixture.pr_arguments())
        self.assertTrue(first["blocking"])
        self.assertEqual(len(first["operations"]["comments"]), 2)

        self.fixture.write(
            self.fixture.comments,
            [
                {"body": labels.WELCOME_MARKER},
                {"body": labels.MAINTAINER_MARKER},
            ],
        )
        second = labels.plan_pull_request(self.fixture.pr_arguments())
        self.assertEqual(second["operations"]["comments"], [])

    def test_bot_never_receives_first_contributor_welcome(self) -> None:
        self.fixture.write_event(author_type="Bot", author_login="dependabot[bot]")
        plan = labels.plan_pull_request(self.fixture.pr_arguments())
        self.assertEqual(plan["operations"]["comments"], [])

    def test_absent_configuration_is_an_explicit_noop(self) -> None:
        self.fixture.config.unlink()
        plan = labels.plan_pull_request(self.fixture.pr_arguments())
        self.assertEqual(plan["status"], "not-configured")
        self.assertEqual(plan["managed_labels"], [])
        self.assertEqual(plan["operations"]["add_labels"], [])

    def test_missing_configured_label_fails_or_warns_by_adoption_mode(self) -> None:
        available = json.loads(self.fixture.available.read_text())
        available = [item for item in available if item["name"] != "📦 package"]
        self.fixture.write(self.fixture.available, available)
        blocking = labels.plan_pull_request(self.fixture.pr_arguments())
        self.assertTrue(blocking["blocking"])
        self.assertIn("📦 package", blocking["violations"][0])

        self.fixture.write_config(missing_label="warn")
        warning = labels.plan_pull_request(self.fixture.pr_arguments())
        self.assertFalse(warning["blocking"])
        self.assertNotIn("📦 package", warning["operations"]["add_labels"])
        self.assertIn("📦 package", warning["warnings"][0])

    def test_apply_rejects_stale_pull_request_and_preserves_comment_idempotence(self) -> None:
        plan = labels.plan_pull_request(self.fixture.pr_arguments())
        self.fixture.write(self.fixture.plan, plan)
        arguments = argparse.Namespace(
            plan=self.fixture.plan,
            repository=self.fixture.repository,
            expected_run_id="1234",
        )
        stale = {
            "head": {"sha": "d" * 40},
            "base": {"sha": "b" * 40},
        }
        with mock.patch.object(labels, "gh_api", return_value=stale):
            with self.assertRaisesRegex(labels.ContractError, "moved after planning"):
                labels.apply_pull_request(arguments)

        calls: list[tuple[str, str, object, bool]] = []

        def fake_api(
            method: str,
            endpoint: str,
            payload: object = None,
            *,
            paginate: bool = False,
        ) -> object:
            calls.append((method, endpoint, payload, paginate))
            if endpoint.endswith("/pulls/7"):
                return {
                    "head": {"sha": "c" * 40},
                    "base": {"sha": "b" * 40},
                }
            if endpoint.endswith("/comments?per_page=100"):
                return [{"body": labels.WELCOME_MARKER}]
            return {}

        with mock.patch.object(labels, "gh_api", side_effect=fake_api):
            evidence = labels.apply_pull_request(arguments)
        self.assertEqual(evidence["comments_added"], 0)
        self.assertTrue(
            any(
                endpoint.endswith("/comments?per_page=100") and paginate
                for _, endpoint, _, paginate in calls
            )
        )
        self.assertFalse(
            any(
                method == "POST" and endpoint.endswith("/comments")
                for method, endpoint, _, _ in calls
            )
        )


if __name__ == "__main__":
    unittest.main()
