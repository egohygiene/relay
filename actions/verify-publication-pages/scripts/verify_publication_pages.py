# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Verify deployed publication bytes and write bounded deployment evidence."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import ipaddress
import json
from pathlib import Path, PurePosixPath
import re
import socket
import sys
import time
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


ACTION_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = (
    ACTION_ROOT
    / "validate-publication-site"
    / "scripts"
    / "validate_publication_site.py"
)
SPEC = importlib.util.spec_from_file_location("relay_publication_site", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - installation corruption
    raise RuntimeError(f"cannot load Relay publication validator: {VALIDATOR_PATH}")
site_contract = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = site_contract
SPEC.loader.exec_module(site_contract)


EVIDENCE_SCHEMA = "egohygiene.relay.publication-pages-evidence/v1"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
MAX_ATTEMPTS = 12
MAX_DELAY_SECONDS = 30.0
MAX_REQUEST_TIMEOUT_SECONDS = 60.0
MAX_ELAPSED_SECONDS = 600.0
MAX_REDIRECTS = 5
PUBLIC_HOST = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)


class VerificationError(ValueError):
    """Remote deployment evidence does not match the validated local site."""


@dataclass(frozen=True)
class FetchResult:
    """Safe result of one HTTPS fetch."""

    body: bytes
    final_url: str
    status: int
    redirect_url: str | None = None


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded network policy shared by every deployment fetch."""

    attempts: int
    delay_seconds: float
    request_timeout_seconds: float
    max_elapsed_seconds: float

    def validate(self) -> None:
        """Reject values that could create an unbounded Actions job."""

        if not 1 <= self.attempts <= MAX_ATTEMPTS:
            raise VerificationError(f"attempts must be between 1 and {MAX_ATTEMPTS}")
        if not 0 <= self.delay_seconds <= MAX_DELAY_SECONDS:
            raise VerificationError(
                f"retry-delay-seconds must be between 0 and {MAX_DELAY_SECONDS:g}"
            )
        if not 1 <= self.request_timeout_seconds <= MAX_REQUEST_TIMEOUT_SECONDS:
            raise VerificationError(
                "request-timeout-seconds must be between 1 and "
                f"{MAX_REQUEST_TIMEOUT_SECONDS:g}"
            )
        if not 1 <= self.max_elapsed_seconds <= MAX_ELAPSED_SECONDS:
            raise VerificationError(
                f"max-elapsed-seconds must be between 1 and {MAX_ELAPSED_SECONDS:g}"
            )


def parse_boolean(value: str, label: str) -> bool:
    """Parse an explicit lowercase workflow boolean."""

    if value == "true":
        return True
    if value == "false":
        return False
    raise VerificationError(f"{label} must be true or false")


def validate_workflow_identity(workflow_ref: str, workflow_sha: str) -> None:
    """Require immutable evidence about the called Relay workflow."""

    if not FULL_SHA.fullmatch(workflow_sha):
        raise VerificationError("workflow-sha must be a full lowercase Git SHA")
    expected = (
        "egohygiene/relay/.github/workflows/publication-pages.yml@" + workflow_sha
    )
    if workflow_ref != expected:
        raise VerificationError("workflow-ref is not the Relay publication workflow")


def validate_public_base_url(value: str, label: str) -> str:
    """Require a standard-port, public-looking DNS HTTPS base."""

    normalized = site_contract.normalize_base_url(value, label)
    parsed = urlsplit(normalized)
    if parsed.port is not None:
        raise VerificationError(f"{label} cannot use a nonstandard port")
    hostname = parsed.hostname or ""
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise VerificationError(f"{label} cannot use an IP literal")
    if (
        not PUBLIC_HOST.fullmatch(hostname)
        or hostname == "localhost"
        or hostname.endswith((".localhost", ".local", ".internal", ".home", ".lan"))
    ):
        raise VerificationError(f"{label} must use a public-looking DNS host")
    return normalized


def assert_public_resolution(url: str) -> None:
    """Reject current DNS answers containing local, private, or reserved addresses."""

    hostname = urlsplit(url).hostname
    if hostname is None:
        raise VerificationError("remote URL has no hostname")
    addresses = {
        record[4][0]
        for record in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    }
    if not addresses:
        raise VerificationError("remote DNS lookup returned no addresses")
    for address in addresses:
        if not ipaddress.ip_address(address).is_global:
            raise VerificationError("remote DNS resolved to a non-public address")


def cache_busted_url(base_url: str, relative: str, revision: str) -> str:
    """Return one exact route URL with a safe deployment-revision cache key."""

    if not FULL_SHA.fullmatch(revision):
        raise VerificationError("cache revision must be a full lowercase Git SHA")
    target = urlsplit(urljoin(base_url, relative))
    if target.query or target.fragment:
        raise VerificationError("publication routes cannot contain query or fragment")
    return urlunsplit(
        (target.scheme, target.netloc, target.path, f"relay_revision={revision}", "")
    )


class _NoRedirect(HTTPRedirectHandler):
    """Expose redirects to Relay instead of allowing urllib to follow them."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def default_fetch(
    url: str,
    timeout: float,
    max_bytes: int,
    deadline: float,
) -> FetchResult:
    """Fetch one public HTTPS resource with no automatic redirects or unbounded read."""

    assert_public_resolution(url)
    request = Request(
        url,
        headers={
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "egohygiene-relay-publication-verifier/1",
        },
        method="GET",
    )
    opener = build_opener(_NoRedirect())
    try:
        response = opener.open(request, timeout=timeout)  # noqa: S310 - URL checked
    except HTTPError as error:
        if error.code not in {301, 302, 303, 307, 308}:
            raise
        location = error.headers.get("Location")
        if not location:
            raise VerificationError("remote redirect omitted Location") from error
        return FetchResult(
            body=b"",
            final_url=url,
            status=error.code,
            redirect_url=urljoin(url, location),
        )
    with response:
        content_encoding = (
            response.headers.get("Content-Encoding") or "identity"
        ).strip().lower()
        if content_encoding != "identity":
            raise VerificationError("remote response used an unsupported content encoding")
        body = bytearray()
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError("remote response exceeded total deadline")
            reader = getattr(response, "read1", response.read)
            chunk = reader(min(64 * 1024, max_bytes + 1 - len(body)))
            if not chunk:
                break
            body.extend(chunk)
            if time.monotonic() >= deadline:
                raise TimeoutError("remote response exceeded total deadline")
            if len(body) > max_bytes:
                raise VerificationError("remote response exceeds reviewed byte count")
        return FetchResult(
            body=bytes(body),
            final_url=url,
            status=int(response.status),
        )


