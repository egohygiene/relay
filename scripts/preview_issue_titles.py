#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Collect and preview one repository's issue titles; no provider writes."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
import html
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "relay_title_runtime", ROOT / "actions/repository-intelligence/scripts/collect_repository_roadmap.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
LOCK = ROOT / "catalog/issue-title-preview.v1.lock.json"
PREFIX = "egohygiene.relay.issue-title-"
MAX_PAGES = 20
PAGE_SIZE = 100
MAX_ISSUES = MAX_PAGES * PAGE_SIZE
STATUSES = ("unchanged", "proposed", "needs-review", "needs-classification", "blocked", "unavailable")


def check(value: object, name: str) -> None:
    schema = base.load_json(base.read_file(ROOT / f"schemas/issue-title-{name}.v1.schema.json"))
    if not jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).is_valid(value):
        base.fail("INPUT")


def selection(repository: str) -> dict:
    lock = base.load_json(base.read_file(LOCK))
    if repository not in lock["allowed_repositories"]:
        base.fail("REPOSITORY")
    return lock


def validate_snapshot(snapshot: dict, repository: str) -> None:
    check(snapshot, "snapshot")
    selection(repository)
    if snapshot["repository"]["name"] != repository:
        base.fail("REPOSITORY")
    if base.utc(snapshot["finished_at"]) < base.utc(snapshot["observed_at"]):
        base.fail("INPUT")
    issues = snapshot["issues"]
    if len({row["id"] for row in issues}) != len(issues) or len({row["number"] for row in issues}) != len(issues):
        base.fail("INPUT")
    if len({label["name"] for label in snapshot["labels"]}) != len(snapshot["labels"]):
        base.fail("INPUT")
    for row in issues:
        if row["url"] != f"https://github.com/{repository}/issues/{row['number']}":
            base.fail("REPOSITORY")
    for domain in ("issues", "labels"):
        coverage = snapshot["coverage"][domain]
        pages = coverage["pages"]
        if [page["number"] for page in pages] != list(range(1, len(pages) + 1)):
            base.fail("INPUT")
        count = len(snapshot[domain]) + (snapshot["excluded_pull_requests"] if domain == "issues" else 0)
        if sum(page["records"] for page in pages) != count:
            base.fail("INPUT")
        if coverage["status"] == "complete":
            if (not pages or pages[-1]["records"] >= PAGE_SIZE or coverage["error"] is not None
                    or any(page["records"] != PAGE_SIZE for page in pages[:-1])):
                base.fail("INPUT")
        elif not coverage["error"]:
            base.fail("INPUT")
    if snapshot["coverage"]["labels"]["status"] == "complete":
        inventory = {label["name"] for label in snapshot["labels"]}
        # Separate REST reads are not atomic; retain this as a coverage conflict.
        if any(set(row["labels"]) - inventory for row in issues if row["complete"]):
            base.fail("INVENTORY_CHANGED")


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def public_get(path: str) -> object:
    """Fixed public GitHub origin, GET only, no credentials or redirect following."""
    request = Request("https://api.github.com" + path, method="GET", headers={
        "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "relay-issue-title-preview"})
    try:
        with build_opener(NoRedirects).open(request, timeout=20) as response:
            raw = response.read(base.MAX_OUTPUT + 1)
        if len(raw) > base.MAX_OUTPUT:
            base.fail("RESPONSE_LIMIT")
        return json.loads(raw, object_pairs_hook=base.unique_pairs,
                          parse_constant=lambda _: base.fail("INPUT"))
    except HTTPError as error:
        base.fail(f"HTTP_{error.code}")
    except (URLError, TimeoutError, OSError, ValueError, UnicodeError):
        base.fail("PROVIDER_UNAVAILABLE")


def collect(repository: str, *, get=public_get, now=None) -> dict:
    """Collect all bounded pages, retaining incomplete reads as explicit evidence."""
    selection(repository)
    clock = now or (lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    observed = clock()
    metadata = get(f"/repos/{repository}")
    if (not isinstance(metadata, dict) or metadata.get("full_name") != repository
            or metadata.get("private") is not False or type(metadata.get("id")) is not int):
        base.fail("REPOSITORY")
    result = {"schema": PREFIX + "snapshot/v1", "kind": "github-public",
              "repository": {"name": repository, "id": metadata["id"], "visibility": "public"},
              "observed_at": observed, "finished_at": observed, "coverage": {},
              "issues": [], "labels": [], "excluded_pull_requests": 0}
    for domain in ("issues", "labels"):
        coverage = {"status": "unavailable", "pages": [], "error": None}
        result["coverage"][domain] = coverage
        seen = set()
        for number in range(1, MAX_PAGES + 1):
            query = "state=open&sort=created&direction=asc&" if domain == "issues" else ""
            try:
                rows = get(f"/repos/{repository}/{domain}?{query}per_page={PAGE_SIZE}&page={number}")
                if not isinstance(rows, list) or len(rows) > PAGE_SIZE:
                    base.fail("INVALID_PAGE")
                additions, excluded, identities = [], 0, set()
                for row in rows:
                    if not isinstance(row, dict):
                        base.fail("INVALID_PAGE")
                    identity = row.get("id") if domain == "issues" else row.get("name")
                    if identity is None or identity in seen or identity in identities:
                        base.fail("DUPLICATE_RECORD")
                    identities.add(identity)
                    if domain == "issues":
                        if "pull_request" in row:
                            excluded += 1
                            continue
                        if row.get("state") != "open" or not isinstance(row.get("labels"), list):
                            base.fail("INVALID_PAGE")
                        item = {key: row[key] for key in ("id", "number", "title", "updated_at")}
                        item.update(url=row["html_url"], complete=True,
                                    labels=[label["name"] for label in row["labels"]])
                    else:
                        item = {"name": row["name"], "color": row["color"],
                                "description": row.get("description") or ""}
                    # Validate before accepting any part of this page.
                    schema = base.load_json(base.read_file(ROOT / "schemas/issue-title-snapshot.v1.schema.json"))
                    fragment = schema["properties"][domain]["items"]
                    jsonschema.Draft202012Validator(fragment, format_checker=jsonschema.FormatChecker()).validate(item)
                    additions.append(item)
                result[domain].extend(additions)
                result["excluded_pull_requests"] += excluded
                seen.update(identities)
                coverage["pages"].append({"number": number, "records": len(rows),
                                          "sha256": base.digest(base.json_bytes(rows))})
                coverage["status"] = "partial"
                if len(rows) < PAGE_SIZE:
                    coverage["status"] = "complete"
                    break
            except (base.CollectorError, KeyError, TypeError, jsonschema.ValidationError):
                error = sys.exception()
                coverage["error"] = str(error) if isinstance(error, base.CollectorError) else "INVALID_PAGE"
                break
        if coverage["status"] != "complete" and coverage["error"] is None:
            coverage["error"] = "PAGE_LIMIT"
    result["issues"].sort(key=lambda row: row["number"])
    result["labels"].sort(key=lambda row: row["name"])
    result["finished_at"] = clock()
    validate_snapshot(result, repository)
    return result


class Egolint:
    """Compose the actual source-built CLI; no title mapping or parsing here."""

    def __init__(self, runtime: Path):
        self.runtime = runtime
        self.lock, self.receipt = base.runtime_files(runtime, lock_path=LOCK)
        self.schemas = {kind: base.load_json(base.read_file(
            runtime / f"egolint/schemas/issue-title-{kind}.schema.json"))
            for kind in ("snapshot", "report", "proposal")}

    def call(self, arguments: list[str], kind: str) -> dict:
        raw = base.run([str(self.runtime / "egolint-bin"), "issue-title", *arguments], allowed=(0, 1, 2))
        if not raw:
            base.fail("INVALID_REVIEW" if kind == "proposal" else "RUNTIME")
        result = base.load_json(raw)
        if not jsonschema.Draft202012Validator(self.schemas[kind]).is_valid(result):
            base.fail("RUNTIME")
        if result["contract"] != self.lock["contract"]:
            base.fail("PIN")
        return result

    def validate(self, snapshot: dict) -> dict:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "snapshot.json"
            source.write_bytes(base.json_bytes(snapshot))
            return self.call(["validate", "--input", str(source)], "report")

    def format(self, kind: str, subject: str) -> dict:
        return self.call(["format", "--type", kind, "--reviewed-subject=" + subject], "proposal")


def report_summary(report: dict) -> dict:
    return {"status": report["status"], "type": report.get("type"), "message": report["message"],
            "report_sha256": base.digest(base.json_bytes(report))}


def preview(snapshot: dict, reviews: dict, repository: str, runtime: Path) -> dict:
    validate_snapshot(snapshot, repository)
    check(reviews, "reviews")
    lock = selection(repository)
    snapshot_digest = base.digest(base.json_bytes(snapshot))
    if reviews["repository"] != repository or reviews["snapshot_sha256"] != snapshot_digest:
        base.fail("STALE_REVIEW")
    by_number = {row["number"]: row for row in reviews["issues"]}
    if len(by_number) != len(reviews["issues"]):
        base.fail("INPUT")
    current_numbers = {row["number"]: row["id"] for row in snapshot["issues"]}
    if any(current_numbers.get(number) != row["id"] for number, row in by_number.items()):
        base.fail("STALE_REVIEW")
    plan = {"schema": PREFIX + "plan/v1", "mode": "observe", "mutation": "forbidden",
            "repository": deepcopy(snapshot["repository"]), "kind": snapshot["kind"],
            "observed_at": snapshot["observed_at"], "finished_at": snapshot["finished_at"],
            "coverage": deepcopy(snapshot["coverage"]), "excluded_pull_requests": snapshot["excluded_pull_requests"],
            "status": "complete", "diagnostics": [], "rows": [], "summary": {},
            "provenance": {"lock_sha256": base.digest(base.read_file(LOCK)),
                           "adapter_sha256": base.digest(Path(__file__).read_bytes()),
                           "shared_runtime_sha256": base.digest(Path(base.__file__).read_bytes()),
                           "snapshot_sha256": snapshot_digest,
                           "reviews_sha256": base.digest(base.json_bytes(reviews)),
                           "selection": {"contract": lock["contract"], "egolint": {
                               key: lock["sources"]["egolint"][key]
                               for key in ("repository", "revision", "tree")}}, "runtime": None}}
    try:
        engine = Egolint(runtime)
        plan["provenance"]["runtime"] = engine.receipt
    except (base.CollectorError, OSError, ValueError, KeyError):
        engine = None
        plan["diagnostics"].append("RUNTIME_UNAVAILABLE_OR_PIN_MISMATCH")
    inventory = {label["name"] for label in snapshot["labels"]}
    inventory_complete = snapshot["coverage"]["labels"]["status"] == "complete"
    for issue in sorted(snapshot["issues"], key=lambda item: item["number"]):
        current = {"schema_version": 1, **{key: deepcopy(issue[key]) for key in ("title", "labels", "complete")}}
        row = {**{key: issue[key] for key in ("id", "number", "url", "updated_at")},
               "current": current, "validation": None, "review": by_number.get(issue["number"]),
               "proposal": None, "status": "unavailable", "reasons": []}
        try:
            if engine is None:
                base.fail("RUNTIME_UNAVAILABLE_OR_PIN_MISMATCH")
            report = engine.validate(current)
            row["validation"] = report_summary(report)
            status = report["status"]
            if status == "unavailable":
                row["reasons"].append("INCOMPLETE_ISSUE")
            elif row["review"] is None:
                row["status"] = ("unchanged" if status == "conformant" else
                                 "needs-review" if status == "nonconformant" else "needs-classification")
                if status != "conformant":
                    row["reasons"].append("REVIEWED_TYPE_AND_SUBJECT_REQUIRED")
            else:
                review = row["review"]
                proposal = engine.format(review["type"], review["subject"])
                intended = {"schema_version": 1, "complete": True, "title": proposal["title"],
                            "labels": [proposal["required_label"]]}
                formatted = engine.validate(intended)
                if formatted["status"] != "conformant" or formatted.get("type") != review["type"]:
                    base.fail("RUNTIME")
                # Preserve every provider label; label migration has separate authority.
                proposed = {**deepcopy(current), "title": proposal["title"]}
                proposed_report = engine.validate(proposed)
                label_status = ("present" if proposal["required_label"] in inventory else
                                "missing" if inventory_complete else "unavailable")
                row["proposal"] = {"snapshot": proposed, "required_label": proposal["required_label"],
                                   "provider_label": label_status, "format_validation": report_summary(formatted),
                                   "validation": report_summary(proposed_report),
                                   "formatter_sha256": base.digest(base.json_bytes(proposal))}
                if label_status != "present":
                    row["reasons"].append("PROVIDER_LABEL_" + label_status.upper())
                if proposed_report["status"] != "conformant":
                    row["reasons"].append("CLASSIFICATION_REVIEW_REQUIRED")
                row["status"] = ("blocked" if row["reasons"] else
                                 "unchanged" if proposed["title"] == current["title"] else "proposed")
        except (base.CollectorError, OSError, ValueError, KeyError):
            error = sys.exception()
            row["proposal"] = None
            row["status"] = "unavailable"
            row["reasons"].append(str(error) if isinstance(error, base.CollectorError) else "RUNTIME")
        plan["rows"].append(row)
    counts = Counter(row["status"] for row in plan["rows"])
    plan["summary"] = {status: counts[status] for status in STATUSES}
    if engine is None or counts["unavailable"]:
        plan["status"] = "unavailable" if not plan["rows"] or counts["unavailable"] == len(plan["rows"]) else "partial"
    if any(coverage["status"] != "complete" for coverage in snapshot["coverage"].values()):
        plan["diagnostics"].append("INCOMPLETE_INVENTORY")
        if plan["status"] == "complete":
            plan["status"] = "partial"
    check(plan, "plan")
    return plan


def empty_reviews(snapshot: dict) -> dict:
    return {"schema": PREFIX + "reviews/v1", "repository": snapshot["repository"]["name"],
            "snapshot_sha256": base.digest(base.json_bytes(snapshot)), "issues": []}


def markdown(plan: dict) -> str:
    def cell(value):
        # Repository titles are untrusted Markdown, never executable report markup.
        text = html.escape(str(value), quote=True)
        for character in "\\`*_{}[]()#+-.!|":
            text = text.replace(character, "\\" + character)
        return text.replace("\n", " ").replace("\r", " ")

    lines = ["# Issue-title preview", "", f"Repository: `{plan['repository']['name']}`. "
             f"Observed {plan['observed_at']} through {plan['finished_at']}.", "",
             f"Coverage: **{plan['status']}**. Candidate contract; observe only; provider writes forbidden.", "",
             "Complete means the recorded page traversal completed, not that the backlog conforms or the reads were atomic.", "",
             "; ".join(f"{name}: {count}" for name, count in plan["summary"].items()) + ".", "",
             "| Issue | Current title | Proposed title | Result | Reasons |",
             "| --- | --- | --- | --- | --- |"]
    for row in plan["rows"]:
        proposed = row["proposal"]["snapshot"]["title"] if row["proposal"] else "—"
        lines.append(f"| [#{row['number']}]({row['url']}) | {cell(row['current']['title'])} | "
                     f"{cell(proposed)} | {row['status']} | {cell(', '.join(row['reasons']) or '—')} |")
    lines += ["", "Reviewed proposals retain the entire observed label set. A conformant formatted title does not "
              "prove provider-label availability, issue classification, adoption, or authorization to apply.", "",
              "Diagnostics: " + cell(", ".join(plan["diagnostics"]) or "none") + ".", "",
              "Next: review classification and labels, then implement a separately approved apply/recovery checkpoint "
              "with current-state comparison, conflicts, receipts, rollback and no-op repeat.", ""]
    return "\n".join(lines)


def write_new(path: Path, data: bytes) -> None:
    path = base.safe_path(path)
    if len(data) > base.MAX_OUTPUT:
        base.fail("INPUT")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def write_plan(directory: Path, plan: dict) -> None:
    directory = base.safe_path(directory)
    if directory.exists():
        base.fail("PATH")
    directory.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory.parent) as temporary:
        staged = Path(temporary) / "preview"
        write_new(staged / "plan.json", base.json_bytes(plan))
        write_new(staged / "preview.md", markdown(plan).encode())
        staged.rename(directory)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = result.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", allow_abbrev=False)
    prepare.add_argument("--egolint", type=Path, required=True)
    prepare.add_argument("--cargo", type=Path, default=Path("cargo"))
    prepare.add_argument("--output", type=Path, required=True)
    capture = commands.add_parser("collect", allow_abbrev=False)
    capture.add_argument("--repository", required=True)
    capture.add_argument("--output", type=Path, required=True)
    render = commands.add_parser("preview", allow_abbrev=False)
    render.add_argument("--repository", required=True)
    render.add_argument("--snapshot", type=Path, required=True)
    render.add_argument("--reviews", type=Path)
    render.add_argument("--runtime", type=Path, required=True)
    render.add_argument("--output-dir", type=Path, required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "prepare":
            base.prepare(args, lock_path=LOCK)
            return 0
        if args.command == "collect":
            snapshot = collect(args.repository)
            write_new(args.output, base.json_bytes(snapshot))
            return 0 if all(item["status"] == "complete" for item in snapshot["coverage"].values()) else 2
        snapshot = base.load_json(base.read_file(args.snapshot, base.MAX_OUTPUT))
        reviews = base.load_json(base.read_file(args.reviews)) if args.reviews else empty_reviews(snapshot)
        plan = preview(snapshot, reviews, args.repository, args.runtime)
        write_plan(args.output_dir, plan)
        print("Issue-title preview retained; provider writes forbidden.")
        return 0 if plan["status"] == "complete" else 2
    except (base.CollectorError, OSError, ValueError, KeyError, TypeError, RecursionError):
        error = sys.exception()
        code = str(error) if isinstance(error, base.CollectorError) else "INPUT"
        print("issue-title preview: " + code, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
