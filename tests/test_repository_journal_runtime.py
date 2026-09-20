# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Keep the repository-journal runtime pinned, bounded, and secret-free."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPOSITORY_ROOT / "scripts/validate_repository_journal_runtime.py"
SPEC = importlib.util.spec_from_file_location("repository_journal_runtime", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)
PROFILE_PATH = REPOSITORY_ROOT / "catalog/repository-journal-runtime.json"
AETHER_PROFILE_PATH = REPOSITORY_ROOT / "catalog/repository-journal-aether.json"
SCHEMA_DIRECTORY = REPOSITORY_ROOT / "schemas"


class RepositoryJournalRuntimeTests(unittest.TestCase):
    """Exercise tool locking, authentication selection, and safe failure."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.profile_bytes = PROFILE_PATH.read_bytes()
        cls.profile = json.loads(cls.profile_bytes)
        cls.aether_profile = json.loads(AETHER_PROFILE_PATH.read_bytes())

    def result(
        self,
        *,
        auth_mode: str = "github-token",
        environment: dict[str, str] | None = None,
        observed_cli_version: str | None = "1.0.85",
        policy_state: str = "enabled",
        permission_state: str = "granted",
        billing_acknowledged: bool = True,
    ) -> dict[str, object]:
        """Build one result without placing a real credential in the process."""

        if environment is None:
            environment = {"GITHUB_TOKEN": "ghs_test_secret_never_emit"}
        return runtime.build_preflight_result(
            self.profile,
            auth_mode=auth_mode,
            environment=environment,
            observed_cli_version=observed_cli_version,
            policy_state=policy_state,
            permission_state=permission_state,
            billing_acknowledged=billing_acknowledged,
            profile_bytes=self.profile_bytes,
        )

    def test_profile_and_locked_npm_graph_are_valid(self) -> None:
        self.assertEqual(runtime.validate_profile(self.profile), [])
        self.assertEqual(
            runtime.validate_locked_toolchain(self.profile, REPOSITORY_ROOT),
            [],
        )
        self.assertEqual(runtime.validate_repository(REPOSITORY_ROOT), [])

        package = self.profile["toolchain"]["package"]
        self.assertEqual(package["name"], "@github/copilot")
        self.assertEqual(package["version"], "1.0.85")
        self.assertRegex(package["integrity"], runtime.SRI_SHA512)

    def test_mutable_or_broadened_runtime_contract_is_rejected(self) -> None:
        mutable = deepcopy(self.profile)
        mutable["toolchain"]["package"]["version"] = "latest"
        self.assertTrue(
            any("exact SemVer" in error for error in runtime.validate_profile(mutable))
        )

        retried = deepcopy(self.profile)
        retried["execution"]["maximum_attempts_per_invocation"] = 3
        self.assertTrue(
            any("bounded non-interactive" in error for error in runtime.validate_profile(retried))
        )

        automatic_fallback = deepcopy(self.profile)
        automatic_fallback["authentication"]["fallback"]["automatic"] = True
        self.assertTrue(
            any("non-automatic" in error for error in runtime.validate_profile(automatic_fallback))
        )

    def test_manifest_or_lock_drift_is_rejected_before_installation(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        destination = root / "vendor/copilot-cli"
        destination.mkdir(parents=True)
        for filename in ("package.json", "package-lock.json"):
            shutil.copy2(
                REPOSITORY_ROOT / "vendor/copilot-cli" / filename,
                destination / filename,
            )

        self.assertEqual(runtime.validate_locked_toolchain(self.profile, root), [])
        (destination / "package-lock.json").write_text("{}\n", encoding="utf-8")
        self.assertTrue(
            any(
                "lock digest mismatch" in error
                for error in runtime.validate_locked_toolchain(self.profile, root)
            )
        )

    def test_aether_distribution_is_immutable_and_executable(self) -> None:
        self.assertEqual(
            runtime.validate_aether_profile(self.aether_profile, REPOSITORY_ROOT),
            [],
        )
        renderer = (
            REPOSITORY_ROOT
            / self.aether_profile["execution"]["renderer"]
        )
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name) / "journal.md"
        machine = Path(temporary.name) / "journal.json"
        source = (
            REPOSITORY_ROOT
            / "vendor/aether/library/organization/skills/quality/"
            "create-repository-journal/templates/"
            "repository-journal-input.template.json"
        )
        completed = subprocess.run(
            [
                "python3",
                str(renderer),
                "render",
                "--input",
                str(source),
                "--output",
                str(output),
                "--json-output",
                str(machine),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        rendered = json.loads(machine.read_text(encoding="utf-8"))
        self.assertEqual(rendered["contract_version"], "1.0.0")
        self.assertEqual(
            rendered["contract_digest"]["value"],
            self.aether_profile["contract"]["spec_digest"]["value"],
        )

    def test_aether_revision_or_vendored_byte_drift_is_rejected(self) -> None:
        mutable = deepcopy(self.aether_profile)
        mutable["source"]["revision"] = "f" * 40
        self.assertTrue(runtime.validate_aether_profile(mutable, REPOSITORY_ROOT))

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(REPOSITORY_ROOT / "vendor", root / "vendor")
        renderer_path = root / runtime.AETHER_FILES["renderer"][1]
        renderer_path.write_text("# drift\n", encoding="utf-8")
        errors = runtime.validate_aether_profile(self.aether_profile, root)
        self.assertTrue(any("renderer" in error for error in errors))

    def test_preferred_github_token_mode_can_be_ready(self) -> None:
        result = self.result()

        self.assertEqual(runtime.validate_result(result), [])
        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["safe_to_invoke"])
        self.assertEqual(result["failure_reasons"], [])
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn("ghs_test_secret_never_emit", serialized)
        self.assertNotIn("ghs_", serialized)

    def test_unknown_policy_permission_or_billing_fails_closed(self) -> None:
        result = self.result(
            policy_state="unknown",
            permission_state="unknown",
            billing_acknowledged=False,
        )

        self.assertEqual(runtime.validate_result(result), [])
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["safe_to_invoke"])
        self.assertEqual(
            set(result["failure_reasons"]),
            {
                "organization-policy-unverified",
                "permission-unverified",
                "billing-unacknowledged",
            },
        )

    def test_missing_version_and_conflicting_credential_fail_closed(self) -> None:
        result = self.result(
            environment={
                "GITHUB_TOKEN": "ghs_test_secret_never_emit",
                "GH_TOKEN": "github_pat_conflicting_secret_never_emit",
            },
            observed_cli_version=None,
        )

        self.assertEqual(runtime.validate_result(result), [])
        self.assertEqual(
            set(result["failure_reasons"]),
            {"cli-unavailable", "credential-precedence-conflict"},
        )
        self.assertEqual(
            result["observed"]["conflicting_environment_variables"],
            ["GH_TOKEN"],
        )
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn("conflicting_secret_never_emit", serialized)

    def test_fine_grained_pat_fallback_is_explicit_and_secret_free(self) -> None:
        result = self.result(
            auth_mode="fine-grained-pat",
            environment={
                "COPILOT_GITHUB_TOKEN": "github_pat_test_secret_never_emit",
                "GITHUB_TOKEN": "ghs_lower_precedence_token",
            },
            policy_state="unknown",
        )

        self.assertEqual(runtime.validate_result(result), [])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["observed"]["policy_state"], "not-applicable")
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn("github_pat_", serialized)
        self.assertNotIn("lower_precedence_token", serialized)

    def test_classic_or_opaque_pat_is_rejected(self) -> None:
        for token in ("ghp_classic_secret", "opaque-secret"):
            with self.subTest(token_type=token.split("_", maxsplit=1)[0]):
                result = self.result(
                    auth_mode="fine-grained-pat",
                    environment={"COPILOT_GITHUB_TOKEN": token},
                    policy_state="not-applicable",
                )
                self.assertIn(
                    "credential-type-unsupported",
                    result["failure_reasons"],
                )
                self.assertNotIn(token, json.dumps(result, sort_keys=True))

    def test_cli_version_inspection_strips_credentials(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["copilot", "--version"],
            returncode=0,
            stdout="GitHub Copilot CLI 1.0.85\n",
            stderr="",
        )
        process_environment = {
            "PATH": "/usr/bin",
            "GITHUB_TOKEN": "ghs_test_secret_never_emit",
            "UNRELATED_SECRET": "also-never-emit",
        }
        with mock.patch.dict(runtime.os.environ, process_environment, clear=True):
            with mock.patch.object(runtime.shutil, "which", return_value="/bin/copilot"):
                with mock.patch.object(runtime.subprocess, "run", return_value=completed) as run:
                    self.assertEqual(runtime.inspect_cli_version("copilot"), "1.0.85")

        environment = run.call_args.kwargs["env"]
        for variable in runtime.SECRET_ENVIRONMENT_VARIABLES:
            self.assertNotIn(variable, environment)
        self.assertNotIn("UNRELATED_SECRET", environment)
        self.assertEqual(environment["PATH"], "/usr/bin")
        self.assertEqual(environment["COPILOT_OFFLINE"], "true")
        self.assertEqual(run.call_args.args[0], ["/bin/copilot", "--version"])

    def test_wrong_cli_version_and_contradictory_result_are_rejected(self) -> None:
        result = self.result(observed_cli_version="1.0.84")
        self.assertIn("cli-version-mismatch", result["failure_reasons"])

        contradictory = deepcopy(result)
        contradictory["status"] = "ready"
        contradictory["safe_to_invoke"] = True
        self.assertTrue(
            any("ready result" in error for error in runtime.validate_result(contradictory))
        )

    def test_malformed_collection_shapes_fail_without_raising(self) -> None:
        malformed_profile = deepcopy(self.profile)
        malformed_profile["failure"]["fail_closed_on"] = "cli-unavailable"
        self.assertTrue(runtime.validate_profile(malformed_profile))

        malformed_result = self.result()
        malformed_result["checks"] = "pass"
        malformed_result["failure_reasons"] = [{}]
        self.assertTrue(runtime.validate_result(malformed_result))

    def test_owned_schemas_are_closed_and_use_relay_ids(self) -> None:
        expected = {
            "repository-journal-aether-profile.v1.schema.json":
                "repository-journal-aether-profile/v1/schema.json",
            "repository-journal-runtime-profile.v1.schema.json":
                "repository-journal-runtime-profile/v1/schema.json",
            "repository-journal-runtime-preflight-result.v1.schema.json":
                "repository-journal-runtime-preflight-result/v1/schema.json",
        }
        for filename, suffix in expected.items():
            with self.subTest(schema=filename):
                schema = json.loads(
                    (SCHEMA_DIRECTORY / filename).read_text(encoding="utf-8")
                )
                self.assertEqual(
                    schema["$schema"],
                    "https://json-schema.org/draft/2020-12/schema",
                )
                self.assertEqual(
                    schema["$id"],
                    f"https://egohygiene.github.io/relay/contracts/{suffix}",
                )
                self.assertFalse(schema["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
