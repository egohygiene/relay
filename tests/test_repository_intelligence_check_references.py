# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Check the real collector/bundle boundary for canonical provider check URLs."""

import importlib.util
from pathlib import Path
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "actions/repository-intelligence/scripts"

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

validator = module("check_reference_validator", SCRIPTS / "validate_repository_intelligence_bundle.py")
collector = module("check_reference_collector", SCRIPTS / "collect_repository_health.py")
REPOSITORY = "egohygiene/empathy"
SOURCE = "7639304babcba9d4baf21ccea163f31f9045a0c6"
BASE = "https://github.com/" + REPOSITORY

class ProviderCheckReferenceTests(unittest.TestCase):
    def test_actual_captured_provider_job_url_is_admitted_unchanged(self):
        url = BASE + "/actions/runs/43543368762/job/132288808577"
        self.assertEqual(collector.public_url(url, REPOSITORY, check=True), url)
        validator.validate_https_reference(url, REPOSITORY, SOURCE)

    def test_both_existing_collector_check_url_shapes_accept_positive_ids(self):
        for path in ("/runs/1", "/runs/43543368762", "/actions/runs/1/job/1", "/actions/runs/43543368762/job/132288808577"):
            with self.subTest(path=path):
                url = BASE + path
                self.assertEqual(collector.public_url(url, REPOSITORY, check=True), url)
                validator.validate_https_reference(url, REPOSITORY, SOURCE)

    def test_nonpositive_or_noncanonical_route_ids_are_rejected(self):
        for path in ("/runs/0", "/runs/01", "/runs/-1", "/runs/+1", "/runs/one", "/runs/1/", "/actions/runs/0/job/1", "/actions/runs/1/job/0", "/actions/runs/01/job/1", "/actions/runs/1/job/01", "/actions/runs/1/job/-1", "/actions/runs/1/jobs/1", "/actions/runs/1/job/1/", "/actions/runs/1/job/1/extra", "/actions//runs/1/job/1", "/actions/runs/1/../job/1", "/runs/%31", "/runs/%2531"):
            with self.subTest(path=path), self.assertRaises(validator.BundleValidationError):
                validator.validate_https_reference(BASE + path, REPOSITORY, SOURCE)

    def test_new_check_routes_cannot_expand_external_repository_admission(self):
        for repository in ("egohygiene/relay", "egohygiene/private-fixture", "elsewhere/empathy", "egohygiene/empathy-extra"):
            for path in ("/runs/1", "/actions/runs/1/job/1"):
                with self.subTest(repository=repository, path=path), self.assertRaises(validator.BundleValidationError):
                    validator.validate_https_reference("https://github.com/" + repository + path, REPOSITORY, SOURCE, {repository})

    def test_new_check_routes_retain_origin_query_fragment_and_credential_guards(self):
        for path in ("/runs/1", "/actions/runs/1/job/1"):
            for url in ("http://github.com/" + REPOSITORY + path, "https://github.com:444/" + REPOSITORY + path, "https://github.com:443/" + REPOSITORY + path, "https://GitHub.com/" + REPOSITORY + path, "https://github.com.evil.invalid/" + REPOSITORY + path, "https://synthetic-user@github.com/" + REPOSITORY + path, BASE + path + "?attempt=1", BASE + path + "#step-summary", BASE + path + "#../private", BASE + path + "\\tail", BASE + path + "\n"):
                with self.subTest(url=url), self.assertRaises(validator.BundleValidationError):
                    validator.validate_https_reference(url, REPOSITORY, SOURCE)

    def test_declared_dependency_roots_require_exact_existing_membership(self):
        allowed = {"egohygiene/egolint", "egohygiene/mantle", "egohygiene/realm", "egohygiene/relay"}
        for name in sorted(allowed):
            with self.subTest(name=name):
                validator.validate_https_reference("https://github.com/" + name, REPOSITORY, SOURCE, allowed)
                with self.assertRaises(validator.BundleValidationError):
                    validator.validate_https_reference("https://github.com/" + name, REPOSITORY, SOURCE)
        for name in ("egohygiene/private-fixture", "egohygiene/relay-extra", "elsewhere/relay", "egohygiene/Relay"):
            with self.subTest(name=name), self.assertRaises(validator.BundleValidationError):
                validator.validate_https_reference("https://github.com/" + name, REPOSITORY, SOURCE, allowed)

    def test_declared_roots_do_not_admit_subpaths_queries_fragments_or_traversal(self):
        base = "https://github.com/egohygiene/relay"
        allowed = {"egohygiene/relay"}
        for suffix in ("/", "/settings", "/../private", "/./", "%2fsettings", "?tab=readme", "#readme", "#../private", "\\tail"):
            with self.subTest(suffix=suffix), self.assertRaises(validator.BundleValidationError):
                validator.validate_https_reference(base + suffix, REPOSITORY, SOURCE, allowed)
        for url in ("http://github.com/egohygiene/relay", "https://github.com:443/egohygiene/relay", "https://github.com:444/egohygiene/relay", "https://synthetic-user@github.com/egohygiene/relay", "https://github.com.evil.invalid/egohygiene/relay"):
            with self.subTest(url=url), self.assertRaises(validator.BundleValidationError):
                validator.validate_https_reference(url, REPOSITORY, SOURCE, allowed)

    def test_existing_immutable_source_and_external_run_routes_keep_their_boundaries(self):
        validator.validate_https_reference(BASE + "/blob/" + SOURCE + "/README.md#L1", REPOSITORY, SOURCE)
        validator.validate_https_reference("https://github.com/egohygiene/relay/actions/runs/1", REPOSITORY, SOURCE, {"egohygiene/relay"})
        with self.assertRaises(validator.BundleValidationError):
            validator.validate_https_reference(BASE + "/blob/" + "0" * 40 + "/README.md", REPOSITORY, SOURCE)

if __name__ == "__main__":
    unittest.main()
