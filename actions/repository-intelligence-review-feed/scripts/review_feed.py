#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Normalize explicitly selected immutable typed sidecars; never execute audits.

Only hash-bound Observatory/Aether/Hygiene owner validators and pure projection
functions are loaded. Candidate repositories supply Git blobs, never executable
runtime, policy, Python modules or prose to reinterpret.
"""

from __future__ import annotations

import argparse
from datetime import datetime, UTC
import importlib
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import types

ROOT = Path(__file__).resolve().parents[1]
RELAY = ROOT.parent.parent
LOCK = ROOT / "contracts/review-feed-owner.v1.lock.json"
PLAN_SCHEMA = ROOT / "contracts/review-plan.v1.schema.json"
RECEIPT_SCHEMA = ROOT / "contracts/review-feed-receipt.v1.schema.json"
CONTRACT = Path(__file__).with_name("review_feed_contract.py")
DENIAL = "Typed review feed denied; inspect the selected public owner inputs locally"
MAX_TOTAL = 16 * 1024 * 1024
MAX_RESOURCES = 32


def module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise ValueError(DENIAL)
    value = importlib.util.module_from_spec(specification)
    sys.modules[name] = value
    specification.loader.exec_module(value)
    return value


contract = module("relay_typed_review_feed_contract", CONTRACT)
require = contract.require


def local_path(value):
    result = Path(value).absolute()
    require(".." not in result.parts and ".git" not in result.parts
        and not any(item.is_symlink() for item in (result, *result.parents)), "PATH")
    return result


def read(path, maximum=contract.MAX_MODEL):
    path = local_path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        info = os.fstat(source.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_size <= maximum, "PIN")
        result = source.read(maximum + 1)
        require(len(result) == info.st_size and len(result) <= maximum, "PIN")
        return result


def git(source, *arguments, maximum=contract.MAX_REPORT, deadline):
    """Bound object reads; disable hooks, network, lazy fetch and ambient Git config."""
    environment = {"PATH": os.defpath, "LC_ALL": "C.UTF-8", "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1",
        "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
    argv = ["/usr/bin/git", "--no-lazy-fetch", "--no-optional-locks", "--literal-pathspecs",
        "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "-c", "log.showSignature=false",
        "-c", "protocol.allow=never",
        "-C", str(source), *arguments]
    process = subprocess.Popen(argv, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, start_new_session=True)
    result = bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = min(15.0, deadline - time.monotonic())
                require(remaining > 0, "SOURCE")
                events = selector.select(remaining)
                require(events, "SOURCE")
                block = os.read(process.stdout.fileno(), min(65536, maximum + 1 - len(result)))
                if not block:
                    break
                result.extend(block)
                require(len(result) <= maximum, "SOURCE")
        require(process.wait(timeout=max(0.01, min(15.0, deadline - time.monotonic()))) == 0, "SOURCE")
        return bytes(result)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        process.stdout.close()


def blob(source, revision, path, *, maximum, deadline):
    contract.relative(path)
    record = git(source, "ls-tree", "-z", revision, "--", path, maximum=4096, deadline=deadline)
    if record == b"":
        return None
    require(record.endswith(b"\x00") and record.count(b"\x00") == 1, "SOURCE")
    header, name = record[:-1].split(b"\t", 1)
    fields = header.split(b" ")
    require(len(fields) == 3 and fields[0] in {b"100644", b"100755"} and fields[1] == b"blob"
        and name.decode("utf-8") == path and contract.SHA.fullmatch(fields[2].decode("ascii")), "SOURCE")
    return git(source, "cat-file", "blob", fields[2].decode("ascii"), maximum=maximum, deadline=deadline)


def source_frame(source, repository, revision, as_of, deadline):
    require(source.is_dir(), "SOURCE")
    contract.hexadecimal(revision, contract.SHA)
    boundary = contract.instant(as_of)
    require(boundary <= datetime.now(UTC), "CLOCK")
    require(git(source, "rev-parse", "--show-toplevel", maximum=4096, deadline=deadline).decode().strip() == str(source), "SOURCE")
    require(git(source, "rev-parse", "--verify", revision + "^{commit}", maximum=128, deadline=deadline).decode().strip() == revision, "SOURCE")
    epoch = git(source, "show", "--no-show-signature", "--no-patch", "--format=%ct", revision,
        maximum=128, deadline=deadline).decode().strip()
    require(epoch.isdigit(), "CLOCK")
    committed = datetime.fromtimestamp(int(epoch), UTC)
    require(committed <= boundary, "CLOCK")
    return {"repository": repository, "represented_commit": revision,
        "commit_at": committed.strftime("%Y-%m-%dT%H:%M:%SZ"), "as_of": as_of}


def public_context(repository, audits, data):
    """Use the authenticated typed owner's catalog before consumer Git reads."""
    _row, admission, _allowed = audits.shared.admission(repository, admission_root=data)
    return admission


