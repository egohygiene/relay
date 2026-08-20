# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""End-to-end tests for the public Repository Intelligence subtree."""

from __future__ import annotations

from datetime import UTC, datetime
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.request import urlopen

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACTION_ROOT = REPOSITORY_ROOT / "actions/repository-intelligence"
FIXTURE_ROOT = REPOSITORY_ROOT / "tests/fixtures"
AS_OF = datetime(2026, 8, 14, 12, tzinfo=UTC)
GENERATOR_COMMIT = "a" * 40
PRIVATE_REPORT_PATH = "evidence/private-issue-123-internal.txt"


def load_module(name: str, path: Path):
    """Load one action script as a test module."""

    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dashboard_builder = load_module(
    "bundle_dashboard_builder",
    ACTION_ROOT / "scripts/generate_repository_intelligence_dashboard.py",
)
output_preparer = load_module(
    "bundle_output_preparer",
    ACTION_ROOT / "scripts/prepare_output_directory.py",
)
bundle_validator = load_module(
    "bundle_validator",
    ACTION_ROOT / "scripts/validate_repository_intelligence_bundle.py",
)


def git(repository: Path, *arguments: str, environment: dict[str, str] | None = None) -> str:
    """Run a deterministic Git command."""

    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    ).stdout.strip()


def initialize_repository(repository: Path) -> str:
    """Create one public fixture checkout at a fixed source instant."""

    git(repository, "init", "--quiet", "--initial-branch", "main")
    git(repository, "config", "user.name", "Private Fixture Author")
    git(repository, "config", "user.email", "private-author@example.test")
    (repository / "README.md").write_text("# Public fixture\n", encoding="utf-8")
    private_report = repository / PRIVATE_REPORT_PATH
    private_report.parent.mkdir(parents=True)
    private_report.write_text("private raw evidence\n", encoding="utf-8")
    git(repository, "add", "README.md", PRIVATE_REPORT_PATH)
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_DATE": "2026-08-14T12:00:00Z",
            "GIT_COMMITTER_DATE": "2026-08-14T12:00:00Z",
        }
    )
    git(repository, "commit", "--quiet", "--message", "private raw subject", environment=environment)
    return git(repository, "rev-parse", "HEAD")


class QuietHandler(SimpleHTTPRequestHandler):
    """Serve fixture output without writing request logs to the test stream."""

    def log_message(self, format: str, *args: object) -> None:
        return None


