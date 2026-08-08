# Mothership Router Plans

Created: 2026-08-08

## Phase 1: WGM composition

| Task | Content | DoD | Depends | Status |
| --- | --- | --- | --- | --- |
| 1.1 | Accept the public WGM handoff shape as task metadata and reject authority-bearing fields. | Valid WGM handoff routes normally; unsupported authority fields fail closed in tests. | - | cc:完了 |
| 1.2 | Add a reproducible WGM-to-Router example and compatibility documentation. | README and composition guide show a local-file-only walkthrough with no execution claim. | 1.1 | cc:完了 |
| 1.3 | Validate the package on available Python 3.12+ and update release metadata. | Tests and checksum verification pass from a clean temporary environment. | 1.1, 1.2 | cc:完了 |
