# Architecture workflow evidence (internal)

This helper belongs exclusively to the experimental
`repository-architecture-validation.yml` workflow. It is not an independently
released composite-action API. The workflow resolves it through `$/` at its
exact Relay revision, and it imports only trusted sibling Relay scripts with
Python isolation enabled.

Operations prepare a bounded request, acquire locked dependencies, build the
native runtime offline, run the shared adapter, finalize fresh evidence, and
present annotations/summary before enforcement. Provider identities come from
the job environment. No operation runs caller code. Fresh adapter output is
copied into isolated runner-temporary storage with a checksummed receipt;
pre-existing caller reports are never accepted as current evidence.

See [the workflow contract](../../../docs/repository-architecture-workflow.md)
for inputs, report privacy, stage semantics, limits and unresolved release gates.
