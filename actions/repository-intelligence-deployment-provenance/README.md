# Repository Intelligence deployment provenance

Bind Relay's deterministic Repository Intelligence build to a consumer-owned
site composition and deployment without giving Relay deployment authority.
This action has no token, network, artifact-upload, Pages, OIDC, or provider
write surface. It reads consumer workspace bytes, writes bounded JSON evidence
outside the deployed site, and fails closed on drift.

## Authority boundary

- `repository-intelligence` builds `dist/intelligence/` and places the
  deterministic `build-manifest.json` inside that subtree.
- This action verifies the manifest and the caller's final site. It never
  deploys the site.
- The consumer workflow remains the only owner of composition, aliases,
  artifact upload, deployment, conclusion, environment, URL, and rollback.
- The deployment receipt is written beneath the configured evidence directory,
  never inside the deterministic Relay bundle or composed site.

## Ordered operations

| Operation | When | Result |
| --- | --- | --- |
| `capture-baseline` | After the consumer builds its existing site, before Relay writes `/intelligence/` | Records the hashes of every unrelated consumer-owned file and route entrypoint. |
| `verify-composition` | After Intelligence and consumer aliases are composed, before upload or deployment | Verifies revisions, contract versions, freshness, bundle digest, required routes, aliases, and non-clobber evidence. |
| `record-receipt` | After the consumer deployment step reports a conclusion | Repeats verification, then writes a separate deployment receipt from explicit consumer metadata. |
| `verify-receipt` | During recovery, audit, or rollback rehearsal | Recomputes the handoff and requires the existing receipt to match exactly. |

Every production invocation must pin the action to the same reviewed full Relay
commit expected in `build-manifest.json`.

## Minimal composition sequence

```yaml
- name: Build consumer-owned site
  run: pnpm run build

- name: Capture consumer routes before composition
  # egohygiene/relay repository-intelligence-deployment-provenance v1.6.0
  uses: egohygiene/relay/actions/repository-intelligence-deployment-provenance@<full-relay-commit-sha>
  with:
    operation: capture-baseline
    consumer-revision: "${{ github.sha }}"

- name: Add Repository Intelligence
  # egohygiene/relay repository-intelligence v1.6.0
  uses: egohygiene/relay/actions/repository-intelligence@<same-full-relay-commit-sha>

- name: Materialize consumer-owned aliases
  run: pnpm run build:intelligence-aliases

- name: Verify composed site before deployment
  id: intelligence_provenance
  uses: egohygiene/relay/actions/repository-intelligence-deployment-provenance@<same-full-relay-commit-sha>
  with:
    operation: verify-composition
    consumer-revision: "${{ github.sha }}"
    relay-revision: "<same-full-relay-commit-sha>"
    required-routes: >-
      ["/","/intelligence/","/intelligence/now/","/intelligence/roadmap/",
      "/intelligence/decisions/","/intelligence/journey/"]
    aliases: >-
      [{"route":"/health/","target":"/intelligence/health/"}]
```

The caller then uploads and deploys its single composed `dist/` tree. Transfer
`dist/` plus the private baseline and verification files to the consumer-owned
deployment job when build and deployment use separate runners.

After the consumer deployment step, record the result:

```yaml
- name: Record consumer deployment receipt
  id: deployment_receipt
  if: "${{ always() && steps.download_provenance_inputs.outcome == 'success' }}"
  uses: egohygiene/relay/actions/repository-intelligence-deployment-provenance@<same-full-relay-commit-sha>
  with:
    operation: record-receipt
    consumer-revision: "${{ github.sha }}"
    relay-revision: "<same-full-relay-commit-sha>"
    workflow-run-id: "${{ github.run_id }}"
    workflow-run-attempt: "${{ github.run_attempt }}"
    deployment-environment: github-pages
    deployment-url: "https://repository.example/"
    deployment-conclusion: "${{ steps.deployment.outcome }}"
    aliases: >-
      [{"route":"/health/","target":"/intelligence/health/"}]
    rollback-revision: "<previous-deployed-consumer-sha>"
    rollback-site-digest: "sha256:<previous-composed-site-digest>"
    rollback-url: "https://repository.example/"
```

Preserve the receipt as a consumer-owned Actions artifact or other reviewed
deployment record. Do not copy it into `dist/intelligence/`; doing so would
couple run-specific metadata to deterministic build bytes.

## Evidence contracts

The action writes three closed public-safe contracts under
`.relay/repository-intelligence-deployment/` by default:

- `consumer-route-baseline.json` — the consumer revision plus every
  pre-composition file and route-entrypoint digest outside `/intelligence/`;
- `composition-verification.json` — manifest identity and digest, final site
  digest, published routes, aliases, freshness policy, and byte-preserved
  consumer routes;
- `deployment-receipt.json` — the exact build-manifest reference, consumer
  workflow run and attempt, environment, URL, conclusion, final composition,
  aliases, and prior deployed rollback point.

The deterministic build manifest uses
`egohygiene.relay.repository-intelligence-build-manifest/v1`. Deployment
receipts use
`egohygiene.relay.repository-intelligence-deployment-receipt/v1`.

## Failure and recovery

The verifier rejects:

- consumer or Relay revision drift;
- any manifest payload digest or inventory mismatch;
- unsupported manifest, input, or schema versions;
- a missing generated, required, or declared alias route;
- a source epoch older than `maximum-source-age-seconds`;
- a removed or byte-changed consumer-owned baseline route;
- an incomplete or inconsistent deployment receipt;
- symlinks, traversal, absolute evidence paths, oversized inventories, unsafe
  URLs, credentials, query strings, fragments, and non-public literal hosts.

To recover, rebuild the exact consumer revision with the same immutable Relay
revision, recapture the baseline from a clean consumer build, re-run
`verify-composition`, and deploy again. To roll back, redeploy the exact prior
consumer revision and composed-site digest named by the last accepted receipt,
then create a new receipt for that rollback deployment. A receipt records
consumer evidence; it never authorizes a deployment or proves remote bytes by
itself.

## Fixture versus production evidence

Relay's tests and reference workflow prove the contract, negative cases,
non-clobber behavior, and deterministic separation without claiming a real
production deployment. A production consumer must retain its own workflow run,
deployment result, receipt artifact, and—when required—separate remote route or
byte verification.
