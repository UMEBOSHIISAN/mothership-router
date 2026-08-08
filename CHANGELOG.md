# Changelog

## 0.3.0 — 2026-08-09

- Version every dry-run result as the closed `router-manifest` 1.0 protocol.
- Preserve validated WGM task identity while keeping legacy task IDs null.
- Package the owner JSON Schema and add Mothership 0.2 conformance evidence.
- Emit canonical compact CLI JSON and fixed, path-free input errors.
- Correct clean-environment test setup and refresh tracked source checksums.

## 0.2.0 — 2026-08-08

- Accept the WGM 0.2 public handoff as reviewed task metadata.
- Reject incomplete or authority-bearing WGM handoffs instead of silently carrying unknown fields.
- Add a reproducible local-file composition walkthrough and compatibility table.

## 0.1.0 — 2026-08-08

- Initial clean-room public package.
- Pure, deterministic candidate selection; registry-bound, expiring human approval.
- JSON-only dry-run CLI with no execution adapters, credentials, endpoints, retry, or fallback.