def implementation():
    return {"producer_sha256": contract.digest(read(Path(__file__))), "contract_sha256": contract.digest(read(CONTRACT)),
        "lock_sha256": contract.digest(read(LOCK)), "receipt_schema_sha256": contract.digest(read(RECEIPT_SCHEMA)),
        "plan_schema_sha256": contract.digest(read(PLAN_SCHEMA))}


def runtime(parent, source):
    """Materialize one exact, closed namespace package outside the consumer."""
    parent = local_path(parent)
    require(parent.is_dir() and parent != source and source not in parent.parents, "PIN")
    lock = contract.parse(read(LOCK))
    contract.closed(lock, {"schema", "owner", "revision", "tree", "files"})
    require(lock["schema"] == "egohygiene.relay.typed-review-runtime-lock/v1"
        and lock["owner"] == "egohygiene/observatory" and lock["revision"] == contract.OBSERVATORY
        and contract.SHA.fullmatch(lock["tree"]) and type(lock["files"]) is dict
        and 1 <= len(lock["files"]) <= MAX_RESOURCES, "PIN")
    resources, total = {}, 0
    for target, entry in lock["files"].items():
        contract.relative(target)
        contract.closed(entry, {"vendored", "sha256"})
        contract.relative(entry["vendored"])
        contract.hexadecimal(entry["sha256"])
        content = read(RELAY / entry["vendored"])
        require(contract.digest(content) == entry["sha256"], "PIN")
        total += len(content)
        require(total <= MAX_TOTAL, "PIN")
        resources[target] = content
    return tempfile.TemporaryDirectory(prefix="relay-typed-review-", dir=parent), resources


def owner_modules(directory, resources):
    directory = Path(directory)
    for target, content in resources.items():
        destination = directory / target
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination.write_bytes(content)
        destination.chmod(0o600)
    name = "relay_pinned_typed_reviews_" + contract.OBSERVATORY
    # Do not import Observatory.__init__: its unrelated engines, providers and
    # dependency closure are outside this profile. Owner source stays unchanged.
    package = types.ModuleType(name)
    package.__path__ = [str(directory / "src/observatory")]
    package.__package__ = name
    package.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
    sys.modules[name] = package
    sys.dont_write_bytecode = True
    audits = importlib.import_module(name + ".audits")
    sanity = importlib.import_module(name + ".sanity")
    data = directory / "src/observatory/data"
    for owner in (audits.contract.owners(data)[2], sanity.contract.owners(data)[2]):
        require(owner["revision"] == contract.AETHER, "PIN")
    return audits, sanity, data


