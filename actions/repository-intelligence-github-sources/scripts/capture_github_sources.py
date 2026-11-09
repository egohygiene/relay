#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Capture bounded public GitHub metadata for the existing Intelligence adapters.

No provider response, exception, URL from provider data, or token is logged.
This producer does not normalize graphs, run consumer code, upload, or publish.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


REPOSITORY = re.compile(r"egohygiene/(?:\.github|[a-z0-9][a-z0-9.-]*)")
SHA = re.compile(r"[0-9a-f]{40}")
SECRET = re.compile(r"(?i)(github_pat_|gh[pousr]_|(?:token|password|secret)\s*[:=]|[\w.+-]+@[\w.-]+\.[a-z]{2,}|/(?:home|Users|workspace|tmp)/)")
MAX_RESPONSE = 2 * 1024 * 1024
MAX_FILE = 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_REQUESTS = 128
OUTCOMES = {"complete", "rate_limited", "access_denied", "provider_unavailable", "collection_failed"}


class CaptureError(Exception):
    """Only fixed, public-safe failure codes may be retained."""


def require(value, code="INPUT"):
    if not value:
        raise CaptureError(code)


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def instant(value):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value), "PROVIDER")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def positive(value, maximum=9007199254740991):
    require(type(value) is int and 1 <= value <= maximum, "PROVIDER")
    return value


def text(value, limit, *, optional=False, filename=False):
    valid = (isinstance(value, str) and 1 <= len(value) <= limit and value == value.strip()
        and not any(ord(c) < 32 or ord(c) == 127 for c in value) and not SECRET.search(value))
    if filename:
        valid = valid and value not in {".", ".."} and "/" not in value and "\\" not in value
    if optional:
        return value if valid else None
    require(valid, "PROVIDER")
    return value


def encoded(value):
    content = (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()
    require(len(content) <= MAX_FILE, "BOUND")
    return content


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "PROVIDER")
        result[key] = value
    return result


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, target):
        return None


class Client:
    def __init__(self, repository, token):
        self.prefix = "/repos/" + repository
        self.token = token
        self.requests = 0
        self.bytes = 0
        self.deadline = time.monotonic() + 240
        # Respect the runtime's inherited HTTPS proxy and CA settings. Redirects
        # cannot send an Authorization header to another host or route.
        self.opener = build_opener(NoRedirect())

    def get(self, path, *, public_proof=False, admission=False):
        require(path.startswith(self.prefix) and not path.startswith("//"), "INPUT")
        # Reserve one request and up to fifteen seconds for final unauthenticated
        # public admission, even after another endpoint exhausts its budget.
        require(self.requests < MAX_REQUESTS - (0 if admission else 1)
            and time.monotonic() < self.deadline - (0 if admission else 15), "BOUND")
        self.requests += 1
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "egohygiene-relay-intelligence-public-capture"}
        if self.token and not public_proof:
            headers["Authorization"] = "Bearer " + self.token
        request = Request("https://api.github.com" + path, headers=headers)
        try:
            with self.opener.open(request, timeout=min(15, max(1, self.deadline - time.monotonic()))) as response:
                size = response.headers.get("Content-Length")
                if size is not None:
                    require(size.isdigit() and int(size) <= MAX_RESPONSE, "BOUND")
                raw = response.read(MAX_RESPONSE + 1)
                self.bytes += len(raw)
                require(len(raw) <= MAX_RESPONSE and self.bytes <= MAX_TOTAL, "BOUND")
                link = response.headers.get("Link", "")
                require(len(link) <= 8192, "PROVIDER")
        except HTTPError as error:
            # Never read or print provider error bodies/headers.
            if error.code == 429 or (error.code == 403 and error.headers.get("X-RateLimit-Remaining") == "0"):
                raise CaptureError("rate_limited") from None
            if error.code in {401, 403, 404}:
                raise CaptureError("access_denied") from None
            raise CaptureError("provider_unavailable") from None
        except (URLError, TimeoutError, OSError, http.client.HTTPException):
            raise CaptureError("provider_unavailable") from None
        try:
            value = json.loads(raw, object_pairs_hook=pairs,
                parse_constant=lambda _value: require(False, "PROVIDER"))
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise CaptureError("collection_failed") from None
        # Only the presence of a next page is used. Its URL is never followed;
        # every next request is rebuilt from the fixed endpoint and page number.
        return value, bool(re.search(r';\s*rel="next"(?:,|$)', link))

    def public_identity(self, repository, repository_id):
        value, _ = self.get(self.prefix, public_proof=True, admission=True)
        # Public visibility is established without credentials before reading
        # IDs or any source inventory. Repeat after collection before output.
        require(isinstance(value, dict) and value.get("private") is False
            and value.get("visibility") == "public", "PUBLIC_ADMISSION")
        require(value.get("full_name") == repository and value.get("id") == repository_id, "IDENTITY")


