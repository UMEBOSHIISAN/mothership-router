# Architecture

```text
reviewed task + local registry
            |
            v
  pure candidate selection
            |
            v
exact human approval + registry digest + expiry
            |
            v
      JSON dry-run manifest
            |
            v
manual, separately configured local action
```

The router owns only the middle boundary. It neither validates governance
evidence nor launches a provider. Those responsibilities remain with the
Workflow Governance Model and a separately reviewed local execution system.
