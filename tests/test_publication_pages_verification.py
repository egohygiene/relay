# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Tests for bounded, byte-exact publication Pages verification."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock
from urllib.error import URLError
from urllib.parse import urljoin, urlsplit, urlunsplit

from tests.test_publication_site_validation import REVISION, build_site


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPOSITORY_ROOT
    / "actions/verify-publication-pages/scripts/verify_publication_pages.py"
)
SPEC = importlib.util.spec_from_file_location("publication_pages_verification", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)
WORKFLOW_SHA = "c" * 40
WORKFLOW_REF = (
    "egohygiene/relay/.github/workflows/publication-pages.yml@" + WORKFLOW_SHA
)


def remote_map(site: Path, fixture: dict) -> dict[str, bytes]:
    """Return exact canonical/fallback URL bytes for a local fixture."""

    catalog = json.loads((site / "site.json").read_text(encoding="utf-8"))
    bases = [fixture["base_url"]]
    if fixture["fallback_base_url"] is not None:
        bases.append(fixture["fallback_base_url"])
    values: dict[str, bytes] = {}
    files = [path for path in site.rglob("*") if path.is_file()]
    for base in bases:
        for path in files:
            relative = path.relative_to(site).as_posix()
            values[urljoin(base, relative)] = path.read_bytes()
        for route in catalog["routes"]:
            entrypoint = route.get("file") or verifier.site_contract.route_entrypoint(
                route["path"]
            )
            values[urljoin(base, route["path"])] = (site / entrypoint).read_bytes()
    return values


def without_query(url: str) -> str:
    """Map Relay's safe cache-busted request to fixture bytes."""

    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