def paginate(client, endpoint, transform, maximum_pages, maximum_records, *, parameters=None, list_key=None, public_only=False):
    records, pages, exhausted, truncated, outcome, total, skipped = [], 0, False, False, "complete", None, False
    identities = set()
    for page in range(1, maximum_pages + 1):
        query = {**(parameters or {}), "per_page": 100, "page": page}
        try:
            value, has_next = client.get(endpoint + "?" + urlencode(query), public_proof=public_only)
            if list_key:
                require(isinstance(value, dict) and type(value.get("total_count")) is int
                    and value["total_count"] >= 0 and isinstance(value.get(list_key), list), "PROVIDER")
                total = max(total or 0, value["total_count"])
                items = value[list_key]
            else:
                items = value
            require(isinstance(items, list) and len(items) <= 100, "PROVIDER")
            require(total is None or total >= len(items), "PROVIDER")
            # The received page counts even when every item is ineligible.
            pages += 1
            for item in items:
                try:
                    result = transform(item)
                except CaptureError as error:
                    if str(error) in {"BOUND", "rate_limited", "access_denied", "provider_unavailable"}:
                        raise
                    skipped = True
                    continue
                if result is None:
                    continue
                identity = result.get("provider_id", result.get("id"))
                if identity in identities:
                    # Moving inventories can repeat records across pages. Never
                    # overwrite silently or call that a complete snapshot.
                    skipped = True
                    continue
                if len(records) >= maximum_records:
                    truncated = True
                    break
                identities.add(identity)
                records.append(result)
            if truncated:
                break
            if not has_next:
                exhausted = True
                break
        except CaptureError as error:
            outcome = str(error) if str(error) in OUTCOMES else "collection_failed"
            if str(error) == "BOUND":
                truncated = bool(pages)
            break
    if pages and not exhausted:
        truncated = True
    return {"records": records, "pages": pages, "exhausted": exhausted, "truncated": truncated,
        "outcome": outcome, "total": total, "skipped": skipped, "captured_at": now() if pages else None}


def work_record(item, kind, include_titles):
    require(isinstance(item, dict), "PROVIDER")
    # The mixed Issues endpoint includes PRs. Do not inspect a PR's identity or
    # title while preparing issue records; the dedicated PR endpoint owns them.
    if kind == "issue" and "pull_request" in item:
        return None
    require(item.get("state") in {"open", "closed"}, "PROVIDER")
    created, updated, closed = item.get("created_at"), item.get("updated_at"), item.get("closed_at")
    require(instant(created) <= instant(updated) and (closed is None or instant(created) <= instant(closed) <= instant(updated)), "PROVIDER")
    require((item["state"] == "open") == (closed is None), "PROVIDER")
    result = {"kind": kind, "visibility": "public", "number": positive(item.get("number"), 2147483647),
        "provider_id": str(positive(item.get("id"))), "title": text(item.get("title"), 240, optional=True) if include_titles else None,
        "state": item["state"], "created_at": created, "updated_at": updated, "closed_at": closed}
    if kind == "issue":
        reason = item.get("state_reason")
        require(reason in {None, "completed", "not_planned", "reopened"}, "PROVIDER")
        require((item["state"] != "open" or reason in {None, "reopened"}) and (item["state"] != "closed" or reason != "reopened"), "PROVIDER")
        result["state_reason"] = reason
    else:
        merged = item.get("merged_at")
        require(type(item.get("draft")) is bool, "PROVIDER")
        if merged is not None:
            require(closed is not None and instant(created) <= instant(merged) <= instant(closed) and item["draft"] is False, "PROVIDER")
            result["state"] = "merged"
        result.update(draft=item["draft"], merged_at=merged)
    return result


def work_inventory(value):
    # Skipped malformed records cannot be represented by a complete claim.
    outcome = "collection_failed" if value["skipped"] and value["outcome"] == "complete" else value["outcome"]
    return {"captured_at": value["captured_at"], "scope": "all", "outcome": outcome,
        "pagination": {"pages_received": value["pages"], "exhausted": value["exhausted"], "truncated": value["truncated"]},
        "records": sorted(value["records"], key=lambda record: record["number"])}


