# Compose WGM and Mothership Router

The public composition is a local-file handoff, not an automatic network call.

## 1. Validate governance metadata

Use [Workflow Governance Model](https://github.com/UMEBOSHIISAN/workflow-governance-model)
to validate the workflow document and its credential-free public handoff.
The handoff schema contains only task identity, capability, risk, token budget,
and opaque evidence references.

## 2. Inspect the handoff

Copy or generate a document shaped like
[`examples/wgm-handoff.json`](../examples/wgm-handoff.json). Never add prompts,
model output, credentials, local paths, or execution permission. Router rejects
unknown fields whenever `schema_version` identifies a WGM handoff.

## 3. Request a dry-run recommendation

```sh
PYTHONPATH=src python3 -m mothership_router \
  examples/wgm-handoff.json examples/registry.json
```

The bundled registry contains only a `staged` executor, so the example returns
`no_ready_executor`. If a local operator explicitly changes a compatible entry
to `ready`, Router may emit `approval_required`. A matching, unexpired,
registry-digest-bound human approval can change that only to
`approved_dry_run`.

At no stage does this package launch a command, contact a provider, load a
credential, or convert a recommendation into execution authority.

## Compatibility

| Producer | Contract | Consumer | Supported |
| --- | --- | --- | --- |
| WGM 0.3.x | `governance-handoff` 1.1 | Mothership Router 0.3.x | Yes, preferred portable contract |
| WGM 0.3.x | `governance-handoff` 1.0 | Mothership Router 0.3.x | Yes, with Router's stricter consumer policy |
| Arbitrary JSON | Unknown fields or embedded authority | Mothership Router | Rejected |
| Mothership Router 0.3.x | `router-manifest` 1.0 | Mothership 0.2.x suite | Yes, shape/version conformance |

Router is the semantic owner of `router-manifest` 1.0. Mothership freezes the
exact owner schema bytes for reproducible cross-repository checks; it does not
redefine Router's status or approval semantics. The public example uses the
shared synthetic task ID `demo-review-001` and capability `code-review`.

Consumers of the former unversioned Router object that ignore unknown fields
remain source-compatible with 0.3.x. Consumers that compare exact object shape
must opt into the closed 1.0 schema because `schema_version`, `task_id`, and
`capability` are now required.

All repositories remain independently installable. No package automatically
discovers or imports another one.
