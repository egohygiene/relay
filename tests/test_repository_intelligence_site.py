# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Tests for the routed Repository Intelligence evidence views."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACTION_ROOT = REPOSITORY_ROOT / "actions/repository-intelligence"
ACTION_MANIFEST = ACTION_ROOT / "action.yml"
FIXTURE = REPOSITORY_ROOT / "tests/fixtures/repository-intelligence-site/snapshot.json"
AS_OF = datetime(2026, 8, 25, 14, tzinfo=UTC)
GENERATOR_COMMIT = "a" * 40


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dashboard_builder = load_module(
    "site_dashboard_builder",
    ACTION_ROOT / "scripts/generate_repository_intelligence_dashboard.py",
)
site_builder = load_module(
    "repository_intelligence_site_builder",
    ACTION_ROOT / "scripts/generate_repository_intelligence_site.py",
)
bundle_validator = load_module(
    "site_bundle_validator",
    ACTION_ROOT / "scripts/validate_repository_intelligence_bundle.py",
)


def git(repository: Path, *arguments: str, environment: dict[str, str] | None = None) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    ).stdout.strip()


def initialize_repository(repository: Path) -> str:
    git(repository, "init", "--quiet", "--initial-branch", "main")
    git(repository, "config", "user.name", "Site Fixture")
    git(repository, "config", "user.email", "fixture@example.test")
    (repository / "README.md").write_text("# Repository\n", encoding="utf-8")
    git(repository, "add", "README.md")
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_DATE": "2026-08-25T14:00:00Z",
            "GIT_COMMITTER_DATE": "2026-08-25T14:00:00Z",
        }
    )
    git(repository, "commit", "--quiet", "--message", "fixture", environment=environment)
    return git(repository, "rev-parse", "HEAD")