def check_record(item, repository, source_commit, include_titles):
    require(isinstance(item, dict) and item.get("head_sha") == source_commit, "PROVIDER")
    identifier = positive(item.get("id"))
    state, conclusion = item.get("status"), item.get("conclusion")
    require(state in {"queued", "in_progress", "completed"}, "PROVIDER")
    require((state == "completed" and conclusion in {"success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required", "unknown"})
        or (state != "completed" and conclusion is None), "PROVIDER")
    started, completed = item.get("started_at"), item.get("completed_at")
    if started is not None:
        instant(started)
    if completed is not None:
        instant(completed)
    require(state != "completed" or completed is not None, "PROVIDER")
    require(started is None or completed is None or instant(started) <= instant(completed), "PROVIDER")
    # Keep only the canonical public check route, without provider-selected
    # details/annotations URLs, queries, app objects, logs, actors or emails.
    url = item.get("html_url")
    require(isinstance(url, str) and re.fullmatch(r"https://github\.com/" + re.escape(repository)
        + r"/(?:runs/[1-9][0-9]*|actions/runs/[1-9][0-9]*(?:/job/[1-9][0-9]*)?)", url), "PROVIDER")
    name = text(item.get("name"), 200, optional=True) if include_titles else None
    return {"id": identifier, "name": name or "GitHub check " + str(identifier), "head_sha": source_commit,
        "status": state, "conclusion": conclusion, "started_at": started, "completed_at": completed, "html_url": url}


