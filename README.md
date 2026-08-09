# Mothership Router

> A human-gated routing boundary for portable AI coding environments.

Mothership Router selects an eligible local alias, verifies a registry-bound
human approval, and emits a dry-run manifest. It ships with no executable
provider command and never invokes a model by default.

日本語: これは「LLM を勝手に動かすルーター」ではありません。候補を安全に
絞り込み、人間の承認が現在のローカル登録簿に結び付いていることを確認し、
実行前に確認できる JSON を出すための境界コンポーネントです。

## Guarantees

- Registries begin with no ready executor.
- A recommendation is not selection, approval, or execution.
- Approval is bound to the exact registry digest and expires.
- Dry runs emit inspectable JSON only.
- No retry, fallback, recursive invocation, background runner, credential, or
  provider endpoint is included.

## Quick start

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m mothership_router examples/task.json examples/registry.json
```

The command reads JSON and prints an advisory dry-run manifest. It does not
launch a process. Router 0.3.0 emits the closed `router-manifest` 1.0 object;
its JSON Schema is packaged with the library at
`mothership_router/schema/router-manifest.1.0.schema.json`.

To pass the portable public WGM 1.1 handoff directly:

```sh
PYTHONPATH=src python3 -m mothership_router \
  examples/wgm-handoff.json examples/registry.json
```

When `schema_version` identifies a supported WGM 1.0 or 1.1 handoff, Router requires the complete
public field set and rejects every unknown field. This prevents embedded
credentials, prompts, local-path fields, path-bearing public identifiers, or
claimed execution permission from being silently carried across the boundary.
Those public identifiers use one portable ASCII token grammar: an alphanumeric
first character followed by alphanumerics, `.`, `_`, `:`, or `-`, with
drive-relative `X:` prefixes rejected. New producers should select WGM 1.1;
1.0 remains recognized for compatibility but Router still applies its own
fail-closed identifier policy at the consumer boundary.

## Input contract

`TASK.json` is a small request object:

```json
{"capability": "code-review", "risk": "low"}
```

`REGISTRY.json` is a local, user-maintained list. An entry must be explicitly
`"ready"` before it can be recommended; the supplied example contains only a
`"staged"` entry, so it safely returns `no_ready_executor`.

```json
{
  "executors": [{
    "alias": "local-reviewer",
    "status": "ready",
    "capabilities": ["code-review"],
    "max_risk": "medium",
    "cost_rank": 1
  }]
}
```

An approval is accepted only when all of these match: the selected alias, the
current SHA-256 digest of the whole registry, a `human` approver class, an
`approve` event, and a future ISO-8601 `expires_at`. Even then, the result is
only `approved_dry_run`; this package has no command-launching API.

## How the parts connect

```text
evidence + task
    |  (validate authority trail)
    v
Workflow Governance Model
    |  (reviewed request)
    v
Mothership Router ──> inspectable dry-run manifest
    |                         |
    |                         `-- no execution here
    v
Mothership contracts / separately configured local tools
```

Use the Workflow Governance Model first when a workflow needs evidence,
claim-strength, approval, and receipt checks. Use Mothership Router only after
that review when you need a deterministic candidate from a local registry.
Mothership supplies the portable environment contracts and diagnostic context.
Each project can also be used independently.

See [the composition walkthrough](docs/composition.md) for the local-file-only
WGM 0.2.x → Mothership Router 0.3.x handoff.

## Status values

| Status | Meaning |
| --- | --- |
| `human_review_required` | High-risk input is deliberately not routed. |
| `no_ready_executor` | No explicit ready local entry matches. |
| `approval_required` | A candidate exists, but no valid current human approval exists. |
| `approved_dry_run` | Approval is valid; inspect the manifest and act manually outside this package. |

Every result has `authority_effect: false` and `execution_effect: false`.
Every 1.0 result also carries `schema_version`, a nullable `task_id`, and a
nullable `capability`. A validated WGM handoff preserves its identity. The
legacy two-field task form preserves a valid capability but emits a null task
ID because that form has no versioned identity contract.

## Mothership conformance

Router owns the semantics and exact bytes of `router-manifest` 1.0. The
[`suite/mothership-0.2-conformance.json`](suite/mothership-0.2-conformance.json)
manifest binds that schema digest to a synthetic, credential-free example.
[Mothership 0.2](https://github.com/UMEBOSHIISAN/mothership) freezes those owner
bytes and checks them as one step in its optional companion chain. Conformance
proves shape, version, and false effects; it does not prove approval, execution,
freshness, or publication.

The 0.3.0 output adds required fields to the former unversioned object. Readers
that already ignored unknown fields remain source-compatible. Exact-shape
readers must deliberately select `router-manifest` 1.0.

## Relationship to the ecosystem

- [Workflow Governance Model](https://github.com/UMEBOSHIISAN/workflow-governance-model)
  validates evidence and authority trails before routing.
- [Mothership](https://github.com/UMEBOSHIISAN/mothership) provides portable
  contracts, diagnostics, and configuration boundaries.
- Mothership Router is the optional handoff point between a reviewed request
  and a separately configured local execution system.

## Non-goals

- Shipping credentials, endpoints, or ready-to-execute commands.
- Automatically executing a recommendation.
- Choosing a fallback after failure.

## Development

Requires Python 3.12 or newer for the published package. The implementation
uses the standard library only.

```sh
python3 -m pip install -e '.[test]'
python3 -m unittest discover -s tests -v
```

Schema conformance tests require the optional test extra; the installed runtime
remains standard-library only.

The clean-environment verification procedure is:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m unittest discover -s tests -v
```

## License

MIT. See [LICENSE](LICENSE).