class RepositoryIntelligenceSiteTests(unittest.TestCase):
    """Prove the shell remains truthful, accessible, local-first, and deterministic."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.repository = Path(self.temporary_directory.name) / "repository"
        self.repository.mkdir()
        self.source_commit = initialize_repository(self.repository)
        self.snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))
        serialized = json.dumps(self.snapshot).replace("1" * 40, self.source_commit)
        self.snapshot = json.loads(serialized)
        health_fixture = json.loads(
            (
                REPOSITORY_ROOT
                / "tests/fixtures/repository-intelligence-health/snapshot.json"
            ).read_text(encoding="utf-8")
        )
        self.snapshot["views"]["health"] = health_fixture["views"]["health"]

    def build(self, relative: str, *, include_snapshot: bool = True) -> Path:
        output = self.repository / relative
        output.mkdir(parents=True)
        dashboard = dashboard_builder.build_dashboard(
            repository_root=self.repository,
            reports_root=self.repository / ".reports",
            repository="example/repository",
            default_branch="main",
            source_commit=self.source_commit,
            as_of=AS_OF,
        )
        provenance = dashboard_builder.build_bundle_provenance(
            repository="example/repository",
            source_commit=self.source_commit,
            generated_at=AS_OF,
            timestamp_source="consumer-source-commit",
            generator_version="1.2.0",
            generator_repository="egohygiene/relay",
            generator_ref=GENERATOR_COMMIT,
            generator_commit=GENERATOR_COMMIT,
            generator_immutable=True,
            consumer_visibility="public",
        )
        dashboard_builder.write_dashboard_bundle(
            output,
            dashboard,
            ACTION_ROOT / "assets/dashboard.css",
            ACTION_ROOT / "assets/explorer.js",
            provenance,
            "dashboard",
        )
        snapshot_path = self.repository / ".cache/repository-intelligence/snapshot.json"
        if include_snapshot:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(
                json.dumps(self.snapshot, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        arguments = [
            "python3",
            str(ACTION_ROOT / "scripts/generate_repository_intelligence_site.py"),
            "--repository-root",
            str(self.repository),
            "--output-root",
            str(output),
            "--summary",
            str(output / "summary.json"),
            "--provenance",
            str(output / "provenance.json"),
            "--repository",
            "example/repository",
            "--source-commit",
            self.source_commit,
            "--stylesheet-source",
            str(ACTION_ROOT / "assets/site.css"),
            "--script-source",
            str(ACTION_ROOT / "assets/site.js"),
        ]
        if include_snapshot:
            arguments.extend(["--snapshot", str(snapshot_path)])
        subprocess.run(arguments, check=True, capture_output=True, text=True)
        supporting_arguments = [
            "--repository-root",
            str(self.repository),
            "--output-root",
            str(output),
            "--summary",
            str(output / "summary.json"),
            "--provenance",
            str(output / "provenance.json"),
            "--repository",
            "example/repository",
            "--source-commit",
            self.source_commit,
        ]
        if include_snapshot:
            supporting_arguments.extend(["--snapshot", str(snapshot_path)])
        for script in (
            "render_repository_intelligence_dependencies.py",
            "render_repository_intelligence_compare.py",
        ):
            subprocess.run(
                ["python3", str(ACTION_ROOT / "scripts" / script), *supporting_arguments],
                check=True,
                capture_output=True,
                text=True,
            )
        bundle_validator.validate_bundle(
            repository_root=self.repository,
            output_root=output,
            repository="example/repository",
            repository_visibility="public",
            source_commit=self.source_commit,
            generator_version="1.2.0",
            generator_source_ref=GENERATOR_COMMIT,
            generator_source_commit=GENERATOR_COMMIT,
            generator_immutable=True,
        )
        return output

    def test_overview_and_now_answer_distinct_questions(self) -> None:
        output = self.build("dist/intelligence")
        root = (output / "index.html").read_text(encoding="utf-8")
        routed = (output / "now/index.html").read_text(encoding="utf-8")
        self.assertIn("Choose the evidence question", root)
        self.assertIn('id="intelligence-heading"', root)
        self.assertIn("Inspect the analytics dashboard", root)
        for label in (
            "Now",
            "Roadmap",
            "Decisions",
            "Journey",
            "Dependencies",
            "Health",
            "Releases",
            "Work",
            "Search",
            "Compare",
        ):
            self.assertIn(f"Open {label}", root)
        self.assertNotIn('id="now-heading"', root)
        self.assertNotIn("The next three grounded moves", root)
        for text in (
            "Where things stand",
            "Current quests",
            "Blockers",
            "Checks that regressed",
            "Decisions awaiting closure",
            "The next three grounded moves",
            "The shared shell is available",
            "Establish the evidence contract",
            "Open canonical work",
        ):
            self.assertIn(text, routed)
        self.assertIn('data-ri-route="intelligence"', root)
        self.assertIn('aria-current="page">Overview</a>', root)
        self.assertIn('data-ri-route="now"', routed)
        self.assertIn('aria-current="page">Now</a>', routed)
        self.assertNotIn("Incomplete work is blocked", routed)
        self.assertTrue((output / "dashboard/index.html").is_file())
        dashboard = (output / "dashboard/index.html").read_text(encoding="utf-8")
        self.assertIn('aria-label="Repository Intelligence views"', dashboard)
        self.assertIn('href="../now/"', dashboard)
        self.assertIn('href="../dependencies/"', dashboard)
        self.assertIn('href="../releases/"', dashboard)
        self.assertIn("data-preserve-context", dashboard)

    def test_ready_queue_is_bounded_to_three_actions(self) -> None:
        snapshot = json.loads(json.dumps(self.snapshot))
        template_entity = snapshot["views"]["now"]["next_ready"][0]
        template_step = snapshot["views"]["roadmap"]["steps"][1]
        ready = []
        steps = [snapshot["views"]["roadmap"]["steps"][0]]
        for index in range(1, 5):
            candidate = json.loads(json.dumps(template_entity))
            candidate["id"] = f"ri:example/repository:roadmap-step:EX-NEXT-{index}"
            candidate["key"] = f"EX-NEXT-{index}"
            candidate["title"] = f"Ready action {index}"
            step = json.loads(json.dumps(template_step))
            step["entity"] = candidate
            ready.append(candidate)
            steps.append(step)
        snapshot["views"]["now"]["next_ready"] = ready
        snapshot["views"]["roadmap"]["steps"] = steps
        rendered = site_builder.render_next_actions(snapshot)
        self.assertEqual(rendered.count('<li class="ri-action"'), 3)
        self.assertIn("Ready action 3", rendered)
        self.assertNotIn("Ready action 4", rendered)

    def test_shell_reserves_every_route_with_consistent_navigation(self) -> None:
        output = self.build("dist/intelligence")
        expected_routes = {route for route, _ in site_builder.ROUTES}
        for route in expected_routes:
            rendered = (output / route / "index.html").read_text(encoding="utf-8")
            self.assertIn('class="ri-route-nav"', rendered)
            self.assertIn(f'data-ri-route="{route}"', rendered)
            self.assertIn('aria-current="page"', rendered)
            self.assertIn("../site.css", rendered)
            self.assertIn("../site.js", rendered)

    def test_url_filters_keyboard_focus_and_local_resume_are_explicit(self) -> None:
        output = self.build("dist/intelligence")
        rendered = (output / "now/index.html").read_text(encoding="utf-8")
        script = (output / "site.js").read_text(encoding="utf-8")
        styles = (output / "site.css").read_text(encoding="utf-8")
        self.assertIn("URLSearchParams", script)
        self.assertIn("history.replaceState", script)
        self.assertIn("data-preserve-context", rendered)
        self.assertIn("contextLinks", script)
        self.assertIn("transferable", script)
        self.assertIn('next.searchParams.set("entity", identifier)', script)
        self.assertIn('selected?.closest("[data-entity-id]")', script)
        self.assertNotIn("target.hash = current.hash", script)
        self.assertIn("localStorage", script)
        self.assertIn("scrollY", script)
        self.assertIn("window.scrollTo", script)
        self.assertIn('searchParams.set("resume", "1")', script)
        self.assertIn("ArrowDown", script)
        self.assertIn('event.key === "/"', script)
        self.assertIn("Resume data stays in this browser", rendered)
        self.assertIn('aria-live="polite"', rendered)
        self.assertIn('href="#main-content"', rendered)
        self.assertIn('@media (prefers-reduced-motion: reduce)', styles)
        self.assertIn("@media print", styles)
        self.assertIn("@media (max-width: 48rem)", styles)
        self.assertNotIn("localStorage", (output / "summary.json").read_text(encoding="utf-8"))
        self.assertNotIn("resume.v1", (output / "provenance.json").read_text(encoding="utf-8"))

    def test_route_context_keeps_supported_values_without_leaking_hashes_or_secrets(self) -> None:
        harness = r'''
const fs = require("fs");
const links = [
  { original: "../health/", href: "" },
  { original: "../search/#search-heading", href: "" },
  { original: "https://github.com/egohygiene/relay/issues/29", href: "" },
].map((link) => ({
  ...link,
  getAttribute(name) { return name === "href" ? this.original : null; },
  addEventListener() {},
}));
global.location = new URL("https://repo.example/intelligence/roadmap/?q=owner&entity=ri%3Aexample&access_token=secret#quest-local");
global.history = { replaceState() {} };
global.localStorage = { getItem() { return null; }, setItem() {}, removeItem() {} };
global.CustomEvent = class CustomEvent { constructor(type) { this.type = type; } };
global.requestAnimationFrame = () => 0;
global.cancelAnimationFrame = () => {};
global.document = {
  body: { dataset: { riRepository: "example/repository", riRoute: "roadmap", riCommit: "a".repeat(40) } },
  activeElement: null,
  querySelector() { return null; },
  querySelectorAll(selector) {
    return selector === "[data-preserve-context-links] a, [data-preserve-context]" ? links : [];
  },
  getElementById() { return null; },
  addEventListener() {},
  dispatchEvent() {},
};
global.window = {
  scrollY: 0,
  addEventListener() {},
  matchMedia() { return { matches: false }; },
  clearInterval() {},
  setInterval() { return 0; },
  scrollTo() {},
};
eval(fs.readFileSync(process.argv[1], "utf8"));
process.stdout.write(JSON.stringify(links.map((link) => link.href)));
'''
        result = subprocess.run(
            ["node", "-e", harness, str(ACTION_ROOT / "assets/site.js")],
            check=True,
            capture_output=True,
            text=True,
        )
        health, search, external = json.loads(result.stdout)
        self.assertEqual(
            health,
            "https://repo.example/intelligence/health/?q=owner&entity=ri%3Aexample",
        )
        self.assertEqual(
            search,
            "https://repo.example/intelligence/search/?q=owner&entity=ri%3Aexample#search-heading",
        )
        self.assertEqual(external, "https://github.com/egohygiene/relay/issues/29")
        explorer = (ACTION_ROOT / "assets/explorer.js").read_text(encoding="utf-8")
        self.assertIn("transferableContext.has(name)", explorer)
        self.assertNotIn('name !== "resume"', explorer)
        self.assertNotIn("target.hash = current.hash", explorer)

    def test_bundle_validation_rejects_an_unmaterialized_supporting_route(self) -> None:
        output = self.build("dist/intelligence")
        health = output / "health/index.html"
        rendered = health.read_text(encoding="utf-8")
        health.write_text(
            rendered.replace('id="health-heading"', 'id="placeholder-heading"', 1),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            bundle_validator.BundleValidationError,
            "health/ was not materialized",
        ):
            bundle_validator.validate_bundle(
                repository_root=self.repository,
                output_root=output,
                repository="example/repository",
                repository_visibility="public",
                source_commit=self.source_commit,
                generator_version="1.2.0",
                generator_source_ref=GENERATOR_COMMIT,
                generator_source_commit=GENERATOR_COMMIT,
                generator_immutable=True,
            )

    def test_optional_supporting_views_can_be_absent_during_incremental_adoption(self) -> None:
        snapshot = json.loads(json.dumps(self.snapshot))
        del snapshot["views"]["health"]
        del snapshot["views"]["work"]
        validated = site_builder.validate_snapshot(
            snapshot,
            "example/repository",
            self.source_commit,
        )
        self.assertNotIn("health", validated["views"])
        self.assertNotIn("work", validated["views"])

    def test_supporting_renderer_orchestration_replaces_every_reserved_route(self) -> None:
        output = self.build("dist/intelligence")
        snapshot_path = self.repository / ".cache/repository-intelligence/snapshot.json"
        common = [
            "--repository-root",
            str(self.repository),
            "--output-root",
            str(output),
            "--summary",
            str(output / "summary.json"),
            "--provenance",
            str(output / "provenance.json"),
            "--snapshot",
            str(snapshot_path),
            "--repository",
            "example/repository",
            "--source-commit",
            self.source_commit,
        ]
        subprocess.run(
            [
                "python3",
                str(ACTION_ROOT / "scripts/render_repository_intelligence_dependencies.py"),
                *common,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "python3",
                str(ACTION_ROOT / "scripts/render_repository_intelligence_compare.py"),
                *common,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        expected = {
            "dependencies": "What depends on what?",
            "health": "What does the current evidence say?",
            "releases": "What has actually shipped?",
            "work": "What work needs attention?",
            "search": "Find a normalized repository object",
            "compare": "What structurally changed?",
        }
        for route, question in expected.items():
            with self.subTest(route=route):
                rendered = (output / route / "index.html").read_text(encoding="utf-8")
                self.assertIn(question, rendered)
                self.assertNotIn("View intentionally not materialized yet", rendered)
        bundle_validator.validate_bundle(
            repository_root=self.repository,
            output_root=output,
            repository="example/repository",
            repository_visibility="public",
            source_commit=self.source_commit,
            generator_version="1.2.0",
            generator_source_ref=GENERATOR_COMMIT,
            generator_source_commit=GENERATOR_COMMIT,
            generator_immutable=True,
        )

    def test_roadmap_renders_stable_quests_progress_and_full_evidence(self) -> None:
        output = self.build("dist/intelligence")
        rendered = (output / "roadmap/index.html").read_text(encoding="utf-8")
        foundation_id = "ri:example/repository:roadmap-step:EX-Q01"
        roadmap_id = "ri:example/repository:roadmap-step:EX-Q04"
        foundation_anchor = site_builder.stable_fragment("quest", foundation_id)
        roadmap_anchor = site_builder.stable_fragment("quest", roadmap_id)
        self.assertIn('aria-label="Roadmap chapters and quests"', rendered)
        self.assertIn(f'id="{foundation_anchor}"', rendered)
        self.assertIn(f'href="#{roadmap_anchor}"', rendered)
        self.assertIn("How progress is determined", rendered)
        self.assertIn("1/2 criteria · 50%", rendered)
        self.assertIn("Commits and other linked records are evidence, never progress units", rendered)
        self.assertIn("Unlocks", rendered)
        self.assertIn("Depends on", rendered)
        self.assertIn("Open canonical ROADMAP.md step", rendered)
        for label in (
            "Architecture Decision",
            "Issue",
            "Pull Request",
            "Commit",
            "Check",
            "Release",
            "Deployment",
            "File",
        ):
            self.assertIn(label, rendered)
        self.assertIn("Assertion", rendered)
        self.assertIn("Confidence", rendered)
        self.assertIn("Freshness", rendered)
        self.assertNotIn("View intentionally not materialized yet", rendered)

    def test_large_roadmap_keeps_static_completeness_and_virtualization_hooks(self) -> None:
        snapshot = json.loads(json.dumps(self.snapshot))
        template = snapshot["views"]["roadmap"]["steps"][1]
        steps = []
        states = [
            "planned",
            "ready",
            "active",
            "blocked",
            "complete",
            "deferred",
            "superseded",
        ]
        for index in range(120):
            step = json.loads(json.dumps(template))
            identifier = f"ri:example/repository:roadmap-step:EX-LARGE-{index:03d}"
            step["entity"].update(
                {
                    "id": identifier,
                    "key": f"EX-LARGE-{index:03d}",
                    "title": f"Large roadmap quest {index:03d}",
                    "state": states[index % len(states)],
                    "canonical_url": (
                        "https://github.com/example/repository/blob/"
                        f"{self.source_commit}/ROADMAP.md#ex-large-{index:03d}"
                    ),
                }
            )
            step["dependencies"] = [] if index == 0 else [steps[-1]["entity"]]
            step["blocked_by"] = []
            step["evidence"] = []
            step["informed_by"] = []
            step["tracked_by"] = []
            step["verified_by"] = []
            step["releases"] = []
            step["deployments"] = []
            step["changed_files"] = []
            step["exit_criteria"] = [
                {"complete": index % 2 == 0, "text": f"Criterion {index:03d}"}
            ]
            steps.append(step)
        steps[-1]["verified_by"] = [
            {
                "assertion": "authoritative",
                "canonical_url": f"https://github.com/example/repository/actions/runs/{9000 + index}",
                "confidence": "authoritative",
                "freshness": "current",
                "id": f"ri:example/repository:check:large-{index:03d}",
                "key": f"large-{index:03d}",
                "kind": "check",
                "repository": "example/repository",
                "state": "success",
                "title": f"Large evidence record {index:03d}",
            }
            for index in range(90)
        ]
        snapshot["views"]["roadmap"]["steps"] = steps
        snapshot["views"]["roadmap"]["roots"] = [steps[0]["entity"]["id"]]
        self.snapshot = snapshot
        output = self.build("dist/intelligence")
        rendered = (output / "roadmap/index.html").read_text(encoding="utf-8")
        script = (output / "site.js").read_text(encoding="utf-8")
        self.assertEqual(rendered.count("data-roadmap-quest"), 120)
        self.assertIn('data-evidence-total="91"', rendered)
        self.assertEqual(rendered.count("Large evidence record"), 90)
        self.assertIn("requestAnimationFrame", script)
        self.assertIn("data-evidence-viewport", script)
        self.assertIn("IntersectionObserver", script)
        self.assertIn("aria-posinset", rendered)
        self.assertIn("aria-setsize", rendered)

    def test_decisions_render_authority_lineage_facets_compare_and_evidence(self) -> None:
        output = self.build("dist/intelligence")
        rendered = (output / "decisions/index.html").read_text(encoding="utf-8")
        old_id = "ri:example/repository:architecture-decision:ADR-006"
        current_id = "ri:example/repository:architecture-decision:ADR-007"
        old_anchor = site_builder.stable_fragment("decision", old_id)
        current_anchor = site_builder.stable_fragment("decision", current_id)
        roadmap_anchor = site_builder.stable_fragment(
            "quest",
            "ri:example/repository:roadmap-step:EX-Q04",
        )
        self.assertIn("The decision ledger", rendered)
        self.assertIn("Inherited organization decisions", rendered)
        self.assertIn("Repository-local decisions", rendered)
        self.assertIn(f'id="{old_anchor}"', rendered)
        self.assertIn(f'href="#{current_anchor}"', rendered)
        self.assertIn(f'href="../roadmap/#{roadmap_anchor}"', rendered)
        self.assertIn("Decision lifecycle", rendered)
        self.assertIn("Implementation", rendered)
        self.assertIn("Open canonical ADR", rendered)
        self.assertIn("Represented revision", rendered)
        self.assertIn("Context, alternatives, and consequences remain in the canonical ADR", rendered)
        for status in ("Accepted", "Deprecated", "Proposed", "Rejected", "Superseded"):
            self.assertIn(status, rendered)
        for label in (
            "Authority",
            "Affected component",
            "Date",
            "Domain",
            "Owner",
            "Roadmap",
        ):
            self.assertIn(label, rendered)
        self.assertIn("Place two decisions side by side", rendered)
        self.assertIn("data-compare-left", rendered)
        self.assertIn("data-compare-right", rendered)
        self.assertIn('data-assertion="inferred"', rendered)
        for label in ("Commit", "Issue", "Pull Request", "Release", "Check"):
            self.assertIn(label, rendered)
        self.assertNotIn("View intentionally not materialized yet", rendered)

    def test_large_decision_history_remains_complete_and_navigable(self) -> None:
        snapshot = json.loads(json.dumps(self.snapshot))
        template = snapshot["views"]["decisions"]["decisions"][2]
        statuses = ["proposed", "accepted", "rejected", "deprecated", "superseded"]
        implementations = [
            "not_started",
            "in_progress",
            "not_applicable",
            "implemented",
            "verified",
        ]
        decisions = []
        for index in range(180):
            decision = json.loads(json.dumps(template))
            identifier = f"ri:example/repository:architecture-decision:ADR-{index + 100:03d}"
            decision["entity"].update(
                {
                    "id": identifier,
                    "key": f"ADR-{index + 100:03d}",
                    "title": f"Historical decision {index:03d}",
                    "state": statuses[index % len(statuses)],
                    "canonical_url": (
                        "https://github.com/example/repository/blob/"
                        f"{self.source_commit}/docs/decisions/ADR-{index + 100:03d}.md"
                    ),
                }
            )
            decision["date"] = f"2026-{(index % 12) + 1:02d}-{(index % 28) + 1:02d}"
            decision["implementation_status"] = implementations[
                index % len(implementations)
            ]
            decision["evidence"] = []
            decision["informs"] = []
            decision["superseded_by"] = []
            decision["supersedes"] = []
            decision["tracked_by"] = []
            decision["verified_by"] = []
            decisions.append(decision)
        snapshot["views"]["decisions"]["decisions"] = decisions
        self.snapshot = snapshot
        output = self.build("dist/intelligence")
        rendered = (output / "decisions/index.html").read_text(encoding="utf-8")
        script = (output / "site.js").read_text(encoding="utf-8")
        self.assertEqual(rendered.count("data-decision-record"), 180)
        self.assertEqual(rendered.count("data-decision-index href"), 180)
        self.assertIn("Historical decision 179", rendered)
        self.assertIn("IntersectionObserver", script)
        self.assertIn("data-decision-index", script)
        self.assertIn("ArrowDown", script)

    def test_journey_renders_release_chapters_lanes_context_and_controls(self) -> None:
        output = self.build("dist/intelligence")
        rendered = (output / "journey/index.html").read_text(encoding="utf-8")
        script = (output / "site.js").read_text(encoding="utf-8")
        chapter_anchor = site_builder.stable_fragment(
            "chapter",
            "chapter:through:v1.2.0",
        )
        event_anchor = site_builder.stable_fragment(
            "event",
            "event:commit-created",
        )
        roadmap_anchor = site_builder.stable_fragment(
            "quest",
            "ri:example/repository:roadmap-step:EX-Q04",
        )
        decision_anchor = site_builder.stable_fragment(
            "decision",
            "ri:example/repository:architecture-decision:ADR-007",
        )
        self.assertIn("The repository journey", rendered)
        self.assertIn("Deterministic chapters", rendered)
        self.assertIn("Only projected merges", rendered)
        self.assertIn("Unclassified context", rendered)
        self.assertIn(f'id="{chapter_anchor}"', rendered)
        self.assertIn(f'id="{event_anchor}"', rendered)
        self.assertIn(f'href="../roadmap/#{roadmap_anchor}"', rendered)
        self.assertIn(f'href="../decisions/#{decision_anchor}"', rendered)
        self.assertIn("Closed by the authoritative v1.2.0 release event", rendered)
        self.assertIn("Open chapter containing events after the latest", rendered)
        self.assertIn("days between projected lifecycle events", rendered)
        self.assertIn("not evidence that no repository work occurred", rendered)
        self.assertIn("Pull request merged", rendered)
        self.assertIn("Check regressed", rendered)
        self.assertIn("Quest-level changed files", rendered)
        self.assertIn("does not claim that this individual event changed each file", rendered)
        for lane in ("Intent", "Work", "Code", "Proof", "Delivery"):
            self.assertIn(lane, rendered)
        self.assertIn("data-journey-replay", rendered)
        self.assertIn("data-journey-scrubber", rendered)
        self.assertIn("data-journey-compare", rendered)
        self.assertIn("Open playback and chapter comparison tools", rendered)
        self.assertIn("data-journey-date-from", rendered)
        self.assertIn("data-journey-date-to", rendered)
        self.assertIn("Branch names and file paths are not projected", rendered)
        self.assertIn("prefers-reduced-motion", script)
        self.assertIn("setInterval", script)
        self.assertIn("journey-left", script)
        self.assertNotIn("View intentionally not materialized yet", rendered)

    def test_large_journey_keeps_every_static_event_and_browser_virtualization(self) -> None:
        snapshot = json.loads(json.dumps(self.snapshot))
        template = snapshot["views"]["journey"]["events"][-1]
        events = []
        started = datetime(2026, 8, 1, 9, tzinfo=UTC)
        for index in range(240):
            event = json.loads(json.dumps(template))
            commit = f"{index + 1:040x}"
            occurred_at = (started + timedelta(minutes=index)).isoformat().replace(
                "+00:00",
                "Z",
            )
            event.update(
                {
                    "id": f"event:historical-commit-{index:03d}",
                    "occurred_at": occurred_at,
                    "subject": f"ri:example/repository:commit:{commit}",
                }
            )
            event["subject_entity"].update(
                {
                    "id": event["subject"],
                    "key": commit,
                    "title": f"Historical commit {index:03d}",
                    "canonical_url": f"https://github.com/example/repository/commit/{commit}",
                }
            )
            event["provenance"] = [f"source:commit-{index:03d}"]
            events.append(event)
        snapshot["views"]["journey"] = {
            "chapters": [
                {
                    "boundary": None,
                    "end_at": events[-1]["occurred_at"],
                    "event_ids": [event["id"] for event in events],
                    "id": "chapter:after:unreleased",
                    "start_at": events[0]["occurred_at"],
                    "title": "Unreleased history",
                }
            ],
            "events": events,
        }
        self.snapshot = snapshot
        output = self.build("dist/intelligence")
        rendered = (output / "journey/index.html").read_text(encoding="utf-8")
        styles = (output / "site.css").read_text(encoding="utf-8")
        self.assertEqual(rendered.count("data-journey-event data-journey-event-id"), 240)
        self.assertIn("Historical commit 239", rendered)
        self.assertIn('data-virtualization="content-visibility"', rendered)
        self.assertIn("content-visibility: auto", styles)
        self.assertIn('aria-posinset="240"', rendered)
        self.assertIn('aria-setsize="240"', rendered)

    def test_bundle_validation_rejects_a_broken_journey_context_link(self) -> None:
        output = self.build("dist/intelligence")
        journey = output / "journey/index.html"
        rendered = journey.read_text(encoding="utf-8")
        roadmap_anchor = site_builder.stable_fragment(
            "quest",
            "ri:example/repository:roadmap-step:EX-Q04",
        )
        journey.write_text(
            rendered.replace(
                f'href="../roadmap/#{roadmap_anchor}"',
                'href="../roadmap/#quest-missing"',
                1,
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            bundle_validator.BundleValidationError,
            "unsupported fragment",
        ):
            bundle_validator.validate_bundle(
                repository_root=self.repository,
                output_root=output,
                repository="example/repository",
                repository_visibility="public",
                source_commit=self.source_commit,
                generator_version="1.2.0",
                generator_source_ref=GENERATOR_COMMIT,
                generator_source_commit=GENERATOR_COMMIT,
                generator_immutable=True,
            )

    def test_journey_links_only_full_immutable_historical_commits(self) -> None:
        output = self.build("dist/intelligence")
        journey = output / "journey/index.html"
        rendered = journey.read_text(encoding="utf-8")
        historical = "2" * 40
        self.assertIn(
            f"https://github.com/example/repository/commit/{historical}",
            rendered,
        )
        journey.write_text(
            rendered.replace(
                f"https://github.com/example/repository/commit/{historical}",
                "https://github.com/example/repository/commit/2222222",
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            bundle_validator.BundleValidationError,
            "outside the consumer contract",
        ):
            bundle_validator.validate_bundle(
                repository_root=self.repository,
                output_root=output,
                repository="example/repository",
                repository_visibility="public",
                source_commit=self.source_commit,
                generator_version="1.2.0",
                generator_source_ref=GENERATOR_COMMIT,
                generator_source_commit=GENERATOR_COMMIT,
                generator_immutable=True,
            )

    def test_journey_contract_rejects_order_partition_and_boundary_drift(self) -> None:
        unordered = json.loads(json.dumps(self.snapshot))
        unordered["views"]["journey"]["events"][0], unordered["views"]["journey"][
            "events"
        ][1] = (
            unordered["views"]["journey"]["events"][1],
            unordered["views"]["journey"]["events"][0],
        )
        with self.assertRaisesRegex(site_builder.SiteInputError, "ordered"):
            site_builder.validate_snapshot(
                unordered,
                "example/repository",
                self.source_commit,
            )
        unresolved = json.loads(json.dumps(self.snapshot))
        unresolved["views"]["journey"]["chapters"][0]["event_ids"][0] = (
            "event:missing"
        )
        with self.assertRaisesRegex(site_builder.SiteInputError, "unresolved"):
            site_builder.validate_snapshot(
                unresolved,
                "example/repository",
                self.source_commit,
            )
        boundary = json.loads(json.dumps(self.snapshot))
        boundary["views"]["journey"]["chapters"][0]["boundary"]["id"] = (
            "ri:example/repository:release:other"
        )
        with self.assertRaisesRegex(site_builder.SiteInputError, "boundary event"):
            site_builder.validate_snapshot(
                boundary,
                "example/repository",
                self.source_commit,
            )

    def test_empty_journey_is_an_explicit_valid_state(self) -> None:
        self.snapshot["views"]["journey"] = {"chapters": [], "events": []}
        output = self.build("dist/intelligence")
        rendered = (output / "journey/index.html").read_text(encoding="utf-8")
        self.assertIn("No journey events projected", rendered)
        self.assertIn("not evidence that the repository has no Git history", rendered)
        self.assertNotIn("data-journey-event", rendered)

    def test_current_observatory_decision_shape_keeps_optional_facets_unknown(self) -> None:
        decision = json.loads(
            json.dumps(self.snapshot["views"]["decisions"]["decisions"][2])
        )
        for field in ("affected_components", "date", "domains", "owners"):
            decision.pop(field, None)
        self.snapshot["views"]["decisions"]["decisions"] = [decision]
        output = self.build("dist/intelligence")
        rendered = (output / "decisions/index.html").read_text(encoding="utf-8")
        self.assertIn('data-filter-date="unknown"', rendered)
        self.assertIn('data-filter-domain="unknown"', rendered)
        self.assertIn('data-filter-component="unknown"', rendered)
        self.assertIn("Not projected", rendered)
        self.assertIn("stable key order otherwise", rendered)

    def test_decision_contract_rejects_duplicate_status_and_shape_drift(self) -> None:
        duplicate = json.loads(json.dumps(self.snapshot))
        duplicate["views"]["decisions"]["decisions"][1]["entity"]["id"] = duplicate[
            "views"
        ]["decisions"]["decisions"][0]["entity"]["id"]
        with self.assertRaisesRegex(site_builder.SiteInputError, "unique"):
            site_builder.validate_snapshot(
                duplicate,
                "example/repository",
                self.source_commit,
            )
        invalid_status = json.loads(json.dumps(self.snapshot))
        invalid_status["views"]["decisions"]["decisions"][0]["entity"]["state"] = (
            "complete"
        )
        with self.assertRaisesRegex(site_builder.SiteInputError, "unsupported status"):
            site_builder.validate_snapshot(
                invalid_status,
                "example/repository",
                self.source_commit,
            )
        invalid_relationship = json.loads(json.dumps(self.snapshot))
        invalid_relationship["views"]["decisions"]["decisions"][0].pop("informs")
        with self.assertRaisesRegex(site_builder.SiteInputError, "informs must be an array"):
            site_builder.validate_snapshot(
                invalid_relationship,
                "example/repository",
                self.source_commit,
            )

    def test_bundle_validation_rejects_a_broken_cross_view_decision_link(self) -> None:
        output = self.build("dist/intelligence")
        decisions = output / "decisions/index.html"
        rendered = decisions.read_text(encoding="utf-8")
        roadmap_anchor = site_builder.stable_fragment(
            "quest",
            "ri:example/repository:roadmap-step:EX-Q04",
        )
        decisions.write_text(
            rendered.replace(
                f'href="../roadmap/#{roadmap_anchor}"',
                'href="../roadmap/#quest-missing"',
                1,
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            bundle_validator.BundleValidationError,
            "unsupported fragment",
        ):
            bundle_validator.validate_bundle(
                repository_root=self.repository,
                output_root=output,
                repository="example/repository",
                repository_visibility="public",
                source_commit=self.source_commit,
                generator_version="1.2.0",
                generator_source_ref=GENERATOR_COMMIT,
                generator_source_commit=GENERATOR_COMMIT,
                generator_immutable=True,
            )

    def test_empty_decisions_are_an_explicit_valid_state(self) -> None:
        self.snapshot["views"]["decisions"] = {"decisions": []}
        output = self.build("dist/intelligence")
        rendered = (output / "decisions/index.html").read_text(encoding="utf-8")
        self.assertIn("No ADRs projected", rendered)
        self.assertIn("not evidence that no decisions exist", rendered)
        self.assertNotIn("data-decision-record", rendered)

    def test_roadmap_contract_rejects_duplicate_ids_and_unresolved_roots(self) -> None:
        duplicate = json.loads(json.dumps(self.snapshot))
        duplicate["views"]["roadmap"]["steps"][1]["entity"]["id"] = duplicate[
            "views"
        ]["roadmap"]["steps"][0]["entity"]["id"]
        with self.assertRaisesRegex(site_builder.SiteInputError, "unique"):
            site_builder.validate_snapshot(
                duplicate,
                "example/repository",
                self.source_commit,
            )
        unresolved = json.loads(json.dumps(self.snapshot))
        unresolved["views"]["roadmap"]["roots"] = ["ri:missing"]
        with self.assertRaisesRegex(site_builder.SiteInputError, "unresolved"):
            site_builder.validate_snapshot(
                unresolved,
                "example/repository",
                self.source_commit,
            )

    def test_bundle_validation_rejects_a_broken_quest_deep_link(self) -> None:
        output = self.build("dist/intelligence")
        roadmap = output / "roadmap/index.html"
        rendered = roadmap.read_text(encoding="utf-8")
        anchor = site_builder.stable_fragment(
            "quest",
            "ri:example/repository:roadmap-step:EX-Q04",
        )
        roadmap.write_text(
            rendered.replace(f'href="#{anchor}"', 'href="#quest-missing"', 1),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            bundle_validator.BundleValidationError,
            "unsupported fragment",
        ):
            bundle_validator.validate_bundle(
                repository_root=self.repository,
                output_root=output,
                repository="example/repository",
                repository_visibility="public",
                source_commit=self.source_commit,
                generator_version="1.2.0",
                generator_source_ref=GENERATOR_COMMIT,
                generator_source_commit=GENERATOR_COMMIT,
                generator_immutable=True,
            )

    def test_empty_roadmap_is_an_explicit_valid_state(self) -> None:
        self.snapshot["views"]["roadmap"] = {"roots": [], "steps": []}
        self.snapshot["views"]["now"]["next_ready"] = []
        output = self.build("dist/intelligence")
        rendered = (output / "roadmap/index.html").read_text(encoding="utf-8")
        self.assertIn("No roadmap quests projected", rendered)
        self.assertIn("ROADMAP.md remains canonical", rendered)
        self.assertNotIn("data-roadmap-quest", rendered)

    def test_missing_snapshot_is_honest_not_green(self) -> None:
        output = self.build("dist/intelligence", include_snapshot=False)
        rendered = (output / "now/index.html").read_text(encoding="utf-8")
        self.assertIn("Observatory snapshot unavailable", rendered)
        self.assertIn("cannot be asserted", rendered)
        self.assertIn('data-state="unknown"', rendered)
        roadmap = (output / "roadmap/index.html").read_text(encoding="utf-8")
        self.assertIn("Observatory roadmap unavailable", roadmap)
        self.assertIn("never infers roadmap state", roadmap)
        decisions = (output / "decisions/index.html").read_text(encoding="utf-8")
        self.assertIn("Observatory decision history unavailable", decisions)
        self.assertIn("never reconstructs architectural intent", decisions)
        journey = (output / "journey/index.html").read_text(encoding="utf-8")
        self.assertIn("Observatory journey unavailable", journey)
        self.assertIn("never reconstructs semantic history", journey)

    def test_snapshot_identity_and_commit_are_required(self) -> None:
        wrong = json.loads(json.dumps(self.snapshot))
        wrong["represented_commit"] = "f" * 40
        with self.assertRaisesRegex(site_builder.SiteInputError, "represent"):
            site_builder.validate_snapshot(
                wrong,
                "example/repository",
                self.source_commit,
            )
        wrong = json.loads(json.dumps(self.snapshot))
        wrong["repository"]["key"] = "example/other"
        with self.assertRaisesRegex(site_builder.SiteInputError, "repository"):
            site_builder.validate_snapshot(
                wrong,
                "example/repository",
                self.source_commit,
            )

    def test_sibling_contract_lock_pins_observatory_and_holon(self) -> None:
        lock = json.loads(
            (
                ACTION_ROOT
                / "contracts/repository-intelligence-siblings.v1.lock.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            lock["observatory"]["contract"],
            site_builder.SNAPSHOT_SCHEMA,
        )
        self.assertRegex(lock["observatory"]["source_commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(lock["holon"]["source_commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(
            lock["holon"]["package"],
            "@egohygiene/repository-intelligence@0.1.0-alpha.1",
        )

    def test_hygiene_registry_lock_matches_repository_route_layout(self) -> None:
        lock = json.loads(
            (
                ACTION_ROOT
                / "contracts/repository-intelligence-siblings.v1.lock.json"
            ).read_text(encoding="utf-8")
        )
        hygiene = lock["hygiene"]
        self.assertEqual(
            hygiene["source_commit"],
            "63d313b1ddf8669808e897853b74928505494da0",
        )
        self.assertEqual(
            hygiene["contract"],
            "egohygiene.public-site-surface-registry/v1",
        )
        self.assertEqual(hygiene["contract_version"], "1.0.0-alpha.1")
        self.assertEqual(hygiene["route_profile"], "repository")
        self.assertRegex(hygiene["registry_sha256"], r"^[0-9a-f]{64}$")
        expected = {
            "intelligence": "/intelligence/",
            **{
                route: f"/intelligence/{route}/"
                for route, _ in site_builder.ROUTES
            },
            "dashboard": "/intelligence/dashboard/",
        }
        self.assertEqual(hygiene["canonical_routes"], expected)

    def test_action_exposes_every_routed_view_as_a_public_output(self) -> None:
        manifest = ACTION_MANIFEST.read_text(encoding="utf-8")
        for route in (
            "now",
            "roadmap",
            "decisions",
            "journey",
            "dependencies",
            "health",
            "releases",
            "work",
            "search",
            "compare",
            "dashboard",
        ):
            with self.subTest(route=route):
                self.assertIn(f"  {route}:\n", manifest)
                self.assertIn(
                    f'${{{{ inputs.output-directory }}}}/{route}/index.html',
                    manifest,
                )

    def test_snapshot_path_rejects_symlink_components(self) -> None:
        outside = Path(self.temporary_directory.name) / "outside.json"
        outside.write_text("{}\n", encoding="utf-8")
        link = self.repository / "snapshot.json"
        link.symlink_to(outside)
        with self.assertRaisesRegex(site_builder.SiteInputError, "symbolic-link"):
            site_builder.validate_repository_path(
                self.repository.resolve(),
                link.absolute(),
                "Observatory snapshot",
            )

    def test_public_bundle_rejects_identity_leakage_from_snapshot_text(self) -> None:
        self.snapshot["views"]["now"]["current_focus"][0]["title"] = (
            "Coordinate with private-person@example.test"
        )
        with self.assertRaisesRegex(bundle_validator.BundleValidationError, "email"):
            self.build("dist/intelligence")

    def test_routed_site_is_byte_stable(self) -> None:
        first = self.build("first/intelligence")
        second = self.build("second/intelligence")
        first_files = {
            path.relative_to(first): path.read_bytes()
            for path in first.rglob("*")
            if path.is_file()
        }
        second_files = {
            path.relative_to(second): path.read_bytes()
            for path in second.rglob("*")
            if path.is_file()
        }
        self.assertEqual(first_files, second_files)


if __name__ == "__main__":
    unittest.main()