def source_exists(root, revision):
    """Read Git object identity only; never hooks, filters or consumer scripts."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
        GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    try:
        result = subprocess.run(["git", "--no-replace-objects", "-C", str(root),
            "-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false",
            "rev-parse", "--verify", revision + "^{commit}"], env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and result.stdout.strip() == revision.encode()


def release_record(client, item, include_titles, maximum_pages, repository_root):
    require(isinstance(item, dict), "PROVIDER")
    # Authenticated release lists may include drafts. Public selection precedes
    # every ID, tag, asset, title, count and relationship in the output.
    require(type(item.get("draft")) is bool, "PROVIDER")
    if item["draft"]:
        return None
    identifier = positive(item.get("id"))
    tag = text(item.get("tag_name"), 160)
    require(type(item.get("prerelease")) is bool, "PROVIDER")
    published = item.get("published_at")
    instant(published)
    # target_commitish is often a branch, not the released commit. Resolve the
    # exact tag ref and peel annotated tags; never label a branch tip as a tag.
    ref, _ = client.get(client.prefix + "/git/ref/tags/" + quote(tag, safe="/"), public_proof=True)
    require(isinstance(ref, dict) and ref.get("ref") == "refs/tags/" + tag, "PROVIDER")
    target = ref.get("object")
    seen = set()
    for _ in range(8):
        require(isinstance(target, dict) and isinstance(target.get("sha"), str) and SHA.fullmatch(target["sha"]), "PROVIDER")
        require(target["sha"] not in seen, "PROVIDER")
        seen.add(target["sha"])
        if target.get("type") == "commit":
            break
        require(target.get("type") == "tag", "PROVIDER")
        annotated, _ = client.get(client.prefix + "/git/tags/" + target["sha"], public_proof=True)
        require(isinstance(annotated, dict) and annotated.get("sha") == target["sha"], "PROVIDER")
        target = annotated.get("object")
    else:
        raise CaptureError("PROVIDER")
    # The existing owner admission path requires each emitted release commit
    # to exist in the inspected consumer Git object database. An unavailable
    # historical object remains incomplete, rather than denying unrelated Work
    # and Health or fetching/running anything from the consumer.
    require(source_exists(repository_root, target["sha"]), "PROVIDER")

    def asset(value):
        require(isinstance(value, dict), "PROVIDER")
        name = text(value.get("name"), 160, filename=True)
        require(type(value.get("size")) is int and 0 <= value["size"] <= 1099511627776, "PROVIDER")
        digest = value.get("digest")
        if digest is not None:
            require(isinstance(digest, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", digest), "PROVIDER")
        return {"id": positive(value.get("id")), "name": name, "size": value["size"], "sha256": digest[7:] if digest else None}

    assets = paginate(client, client.prefix + "/releases/" + str(identifier) + "/assets", asset, maximum_pages, 64, public_only=True)
    if assets["outcome"] != "complete":
        raise CaptureError(assets["outcome"])
    require(assets["pages"] and assets["exhausted"] and not assets["truncated"] and not assets["skipped"]
        and assets["outcome"] == "complete", "PROVIDER")
    names = [value["name"] for value in assets["records"]]
    require(len(names) == len(set(names)), "PROVIDER")
    return {"id": identifier, "visibility": "public", "tag_name": tag,
        "title": text(item.get("name"), 240, optional=True) if include_titles else None,
        "source_commit": target["sha"], "draft": False, "prerelease": item["prerelease"], "state": "published",
        "published_at": published, "assets": sorted([{key: value for key, value in record.items() if key != "id"}
            for record in assets["records"]], key=lambda value: value["name"])}


def release_inventory(value):
    if not value["pages"]:
        status = {"access_denied": "denied", "rate_limited": "unavailable", "provider_unavailable": "unavailable"}.get(value["outcome"], "failed")
    else:
        status = "truncated" if value["truncated"] else "incomplete" if value["skipped"] or value["outcome"] != "complete" else "complete"
    return {"status": status, "observed_at": value["captured_at"], "pages_captured": value["pages"],
        "pagination_complete": value["exhausted"], "records": sorted(value["records"], key=lambda record: record["id"])}


def safe(path):
    result = Path(path).absolute()
    require(".." not in result.parts and "\n" not in str(result) and "\r" not in str(result)
        and not any(value.is_symlink() for value in (result, *result.parents)), "PATH")
    return result


def capture(args):
    require(REPOSITORY.fullmatch(args.repository) and SHA.fullmatch(args.source_commit), "INPUT")
    positive(args.repository_id)
    require(1 <= args.maximum_pages <= 20 and 1 <= args.maximum_work_records <= 2000
        and 1 <= args.maximum_age_seconds <= 2678400, "INPUT")
    selected = [value.strip() for value in args.sources.split(",")]
    require(bool(selected) and set(selected) <= {"work", "health", "releases"} and len(selected) == len(set(selected)), "INPUT")
    root, runner = safe(args.repository_root), safe(args.runner_temp)
    require(root.is_dir() and runner.is_dir() and not runner.is_relative_to(root), "PATH")
    client = Client(args.repository, os.environ.get("RELAY_GITHUB_READ_TOKEN", ""))
    client.public_identity(args.repository, args.repository_id)
    require(source_exists(root, args.source_commit), "SOURCE")
    source, _ = client.get(client.prefix + "/commits/" + args.source_commit)
    require(isinstance(source, dict) and source.get("sha") == args.source_commit, "SOURCE")
    files, plan, inventories = {}, {"schema": "egohygiene.relay.source-capture-plan/v1"}, {}
    if "work" in selected:
        issues = paginate(client, client.prefix + "/issues", lambda item: work_record(item, "issue", args.include_titles),
            args.maximum_pages, args.maximum_work_records, parameters={"state": "all", "sort": "created", "direction": "asc"})
        pulls = paginate(client, client.prefix + "/pulls", lambda item: work_record(item, "pull_request", args.include_titles),
            args.maximum_pages, args.maximum_work_records, parameters={"state": "all", "sort": "created", "direction": "asc"})
        # The independent issue and PR inventories can move while read. A shared
        # native number is contradictory; let the collector deny rather than
        # manufacturing a new identity or silently reclassifying it.
        files["work-provider.json"] = {"schema": "egohygiene.relay.work-provider-capture/v1", "repository": args.repository,
            "source_commit": args.source_commit, "visibility": "public", "inventories": {
                "issues": work_inventory(issues), "pull_requests": work_inventory(pulls)}, "relationships": []}
        plan["work"] = {"provider_evidence": "work-provider.json", "maximum_age_seconds": args.maximum_age_seconds}
        inventories.update(issues=issues, pull_requests=pulls)
    if "health" in selected:
        checks = paginate(client, client.prefix + "/commits/" + args.source_commit + "/check-runs",
            lambda item: check_record(item, args.repository, args.source_commit, args.include_titles), args.maximum_pages, 256,
            parameters={"filter": "all"}, list_key="check_runs")
        selection = {"state": "failed" if checks["outcome"] == "collection_failed" else "unavailable"}
        if checks["pages"]:
            files["check-runs.json"] = {"total_count": checks["total"], "check_runs": sorted(checks["records"], key=lambda item: item["id"]),
                "relay_capture": {"schema": "egohygiene.relay.github-check-runs-capture/v1", "repository": args.repository,
                    "source_commit": args.source_commit, "captured_at": checks["captured_at"],
                    "outcome": "collection_failed" if checks["skipped"] and checks["outcome"] == "complete" else checks["outcome"],
                    "pagination": {"pages_received": checks["pages"], "exhausted": checks["exhausted"], "truncated": checks["truncated"]}}}
            selection = {"state": "observed", "path": "check-runs.json", "observed_at": checks["captured_at"]}
        # Provider pagination cannot establish the applicable producer set.
        # Normalized OSV/MegaLinter/Scorecard summaries remain separate inputs.
        plan["health"] = {"inventory": "partial", "expected_reports": [], "reports": {}, "check_runs": selection,
            "maximum_age_seconds": args.maximum_age_seconds}
        inventories["checks"] = checks
    if "releases" in selected:
        releases = paginate(client, client.prefix + "/releases",
            lambda item: release_record(client, item, args.include_titles, args.maximum_pages, root), args.maximum_pages, 256, public_only=True)
        files["release-provider.json"] = {"schema": "egohygiene.relay.release-provider-capture/v1", "repository": args.repository,
            "visibility": "public", "scope": "public-only", "represented_commit": args.source_commit,
            "releases": release_inventory(releases), "deployments": {"status": "uncollected", "observed_at": None,
                "pages_captured": 0, "pagination_complete": False, "records": []}}
        plan["releases"] = {"capture": "release-provider.json", "public_environments": [], "deployment_receipts": [],
            "maximum_age_seconds": args.maximum_age_seconds}
        inventories["releases"] = releases
    # A repository that became nonpublic or changed identity during capture
    # produces no usable capture output, even if earlier pages were public.
    client.public_identity(args.repository, args.repository_id)
    observed = now()
    files["source-plan.json"] = plan
    contents = {name: encoded(value) for name, value in files.items()}
    require(sum(map(len, contents.values())) <= 16 * MAX_FILE, "BOUND")
    directory = Path(tempfile.mkdtemp(prefix="repository-intelligence-public-captures-", dir=runner))
    proof_directory = Path(tempfile.mkdtemp(prefix="repository-intelligence-public-capture-proof-", dir=runner))
    try:
        for name, content in contents.items():
            (directory / name).write_bytes(content)
        receipt = {"schema": "egohygiene.relay.github-source-capture-receipt/v1", "repository": args.repository,
            "repository_id": args.repository_id, "source_commit": args.source_commit, "observed_at": observed,
            "public_admission": "unauthenticated-before-and-after", "sources": sorted(selected),
            "capture_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "requests": client.requests,
            "bounds": {"maximum_pages": args.maximum_pages, "maximum_work_records": args.maximum_work_records,
                "maximum_check_records": 256, "maximum_release_records": 256, "maximum_asset_records": 64,
                "maximum_requests": MAX_REQUESTS, "maximum_response_bytes": MAX_RESPONSE, "maximum_total_bytes": MAX_TOTAL},
            "inventories": {name: {"outcome": value["outcome"], "pages_received": value["pages"],
                "exhausted": value["exhausted"], "truncated": value["truncated"], "rejected_records": value["skipped"],
                "captured_at": value["captured_at"]} for name, value in sorted(inventories.items())},
            "files": [{"path": name, "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
                for name, content in sorted(contents.items())]}
        (proof_directory / "producer-receipt.json").write_bytes(encoded(receipt))
        # GitHub output files are caller/runtime-owned. Values contain no raw
        # provider text and are validated against multiline output injection.
        outputs = {"source-directory": str(directory), "producer-receipt": str(proof_directory / "producer-receipt.json"), "as-of": observed}
        if args.github_output:
            output = safe(args.github_output)
            require(output.is_file() and all("\n" not in value and "\r" not in value for value in outputs.values()), "PATH")
            with output.open("a", encoding="utf-8") as stream:
                for key, value in outputs.items():
                    stream.write(key + "=" + value + "\n")
        else:
            print(json.dumps(outputs, sort_keys=True))
    except BaseException:
        shutil.rmtree(directory)
        shutil.rmtree(proof_directory)
        raise


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repository", required=True)
    result.add_argument("--repository-id", required=True, type=int)
    result.add_argument("--source-commit", required=True)
    result.add_argument("--repository-root", required=True)
    result.add_argument("--runner-temp", required=True)
    result.add_argument("--sources", default="work,health,releases")
    result.add_argument("--maximum-pages", type=int, default=3)
    result.add_argument("--maximum-work-records", type=int, default=256)
    result.add_argument("--maximum-age-seconds", type=int, default=86400)
    result.add_argument("--include-titles", action="store_true")
    result.add_argument("--github-output", default="")
    return result


def main():
    try:
        capture(parser().parse_args())
    except Exception:
        # Retain no stale successful output; private directories are created
        # only after public admission and complete transport construction.
        print("GitHub source capture denied; no usable source handoff was produced.", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
