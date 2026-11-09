# Public fleet artifact delivery

Refs [Relay #153](https://github.com/egohygiene/relay/issues/153) and
[site #27](https://github.com/egohygiene/egohygiene.io/issues/27).

`repository-intelligence-fleet-artifact` completes the transport around the
existing offline fleet assembler. It reads only explicitly selected public
repository artifacts, invokes the pinned Observatory fleet model and retains
one ordinary handoff artifact. It does not discover a fleet, execute consumer
code, modify canonical intent, install a schedule, upload Pages or deploy.

## Admission and compatibility

The action requires a full Relay commit pin. It optionally accepts a trusted Hygiene Git
object store, or acquires only the separately locked public catalog source selected by
`public-catalog-admission.v1.lock.json`. That profile consumes Hygiene #97's
derived public projection, rather than validating its new fields against the
historical raw catalog schema. Canonical role/gate authority remains Hygiene;
fresh identity observations do not refresh older role/gate declarations.

The historical `public-fleet.v1.lock.json`, default `legacy-review` assembler
profile and review envelope are preserved. The opt-in `public-catalog-v1`
assembler profile changes only catalog admission. Its existing exact graph,
coverage, native validation and fleet normalization boundary remains selected.
`prepare_repository_adr_build.acquire(..., normalization_profile="public-fleet-v1")`
prepares that exact fleet runtime; no historical collector lock is rewritten.

The closed plan schema is
`actions/repository-intelligence/schemas/public-fleet-artifact-plan.v1.schema.json`.
It identifies the organization, public visibility, exact catalog revision and
selected repository rows. Each row supplies its requested represented commit
and nullable `candidate` / `last_known` selections. A selection has exact
`artifact_id`, `artifact_sha256` (ZIP bytes), `source_commit`, `run_id` and
`run_attempt`. Supply real retained values from the Compare artifact producer;
there is no latest-run/name lookup and no implicit baseline.

Public catalog admission precedes artifact selection validation, metadata
lookup, hash inspection or acquisition. Unknown/nonpublic selections are
ignored without exported names, counts, placeholders or provider diagnostics.
Each admitted repository is isolated from another's missing, expired,
inaccessible, incompatible or malformed artifact. A failed current selection
can fall back only to its explicitly selected compatible last-known capture;
original source times and represented commits remain unchanged and stale.

Each selected provider run must be completed/successful, match its exact
attempt/source commit and have the catalog's public numeric repository identity.
Artifacts must match their exact ID/name/run/repository/source binding, ZIP
digest, bounded size, lifetime and original three-file snapshot pair manifest.
Original projection and snapshot checksums remain acquisition evidence. The
exact original public projection is revalidated/re-normalized by the existing
assembler; untrusted captured views and aggregate counts are discarded.
The supported retained profiles are `legacy-adr` and `search-attribution-v1`,
each requiring its exact selected runtime lock identity. Fleet normalization
keeps its own older owner intersection and does not claim an equivalent original
snapshot digest or attributed Search migration.

Acquisition is bounded to three requests per selected artifact and a 60-second
deadline, with one allowlisted storage redirect and no credential forwarding to
storage. Up to64 public repositories, two explicit selections each, and the
existing bounded snapshot ZIP size are supported. The site-compatible fleet
file is capped at16MiB and its handoff manifest at1MiB; the offline review
assembler retains its independent64MiB review bound. Cross-repository artifact
permissions are not assumed: use a credential authorized for read-only public
Actions artifacts; inaccessible input remains isolated. Private/internal caller
visibility and unsupported producer events are denied without public output.

## Handoff and lifecycle

The uploaded directory contains `fleet-artifact.json` and, when any repository
is usable, `fleet.json`. The manifest binds exact fleet file bytes, catalog,
generator, owner runtime, explicit observation/expiry, producer run identity,
public availability/coverage and acquisition mode. `status` is assembly
`ready`, `partial` or `unavailable`; it is not adoption, conformance, upload,
deployment, ratification or publication success. An unavailable handoff has no
invented empty fleet. The action exposes actual ordinary upload ID/ZIP digest
separately, so a consumer can retain an exact producing run/attempt and review
packet. It never overwrites a selected artifact or baseline.

The review wrapper remains `publication: denied` and stays outside the uploaded
handoff. The host's own reviewed intake and publication boundary still applies.
Retention is1–90days (default30); an expired handoff must be refreshed. Source
aging is separately evaluated from original observations (default1day), with
explicit last-known recovery aging (default31days). No scheduler or automatic
refresh dispatch is installed. Rerun the ordinary producer with a newly reviewed
explicit plan to create a new immutable handoff; retain the prior artifact's
ID/digest if selected for recovery.

The existing site loader accepts the exact `fleet.json` through
`EGOHYGIENE_INTELLIGENCE_FLEET`, `EGOHYGIENE_INTELLIGENCE_SHA256` and the explicit
`EGOHYGIENE_INTELLIGENCE_AS_OF`. The companion site change accepts optional
`EGOHYGIENE_INTELLIGENCE_MANIFEST` and
`EGOHYGIENE_INTELLIGENCE_MANIFEST_SHA256`, checking bytes, compatibility,
lifetime and fleet binding and preserving partial assembly state. It never
imports the publication-denied review wrapper or exports acquisition metadata
to browsers. Each repository's Pages site remains its detailed destination;
the site is the fleet overview.

## Captured-input replay

`repository_fleet_artifact.py` uses the same admission path for read-only
provider acquisition and `--captured-inputs`. Captures contain, per sorted public
selection slot (`00-candidate`, `00-last_known`, etc.), `run.json`,
`artifact.json`, `artifact.zip`. They remain private operational files and are
excluded from the uploaded handoff. Captured replay is explicitly labeled;
local metadata alone never proves authenticated provider truth. The CLI
requires explicit caller identity/run/event/public visibility, generator source,
as-of, plan, consumer root and a new output in runner-temporary storage outside the consumer.
Supply the trusted catalog source explicitly for network-free captured replay.
An optional prepared runtime must also live outside the consumer checkout.

## Deferred evidence

Static source/AST/JSON-schema/YAML/shell inspection is separate from execution.
No runtime acquisition, normalization, artifact download/upload, real canary,
tests, builds, CI, browser, publication or recovery exercise ran for this change.
Real retained repository pairs, exact provider upload identities, host intake
selection and mixed-state live refresh/recovery proof remain acceptance inputs.
Cross-organization namespaces/profile compatibility remain upstream work.
