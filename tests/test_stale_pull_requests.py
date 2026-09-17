# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Safety and lifecycle tests for stale pull-request automation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT / "actions/stale-pull-requests/scripts/stale_pull_requests.py"
)
SPEC = importlib.util.spec_from_file_location("stale_pull_requests", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
stale = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stale)

NOW = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
PLAN_TIME = datetime(2026, 9, 16, 0, 0, tzinfo=timezone.utc)


def config(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "inactivity_days": 30,
        "warning_days": 7,
        "stale_label": "stale",
        "closed_label": "",
        "exempt_labels": [
            "area:security",
            "critical",
            "dependencies",
            "do-not-stale",
            "pinned",
            "priority:p0",
            "security",
        ],
        "exempt_users": [],
        "exempt_review_teams": [],
        "exempt_drafts": True,
        "exempt_bots": True,
        "process_issues": False,
        "close_enabled": False,
        "maximum_items": 100,
        "warning_message": "",
        "close_message": "",
    }
    value.update(overrides)
    return value


def snapshot(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "number": 14,
        "kind": "pull_request",
        "state": "open",
        "updated_at": "2026-08-01T12:00:00Z",
        "head_sha": "a" * 40,
        "author": {"login": "octocat", "type": "User"},
        "draft": False,
        "labels": [],
        "assignees": [],
        "requested_review_users": [],
        "requested_review_teams": [],
        "warning": None,
        "latest_comment_id": None,
    }
    value.update(overrides)
    return value


def warning(
    configuration: dict[str, object],
    *,
    created_at: str = "2026-09-09T12:00:00Z",
    comment_id: int = 500,
    promised_warning_days: int | None = None,
    close_enabled: bool | None = None,
) -> dict[str, object]:
    close_value = (
        bool(configuration["close_enabled"])
        if close_enabled is None
        else close_enabled
    )
    policy_config = dict(configuration)
    policy_config["close_enabled"] = close_value
    return {
        "comment_id": comment_id,
        "created_at": created_at,
        "updated_at": created_at,
        "body_sha256": "b" * 64,
        "promised_warning_days": (
            int(configuration["warning_days"])
            if promised_warning_days is None
            else promised_warning_days
        ),
        "close_enabled": close_value,
        "policy_sha256": stale.policy_sha256(policy_config),
        "head_sha": "a" * 40,
    }


def provider_item(number: int = 14, **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "number": number,
        "state": "open",
        "updated_at": "2026-08-01T12:00:00Z",
        "user": {"login": "octocat", "type": "User"},
        "labels": [],
        "assignees": [],
        "draft": False,
        "head": {"sha": "a" * 40},
        "_relay_kind": "pull_request",
    }
    value.update(overrides)
    return value