class PublicationPagesVerificationTests(unittest.TestCase):
    """Keep remote verification exact, deterministic, and bounded."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name)

    def verify(self, fixture_name: str, *, fallback: bool) -> dict:
        """Verify one local fixture through an in-memory HTTPS transport."""

        fixture, site = build_site(self.workspace, fixture_name)
        responses = remote_map(site, fixture)

        def fetch(url: str, timeout: float, max_bytes: int, deadline: float) -> object:
            self.assertGreater(timeout, 0)
            self.assertGreater(deadline, time.monotonic())
            self.assertEqual(urlsplit(url).query, f"relay_revision={REVISION}")
            plain = without_query(url)
            if plain not in responses:
                raise URLError("not ready")
            self.assertLessEqual(len(responses[plain]), max_bytes)
            return verifier.FetchResult(body=responses[plain], final_url=url, status=200)

        return verifier.verify_publication_pages(
            workspace=self.workspace,
            site_directory=fixture["site_directory"],
            expected_base_url=fixture["base_url"],
            expected_source_revision=REVISION,
            required_routes_json=json.dumps(fixture["required_routes"]),
            catalog_path="site.json",
            checksum_path="SHA256SUMS",
            fallback_base_url=fixture["fallback_base_url"] or "",
            verify_fallback=fallback,
            deployment_url=fixture["base_url"],
            workflow_ref=WORKFLOW_REF,
            workflow_sha=WORKFLOW_SHA,
            policy=verifier.RetryPolicy(2, 0, 5, 30),
            fetch=fetch,
            sleep=lambda _: None,
        )

    def test_custom_domain_and_fallback_bytes_produce_stable_evidence(self) -> None:
        first = self.verify("custom-domain", fallback=True)
        second = self.verify("custom-domain", fallback=True)

        self.assertEqual(first, second)
        self.assertEqual(first["result"], "passed")
        self.assertEqual(first["source_revision"], REVISION)
        self.assertEqual([item["target"] for item in first["targets"]], [
            "canonical",
            "fallback",
        ])
        self.assertEqual(first["workflow"]["sha"], WORKFLOW_SHA)

    def test_repository_subpath_verifies_without_a_fallback(self) -> None:
        evidence = self.verify("repository-subpath", fallback=False)

        self.assertEqual(len(evidence["targets"]), 1)
        self.assertEqual(
            evidence["targets"][0]["base_url"],
            "https://example.github.io/publication/",
        )

    def test_remote_byte_drift_fails_without_leaking_the_body(self) -> None:
        fixture, site = build_site(self.workspace, "custom-domain")
        responses = remote_map(site, fixture)
        target = urljoin(fixture["base_url"], "files/paper.pdf")
        responses[target] = b"x" * len(responses[target])

        def fetch(url: str, _: float, __: int, ___: float) -> object:
            return verifier.FetchResult(
                body=responses[without_query(url)], final_url=url, status=200
            )

        with self.assertRaisesRegex(verifier.VerificationError, "bounded retries") as caught:
            verifier.verify_publication_pages(
                workspace=self.workspace,
                site_directory=fixture["site_directory"],
                expected_base_url=fixture["base_url"],
                expected_source_revision=REVISION,
                required_routes_json=json.dumps(fixture["required_routes"]),
                catalog_path="site.json",
                checksum_path="SHA256SUMS",
                fallback_base_url=fixture["fallback_base_url"],
                verify_fallback=False,
                deployment_url=fixture["base_url"],
                workflow_ref=WORKFLOW_REF,
                workflow_sha=WORKFLOW_SHA,
                policy=verifier.RetryPolicy(1, 0, 5, 30),
                fetch=fetch,
                sleep=lambda _: None,
            )
        self.assertNotIn("secret remote", str(caught.exception))

    def test_retry_and_redirect_rules_are_bounded(self) -> None:
        calls = 0

        def eventually(url: str, _: float, __: int, ___: float) -> object:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise URLError("certificate pending")
            return verifier.FetchResult(
                body=b"ready",
                final_url=url,
                status=200,
            )

        result = verifier.fetch_with_retry(
            "https://publication.example.test/",
            "site.json",
            revision=REVISION,
            expected_bytes=5,
            policy=verifier.RetryPolicy(3, 0, 5, 30),
            deadline=time.monotonic() + 30,
            declared_bases=("https://publication.example.test/",),
            fetch=eventually,
            sleep=lambda _: None,
        )
        self.assertEqual(result.body, b"ready")
        self.assertEqual(calls, 3)

        stale_calls = 0

        def stale_then_current(url: str, _: float, __: int, ___: float) -> object:
            nonlocal stale_calls
            stale_calls += 1
            body = b"stale" if stale_calls < 3 else b"fresh"
            return verifier.FetchResult(body=body, final_url=url, status=200)

        current = verifier.fetch_with_retry(
            "https://publication.example.test/",
            "site.json",
            revision=REVISION,
            expected_bytes=5,
            expected_body=b"fresh",
            policy=verifier.RetryPolicy(3, 0, 5, 30),
            deadline=time.monotonic() + 30,
            declared_bases=("https://publication.example.test/",),
            fetch=stale_then_current,
            sleep=lambda _: None,
        )
        self.assertEqual(current.body, b"fresh")
        self.assertEqual(stale_calls, 3)

        redirect_calls = 0

        def redirected(url: str, _: float, __: int, ___: float) -> object:
            nonlocal redirect_calls
            redirect_calls += 1
            return verifier.FetchResult(
                body=b"",
                final_url=url,
                status=302,
                redirect_url=(
                    "https://attacker.example/site.json?relay_revision=" + REVISION
                ),
            )

        with self.assertRaisesRegex(verifier.VerificationError, "bounded retries"):
            verifier.fetch_with_retry(
                "https://publication.example.test/",
                "site.json",
                revision=REVISION,
                expected_bytes=5,
                policy=verifier.RetryPolicy(1, 0, 5, 30),
                deadline=time.monotonic() + 30,
                declared_bases=("https://publication.example.test/",),
                fetch=redirected,
                sleep=lambda _: None,
            )
        self.assertEqual(redirect_calls, 1)

    def test_policy_workflow_identity_and_deployment_url_fail_closed(self) -> None:
        for policy in (
            verifier.RetryPolicy(13, 0, 5, 30),
            verifier.RetryPolicy(1, 31, 5, 30),
            verifier.RetryPolicy(1, 0, 61, 30),
            verifier.RetryPolicy(1, 0, 5, 601),
        ):
            with self.subTest(policy=policy):
                with self.assertRaises(verifier.VerificationError):
                    policy.validate()

        with self.assertRaisesRegex(verifier.VerificationError, "Relay publication workflow"):
            verifier.validate_workflow_identity(WORKFLOW_REF, "d" * 40)
        with self.assertRaisesRegex(verifier.VerificationError, "Relay publication workflow"):
            verifier.validate_workflow_identity(
                "egohygiene/relay/.github/workflows/publication-pages.yml@evil@"
                + WORKFLOW_SHA,
                WORKFLOW_SHA,
            )

        fixture, site = build_site(self.workspace, "custom-domain")
        responses = remote_map(site, fixture)

        def fetch(url: str, _: float, __: int, ___: float) -> object:
            return verifier.FetchResult(
                body=responses[without_query(url)], final_url=url, status=200
            )

        with self.assertRaisesRegex(verifier.VerificationError, "deployment URL"):
            verifier.verify_publication_pages(
                workspace=self.workspace,
                site_directory=fixture["site_directory"],
                expected_base_url=fixture["base_url"],
                expected_source_revision=REVISION,
                required_routes_json="[]",
                catalog_path="site.json",
                checksum_path="SHA256SUMS",
                fallback_base_url=fixture["fallback_base_url"],
                verify_fallback=False,
                deployment_url="https://wrong.example.test/",
                workflow_ref=WORKFLOW_REF,
                workflow_sha=WORKFLOW_SHA,
                policy=verifier.RetryPolicy(1, 0, 5, 30),
                fetch=fetch,
                sleep=lambda _: None,
            )

    def test_catalog_fallback_requires_explicit_remote_authorization(self) -> None:
        fixture, _ = build_site(self.workspace, "custom-domain")
        common = {
            "workspace": self.workspace,
            "site_directory": fixture["site_directory"],
            "expected_base_url": fixture["base_url"],
            "expected_source_revision": REVISION,
            "required_routes_json": json.dumps(fixture["required_routes"]),
            "catalog_path": "site.json",
            "checksum_path": "SHA256SUMS",
            "fallback_base_url": "",
            "deployment_url": fixture["base_url"],
            "workflow_ref": WORKFLOW_REF,
            "workflow_sha": WORKFLOW_SHA,
            "policy": verifier.RetryPolicy(1, 0, 5, 30),
        }
        _, _, authorized_fallback = verifier.validate_verification_configuration(
            **common,
            verify_fallback=False,
        )
        self.assertIsNone(authorized_fallback)

        with self.assertRaisesRegex(
            verifier.VerificationError, "explicit matching fallback-base-url"
        ):
            verifier.validate_verification_configuration(
                **common,
                verify_fallback=True,
            )

        calls: list[str] = []

        def redirect_to_unpinned_fallback(
            url: str, _: float, __: int, ___: float
        ) -> object:
            calls.append(url)
            return verifier.FetchResult(
                body=b"",
                final_url=url,
                status=302,
                redirect_url=verifier.cache_busted_url(
                    fixture["fallback_base_url"], "site.json", REVISION
                ),
            )

        with self.assertRaisesRegex(verifier.VerificationError, "bounded retries"):
            verifier.fetch_with_retry(
                fixture["base_url"],
                "site.json",
                revision=REVISION,
                expected_bytes=10,
                policy=verifier.RetryPolicy(1, 0, 5, 30),
                deadline=time.monotonic() + 30,
                declared_bases=(fixture["base_url"],),
                fetch=redirect_to_unpinned_fallback,
                sleep=lambda _: None,
            )
        self.assertEqual(len(calls), 1)

    def test_public_endpoint_and_redirect_policy_blocks_ssrf_before_fetch(self) -> None:
        for url in (
            "http://publication.example.test/",
            "https://localhost/",
            "https://127.0.0.1/",
            "https://169.254.169.254/",
            "https://publication.example.test:8443/",
            "https://internal/",
        ):
            with self.subTest(url=url):
                with self.assertRaises(
                    (verifier.VerificationError, verifier.site_contract.ValidationError)
                ):
                    verifier.validate_public_base_url(url, "fixture")

        for redirect in (
            "http://publication.example.test/site.json",
            "https://127.0.0.1/site.json",
            "https://169.254.169.254/latest/meta-data/",
            "https://publication.example.test:8443/site.json",
            "https://undeclared.example/site.json",
        ):
            calls: list[str] = []

            def fetch(url: str, _: float, __: int, ___: float) -> object:
                calls.append(url)
                return verifier.FetchResult(
                    body=b"",
                    final_url=url,
                    status=302,
                    redirect_url=redirect,
                )

            with self.subTest(redirect=redirect):
                with self.assertRaisesRegex(verifier.VerificationError, "bounded retries"):
                    verifier.fetch_with_retry(
                        "https://publication.example.test/",
                        "site.json",
                        revision=REVISION,
                        expected_bytes=10,
                        policy=verifier.RetryPolicy(1, 0, 5, 30),
                        deadline=time.monotonic() + 30,
                        declared_bases=("https://publication.example.test/",),
                        fetch=fetch,
                        sleep=lambda _: None,
                    )
                self.assertEqual(len(calls), 1)

    def test_cache_busting_preserves_exact_repository_subpath(self) -> None:
        self.assertEqual(
            verifier.cache_busted_url(
                "https://example.github.io/publication/", "paper/", REVISION
            ),
            "https://example.github.io/publication/paper/"
            f"?relay_revision={REVISION}",
        )

    def test_exact_byte_fetch_refuses_content_encoding(self) -> None:
        class EncodedResponse:
            status = 200
            headers = {"Content-Encoding": "gzip"}

            def __enter__(self) -> "EncodedResponse":
                return self

            def __exit__(self, *_: object) -> None:
                return None

        class Opener:
            request = None

            def open(self, request: object, *, timeout: float) -> EncodedResponse:
                self.request = request
                self.timeout = timeout
                return EncodedResponse()

        opener = Opener()
        with (
            mock.patch.object(verifier, "assert_public_resolution"),
            mock.patch.object(verifier, "build_opener", return_value=opener),
            self.assertRaisesRegex(
                verifier.VerificationError,
                "unsupported content encoding",
            ),
        ):
            verifier.default_fetch(
                "https://publication.example.test/site.json",
                timeout=5,
                max_bytes=1024,
                deadline=time.monotonic() + 5,
            )
        self.assertEqual(opener.request.get_header("Accept-encoding"), "identity")

    def test_failure_evidence_is_sanitized_and_configuration_only_is_offline(self) -> None:
        fixture, _ = build_site(self.workspace, "repository-subpath")
        evidence = self.workspace / ".relay/verification-failure.json"
        result = verifier.main(
            [
                "--workspace",
                str(self.workspace),
                "--site-directory",
                fixture["site_directory"],
                "--expected-base-url",
                fixture["base_url"],
                "--expected-source-revision",
                REVISION,
                "--configuration-only",
                "true",
                "--workflow-ref",
                "secret-token-not-a-workflow-ref",
                "--workflow-sha",
                WORKFLOW_SHA,
                "--evidence-output",
                ".relay/verification-failure.json",
            ]
        )
        self.assertEqual(result, 2)
        failure = evidence.read_text(encoding="utf-8")
        self.assertIn("predeploy-configuration", failure)
        self.assertNotIn("secret-token", failure)
        self.assertNotIn(str(self.workspace), failure)


if __name__ == "__main__":
    unittest.main()
