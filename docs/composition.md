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
| WGM 0.2.x | `workflow-handoff` 1.0 | Mothership Router 0.2.x | Yes |
| Arbitrary JSON | Unknown fields or embedded authority | Mothership Router | Rejected |
| Mothership Router manifest | Read-only inspection | Mothership 0.1.x diagnostics | Documented composition only |

All repositories remain independently installable. No package automatically
discovers or imports another one.