def fetch_with_retry(
    base_url: str,
    relative: str,
    *,
    revision: str,
    expected_bytes: int,
    expected_body: bytes | None = None,
    expected_sha256: str | None = None,
    policy: RetryPolicy,
    deadline: float,
    declared_bases: tuple[str, ...],
    fetch: Callable[[str, float, int, float], FetchResult] = default_fetch,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> FetchResult:
    """Fetch a resource under attempt, timeout, redirect, and total-time caps."""

    allowed_urls = {
        cache_busted_url(declared, relative, revision) for declared in declared_bases
    }
    url = cache_busted_url(base_url, relative, revision)
    if url not in allowed_urls:
        raise VerificationError("remote verification accepts only declared HTTPS routes")
    last_error = "request did not run"
    for attempt in range(1, policy.attempts + 1):
        remaining = deadline - clock()
        if remaining <= 0:
            break
        timeout = min(policy.request_timeout_seconds, max(1.0, remaining))
        try:
            current = url
            for redirect_count in range(MAX_REDIRECTS + 1):
                remaining = deadline - clock()
                if remaining <= 0:
                    raise TimeoutError("remote request exceeded total deadline")
                timeout = min(policy.request_timeout_seconds, max(1.0, remaining))
                if current not in allowed_urls:
                    raise VerificationError(
                        "remote request redirected outside the exact declared route"
                    )
                result = fetch(current, timeout, expected_bytes, deadline)
                if result.redirect_url is None:
                    if result.final_url != current:
                        raise VerificationError("transport followed an unvalidated redirect")
                    if result.status != 200:
                        raise VerificationError(
                            f"remote request returned HTTP {result.status}"
                        )
                    if len(result.body) > expected_bytes:
                        raise VerificationError(
                            "remote response exceeds reviewed byte count"
                        )
                    if expected_body is not None and result.body != expected_body:
                        raise VerificationError(
                            "remote response does not match reviewed bytes"
                        )
                    if (
                        expected_sha256 is not None
                        and hashlib.sha256(result.body).hexdigest() != expected_sha256
                    ):
                        raise VerificationError(
                            "remote response does not match reviewed digest"
                        )
                    return result
                if redirect_count == MAX_REDIRECTS:
                    raise VerificationError("remote request exceeded redirect limit")
                current = result.redirect_url
            raise VerificationError("remote request exceeded redirect limit")
        except (HTTPError, URLError, TimeoutError, OSError, VerificationError) as error:
            last_error = type(error).__name__
            if attempt == policy.attempts:
                break
            remaining = deadline - clock()
            if remaining <= 0:
                break
            sleep(min(policy.delay_seconds, remaining))
    raise VerificationError(
        f"remote resource was unavailable after bounded retries ({last_error})"
    )


def verify_remote_target(
    *,
    target_kind: str,
    base_url: str,
    local_site: Path,
    validation: Any,
    revision: str,
    policy: RetryPolicy,
    deadline: float,
    declared_bases: tuple[str, ...],
    fetch: Callable[[str, float, int, float], FetchResult] = default_fetch,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Verify the catalog, inventory, all bytes, and every declared route."""

    catalog_local = (local_site / validation.catalog_path).read_bytes()
    checksum_local = (local_site / validation.checksum_path).read_bytes()
    catalog_remote = fetch_with_retry(
        base_url,
        validation.catalog_path,
        revision=revision,
        expected_bytes=len(catalog_local),
        expected_body=catalog_local,
        policy=policy,
        deadline=deadline,
        declared_bases=declared_bases,
        fetch=fetch,
        sleep=sleep,
        clock=clock,
    )
    if catalog_remote.body != catalog_local:
        raise VerificationError(f"{target_kind} catalog bytes do not match the reviewed site")
    checksum_remote = fetch_with_retry(
        base_url,
        validation.checksum_path,
        revision=revision,
        expected_bytes=len(checksum_local),
        expected_body=checksum_local,
        policy=policy,
        deadline=deadline,
        declared_bases=declared_bases,
        fetch=fetch,
        sleep=sleep,
        clock=clock,
    )
    if checksum_remote.body != checksum_local:
        raise VerificationError(
            f"{target_kind} checksum inventory does not match the reviewed site"
        )

    verified_files: list[dict[str, str]] = []
    for relative, expected_digest in validation.files:
        local_size = (local_site / PurePosixPath(relative)).stat().st_size
        result = fetch_with_retry(
            base_url,
            relative,
            revision=revision,
            expected_bytes=local_size,
            expected_sha256=expected_digest,
            policy=policy,
            deadline=deadline,
            declared_bases=declared_bases,
            fetch=fetch,
            sleep=sleep,
            clock=clock,
        )
        observed = hashlib.sha256(result.body).hexdigest()
        if observed != expected_digest:
            raise VerificationError(
                f"{target_kind} deployed digest does not match: {relative}"
            )
        verified_files.append({"path": relative, "sha256": observed})

    verified_routes: list[dict[str, str]] = []
    for route, entrypoint in validation.route_files:
        expected = (local_site / PurePosixPath(entrypoint)).read_bytes()
        result = fetch_with_retry(
            base_url,
            route,
            revision=revision,
            expected_bytes=len(expected),
            expected_body=expected,
            policy=policy,
            deadline=deadline,
            declared_bases=declared_bases,
            fetch=fetch,
            sleep=sleep,
            clock=clock,
        )
        if result.body != expected:
            raise VerificationError(
                f"{target_kind} route bytes do not match: {route or '/'}"
            )
        verified_routes.append(
            {
                "path": route,
                "sha256": hashlib.sha256(result.body).hexdigest(),
            }
        )
    return {
        "base_url": base_url,
        "catalog_sha256": hashlib.sha256(catalog_remote.body).hexdigest(),
        "checksum_sha256": hashlib.sha256(checksum_remote.body).hexdigest(),
        "file_count": len(verified_files),
        "route_count": len(verified_routes),
        "routes": verified_routes,
        "status": "passed",
        "target": target_kind,
    }


def verification_evidence(
    *,
    validation: Any,
    workflow_ref: str,
    workflow_sha: str,
    targets: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return deterministic successful deployment evidence."""

    return {
        "file_count": validation.file_count,
        "result": "passed",
        "schema": EVIDENCE_SCHEMA,
        "site_tree_sha256": validation.site_tree_sha256,
        "source_revision": validation.source_revision,
        "targets": targets,
        "total_bytes": validation.total_bytes,
        "workflow": {
            "ref": workflow_ref,
            "repository": "egohygiene/relay",
            "sha": workflow_sha,
        },
    }


def validate_verification_configuration(
    *,
    workspace: Path,
    site_directory: str,
    expected_base_url: str,
    expected_source_revision: str,
    required_routes_json: str,
    catalog_path: str,
    checksum_path: str,
    fallback_base_url: str,
    verify_fallback: bool,
    deployment_url: str,
    workflow_ref: str,
    workflow_sha: str,
    policy: RetryPolicy,
) -> tuple[Any, str, str | None]:
    """Validate every local, endpoint, identity, and retry input without networking."""

    policy.validate()
    validate_workflow_identity(workflow_ref, workflow_sha)
    validation = site_contract.validate_publication_site(
        workspace=workspace,
        site_directory=site_directory,
        expected_base_url=expected_base_url,
        expected_source_revision=expected_source_revision,
        required_routes_json=required_routes_json,
        catalog_path=catalog_path,
        checksum_path=checksum_path,
    )
    canonical = validate_public_base_url(
        validation.canonical_base_url, "canonical-base-url"
    )
    if deployment_url:
        observed_deployment = validate_public_base_url(
            deployment_url, "deployment-url"
        )
        if observed_deployment != canonical:
            raise VerificationError(
                "GitHub Pages deployment URL does not match the canonical catalog URL"
            )
    catalog_fallback = (
        validate_public_base_url(validation.fallback_base_url, "catalog fallback-base-url")
        if validation.fallback_base_url is not None
        else None
    )
    authorized_fallback: str | None = None
    if fallback_base_url:
        authorized_fallback = validate_public_base_url(
            fallback_base_url, "fallback-base-url"
        )
        if authorized_fallback != catalog_fallback:
            raise VerificationError("fallback-base-url does not match the site catalog")
    if verify_fallback and authorized_fallback is None:
        raise VerificationError(
            "fallback verification requires an explicit matching fallback-base-url"
        )
    return validation, canonical, authorized_fallback


def verify_publication_pages(
    *,
    workspace: Path,
    site_directory: str,
    expected_base_url: str,
    expected_source_revision: str,
    required_routes_json: str,
    catalog_path: str,
    checksum_path: str,
    fallback_base_url: str,
    verify_fallback: bool,
    deployment_url: str,
    workflow_ref: str,
    workflow_sha: str,
    policy: RetryPolicy,
    fetch: Callable[[str, float, int, float], FetchResult] = default_fetch,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Validate the local site, then prove canonical and optional fallback bytes."""

    validation, canonical, fallback = validate_verification_configuration(
        workspace=workspace,
        site_directory=site_directory,
        expected_base_url=expected_base_url,
        expected_source_revision=expected_source_revision,
        required_routes_json=required_routes_json,
        catalog_path=catalog_path,
        checksum_path=checksum_path,
        fallback_base_url=fallback_base_url,
        verify_fallback=verify_fallback,
        deployment_url=deployment_url,
        workflow_ref=workflow_ref,
        workflow_sha=workflow_sha,
        policy=policy,
    )

    declared_bases = tuple(value for value in (canonical, fallback) if value is not None)
    deadline = clock() + policy.max_elapsed_seconds
    local_site = site_contract.resolve_site_directory(workspace, site_directory)
    targets = [
        verify_remote_target(
            target_kind="canonical",
            base_url=canonical,
            local_site=local_site,
            validation=validation,
            revision=expected_source_revision,
            policy=policy,
            deadline=deadline,
            declared_bases=declared_bases,
            fetch=fetch,
            sleep=sleep,
            clock=clock,
        )
    ]
    if verify_fallback and fallback is not None:
        targets.append(
            verify_remote_target(
                target_kind="fallback",
                base_url=fallback,
                local_site=local_site,
                validation=validation,
                revision=expected_source_revision,
                policy=policy,
                deadline=deadline,
                declared_bases=declared_bases,
                fetch=fetch,
                sleep=sleep,
                clock=clock,
            )
        )
    return verification_evidence(
        validation=validation,
        workflow_ref=workflow_ref,
        workflow_sha=workflow_sha,
        targets=targets,
    )


def parse_arguments(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse composite-action inputs."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--site-directory", required=True)
    parser.add_argument("--expected-base-url", required=True)
    parser.add_argument("--expected-source-revision", required=True)
    parser.add_argument("--required-routes", default="[]")
    parser.add_argument("--catalog-path", default="site.json")
    parser.add_argument("--checksum-path", default="SHA256SUMS")
    parser.add_argument("--fallback-base-url", default="")
    parser.add_argument("--verify-fallback", default="false")
    parser.add_argument("--deployment-url", default="")
    parser.add_argument("--configuration-only", default="false")
    parser.add_argument("--attempts", type=int, default=8)
    parser.add_argument("--retry-delay-seconds", type=float, default=5)
    parser.add_argument("--request-timeout-seconds", type=float, default=20)
    parser.add_argument("--max-elapsed-seconds", type=float, default=300)
    parser.add_argument("--workflow-ref", required=True)
    parser.add_argument("--workflow-sha", required=True)
    parser.add_argument("--evidence-output", required=True)
    parser.add_argument("--github-output", default="")
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    """Verify a deployed publication site and emit stable evidence."""

    parsed = parse_arguments(arguments)
    evidence_path: Path | None = None
    failure_stage = "input-validation"
    try:
        workspace = Path(parsed.workspace)
        site = site_contract.resolve_site_directory(workspace, parsed.site_directory)
        evidence_path = site_contract.resolve_workspace_output(
            workspace, parsed.evidence_output, site=site
        )
        verify_fallback = parse_boolean(parsed.verify_fallback, "verify-fallback")
        configuration_only = parse_boolean(
            parsed.configuration_only, "configuration-only"
        )
        failure_stage = (
            "predeploy-configuration" if configuration_only else "remote-verification"
        )
        policy = RetryPolicy(
            attempts=parsed.attempts,
            delay_seconds=parsed.retry_delay_seconds,
            request_timeout_seconds=parsed.request_timeout_seconds,
            max_elapsed_seconds=parsed.max_elapsed_seconds,
        )
        common = {
            "workspace": workspace,
            "site_directory": parsed.site_directory,
            "expected_base_url": parsed.expected_base_url,
            "expected_source_revision": parsed.expected_source_revision,
            "required_routes_json": parsed.required_routes,
            "catalog_path": parsed.catalog_path,
            "checksum_path": parsed.checksum_path,
            "fallback_base_url": parsed.fallback_base_url,
            "verify_fallback": verify_fallback,
            "deployment_url": parsed.deployment_url,
            "workflow_ref": parsed.workflow_ref,
            "workflow_sha": parsed.workflow_sha,
            "policy": policy,
        }
        if configuration_only:
            validation, canonical, fallback = validate_verification_configuration(
                **common
            )
            evidence = {
                "canonical_base_url": canonical,
                "fallback_base_url": fallback,
                "file_count": validation.file_count,
                "result": "passed",
                "schema": EVIDENCE_SCHEMA,
                "site_tree_sha256": validation.site_tree_sha256,
                "source_revision": validation.source_revision,
                "stage": "predeploy-configuration",
                "targets": [],
                "total_bytes": validation.total_bytes,
                "workflow": {
                    "ref": parsed.workflow_ref,
                    "repository": "egohygiene/relay",
                    "sha": parsed.workflow_sha,
                },
            }
        else:
            evidence = verify_publication_pages(**common)
        site_contract.write_json(evidence_path, evidence)
        if parsed.github_output:
            with Path(parsed.github_output).open("a", encoding="utf-8") as output:
                output.write(f"site-tree-sha256={evidence['site_tree_sha256']}\n")
                output.write(f"target-count={len(evidence['targets'])}\n")
                output.write(f"file-count={evidence['file_count']}\n")
                output.write(f"total-bytes={evidence['total_bytes']}\n")
    except (site_contract.ValidationError, VerificationError) as error:
        failure = {
            "error": "publication-pages-verification-failed",
            "reason": (
                "configuration-rejected"
                if failure_stage != "remote-verification"
                else "remote-proof-failed"
            ),
            "result": "failed",
            "schema": EVIDENCE_SCHEMA,
            "stage": failure_stage,
            "workflow": {
                "identity": "unverified",
                "repository": "egohygiene/relay",
            },
        }
        if evidence_path is not None:
            site_contract.write_json(evidence_path, failure)
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(
        f"Verified {len(evidence['targets'])} publication target(s) for "
        f"{evidence['source_revision']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
