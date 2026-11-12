# Typed review source feed

The [typed review feed action](../actions/repository-intelligence-review-feed/README.md)
is an additive source adapter for the already implemented Audits and Sanity
routes. It consumes exact Aether JSON sidecars from explicitly selected Git
objects, delegates normalization to pinned Observatory queries, and retains
separate ordinary artifact receipts. Existing native inputs, frozen recovery
pins, model defaults, deployment gates and publication authority are untouched.

Consumers select a checked-in closed plan, explicit canonical repository/full
source SHA, and the same actual UTC boundary as source capture and builder.
Empty or absent report selections yield owner-defined unavailable evidence.
Malformed provided input fails closed. Git-only reviews may represent older
revisions; their original clocks and historical context are preserved.

The receipt is byte/source evidence, not proof of auditor execution or human
ratification. No Markdown reinterpretation, provider lookup, new policy or
trusted human context is introduced. A separately retained singleton fleet can
be selected by the website without re-normalization or clock rewriting. Actual
multi-capture aggregation and uncommitted current-review capture require later
owner-reviewed bridge contracts.

Tests, native/helper execution, builders, browser and CI qualification remain
deferred. The root handoff records exact source commits and consumer review
links separately from these functional sources.

Refs #74, #76 and egohygiene/reflector#258.
