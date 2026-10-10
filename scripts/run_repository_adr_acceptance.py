#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Exercise fresh locked acquisition and owner-native ADR builds in read-only CI."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "actions/repository-intelligence/scripts/prepare_repository_adr_build.py"
spec = importlib.util.spec_from_file_location("relay_adr_build", SCRIPT)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def main():
    with tempfile.TemporaryDirectory(prefix="relay-adr-acceptance-") as temporary:
        python, runtime = build.acquire(Path(temporary))
        work = Path(temporary)
        replay = work / "different-runtime-location"
        cargo = next((work / "rustup/toolchains").glob("1.85.1-*/bin/cargo"))
        environment = {**os.environ, "CARGO_HOME": str(work / "cargo"), "RUSTUP_HOME": str(work / "rustup"),
                       "CARGO_BUILD_JOBS": "2", "RELAY_ADR_RUNTIME": str(runtime),
                       "RELAY_ADR_REPLAY_RUNTIME": str(replay), "RELAY_ADR_CANARY": str(work / "hygiene")}
        command = [str(python), "-I", str(SCRIPT.with_name("collect_repository_adrs.py")), "prepare",
                   "--cargo", str(cargo), "--output", str(replay)]
        for owner in ("egolint", "hygiene", "observatory"):
            command.extend(["--" + owner, str(work / owner)])
        build.execute(command, work, environment, timeout=360)
        if json.loads((runtime / "runtime.json").read_text()) != json.loads((replay / "runtime.json").read_text()):
            raise ValueError("fresh ADR runtimes must reproduce identical executable evidence")
        print("Fresh ADR runtimes match across build locations", flush=True)
        return subprocess.run([str(python), "-m", "unittest", "discover", "--start-directory", "tests",
                               "--pattern", "test_repository_adr_*.py", "--verbose"],
                              cwd=ROOT, env=environment, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