def plan_arguments(**overrides: str) -> argparse.Namespace:
    values = {
        "repository": "egohygiene/example",
        "inactivity_days": "30",
        "warning_days": "7",
        "stale_label": "stale",
        "closed_label": "",
        "exempt_labels": (
            "do-not-stale,pinned,critical,security,dependencies,priority:p0,"
            "area:security"
        ),
        "exempt_users": "",
        "exempt_review_teams": "",
        "exempt_drafts": "true",
        "exempt_bots": "true",
        "process_issues": "false",
        "close_enabled": "false",
        "maximum_items": "100",
        "warning_message": "",
        "close_message": "",
        "evaluation_time": stale.format_timestamp(PLAN_TIME),
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class StalePullRequestTests(unittest.TestCase):
    def test_inactive_item_gets_visible_checksum_bound_warning(self) -> None:
        configuration = config(close_enabled=True)

        decision = stale.decide(snapshot(), configuration, NOW)

        self.assertEqual(decision["action"], "warn")
        self.assertIn("will be closed after 7 day(s)", decision["comment"])
        self.assertTrue(decision["comment"].splitlines()[-1].startswith(stale.MARKER_PREFIX))
        self.assertIsNotNone(stale.MARKER_PATTERN.search(decision["comment"]))

    def test_manual_stale_label_without_marker_gets_repair_warning_only(self) -> None:
        current = snapshot(updated_at="2026-09-17T11:00:00Z", labels=["stale"])

        decision = stale.decide(current, config(close_enabled=True), NOW)

        self.assertEqual(decision["action"], "warn")
        self.assertEqual(decision["reason"], "untrusted-stale-label")

    def test_closure_requires_label_trusted_marker_and_elapsed_window(self) -> None:
        configuration = config(close_enabled=True)
        marker = warning(configuration)
        current = snapshot(
            updated_at=marker["created_at"],
            labels=["stale"],
            warning=marker,
            latest_comment_id=marker["comment_id"],
        )

        decision = stale.decide(current, configuration, NOW)

        self.assertEqual(decision["action"], "close")
        self.assertEqual(decision["reason"], "warning-window-elapsed")

    def test_enabling_closure_restarts_warning_instead_of_closing(self) -> None:
        warning_only = config(close_enabled=False)
        marker = warning(warning_only)
        enabled = config(close_enabled=True)
        current = snapshot(
            updated_at=marker["created_at"],
            labels=["stale"],
            warning=marker,
            latest_comment_id=marker["comment_id"],
        )

        decision = stale.decide(current, enabled, NOW)

        self.assertEqual(decision["action"], "warn")
        self.assertEqual(decision["reason"], "closure-policy-changed")

    def test_post_warning_activity_one_second_later_resets(self) -> None:
        configuration = config(close_enabled=True)
        marker = warning(configuration)
        current = snapshot(
            updated_at="2026-09-09T12:00:01Z",
            labels=["stale"],
            warning=marker,
            latest_comment_id=marker["comment_id"],
        )

        decision = stale.decide(current, configuration, NOW)

        self.assertEqual(decision["action"], "reset")
        self.assertEqual(decision["reason"], "activity-after-warning")

    def test_same_second_later_comment_resets_by_comment_id(self) -> None:
        configuration = config(close_enabled=True)
        marker = warning(configuration)
        current = snapshot(
            updated_at=marker["created_at"],
            labels=["stale"],
            warning=marker,
            latest_comment_id=int(marker["comment_id"]) + 1,
        )

        self.assertEqual(stale.decide(current, configuration, NOW)["action"], "reset")

    def test_same_second_head_change_resets_by_marker_fingerprint(self) -> None:
        configuration = config(close_enabled=True)
        marker = warning(configuration)
        current = snapshot(
            updated_at=marker["created_at"],
            head_sha="c" * 40,
            labels=["stale"],
            warning=marker,
            latest_comment_id=marker["comment_id"],
        )

        self.assertEqual(stale.decide(current, configuration, NOW)["action"], "reset")

    def test_exemptions_cover_labels_bots_drafts_users_and_requested_teams(self) -> None:
        cases = [
            snapshot(labels=["area:security"]),
            snapshot(author={"login": "dependabot[bot]", "type": "Bot"}),
            snapshot(draft=True),
            snapshot(assignees=["release-manager"]),
            snapshot(requested_review_users=["release-manager"]),
            snapshot(requested_review_teams=["security-reviewers"]),
        ]
        configuration = config(
            exempt_users=["release-manager"],
            exempt_review_teams=["security-reviewers"],
        )

        for current in cases:
            with self.subTest(current=current):
                decision = stale.decide(current, configuration, NOW)
                self.assertEqual(decision["action"], "exempt")

    def test_new_exemption_clears_existing_lifecycle_labels(self) -> None:
        current = snapshot(labels=["stale", "security"])

        decision = stale.decide(current, config(), NOW)

        self.assertEqual(decision["action"], "reset")
        self.assertEqual(decision["reason"], "exempt")

    def test_reopened_item_clears_both_managed_labels(self) -> None:
        configuration = config(closed_label="closed-stale")
        current = snapshot(labels=["stale", "closed-stale"])

        decision = stale.decide(current, configuration, NOW)

        self.assertEqual(decision["action"], "reset")
        self.assertEqual(decision["reason"], "reopened")
        self.assertEqual(
            stale.managed_labels_present(current, configuration),
            ["stale", "closed-stale"],
        )

    def test_marker_requires_exact_bot_and_unquoted_final_line(self) -> None:
        configuration = config(close_enabled=True)
        body = stale.warning_body("", configuration, "a" * 40)
        base = {
            "id": 50,
            "body": body,
            "created_at": "2026-09-09T12:00:00Z",
            "updated_at": "2026-09-09T12:00:00Z",
            "user": {"login": "github-actions[bot]", "type": "Bot"},
        }
        self.assertIsNotNone(stale.trusted_warning([base]))
        unrelated = dict(base, user={"login": "other[bot]", "type": "Bot"})
        quoted = dict(base, body=body.replace(stale.MARKER_PREFIX, "> " + stale.MARKER_PREFIX))
        trailing = dict(base, body=body + "\nextra")
        duplicate = dict(base, body=body + "\n" + body.splitlines()[-1])
        for comment in (unrelated, quoted, trailing, duplicate):
            self.assertIsNone(stale.trusted_warning([comment]))

    def test_empty_closed_label_is_supported(self) -> None:
        configuration = stale.configuration_from_arguments(plan_arguments())
        self.assertEqual(configuration["closed_label"], "")
        self.assertEqual(
            stale.managed_labels_present(snapshot(labels=["stale"]), configuration),
            ["stale"],
        )

    def test_reserved_marker_is_rejected_in_custom_messages(self) -> None:
        with self.assertRaisesRegex(stale.ContractError, "reserved marker"):
            stale.configuration_from_arguments(
                plan_arguments(warning_message=stale.MARKER_PREFIX)
            )

    def test_custom_message_cannot_hide_the_visible_warning(self) -> None:
        configuration = config(warning_message="<!-- hide the warning")

        body = stale.warning_body(
            str(configuration["warning_message"]), configuration, "a" * 40
        )

        self.assertIn("&lt;!-- hide the warning", body)
        self.assertIn(stale.DEFAULT_WARNING_MESSAGE, body)
        self.assertEqual(body.count("<!--"), 1)

    def test_normalized_pull_request_binds_head_sha(self) -> None:
        normalized = stale.normalize_item(provider_item(), [], [], [])
        self.assertEqual(normalized["head_sha"], "a" * 40)
        with self.assertRaisesRegex(stale.ContractError, "head SHA"):
            stale.normalize_item(
                provider_item(head={"sha": "main"}), [], [], []
            )

    def test_plan_checksum_rejects_tampering(self) -> None:
        decision = stale.public_decision(stale.decide(snapshot(), config(), NOW))
        plan = stale.bind_plan(
            {
                "schema": stale.PLAN_SCHEMA,
                "status": "planned",
                "repository": "egohygiene/example",
                "evaluation_time": stale.format_timestamp(PLAN_TIME),
                "configuration": stale.public_configuration(config()),
                "counts": stale.plan_counts([decision]),
                "truncated": False,
                "decisions": [decision],
            }
        )
        stale.verify_plan(plan)
        plan["configuration"]["close_enabled"] = True
        with self.assertRaisesRegex(stale.ContractError, "checksum"):
            stale.verify_plan(plan)

    def test_future_evaluation_time_cannot_accelerate_planning(self) -> None:
        arguments = plan_arguments(evaluation_time="2999-01-01T00:00:00Z")
        with mock.patch.object(stale, "validate_managed_labels"):
            with self.assertRaisesRegex(stale.ContractError, "must not be in the future"):
                stale.create_plan(arguments)

    def test_live_plan_captures_time_after_provider_snapshots(self) -> None:
        events: list[str] = []

        def fetch_items(*_args: object) -> list[dict[str, object]]:
            events.append("items")
            return [provider_item(updated_at=stale.format_timestamp(PLAN_TIME))]

        def fetch_comments(*_args: object) -> list[object]:
            events.append("comments")
            return []

        def now() -> datetime:
            events.append("clock")
            return NOW

        arguments = plan_arguments(evaluation_time="")
        with (
            mock.patch.object(stale, "validate_managed_labels"),
            mock.patch.object(stale, "fetch_open_items", side_effect=fetch_items),
            mock.patch.object(stale, "fetch_comments", side_effect=fetch_comments),
            mock.patch.object(stale, "current_time", side_effect=now),
        ):
            plan = stale.create_plan(arguments)

        self.assertEqual(events, ["items", "comments", "clock"])
        self.assertEqual(plan["evaluation_time"], stale.format_timestamp(NOW))

    def test_apply_rejects_a_future_time_even_with_a_valid_checksum(self) -> None:
        configuration = config()
        plan = stale.bind_plan(
            {
                "schema": stale.PLAN_SCHEMA,
                "status": "planned",
                "repository": "egohygiene/example",
                "evaluation_time": "2999-01-01T00:00:00Z",
                "configuration": stale.public_configuration(configuration),
                "counts": stale.plan_counts([]),
                "truncated": False,
                "decisions": [],
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "plan.json"
            path.write_text(json.dumps(plan), encoding="utf-8")
            arguments = plan_arguments()
            arguments.plan = path
            arguments.expected_plan_sha256 = plan["plan_sha256"]
            with self.assertRaisesRegex(stale.ContractError, "must not be in the future"):
                stale.apply_plan(arguments)

    def test_maximum_items_caps_actions_not_active_or_exempt_items(self) -> None:
        items = [
            provider_item(1, updated_at="2026-09-15T11:00:00Z"),
            provider_item(2, labels=[{"name": "security"}]),
            provider_item(3),
            provider_item(4),
        ]
        arguments = plan_arguments(maximum_items="1")
        with (
            mock.patch.object(stale, "validate_managed_labels"),
            mock.patch.object(stale, "fetch_open_items", return_value=items),
            mock.patch.object(stale, "fetch_comments", return_value=[]),
        ):
            plan = stale.create_plan(arguments)

        self.assertTrue(plan["truncated"])
        self.assertEqual(plan["counts"]["candidate"], 1)
        self.assertEqual([item["number"] for item in plan["decisions"]], [1, 2, 3])
        self.assertNotIn("warning_message", plan["configuration"])
        self.assertNotIn("comment", plan["decisions"][-1])

    def test_ordinary_issues_are_fetched_only_when_explicitly_enabled(self) -> None:
        with (
            mock.patch.object(stale, "fetch_bounded_pull_requests", return_value=[]),
            mock.patch.object(stale, "fetch_bounded_issues", return_value=[]) as issues,
        ):
            stale.fetch_open_items("egohygiene/example", False)
            issues.assert_not_called()
            stale.fetch_open_items("egohygiene/example", True)
            self.assertEqual(issues.call_count, 2)
            issues.assert_called_with("egohygiene/example")

    def test_open_item_scan_rejects_duplicates_and_identity_drift(self) -> None:
        duplicate = [provider_item(1), provider_item(1)]
        with (
            mock.patch.object(
                stale, "fetch_bounded_pull_requests", return_value=duplicate
            ),
            mock.patch.object(stale, "fetch_bounded_issues", return_value=[]),
        ):
            with self.assertRaisesRegex(stale.ContractError, "duplicate"):
                stale.fetch_open_items("egohygiene/example", False)

        with (
            mock.patch.object(
                stale,
                "fetch_bounded_pull_requests",
                side_effect=[[provider_item(1)], [provider_item(1), provider_item(2)]],
            ),
            mock.patch.object(stale, "fetch_bounded_issues", return_value=[]),
        ):
            with self.assertRaisesRegex(stale.ContractError, "changed"):
                stale.fetch_open_items("egohygiene/example", False)

    def test_incomplete_issue_search_fails_closed(self) -> None:
        for incomplete in (True, None, "false"):
            with self.subTest(incomplete=incomplete):
                response = {
                    "total_count": 0,
                    "items": [],
                }
                if incomplete is not None:
                    response["incomplete_results"] = incomplete
                with mock.patch.object(stale, "gh_api", return_value=response):
                    with self.assertRaisesRegex(
                        stale.ContractError, "incomplete results"
                    ):
                        stale.fetch_bounded_issues("egohygiene/example")

    def test_repository_relative_paths_reject_symlink_components(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            outside = Path(temporary) / "outside"
            root.mkdir()
            outside.mkdir()
            (root / ".relay").symlink_to(outside, target_is_directory=True)
            with mock.patch.dict(
                stale.os.environ, {"GITHUB_WORKSPACE": str(root)}, clear=False
            ):
                with self.assertRaisesRegex(stale.ContractError, "symbolic link"):
                    stale.validate_relative_path(".relay/result.json", "output")

    def test_apply_preflights_every_item_before_first_write(self) -> None:
        configuration = config()
        first_raw = stale.decide(snapshot(number=1), configuration, NOW)
        second_raw = stale.decide(snapshot(number=2), configuration, NOW)
        first = stale.public_decision(first_raw)
        second = stale.public_decision(second_raw)
        decisions = [first, second]
        plan = stale.bind_plan(
            {
                "schema": stale.PLAN_SCHEMA,
                "status": "planned",
                "repository": "egohygiene/example",
                "evaluation_time": stale.format_timestamp(PLAN_TIME),
                "configuration": stale.public_configuration(configuration),
                "counts": stale.plan_counts(decisions),
                "truncated": False,
                "decisions": decisions,
            }
        )
        changed = dict(second["snapshot"], head_sha="c" * 40)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "plan.json"
            path.write_text(json.dumps(plan), encoding="utf-8")
            arguments = plan_arguments()
            arguments.plan = path
            arguments.expected_plan_sha256 = plan["plan_sha256"]
            with (
                mock.patch.object(stale, "authorize_apply"),
                mock.patch.object(stale, "validate_managed_labels"),
                mock.patch.object(
                    stale,
                    "live_snapshot",
                    side_effect=[first["snapshot"], changed],
                ),
                mock.patch.object(stale, "apply_decision") as apply_decision,
            ):
                with self.assertRaisesRegex(stale.ContractError, "changed after planning"):
                    stale.apply_plan(arguments)

        apply_decision.assert_not_called()

    def test_apply_accepts_exact_nondefault_configuration_and_message_hashes(self) -> None:
        arguments = plan_arguments(
            inactivity_days="45",
            warning_days="9",
            stale_label="waiting",
            closed_label="archived",
            exempt_labels="hold,security",
            exempt_users="release-manager",
            exempt_review_teams="maintainers",
            exempt_drafts="false",
            exempt_bots="false",
            process_issues="true",
            close_enabled="true",
            maximum_items="12",
            warning_message="A custom warning.",
            close_message="A custom close note.",
        )
        configuration = stale.configuration_from_arguments(arguments)
        current = snapshot(number=8)
        raw_decision = stale.decide(current, configuration, NOW)
        decision = stale.public_decision(raw_decision)
        plan = stale.bind_plan(
            {
                "schema": stale.PLAN_SCHEMA,
                "status": "planned",
                "repository": "egohygiene/example",
                "evaluation_time": stale.format_timestamp(PLAN_TIME),
                "configuration": stale.public_configuration(configuration),
                "counts": stale.plan_counts([decision]),
                "truncated": False,
                "decisions": [decision],
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "plan.json"
            path.write_text(json.dumps(plan), encoding="utf-8")
            arguments.plan = path
            arguments.expected_plan_sha256 = plan["plan_sha256"]
            with (
                mock.patch.object(stale, "authorize_apply"),
                mock.patch.object(stale, "validate_managed_labels"),
                mock.patch.object(
                    stale, "live_snapshot", return_value=raw_decision["snapshot"]
                ),
                mock.patch.object(stale, "apply_decision") as apply_decision,
            ):
                result = stale.apply_plan(arguments)

        self.assertEqual(result["status"], "applied")
        apply_decision.assert_called_once_with(
            "egohygiene/example", decision, configuration
        )

    def test_live_snapshot_reads_pull_state_last_without_issues_api(self) -> None:
        pull = provider_item()
        pull.pop("_relay_kind")
        with mock.patch.object(
            stale,
            "gh_api",
            side_effect=[[], pull],
        ) as api:
            result = stale.live_snapshot(
                "egohygiene/example",
                {"number": 14, "kind": "pull_request"},
                config(),
            )

        self.assertEqual(result["number"], 14)
        self.assertIn("/comments?", api.call_args_list[0].args[1])
        self.assertTrue(api.call_args_list[1].args[1].endswith("/pulls/14"))
        self.assertFalse(
            any(call.args[1].endswith("/issues/14") for call in api.call_args_list)
        )

    def test_live_snapshot_reads_issue_state_last_when_enabled(self) -> None:
        issue = provider_item()
        issue.pop("_relay_kind")
        issue.pop("draft")
        issue.pop("head")
        with mock.patch.object(
            stale,
            "gh_api",
            side_effect=[[], issue],
        ) as api:
            result = stale.live_snapshot(
                "egohygiene/example",
                {"number": 14, "kind": "issue"},
                config(process_issues=True),
            )

        self.assertEqual(result["kind"], "issue")
        self.assertIn("/comments?", api.call_args_list[0].args[1])
        self.assertTrue(api.call_args_list[1].args[1].endswith("/issues/14"))

    def test_close_is_first_mutation_then_optional_metadata(self) -> None:
        configuration = config(
            close_enabled=True,
            closed_label="closed-stale",
            close_message="Closing this item.",
        )
        marker = warning(configuration)
        current = snapshot(
            updated_at=marker["created_at"],
            labels=["stale"],
            warning=marker,
            latest_comment_id=marker["comment_id"],
        )
        decision = stale.decide(current, configuration, NOW)

        with mock.patch.object(stale, "gh_api") as api:
            stale.apply_decision("egohygiene/example", decision, configuration)

        calls = api.call_args_list
        self.assertEqual(calls[0].args[0], "PATCH")
        self.assertEqual(calls[0].args[2], {"state": "closed"})
        self.assertEqual(calls[1].args[0], "POST")
        self.assertIn("/labels", calls[1].args[1])
        self.assertEqual(calls[2].args[0], "POST")
        self.assertIn("Reopen this item", calls[2].args[2]["body"])
        self.assertNotIn("<!--", calls[2].args[2]["body"].split(stale.CLOSED_MARKER)[0])
        self.assertTrue(calls[2].args[2]["body"].endswith(stale.CLOSED_MARKER))


if __name__ == "__main__":
    unittest.main()