def collect(source, plan_path, frame, audits, sanity, data, deadline):
    repository, revision = frame["repository"], frame["represented_commit"]
    _row, admission, allowed = audits.shared.admission(repository, admission_root=data)
    raw_plan = blob(source, revision, plan_path, maximum=contract.MAX_PLAN, deadline=deadline)
    if raw_plan is None:
        plan = {"schema": contract.PLAN_SCHEMA, "contract_version": contract.VERSION,
            "visibility": "public", "repository": repository, "audits": [], "sanity": []}
    else:
        plan = contract.parse(raw_plan, contract.MAX_PLAN)
        require(audits.shared.ownership_preflight(plan, allowed), "VISIBILITY")
        contract.validate_plan(plan, repository)
    reports, wrappers, total = [], {"audits": [], "sanity": []}, 0
    for domain, engine in (("audits", audits), ("sanity", sanity)):
        for selector in plan[domain]:
            path = selector["path"]
            raw = blob(source, revision, path, maximum=contract.MAX_REPORT, deadline=deadline)
            if raw is None:
                reports.append({"domain": domain, "path": path, "expected_sha256": selector["sha256"],
                    "state": "missing", "sha256": None})
                continue
            total += len(raw)
            require(total <= MAX_TOTAL, "REPORT")
            # Owner ambiguity-preserving parsing and all-source public admission
            # happen before the report ID, count or either content digest.
            parsed = engine.contract.parse(raw)
            if domain == "audits":
                require(engine._public_source(parsed, allowed, repository), "VISIBILITY")
                native, _registry, _owner = engine.contract.owners(data)
                require(set(native.referenced_repositories(parsed)) <= allowed, "VISIBILITY")
            else:
                require(engine._public_source(parsed, allowed, repository, review=True), "VISIBILITY")
            engine.shared.base.unambiguous(parsed)
            checksum = contract.digest(raw)
            require(checksum == selector["sha256"], "REPORT")
            wrappers[domain].append({"visibility": "public", "repository": repository, "evidence": raw,
                "source": {"repository": repository, "revision": revision, "path": path,
                    "url": f"https://github.com/{repository}/blob/{revision}/{path}", "sha256": checksum}})
            reports.append({"domain": domain, "path": path, "expected_sha256": selector["sha256"],
                "state": "provided", "sha256": checksum})
    arguments = {"repository": repository, "represented_commit": revision, "as_of": frame["as_of"], "admission_root": data}
    targets = [{"repository": repository, "represented_commit": revision}]
    models = {
        "repository-audits": audits.build_repository_audits(wrappers["audits"], **arguments),
        "repository-sanity": sanity.build_repository_sanity(wrappers["sanity"], **arguments),
        "fleet-audits": audits.build_fleet_audits(wrappers["audits"], repositories=targets, as_of=frame["as_of"], admission_root=data),
        "fleet-sanity": sanity.build_fleet_sanity(wrappers["sanity"], repositories=targets, as_of=frame["as_of"], admission_root=data),
    }
    require(len(models["repository-audits"]["runs"]) == len(wrappers["audits"])
        and len(models["repository-sanity"]["reviews"]) == len(wrappers["sanity"]), "REPORT")
    for domain in ("audits", "sanity"):
        require(contract.encoded(models["fleet-" + domain]["repositories"]) == contract.encoded([models["repository-" + domain]]), "REPORT")
    plan_receipt = {"path": plan_path, "sha256": contract.digest(raw_plan) if raw_plan is not None else None,
        "state": "present" if raw_plan is not None else "missing"}
    return models, plan_receipt, reports, admission


def output_path(source, selected, plan_path):
    contract.relative(selected)
    require(selected.startswith(".cache/") and selected != plan_path and not plan_path.startswith(selected + "/"), "PATH")
    output = local_path(source / selected)
    require(source in output.parents and not output.exists() and not output.is_symlink(), "OUTPUT")
    return output


def stage(output, files):
    require(not output.exists() and not output.is_symlink(), "OUTPUT")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    local_path(output.parent)
    output.mkdir(mode=0o700)
    try:
        for name, content in files.items():
            require("/" not in name, "OUTPUT")
            with (output / name).open("xb") as target:
                target.write(content)
            (output / name).chmod(0o600)
    except BaseException:
        shutil.rmtree(output)
        raise


def publish_outputs(outputs, destination):
    if destination:
        destination = local_path(destination)
        descriptor = os.open(destination, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "a", encoding="utf-8") as target:
            require(stat.S_ISREG(os.fstat(target.fileno()).st_mode), "OUTPUT")
            for key, value in outputs.items():
                target.write(key + "=" + value + "\n")
    print(contract.encoded(outputs).decode(), end="")


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise contract.FeedError("INPUT")