class RepositoryIntelligenceBundleTests(unittest.TestCase):
    """Prove composition, provenance, routing, privacy, and byte stability."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.repository = Path(self.temporary_directory.name) / "repository"
        self.repository.mkdir()
        self.source_commit = initialize_repository(self.repository)
        self.public_fixture = json.loads(
            (
                FIXTURE_ROOT
                / "repository-intelligence-privacy/public-repository.json"
            ).read_text(encoding="utf-8")
        )
        self.private_fixture = json.loads(
            (
                FIXTURE_ROOT
                / "repository-intelligence-privacy/private-work.json"
            ).read_text(encoding="utf-8")
        )
        self.private_repository_fixture = json.loads(
            (
                FIXTURE_ROOT
                / "repository-intelligence-privacy/private-repository.json"
            ).read_text(encoding="utf-8")
        )
        self.work_root = self.repository / ".cache/repository-intelligence"
        activity = self.work_root / "activity"
        activity.mkdir(parents=True)
        (activity / "private-work.json").write_text(
            json.dumps(self.private_fixture),
            encoding="utf-8",
        )
        self.reports_root = self.repository / ".reports"
        osv_root = self.reports_root / "osv"
        osv_root.mkdir(parents=True)
        osv = json.loads(
            (
                FIXTURE_ROOT
                / "repository-intelligence-dashboard/osv/summary.json"
            ).read_text(encoding="utf-8")
        )
        osv["repository"] = self.public_fixture["repository"]
        osv["commit"] = self.source_commit
        osv["execution"]["message"] = self.private_fixture["private_issue_body"]
        osv["links"]["detail"] = "https://github.com/example/repository?token=private"
        osv["osv"]["severity_threshold"] = self.private_fixture["private_issue_body"]
        osv_root.joinpath("summary.json").write_text(json.dumps(osv), encoding="utf-8")

    def validate_bundle(
        self,
        output: Path,
        *,
        repository: str | None = None,
        visibility: str = "public",
        generator_ref: str = GENERATOR_COMMIT,
        generator_commit: str = GENERATOR_COMMIT,
        generator_immutable: bool = True,
    ) -> None:
        """Run the complete bundle validator with explicit expected provenance."""

        bundle_validator.validate_bundle(
            repository_root=self.repository,
            output_root=output,
            repository=repository or self.public_fixture["repository"],
            repository_visibility=visibility,
            source_commit=self.source_commit,
            generator_version="1.1.0",
            generator_source_ref=generator_ref,
            generator_source_commit=generator_commit,
            generator_immutable=generator_immutable,
        )

    def build_bundle(
        self,
        relative_output: str,
        *,
        repository: str | None = None,
        visibility: str = "public",
        default_branch: str = "main",
        generator_ref: str = GENERATOR_COMMIT,
        generator_commit: str = GENERATOR_COMMIT,
        generator_immutable: bool = True,
        reports_directory: str = ".reports",
        analytics_summary: Path | None = None,
        repository_tree: Path | None = None,
    ) -> Path:
        """Generate the complete five-file public subtree."""

        consumer_repository = repository or self.public_fixture["repository"]
        output_preparer.validate_directory_layout(
            self.repository,
            relative_output,
            ".cache/repository-intelligence",
            reports_directory,
        )
        output = output_preparer.prepare_output_directory(self.repository, relative_output)
        dashboard = dashboard_builder.build_dashboard(
            repository_root=self.repository,
            reports_root=self.repository / reports_directory,
            repository=consumer_repository,
            default_branch=default_branch,
            source_commit=self.source_commit,
            as_of=AS_OF,
            analytics_summary=analytics_summary,
            repository_tree=repository_tree,
        )
        provenance = dashboard_builder.build_bundle_provenance(
            repository=consumer_repository,
            source_commit=self.source_commit,
            generated_at=AS_OF,
            timestamp_source="consumer-source-commit",
            generator_version="1.1.0",
            generator_repository="egohygiene/relay",
            generator_ref=generator_ref,
            generator_commit=generator_commit,
            generator_immutable=generator_immutable,
            consumer_visibility=visibility,
        )
        dashboard_builder.write_dashboard_bundle(
            output,
            dashboard,
            ACTION_ROOT / "assets/dashboard.css",
            ACTION_ROOT / "assets/explorer.js",
            provenance,
        )
        self.validate_bundle(
            output,
            repository=consumer_repository,
            visibility=visibility,
            generator_ref=generator_ref,
            generator_commit=generator_commit,
            generator_immutable=generator_immutable,
        )
        return output

    def test_public_fixture_composes_without_copying_private_work(self) -> None:
        root_index = self.repository / "dist/index.html"
        cname = self.repository / "dist/CNAME"
        root_index.parent.mkdir()
        root_index.write_text("root landing page\n", encoding="utf-8")
        cname.write_text("example.test\n", encoding="utf-8")

        output = self.build_bundle("dist/intelligence")

        self.assertEqual(
            {path.name for path in output.iterdir()},
            set(self.public_fixture["expected_files"]),
        )
        self.assertEqual(root_index.read_text(encoding="utf-8"), "root landing page\n")
        self.assertEqual(cname.read_text(encoding="utf-8"), "example.test\n")
        public_bytes = b"\n".join(path.read_bytes() for path in sorted(output.iterdir()))
        for value in self.private_fixture.values():
            if isinstance(value, str) and value != "private":
                self.assertNotIn(value.encode("utf-8"), public_bytes)

    def test_identical_inputs_produce_byte_stable_public_bundles(self) -> None:
        first = self.build_bundle("first/intelligence")
        second = self.build_bundle("second/intelligence")

        first_files = {path.name: path.read_bytes() for path in sorted(first.iterdir())}
        second_files = {path.name: path.read_bytes() for path in sorted(second.iterdir())}

        self.assertEqual(first_files, second_files)

    def test_report_local_fragment_cannot_enter_the_generated_bundle(self) -> None:
        sentinel = "PRIVATE-ISSUE-BODY-SENTINEL-LEAK"
        summary_path = self.reports_root / "osv/summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["links"]["detail"] = f"./summary.json#{sentinel}"
        summary_path.write_text(json.dumps(summary), encoding="utf-8")

        output = self.build_bundle("fragment/intelligence")
        public_bytes = b"\n".join(path.read_bytes() for path in sorted(output.iterdir()))

        self.assertNotIn(sentinel.encode("utf-8"), public_bytes)

    def test_action_like_bundle_excludes_nondefault_report_evidence(self) -> None:
        tree_script = ACTION_ROOT / "scripts/generate_repository_intelligence.py"
        analytics_script = ACTION_ROOT / "scripts/generate_repository_analytics.py"
        excluded_paths = ".git,.cache,evidence,dist"
        subprocess.run(
            [
                sys.executable,
                str(tree_script),
                "--repo-root",
                str(self.repository),
                "--output-root",
                str(self.work_root),
                "--ref",
                "HEAD",
                "--max-depth",
                "10",
                "--excluded-paths",
                excluded_paths,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        analytics_path = self.work_root / "analytics/summary.json"
        subprocess.run(
            [
                sys.executable,
                str(analytics_script),
                "--repo-root",
                str(self.repository),
                "--output",
                str(analytics_path),
                "--ref",
                "HEAD",
                "--since",
                "1 year ago",
                "--excluded-paths",
                excluded_paths,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        output = self.build_bundle(
            "dist/intelligence",
            reports_directory="evidence",
            analytics_summary=analytics_path,
            repository_tree=self.work_root / "tree/repo.json",
        )
        public_bytes = b"\n".join(path.read_bytes() for path in sorted(output.iterdir()))

        self.assertNotIn(PRIVATE_REPORT_PATH.encode("utf-8"), public_bytes)
        self.assertNotIn(b"private raw evidence", public_bytes)
        self.assertIn(b'"availability": "available"', public_bytes)

    def test_private_repository_is_classified_for_internal_artifacts(self) -> None:
        fixture = self.private_repository_fixture
        output = self.build_bundle(
            "private-site/intelligence",
            repository=fixture["repository"],
            visibility=fixture["visibility"],
        )
        provenance = json.loads(
            (output / "provenance.json").read_text(encoding="utf-8")
        )
        public_bytes = b"\n".join(path.read_bytes() for path in sorted(output.iterdir()))

        self.assertEqual(provenance["consumer"]["visibility"], "private")
        self.assertEqual(
            provenance["projection"]["classification"],
            fixture["expected_classification"],
        )
        self.assertEqual(provenance["projection"]["deployment_authority"], "consumer")
        self.assertNotIn(
            fixture["private_repository_metadata"].encode("utf-8"),
            public_bytes,
        )

    def test_mutable_reusable_workflow_ref_retains_commit_without_claiming_immutability(self) -> None:
        mutable_ref = (
            "egohygiene/relay/.github/workflows/"
            "repository-intelligence.yml@refs/tags/v1"
        )
        output = self.build_bundle(
            "moving-ref/intelligence",
            generator_ref=mutable_ref,
            generator_commit=GENERATOR_COMMIT,
            generator_immutable=False,
        )
        provenance = json.loads(
            (output / "provenance.json").read_text(encoding="utf-8")
        )

        self.assertEqual(provenance["generator"]["source_commit"], GENERATOR_COMMIT)
        self.assertFalse(provenance["generator"]["immutable"])

    def test_private_named_branch_is_not_misclassified_as_a_runner_path(self) -> None:
        self.build_bundle(
            "branch-name/intelligence",
            default_branch="feature/private/ref",
        )

    def test_percent_encoded_contributor_identity_cannot_enter_public_bundle(self) -> None:
        report_path = self.reports_root / "osv/summary.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        for index, encoded_identity in enumerate(
            ("private-author%40example.test", "private-author%2540example.test")
        ):
            with self.subTest(encoded_identity=encoded_identity):
                report["links"]["detail"] = (
                    f"https://github.com/{self.public_fixture['repository']}/blob/"
                    f"{self.source_commit}/{encoded_identity}"
                )
                report_path.write_text(json.dumps(report), encoding="utf-8")

                output = self.build_bundle(f"encoded-identity-{index}/intelligence")
                public_bytes = b"\n".join(
                    path.read_bytes() for path in sorted(output.iterdir())
                )

                self.assertNotIn(encoded_identity.encode("utf-8"), public_bytes)
                self.assertNotIn(b"private-author@example.test", public_bytes)

                route = output / "index.html"
                original = route.read_text(encoding="utf-8")
                route.write_text(
                    original
                    + (
                        "\n<a href=\"https://github.com/"
                        f"{self.public_fixture['repository']}/blob/{self.source_commit}/"
                        f"{encoded_identity}\">identity</a>\n"
                    ),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    bundle_validator.BundleValidationError,
                    "encoded identity",
                ):
                    self.validate_bundle(output)

    def test_intelligence_route_and_assets_are_servable(self) -> None:
        self.build_bundle("dist/intelligence")
        self.build_bundle("project/repository/intelligence")
        handler = functools.partial(QuietHandler, directory=str(self.repository))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        bases = (
            f"http://127.0.0.1:{server.server_port}/dist/intelligence/",
            f"http://127.0.0.1:{server.server_port}/project/repository/intelligence/",
        )

        for base in bases:
            for relative in ("", "styles.css", "explorer.js", "summary.json", "provenance.json"):
                with self.subTest(base=base, relative=relative), urlopen(
                    base + relative,
                    timeout=5,
                ) as response:
                    self.assertEqual(response.status, 200)

    def test_validator_rejects_unexpected_broken_and_private_output(self) -> None:
        output = self.build_bundle("dist/intelligence")
        (output / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")
        with self.assertRaisesRegex(bundle_validator.BundleValidationError, "unexpected"):
            self.validate_bundle(output)
        (output / "unexpected.txt").unlink()

        index = output / "index.html"
        original = index.read_text(encoding="utf-8")
        index.write_text(original.replace("./styles.css", "../private.css"), encoding="utf-8")
        with self.assertRaisesRegex(bundle_validator.BundleValidationError, "traversal"):
            self.validate_bundle(output)
        index.write_text(original, encoding="utf-8")
        with self.assertRaisesRegex(bundle_validator.BundleValidationError, "relative"):
            bundle_validator.resolve_local_reference(
                output,
                "%2Fetc%2Fpasswd",
                self.public_fixture["repository"],
                self.source_commit,
            )

        with self.assertRaisesRegex(
            bundle_validator.BundleValidationError,
            "nonstandard HTTPS port",
        ):
            bundle_validator.validate_https_reference(
                "https://github.com:444/example/repository/actions/runs/123",
                self.public_fixture["repository"],
                self.source_commit,
            )
        with self.assertRaisesRegex(
            bundle_validator.BundleValidationError,
            "outside the consumer contract",
        ):
            bundle_validator.validate_https_reference(
                f"https://github.com/example/repository/commit/{'b' * 40}",
                self.public_fixture["repository"],
                self.source_commit,
            )

        index.write_text(
            original
            + '\n<a href="./summary.json#PRIVATE-ISSUE-BODY-SENTINEL-LEAK">leak</a>\n',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            bundle_validator.BundleValidationError,
            "unsupported fragment",
        ):
            self.validate_bundle(output)
        index.write_text(original, encoding="utf-8")

        summary_path = output / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["unexpected_contract_field"] = True
        summary_path.write_text(json.dumps(summary), encoding="utf-8")
        with self.assertRaisesRegex(bundle_validator.BundleValidationError, "invalid members"):
            self.validate_bundle(output)
        summary.pop("unexpected_contract_field")
        summary_path.write_text(
            json.dumps(summary, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        original_summary = summary_path.read_text(encoding="utf-8")
        mutations = {
            "execution state": lambda value: value["producers"]["osv"]["execution"].update(
                {"state": "green"}
            ),
            "producer commit": lambda value: value["producers"]["osv"].update(
                {"commit": "b" * 40}
            ),
            "negative finding": lambda value: value["producers"]["osv"]["findings"].update(
                {"total": -99}
            ),
            "empty analytics": lambda value: value["analytics"].update(
                {"availability": "available", "summary": {}}
            ),
            "vitality commit": lambda value: value["vitality"].update(
                {"source_commit": "b" * 40}
            ),
            "contradictory state counts": lambda value: value["states"]["findings"].update(
                {"attention": 0, "clear": 3, "unknown": 0}
            ),
        }
        for label, mutate in mutations.items():
            changed = json.loads(original_summary)
            mutate(changed)
            summary_path.write_text(json.dumps(changed), encoding="utf-8")
            with self.subTest(label=label), self.assertRaises(
                bundle_validator.BundleValidationError
            ):
                self.validate_bundle(output)
        summary_path.write_text(original_summary, encoding="utf-8")

        styles = output / "styles.css"
        original_styles = styles.read_text(encoding="utf-8")
        styles.write_text(
            original_styles + "\n/* changed */\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(bundle_validator.BundleValidationError, "canonical Relay asset"):
            self.validate_bundle(output)
        styles.write_text(original_styles, encoding="utf-8")

        index.write_text(original + "\n<!-- /home/runner/work/private/file -->\n", encoding="utf-8")
        with self.assertRaisesRegex(bundle_validator.BundleValidationError, "local filesystem path"):
            self.validate_bundle(output)


if __name__ == "__main__":
    unittest.main()
