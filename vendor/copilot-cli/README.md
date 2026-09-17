# Repository-journal Copilot CLI lock

This directory locks the agent runtime selected by
[`catalog/repository-journal-runtime.json`](../../catalog/repository-journal-runtime.json).
It is not a JavaScript application and contains no consumer repository code.

The manifest pins `@github/copilot` exactly. The npm lockfile additionally pins
the platform packages, transitive dependencies, registry locations, and
integrity values used by a future repository-journal workflow.

Install the locked runtime without lifecycle scripts:

```bash
npm ci \
  --ignore-scripts \
  --no-audit \
  --no-fund
```

Verify the selected executable without authenticating or making an agent
request:

```bash
node_modules/.bin/copilot --version
```

Do not update the package or regenerate the lockfile independently. A runtime
upgrade must update the profile version, package version and integrity,
lockfile digests, validation evidence, and security review together.
