# Pinned Aether repository-journal contract

This directory contains only the Aether files required to validate and render
Relay repository journals. Every byte is copied from immutable Aether merge
commit `aa0cb090a7ca4a47f22268784af0ce34aaf69b48` and is recorded in
[`catalog/repository-journal-aether.json`](../../catalog/repository-journal-aether.json).

The upstream contract is version `1.0.0` with lifecycle `draft`. Relay
therefore exposes it as a proposed surface and preserves that maturity in
provenance. Vendoring does not transfer semantic ownership from Aether.

The source-compatible directory layout is intentional. The byte-identical
renderer resolves its governing specification relative to that layout and runs
offline. Updates must change the immutable source revision, every affected
checksum, the profile version, validation evidence, and review together.