def main():
    parser = Arguments(description=__doc__, allow_abbrev=False)
    for name in ("source-root", "plan", "repository", "represented-commit", "as-of", "output-directory"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--github-output")
    parser.add_argument("--runtime-parent", default=os.environ.get("RUNNER_TEMP") or tempfile.gettempdir())
    context, output, args = None, None, None
    try:
        args = parser.parse_args()
        # Preserve alias/containment guards before allocating owner runtime.
        # The locked owner must admit identity before consumer Git reads.
        source = local_path(args.source_root)
        temporary, resources = runtime(args.runtime_parent, source)
        with temporary as directory:
            audits, sanity, data = owner_modules(directory, resources)
            admission = public_context(args.repository, audits, data)
            plan_path = contract.relative(args.plan)
            output = output_path(source, args.output_directory, plan_path)
            deadline = time.monotonic() + 120
            frame = source_frame(source, args.repository, args.represented_commit, args.as_of, deadline)
            context = {"source": frame, "admission": admission}
            models, plan, reports, owner_admission = collect(source, plan_path, frame, audits, sanity, data, deadline)
        require(admission == owner_admission, "PIN")
        files = {key + ".json": contract.encoded(value) for key, value in models.items()}
        require(sum(len(content) for content in files.values()) <= MAX_TOTAL, "REPORT")
        metadata = {}
        for key, value in models.items():
            content = files[key + ".json"]
            require(len(content) <= contract.MAX_MODEL, "REPORT")
            metadata[key] = {"path": key + ".json", "sha256": contract.digest(content), "size_bytes": len(content),
                "schema": value["schema"], "contract_version": value["contract_version"],
                "repository": frame["repository"], "represented_commit": frame["represented_commit"], "as_of": frame["as_of"],
                "evidence_state": value["evidence"]["state"], "canonical_digest": value["digest"]}
        binding = implementation()
        receipt = {"schema": contract.SCHEMA, "contract_version": contract.VERSION, "visibility": "public",
            "status": "normalized", "publication": "review-only", "source": frame, "admission": admission,
            "plan": plan, "reports": reports, "models": metadata, "owners": contract.owner_profile(binding["lock_sha256"]),
            "implementation": binding, "qualification": contract.QUALIFICATION}
        contract.validate_receipt(receipt, admission=admission, expected_implementation=binding,
            repository=frame["repository"], represented_commit=frame["represented_commit"], as_of=frame["as_of"])
        for key in contract.MODELS:
            contract.validate_model_bytes(receipt, key, files[key + ".json"])
        files["review-feed-receipt.json"] = contract.encoded(receipt)
        require(len(files["review-feed-receipt.json"]) <= contract.MAX_RECEIPT, "REPORT")
        stage(output, files)
        outputs = {key: args.output_directory + "/" + key + ".json" for key in contract.MODELS}
        outputs.update({"artifact-directory": args.output_directory,
            "receipt-path": args.output_directory + "/review-feed-receipt.json",
            "receipt-sha256": contract.digest(files["review-feed-receipt.json"])})
        publish_outputs(outputs, args.github_output)
        return 0
    except Exception as error:
        # A denied selected input yields no model paths and never reflects raw
        # payload, exception, filename, protected identity or owner diagnostic.
        if context is not None and output is not None and not output.exists():
            try:
                code = str(error) if isinstance(error, contract.FeedError) else "REPORT"
                if code not in {"INPUT", "PATH", "SOURCE", "CLOCK", "REPORT", "PIN", "OUTPUT", "VISIBILITY"}:
                    code = "REPORT"
                denial = {"schema": "egohygiene.relay.typed-review-feed-denial/v1", "contract_version": contract.VERSION,
                    "visibility": "public", "status": "denied", "publication": "review-only", **context,
                    "diagnostic": code, "qualification": contract.QUALIFICATION}
                content = contract.encoded(denial)
                stage(output, {"review-feed-denial.json": content})
                publish_outputs({"artifact-directory": args.output_directory,
                    "receipt-path": args.output_directory + "/review-feed-denial.json", "receipt-sha256": contract.digest(content)}, args.github_output)
            except Exception:
                pass
        print(DENIAL, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
