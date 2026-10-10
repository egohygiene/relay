#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Prepare a fresh, validated ADR snapshot for the existing Intelligence builder.

With --runtime, execution is offline and uses the caller's trusted prepared
runtime and pinned Python environment. Otherwise acquire immutable public owner
sources and locked dependencies in a fresh private directory first.
"""

from __future__ import annotations

import argparse
from datetime import datetime, UTC
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
LOCK = ROOT / "contracts/adr-collector.v1.lock.json"
REQUIREMENTS = ROOT / "contracts/adr-build-requirements.txt"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def execute(argv, cwd, env, timeout=180):
    # Dependency logs and consumer-derived exception text never enter run evidence.
    with tempfile.TemporaryFile() as log:
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=log, stderr=log,
                                timeout=timeout, check=False)
        if result.returncode or log.tell() > 32 * 1024 * 1024:
            raise ValueError("acquisition")


def acquire(work):
    if sys.version_info[:2] != (3, 12) or sys.platform != "linux" or platform.machine() != "x86_64":
        raise ValueError("acquisition-platform")
    env = {"PATH": os.environ.get("PATH", os.defpath), "LC_ALL": "C.UTF-8",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0",
           "CARGO_HOME": str(work / "cargo"), "RUSTUP_HOME": str(work / "rustup"),
           "RUSTUP_TOOLCHAIN": "1.85.1", "CARGO_BUILD_JOBS": "2"}
    # Preserve managed-network routing and CA trust, never consumer package/Git configuration.
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy",
                "all_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE",
                "CURL_CA_BUNDLE", "GIT_SSL_CAINFO"):
        if key in os.environ:
            env[key] = os.environ[key]
    lock = json.loads(LOCK.read_text())
    sources = {}
    for name, pin in lock["sources"].items():
        owner = "hygiene" if name.startswith("hygiene_") else name
        source = work / owner
        if owner not in sources:
            execute(["git", "init", "--bare", str(source)], work, env)
            sources[owner] = source
        execute(["git", "-C", str(source), "fetch", "--no-tags", "--depth=1",
                 "https://github.com/" + pin["repository"] + ".git", pin["revision"]], work, env)
    execute([sys.executable, "-I", "-m", "venv", str(work / "venv")], work, env)
    python = work / "venv/bin/python"
    pip = [str(python), "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "--no-cache-dir"]
    execute([*pip, "download", "--only-binary=:all:", "--require-hashes", "-r", str(REQUIREMENTS),
             "--dest", str(work / "wheels")], work, env)
    execute([*pip, "install", "--no-index", "--find-links", str(work / "wheels"), "--require-hashes",
             "-r", str(REQUIREMENTS)], work, env)
    execute(["rustup", "toolchain", "install", "1.85.1", "--profile", "minimal", "--no-self-update"], work, env)
    cargo = subprocess.check_output(["rustup", "which", "--toolchain", "1.85.1", "cargo"],
                                    cwd=work, env=env, stderr=subprocess.DEVNULL).decode().strip()
    if not Path(cargo).is_relative_to(work / "rustup") or not Path(cargo).is_file():
        raise ValueError("acquisition-toolchain")
    env["PATH"] = str(Path(cargo).parent) + os.pathsep + env["PATH"]
    # Only pinned manifests are materialized for dependency acquisition; source
    # compilation later uses the collector's verified Git archive, offline.
    manifests = work / "manifests"
    manifests.mkdir()
    for name in ("Cargo.toml", "Cargo.lock"):
        content = subprocess.check_output(["git", "-C", str(sources["egolint"]), "show",
            lock["sources"]["egolint"]["revision"] + ":" + name], env=env, stderr=subprocess.DEVNULL)
        import hashlib
        if hashlib.sha256(content).hexdigest() != lock["sources"]["egolint"]["files"][name]:
            raise ValueError("acquisition-pin")
        (manifests / name).write_bytes(content)
    (manifests / "src").mkdir()
    (manifests / "src/main.rs").write_text("fn main() {}\n")
    execute([cargo, "fetch", "--locked", "--manifest-path", str(manifests / "Cargo.toml")], work, env)
    runtime = work / "runtime"
    command = [str(python), "-I", str(SCRIPTS / "collect_repository_adrs.py"), "prepare",
               "--cargo", cargo, "--output", str(runtime)]
    for owner, source in sources.items():
        command.extend(["--" + owner, str(source)])
    execute(command, work, env, timeout=360)
    return python, runtime


def output_paths(args):
    # This check is stdlib-only so it runs before any dependency acquisition.
    root = args.repository_root.absolute()
    relative = Path(args.work_directory)
    if (".." in root.parts or relative.as_posix() != args.work_directory
            or relative.is_absolute() or not relative.parts or ".." in relative.parts
            or relative.parts[0] not in {".cache", ".staging", "build", "dist"}):
        raise ValueError("output-layout")
    target = root / relative / "adr"
    if any(p.is_symlink() for p in (root, target, *target.parents)):
        raise ValueError("output-path")
    tracked = subprocess.check_output(["git", "--no-optional-locks", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
        "-C", str(root), "ls-files", "--", str(relative / "adr")], stderr=subprocess.DEVNULL)
    if tracked or (target.exists() and not target.is_dir()):
        raise ValueError("output-tracked")
    target.mkdir(parents=True, exist_ok=True)
    # Own just these two files. A denied retry cannot leave an old build candidate.
    for name in ("snapshot.json", "receipt.json"):
        path = target / name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError("output-path")
    for name in ("snapshot.json", "receipt.json"):
        (target / name).unlink(missing_ok=True)
    return target


def collect(args, target):
    collector = module("relay_adr_collector", SCRIPTS / "collect_repository_adrs.py")
    if collector.base.safe_path(args.runtime).is_relative_to(collector.base.safe_path(args.repository_root)):
        raise ValueError("runtime-must-be-outside-consumer")
    # Action timestamps also permit explicit offsets; normalize once for native parity.
    instant = datetime.fromisoformat(args.observed_at.replace("Z", "+00:00"))
    if instant.tzinfo is None or instant.microsecond:
        raise ValueError("observation")
    observed = instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    native = collector.parser().parse_args([
        "collect", "--runtime", str(args.runtime), "--repository-root", str(args.repository_root),
        "--repository", args.repository, "--visibility", args.visibility,
        "--source-commit", args.source_commit, "--observed-at", observed,
        "--adoption", "present", "--output", str(target.parent / "unused-review.json")])
    current_stage = ["collection"]
    try:
        result = collector.collect(native, on_stage=lambda name: current_stage.__setitem__(0, name))
    except (collector.base.CollectorError, OSError, ValueError, KeyError, TypeError, collector.yaml.YAMLError, RecursionError):
        raise ValueError(current_stage[0]) from None
    if result["validation"]["hygiene"] != "valid":
        raise ValueError("normalization")
    if result["status"] != "ready":
        # Keep the review-only CLI available for bounded, richer diagnostics.
        raise ValueError("source-validation" if result["status"] == "invalid" else "collection-coverage")
    if (result["validation"]["diagnostics_truncated"] or result["validation"]["egolint"] not in {"valid", "incomplete"}
            or result["coverage"]["decisions"]["freshness"] != "current"):
        raise ValueError("source-validation")
    contract = module("relay_adr_build_contract", SCRIPTS / "repository_adr_build_contract.py")
    receipt = {"schema": contract.SCHEMA, "repository": args.repository, "source_commit": args.source_commit,
               "observed_at": observed, **result["inputs"], "runtime": result["runtime"],
               "validation": result["validation"], "coverage": result["coverage"],
               "candidate_digests": result["candidate_digests"]}
    contract.validate(receipt, args.repository, args.source_commit)
    # No second normalization or candidate-envelope promotion: this invocation ran
    # the native collector and all owner validation against the represented Git objects.
    for name, value in (("snapshot.json", result["snapshot_candidate"]), ("receipt.json", receipt)):
        descriptor, temporary = tempfile.mkstemp(dir=target)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(collector.base.json_bytes(value))
            os.replace(temporary, target / name)
        finally:
            Path(temporary).unlink(missing_ok=True)


def parser():
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    result.add_argument("--runtime", type=Path)
    result.add_argument("--repository-root", type=Path, required=True)
    result.add_argument("--work-directory", default=".cache/repository-intelligence")
    for name in ("repository", "visibility", "source-commit", "observed-at"):
        result.add_argument("--" + name, required=True)
    result.add_argument("--observatory-snapshot", default="")
    result.add_argument("--observatory-comparison", default="")
    return result


def main():
    args = parser().parse_args()
    stage = "input"
    try:
        if args.observatory_snapshot or args.observatory_comparison:
            raise ValueError("conflicting-inputs")
        target = output_paths(args)
        if args.visibility != "public":
            raise ValueError("visibility")
        if args.runtime is None:
            stage = "acquisition"
            with tempfile.TemporaryDirectory(prefix="relay-adr-build-") as temporary:
                work = Path(temporary)
                if work.is_relative_to(args.repository_root.absolute()):
                    raise ValueError("runtime-layout")
                python, runtime = acquire(work)
                forwarded = [str(python), "-I", str(Path(__file__).resolve()),
                             *sys.argv[1:], "--runtime", str(runtime)]
                # Forward only this program's fixed diagnostics after acquisition.
                return subprocess.run(forwarded, cwd=work, check=False).returncode
        stage = "collection-validation-normalization"
        collect(args, target)
        print("ADR build: validated canonical Decisions snapshot prepared")
        return 0
    except (ValueError, OSError, KeyError, TypeError, ImportError, RecursionError, subprocess.SubprocessError):
        error = sys.exception()
        code = str(error) if type(error) is ValueError and str(error) in {
            "conflicting-inputs", "visibility", "source-validation", "collection-coverage", "collection", "normalization",
            "runtime-must-be-outside-consumer", "output-layout", "output-path", "output-tracked"} else "denied"
        print(f"ADR build: {stage}: {code}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
