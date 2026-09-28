# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Run the native acceptance matrix without silent skips and optionally keep evidence."""

import argparse
import json
import os
from pathlib import Path
import sys
import unittest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True, help="Trusted prepared architecture runtime")
    parser.add_argument("--evidence-directory", type=Path, help="New directory for synthetic local report bundles")
    args = parser.parse_args()
    # Load only this trusted test package even under Python isolated mode.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    os.environ["RELAY_ARCHITECTURE_RUNTIME"] = str(args.runtime.resolve())
    os.environ.pop("RELAY_ARCHITECTURE_ACCEPTANCE_EVIDENCE", None)
    import test_architecture_validation_acceptance as acceptance

    acceptance.adapter.runtime_files(args.runtime.resolve(), acceptance.adapter.profile())
    if args.evidence_directory:
        args.evidence_directory.mkdir(parents=True, exist_ok=False)
        os.environ["RELAY_ARCHITECTURE_ACCEPTANCE_EVIDENCE"] = str(args.evidence_directory.resolve())
    suite = unittest.defaultTestLoader.loadTestsFromModule(acceptance)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.wasSuccessful() and not result.skipped
    if args.evidence_directory:
        (args.evidence_directory / "acceptance.json").write_text(json.dumps({
            "kind": "local-fixture-evidence", "passed": passed, "tests": result.testsRun,
            "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
            "hosted_execution": "not-run", "artifact_upload": "not-run",
            "provider_identity": "synthetic", "stage_outcomes": "synthetic",
            "profile_sha256": acceptance.adapter.digest(acceptance.adapter.read_file(acceptance.adapter.PROFILE_PATH)),
        }, indent=2, sort_keys=True) + "\n")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
