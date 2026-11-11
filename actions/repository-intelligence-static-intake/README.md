# Repository Intelligence Static Intake

This experimental, offline action verifies the website owner's portable
organization Intelligence export and stages exact review bytes. It downloads
nothing, executes no candidate code, and grants no publication authority.

The producer owns the export contract and route inventory. Observatory remains
the model owner; Hygiene remains the public inventory and policy owner. The
consumer chooses the exact producer artifact and an intended origin/mount.
Accepting this review contract does not admit a Hygiene site declaration,
approve the proposed `.github` hosting transition, or change canonical roles.

## Inputs and outputs

All inputs are required:

| Input | Meaning |
| --- | --- |
| `archive` | Local, raw ZIP downloaded by a separate trusted caller |
| `archive-sha256` | Exact ZIP digest, 64 lowercase hex characters |
| `manifest-sha256` | Exact `export-manifest.json` digest, 64 lowercase hex characters |
| `producer-commit` | Full 40-character `egohygiene/egohygiene.io` source commit |
| `origin` | Explicit intended public HTTPS origin, without trailing slash |
| `base-path` | Intended directory mount, for example `/.github/` |
| `output-directory` | New local directory under an existing trusted parent |

The outputs are `review-directory`, `site-directory`, `receipt-path`,
`receipt-sha256`, and `publication` (always `review-only`). The directory contains
the unchanged `export-manifest.json`, only its declared `site/` bytes, and a
separate `intake-receipt.json`. An existing destination is rejected. File modes
are private local review modes; the receipt records no upload or deployment.

Pin this action to a reviewed full Relay commit. A calling workflow needs no
permissions for the intake itself. A separate artifact downloader must prove the
exact public producer repository, source commit, workflow path, event, branch,
run and attempt, artifact name/ID/digest, and unexpired status. Select the exact
expected manifest digest independently; a hash extracted from the candidate
establishes byte consistency only. Preserve that transport evidence beside the
ordinary review artifact. Never treat this action's success as that proof.

## Local review

The stdlib-only CLI also accepts `--directory` instead of `--archive`:

```bash
python3 -I actions/repository-intelligence-static-intake/scripts/static_intake.py \
  --directory /absolute/path/to/producer-export \
  --manifest-sha256 "$REVIEWED_MANIFEST_SHA256" \
  --producer-commit "$REVIEWED_PRODUCER_COMMIT" \
  --origin https://egohygiene.github.io \
  --base-path /.github/ \
  --output-directory /absolute/path/to/new-review
```

Directory mode has no ZIP digest and cannot prove which downloaded archive
contained the bytes. Both modes reject symlinks, special files, ambiguous paths,
extra files, invalid UTF-8 text, duplicate JSON keys, unrecognized fields,
resource escapes, missing routes, and mismatched expected identities or hashes.
The action supports ZIP mode only. No token, package installation, Git checkout,
producer import, browser, or application runtime is needed by the intake.

## Verification boundary

The producer's closed manifest and exact 39-route fixture are byte mirrors bound
to an immutable owner source in `contracts/export-owner.v1.lock.json`. The
review-only profile includes the existing 19 canonical organization Intelligence
pages, their aliases and root redirect, plus `404.html`, empty `.nojekyll`, and
local hashed assets. It excludes general website/store/business routes, CNAME,
source maps, service workers, inline scripts and external markup/CSS resource origins.
The same pinned public catalog used by native collection authenticates every
selected repository and the admission digest. An empty admitted selection is
valid and supports the explicit unavailable skeleton.

The bounded intake allows at most 256 site files, 16 MiB per file and 64 MiB of
site bytes. ZIP input is read in place with no extraction and has separate entry,
compression, and archive limits. It never preserves candidate executable modes.
All text HTML/JS/CSS/SVG must decode as strict UTF-8. Generated HTML must carry
the exact restrictive CSP before resources and use the fixed canonical routes.
Inline SVG and React style attributes have a bounded static profile. Local
resources must name inventoried hashed assets; public hyperlinks may name only
the admitted public GitHub repository roster or its project Pages destinations.

An asset digest authenticates bytes, not arbitrary JavaScript behavior. Static
HTML/CSS checks and a bounded literal module-edge diagnostic do not prove that a bundle is safe to
execute or that it contains only the intended application modules. The CSP
blocks resource-network and worker capabilities within its browser support;
this intake does not execute it or claim a browser sandbox. The producer's
isolated entry/module boundary, immutable artifact provenance and later browser
qualification remain required review evidence. Intake never fetches hyperlinks.
The import diagnostic rejects recognizable external/unlisted literal edges;
lexical uncertainty or its 500,000-token budget ends that diagnostic. It is not a
JavaScript parser or a proof that all computed, template or module edges are
local. The receipt labels it `diagnostic-only`; the mandatory CSP and HTML
resource checks do not depend on that diagnostic succeeding.

`models.*.state=available` means the producer admitted a compatible normalized
input, even when that input explicitly reports unavailable or partial evidence.
Freshness and evidence gaps stay in the rendered pages. Presentation hashes are
producer declarations: no normalized model JSON is exported or replayed here.
The receipt explicitly records `producer-declared-not-replayed`,
`script_execution=not-performed`, `browser_qualification=unavailable`,
`hosting_transition=not-admitted`, and `deployment_authorized=false`.

Native runs, export/browser qualification, malicious-fixture execution, full
repository tests and CI remain deferred for this implementation checkpoint.

Refs egohygiene/.github#41.
