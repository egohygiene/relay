# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Bound caller declarations before native ADR validation; no target acquisition."""

import json
import os
import re
import sys


EXTERNAL_DECISION = re.compile(r"[a-z0-9.-]+/[a-z0-9.-]+#ADR-[0-9]{3,4}")
MAX_EXTERNAL_DECISIONS = 64
MAX_EXTERNAL_INPUT_BYTES = 8192


def external_decisions(raw):
    """Normalize a bounded JSON array of explicitly declared external keys."""
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_EXTERNAL_INPUT_BYTES:
        raise ValueError("external-decisions")
    try:
        values = json.loads(raw)
    except (ValueError, RecursionError):
        raise ValueError("external-decisions") from None
    if (not isinstance(values, list) or len(values) > MAX_EXTERNAL_DECISIONS
            or any(not isinstance(value, str) or len(value) > 240
                   or not EXTERNAL_DECISION.fullmatch(value) for value in values)
            or len(set(values)) != len(values)):
        raise ValueError("external-decisions")
    return sorted(values)


def selection(raw, collect_adrs):
    values = external_decisions(raw)
    if values and collect_adrs != "true":
        raise ValueError("external-decisions")
    return values


if __name__ == "__main__":
    try:
        selection(os.environ.get("INPUT_ADR_KNOWN_EXTERNAL_DECISIONS", "[]"),
                  os.environ.get("INPUT_COLLECT_ADRS", "false"))
    except ValueError:
        print("ADR external decision inputs denied", file=sys.stderr)
        raise SystemExit(2) from None
