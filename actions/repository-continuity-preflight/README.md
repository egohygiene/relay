# Repository Continuity Preflight

Runs the exact source-pinned EgoLint continuity validator in offline mode and
normalizes its dedicated report into Relay's shared result contract. Validation
runs in an ephemeral copy, so only the request-selected Relay JSON output is
written to the caller checkout.

The caller supplies a request, the exact pinned EgoLint source checkout, and a
repository-owned continuity policy. The action never fetches dependencies,
stages, commits, pushes, contacts GitHub, or authors continuity prose. Missing
or incompatible execution inputs produce an explicit schema-valid
`unavailable` result and a failing exit status.

Pull-request workflow composition and checkout acquisition belong to #63.

