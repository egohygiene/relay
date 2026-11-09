#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Read a closed non-executable Work/Health capture plan before acquisition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

SCHEMA = "egohygiene.relay.source-capture-plan/v1"
PRODUCERS = {"osv", "megalinter", "scorecard"}


def require(value):
    if not value:
        raise ValueError("Source capture plan denied")


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result)
        result[key] = value
    return result


def relative(value):
    require(isinstance(value, str) and 1 <= len(value) <= 240
        and re.fullmatch(r"[A-Za-z0-9._/-]+", value)
        and not value.startswith("/") and not value.endswith("/")
        and all(part not in {"", ".", "..", ".git"} for part in value.split("/")))
    return value


def age(value):
    require(type(value) is int and 1 <= value <= 2678400)
    return value


def apply(args):
    path = args.capture_plan.absolute()
    require(not any(part.is_symlink() for part in (path, *path.parents))
        and path.is_file() and path.stat().st_size <= 65536)
    content = path.read_bytes()
    plan = json.loads(content, object_pairs_hook=pairs, parse_constant=lambda _value: require(False))
    require(isinstance(plan, dict) and set(plan) <= {"schema", "work", "health"}
        and plan.get("schema") == SCHEMA and bool(set(plan) & {"work", "health"}))
    root = getattr(args, "capture_root", None) or args.repository_root
    root = root.absolute()
    require(root.is_dir() and not any(part.is_symlink() for part in (root, *root.parents)))
    if "work" in plan:
        work = plan["work"]
        require(isinstance(work, dict) and set(work) == {"provider_evidence", "maximum_age_seconds"}
            and not args.collect_work and args.work_capture is None and args.work_maximum_age_seconds == 86400)
        args.collect_work = True
        args.work_capture = root / relative(work["provider_evidence"])
        args.work_maximum_age_seconds = age(work["maximum_age_seconds"])
    if "health" in plan:
        health = plan["health"]
        require(isinstance(health, dict) and set(health) == {
            "inventory", "expected_reports", "reports", "check_runs", "maximum_age_seconds"}
            and not args.collect_health and not args.health_expect_report and not args.health_report
            and args.health_check_runs is None and args.health_check_runs_observed_at is None
            and args.health_check_runs_state == "not-requested" and args.health_inventory == "partial"
            and args.health_maximum_age_seconds == 86400)
        require(health["inventory"] in {"partial", "complete", "not-applicable"})
        expected, reports, checks = health["expected_reports"], health["reports"], health["check_runs"]
        require(isinstance(expected, list) and len(expected) <= 3 and all(name in PRODUCERS for name in expected)
            and len(set(expected)) == len(expected) and isinstance(reports, dict) and set(reports) <= set(expected))
        require(isinstance(checks, dict) and checks.get("state") in {"not-requested", "observed", "unavailable", "failed"})
        require(set(checks) == ({"state", "path", "observed_at"} if checks["state"] == "observed" else {"state"}))
        if checks["state"] == "observed":
            require(isinstance(checks["observed_at"], str)
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", checks["observed_at"]))
            args.health_check_runs = root / relative(checks["path"])
            args.health_check_runs_observed_at = checks["observed_at"]
        if health["inventory"] == "not-applicable":
            require(not expected and not reports and checks["state"] == "not-requested")
        args.collect_health = True
        args.health_inventory = health["inventory"]
        args.health_expect_report = sorted(expected)
        args.health_report = [name + "=" + str(root / relative(filename)) for name, filename in sorted(reports.items())]
        args.health_check_runs_state = checks["state"]
        args.health_maximum_age_seconds = age(health["maximum_age_seconds"])
    return hashlib.sha256(content).hexdigest()
