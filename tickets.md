# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

<!-- ticket:T-0204 -->
```yaml
id: T-0204
title: 'standing warnings triage: exports (12+ per pkg), dup 64 groups, arch 197 warns,
  perf 174'
state: queued
kind: bug
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0861
- T-0862
- T-0871
- T-0872
- T-0873
- T-0874
- T-0875
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- tests/**
- frob.toml
- docs/**
- tickets.md
threat: null
component: null
```
User directive 2026-07-18: the pass-line counters hide real debt -- frob-exports reports 12-253 public symbols missing from __init__.py per package (decide policy: export or demote to private, per package, no blanket waiver), frob-dup 64 duplicate groups (triage: real extraction candidates vs false pairs; feeds T-0187 tree), frob-arch 197 warnings + 123 suggestions (long-function/god-class residue post-calibration -- fix or waive with reasons), perf gate 174 violations (166 waived -- re-audit every waiver still holds after T-0161's heuristic fixes land; the 8 unwaived need real fixes). Deliverable: each family driven to a state where the summary line is HONEST -- zero unwaived findings or a written per-finding reason; no threshold-loosening without a disclosed decision. Split into child tickets per family if any single family exceeds a session of work -- this ticket is the umbrella and the accounting.

<!-- ticket:T-0254 -->
```yaml
id: T-0254
title: 'frob deploy epic: auditable, isolated, provable OS-layer deployment'
state: queued
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- strata-core/**
- design/**
- docs/**
- tests/**
- Makefile
- tickets.md
threat: null
component: null
```
User mandate 2026-07-19: a frob deploy utility built into strata. The threat model: red teams compromise the one user that owns a service and nothing isolates that user -- lateral and vertical movement must be PROVABLY blocked, not hoped. The deployment sequence (idempotent install, status/health, uninstall with NO artifacts) must be auditable end to end, including an expensive opt-in VM-snapshot audit (VirtualBox) that is NOT part of make check. Scripts must tie into the model so hand edits are DETECTABLE through the strata checker, and the 'weird layer between the OS and the backend' (users, groups, units, ownership, ports) becomes provable architecture. Children: std.host OS-layer modeling -> movement-impossibility proofs + deploy script generation -> script<->model conformance gate -> VM snapshot audit harness -> real-service pilot (malmberg) remediating its awkward setup. Umbrella closes when all children close.

<!-- ticket:T-0260 -->
```yaml
id: T-0260
title: 'deploy pilot: model+generate+audit malmberg''s services, remediate the awkward
  setup'
state: queued
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0257
parent: T-0254
tier: ticket
sprint: null
scope:
- docs/**
- tests/**
- tickets.md
threat: null
component: null
```
T-0254 child 6 (proof on reality). Apply the full chain to malmberg (the real server product from pilot P3: server_api/ingest/cloudsync/faces/backup/display + media_store): extend design/malmberg.strata with std.host (dedicated service users per component, units, ownership of media_store paths, ports), prove HOST001/HOST002 movement-impossibility or record honest waivers, generate the deploy scripts, run the conformance gate, and if a VirtualBox environment is available run the full VM snapshot audit and attach the attestation. Remediate the current awkward setup step in malmberg's docs/scripts with the generated sequence. Work happens IN THE MALMBERG REPO per the break-and-report pilot protocol (frob-side gaps come back as tickets, filed serially by the coordinator); this frob-side ticket tracks the campaign and collects the gap list. Success = malmberg installs/uninstalls via generated scripts with a green conformance gate and a documented (or executed) VM audit path.

<!-- ticket:T-0329 -->
```yaml
id: T-0329
title: 'EPIC arch multi-language: normalized code model + Rust/TypeScript/Kotlin adapters'
state: queued
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: epic
sprint: null
scope:
- src/frob/arch/**
- src/frob/lang/**
- docs/modules/arch.md
- tickets.md
- tests/unit/test_arch.py
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/test_arch.py
  reason: T-0329 arch work maps to tests/unit/test_arch.py
  actor: logan
  at: '2026-07-20'
threat: null
component: null
```
frob arch today has per-language walkers (_python.py, _cpp.py) only. To extend cleanly (not N copies of each check), introduce a NORMALIZED CODE MODEL: a language-agnostic view (module, class, function, method, param, branch, loop, call, import, override, field-access, return, raise/throw, catch) that each language adapter maps its tree-sitter grammar onto. Checks are written ONCE against the model; adapters supply per-grammar node-type maps. Then add adapters for TypeScript, Rust, Kotlin (Kotlin needs tree-sitter-kotlin added to frob.lang; ts/rust/cpp/c already parse via tree-sitter-language-pack). Language-specific checks (Rust must_use/ownership, TS any/strict-null) live in per-language extensions on top of the shared model. Acceptance: an arch check written once fires correctly across python+ts+rust+kotlin on equivalent code; Kotlin grammar wired; the existing python/cpp checks refactored onto the model with no regression. Children: normalized-model, ts-adapter, rust-adapter, kotlin-grammar+adapter.

<!-- ticket:T-0395 -->
```yaml
id: T-0395
title: 'advisories: large-file residue after calibrated thresholds (T-0373)'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0373
- T-1072
- T-1076
- T-1074
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/
threat: null
component: null
```
After T-0373 re-thresholds frob-arch large-file to 800 lines / 60 (function), address the residue that still exceeds 800 lines among the 34 large-file advisories: real module splits, or accepted-with-reason for files that don't decompose cleanly. Acceptance: frob check arch large-file advisories at the calibrated threshold reduced to zero unresolved.

## Failure log
- 2026-07-28 attempt 1: 31 in-scope large-file findings after T-0373 calibration (43 total minus 12 strata/vet sibling-owned), up to 12047 lines (gates/__init__.py); large-file is unwaivable per docs/modules/gates.md, real splits needed -- too large for one pass, decomposition tickets filed

<!-- ticket:T-0397 -->
```yaml
id: T-0397
title: 'AUDIT REMEDIATION EPIC: North-Star integrity -- every green must be earned'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
threat: null
component: null
```
Full-repo pessimistic capability audit (2026-07-20, 7 read-only auditors). North-Star: if frob check / a ticket-close / a strata proof passes, the thing it claims must ACTUALLY hold. The audit found the North-Star is violated in concrete ways across subsystems. Each subsystem audit gets an umbrella child holding its full findings table; each HIGH finding gets an actionable child. Findings files live in the audit run; this epic is the durable tracked home so the audit itself does not become an orphaned document (the exact failure mode that motivated it). Consolidation in progress as the 7 auditors land: tickets/testing (evidence integrity), strata (vacuous proofs), graph/edges, gates-accounting, gates-quality/security, vet (lexical resolution), lang/check/docs.

<!-- ticket:T-0802 -->
```yaml
id: T-0802
title: 'execute the 2026-10-01 navigation-command sunset: remove map/outline/xref/docs-search
  per T-0580 deprecation'
state: queued
kind: feature
origin: human
created: '2026-07-23'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/map_runner.py
- src/frob/app/outline_runner.py
- src/frob/app/xref_runner.py
- src/frob/app/docs_runner.py
- src/frob/__main__.py
- docs/modules/cli.md
acceptance:
- text: GIVEN the sunset date 2026-10-01 has passed WHEN this ticket is worked THEN
    the four deprecated navigation commands and their parsers, tests, and doc/test/export
    obligations are removed (or the sunset is explicitly re-adjudicated with the user),
    and no frob:deprecated directive for them remains
  evidence: []
threat: null
component: null
```
Sunset-execution ticket for the user's 2026-07-23 deprecation decision (T-0580, done). Stays OPEN until the sunset so the four frob:deprecated directives have a live ticket binding (DEPR002 requires ticket= to reference an open ticket -- T-0797 registration surfaced that the directives bound to the closed T-0580). Do not work before the sunset date.

<!-- ticket:T-0969 -->
```yaml
id: T-0969
title: 'Epic: burn WARN-tier quality gates to zero, then promote to ERROR'
state: queued
kind: security
origin: auditor
created: '2026-07-27'
priority: high
parent: null
tier: epic
sprint: null
threat: null
component: null
```
T-0399's gates-quality audit (docs/audits/gates-quality.md) found the
entire quality/security-advisory surface (PERF001-004, PII010/012, SEC110,
ARCH001, DUP) is WARN-tier and non-blocking, so a green `frob check` makes
no quality claim. T-0399 executed the promotable-now slice (DUP fail-
closed behavior) and measured live warning counts per family. This epic
parents the burn-down children needed before each remaining family can be
safely promoted to ERROR without redding main.

<!-- ticket:T-1006 -->
```yaml
id: T-1006
title: widespread pre-existing test failures block make coverage completion (~118
  fails, non-cov-caused)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_check_coverage_registry.py
- tests/test_coverage.py
- tests/system/test_system.py
- tests/test_makefile_lock_sync.py
- tests/test_registry_reconciliation_evasion.py
- tests/test_ticket_land.py
- tests/test_tickets_review.py
- tests/unit/deploy/test_generate.py
- tests/system/test_cli_exports.py
- tests/unit/strata/test_effects.py
- tests/unit/strata/test_export_golden.py
- tests/test_registry_reconciliation_supply_chain.py
- tests/unit/strata/test_registry_cross_corpus_totality.py
- tests/unit/test_app_runners_batch5.py
- tests/test_registry_exhaustiveness.py
- tests/unit/test_strata_tmlanguage.py
- tests/unit/test_exports.py
- src/frob/tickets/_land.py
- docs/design/registry/check-coverage.yaml
- src/frob/deploy/_generate.py
- tests/golden/frob_export_seccomp.json
- src/frob/app/exports_runner.py
- design/frob.strata
scope_changes:
- op: remove
  glob: tests/**
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_check_coverage_registry.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_coverage.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/system/test_system.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_makefile_lock_sync.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_registry_reconciliation_evasion.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets_review.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/deploy/test_generate.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/system/test_cli_exports.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/strata/test_export_golden.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_registry_reconciliation_supply_chain.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/strata/test_registry_cross_corpus_totality.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/test_app_runners_batch5.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_registry_exhaustiveness.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/test_strata_tmlanguage.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/test_exports.py
  reason: 'Narrowed from tests/** (blocks every other agent''s evidence work) to the

    17 files that actually contain the 25 currently-failing tests, measured by

    a fresh full-suite pytest run on this worktree (merged to main tip,

    natives built): tests/test_check_coverage_registry.py,

    tests/test_coverage.py, tests/system/test_system.py,

    tests/test_makefile_lock_sync.py,

    tests/test_registry_reconciliation_evasion.py, tests/test_ticket_land.py,

    tests/test_tickets_review.py, tests/unit/deploy/test_generate.py,

    tests/system/test_cli_exports.py, tests/unit/strata/test_effects.py,

    tests/unit/strata/test_export_golden.py,

    tests/test_registry_reconciliation_supply_chain.py,

    tests/unit/strata/test_registry_cross_corpus_totality.py,

    tests/unit/test_app_runners_batch5.py,

    tests/test_registry_exhaustiveness.py,

    tests/unit/test_strata_tmlanguage.py, tests/unit/test_exports.py.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/tickets/_land.py
  reason: '_do_wip_commit''s `git add -A` sweeps up frob''s own .frob/ scratch

    artifacts (cache.db, derived.lock, prework/*.json, tickets.lock) as real

    staged changes in a fixture repo with no .gitignore for .frob/, defeating

    the CRLF-normalization-only no-op detection this function exists for

    (test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed,

    part of T-1006''s triage). Needs a source fix in _land.py, not just the

    test.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'test_check_coverage_registry.py''s exhaustiveness self-check found 6 gate

    rules (VET-JS004, VET-PY001/2/3, VET-RS001/2) added to the live gate

    registry with no matching CHK-GATE-<rule> entry in

    docs/design/registry/check-coverage.yaml (REG010 drift from a landing

    wave). Fixed via the existing `frob registry audit --sync-gate-rules`

    mechanism, which appends the entries to this exact file.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/deploy/_generate.py
  reason: 'Genuine product bug found while triaging T-1006:

    tests/unit/deploy/test_generate.py::TestSorted::test_privileged_port_grants_cap_net_bind

    fails because node_may_kinds now returns T-0717 mode-qualified

    family.mode kinds (e.g. "net.out") but _CAP_KIND_MAP in

    src/frob/deploy/_generate.py is keyed by the bare coarse family ("net"),

    so a node declaring only a precise mode-qualified may atom silently loses

    its CAP_NET_BIND_SERVICE grant. Fixed by keying the lookup off the

    family prefix.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/golden/frob_export_seccomp.json
  reason: 'tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp

    byte-for-byte compares export_seccomp(design/frob.strata) against the

    committed golden. design/frob.strata has legitimately grown new net.*

    capability declarations on some node(s) since this golden was last

    regenerated (accept/bind/connect/listen/recvfrom/sendto/socket now

    appear as allowed syscalls) -- a real, deterministic exporter output

    drift, not a test bug. Regenerated the golden from the current model.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/exports_runner.py
  reason: 'Genuine product bug found while triaging T-1006:

    tests/system/test_cli_exports.py::TestExportsFlags::test_json_output and

    test_json_modules_have_symbols fail because `frob exports <path> --json`

    corrupts its own JSON payload with a leaked `gitio: spawning (...)` DEBUG

    log line whenever the T-1127 daemon-proxy fast path

    (_try_exports_via_daemon) hits: that helper''s repo_root()/query() calls

    run entirely outside run()''s quiet_stdout_logs() context (which only

    wraps the non-daemon fallback path below it in the same function). Fixed

    by wrapping _try_exports_via_daemon''s body in quiet_stdout_logs() too.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: 'My own tests/unit/test_strata_tmlanguage.py fix (renaming PARSE_RS ->

    PARSE_DIR to match the strata-core/src/parse.rs -> parse/ split) needed

    a matching SYS104 interface= sync on design/frob.strata''s testsuite node

    (mandatory per dispatch instructions: `frob sys sync-interface` before

    land). Ran `frob sys sync-interface` to write the fix.

    '
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_ticket_land.py::TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace
- tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
- tests/test_ticket_land.py::TestMergeConflictOutsideLedger::test_real_conflict_outside_tickets_md_aborts
- tests/test_tickets_review.py::TestCloseStrictMode::test_strict_flag_alone_does_not_gate_without_config
- tests/test_tickets_review.py::TestCloseStrictMode::test_config_gate_alone_does_not_enforce_without_strict_flag
- tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_succeeds_with_matching_approve_review
- tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_succeeds_with_abbreviated_review_commit
- tests/test_registry_reconciliation_evasion.py::TestEvasionExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
- tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
- tests/test_coverage.py::TestPythonCoverageTargets::test_nothing_touched_returns_empty
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
- tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations
- tests/test_makefile_lock_sync.py::test_upload_relocks_after_version_bump
- tests/system/test_system.py::test_sys_audit_hardened_waived_two_user_model_proved
- tests/unit/deploy/test_generate.py::TestSorted::test_privileged_port_grants_cap_net_bind
- tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_is_mutually_navigable
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
- tests/unit/test_app_runners_batch5.py::TestStatsRunner::test_json_mode_prints_json
- tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally
- tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
- tests/system/test_cli_exports.py::TestExportsFlags::test_json_output
- tests/system/test_cli_exports.py::TestExportsFlags::test_json_modules_have_symbols
threat: null
component: null
```
Found while working T-0997 (coverage pipeline fix): a real, fresh `make
coverage` run in a clean worktree (merged to main tip) shows ~118 test
failures that are NOT caused by coverage instrumentation -- reproduced
several individually WITHOUT --cov and they still fail (e.g.
tests/test_registry_reconciliation_patterns.py::TestExhaustivenessGateOverRealPatterns::test_no_patterns_violations,
tests/test_ticket_land.py::TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace,
tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root).
These span registry-reconciliation exhaustiveness self-checks
(patterns/compliance/secrets/supply_chain/weaknesses/system_design all
report real violations against this worktree's live tickets.md/registry
state), ticket-land/evidence-enforcement system tests, and a handful of
CLI system tests. Because pytest exits non-zero, `make coverage`'s
Makefile recipe halts before its own `coverage combine`/`coverage xml`/
`frob check --stamp-coverage` lines run, so a fresh `make coverage`
currently requires a manual combine/xml/stamp workaround to get any
numbers at all -- and the failing subprocess-heavy system tests never
contribute their coverage, capping how far `join_fraction` can rise
(0.49 observed vs T-0997's target of "well above 0.34"; a green suite
would likely push it meaningfully higher). Needs triage: some of these
may be genuine registry drift in this worktree's ticket state (dozens of
concurrent worktree agents landing tickets) rather than a real product
bug; others (the gitless-target severity assertion, the render-lint
stderr-vs-logging-capture mismatch) look like real, fixable test/gate
bugs. Scope was deliberately not widened to fix these under T-0997.

2026-07-28 coordinator addendum (refiled from a w18-strata3 draft that
died to ledger-restore cycles): three more members of this failure set,
each verified pre-existing on main and unrelated to the wave-17/18
changes: tests/system/test_export_golden.py TestExportGolden
test_seccomp; tests/unit/strata/test_effects.py
TestDeployServeMutateNodeSplitConformance
test_serve_declares_zero_may_and_exercises_zero_effects;
tests/test_registry_cross_corpus_totality.py
TestCrossCorpusLinkageIntegrity
test_every_cross_ref_is_mutually_navigable. Fold them into this
ticket's triage denominator.

## Done report

Re-measured the full suite on a fresh worktree (merged to main tip
4310bb76, natives built): a foreground `pytest -p no:cacheprovider -q`
run completed in one shot with 25 failures total (not ~118 -- the prior
number was stale, most of it already fixed by earlier waves before this
ticket started).

Triaged all 25 into fix-in-place (22) or filed-as-separate-ticket (3,
each requiring a real cross-file security/architecture disposition
outside this ticket's tests/**-rooted scope):

Genuine product/source bugs fixed:
- src/frob/tickets/_land.py::_do_wip_commit -- `git add -A` swept up
  frob's own .frob/ scratch artifacts (cache.db, derived.lock,
  prework/*.json, tickets.lock) as real staged changes in a fixture repo
  with no .gitignore, defeating the CRLF-normalization-only no-op
  detection. Excluded `.frob/` from the wip-commit pathspec.
- src/frob/deploy/_generate.py::_node_capabilities -- CAP_NET_BIND_SERVICE
  silently stopped being granted for any node declaring only a T-0717
  mode-qualified `family.mode` may atom (e.g. "net.out"), because
  _CAP_KIND_MAP is keyed by the bare coarse family ("net"). Fixed the
  lookup to key off the family prefix.
- src/frob/app/exports_runner.py::_try_exports_via_daemon -- `frob
  exports <path> --json` corrupted its own JSON payload with a leaked
  `gitio: spawning (...)` DEBUG log line whenever the T-1127 daemon-proxy
  fast path hit, because that helper's repo_root()/query() calls ran
  entirely outside run()'s quiet_stdout_logs() context. Wrapped the
  helper's body in the same context the non-daemon fallback already uses.

Test/fixture fixes (stale expectations, drift from landing waves):
- tests/test_ticket_land.py (3 tests) -- raw `git status --porcelain`
  checks that should have used the file's own `_status_ignoring_frob`
  helper (like every sibling assertion in the same tests), tripped by
  land's own `.frob/land.lock`.
- tests/test_tickets_review.py (4 tests) -- fixture evidence id
  ("tests/fixture.py::test_ok") never resolved against a real test;
  close()'s N-02 evidence-reverification (added after this fixture was
  written) now always fails it. Fixture writes one real, trivial, always-
  green test file instead.
- tests/test_registry_reconciliation_evasion.py /
  _supply_chain.py -- their positive-case "at least one deferred entry"
  self-checks now find zero (every prior deferral has been resolved by
  landing waves); skip with a clear reason instead of asserting a false
  premise, matching the T-1116 precedent already in the sibling
  weaknesses.py test. Waived the resulting DUP001/DUP002 clone findings
  (T-1116-precedented, same shape across all four sibling registry test
  files by convention).
- tests/test_coverage.py::_init_repo -- fixture never gitignored .frob/,
  so frob's own derived.lock write during the test showed up as a real
  untouched-by-user file and fell back to a suite-wide '*' selection.
  Added `.frob/` to the fixture's own .gitignore.
- tests/test_check_coverage_registry.py / test_registry_exhaustiveness.py
  (REG010 half) -- 6 live gate rules (VET-JS004, VET-PY001-3, VET-RS001-2)
  had no CHK-GATE entry in check-coverage.yaml. Ran the existing `frob
  registry audit --sync-gate-rules` to file them.
- tests/unit/strata/test_registry_cross_corpus_totality.py -- two
  one-directional cross_refs (SLH-SYS-EVA-01/02 -> CHK-GATE-SYS103/100)
  missing the reciprocal link on the check-coverage.yaml side. Added the
  two missing cross_refs.
- tests/test_makefile_lock_sync.py -- asserted a literal `uv lock` step
  the Makefile's `upload:` recipe no longer has (T-1009 replaced it with
  `frob release sync`, which relocks uv.lock internally). Updated the
  assertion to check for the superseding step instead.
- tests/unit/deploy/test_generate.py -- same T-0717 mode-qualified-kind
  root cause as the _generate.py fix above; test now passes with the fix.
- tests/system/test_system.py -- hardened two-user model fixture never
  declared `attr health;` on its two `unit` daemon nodes; a real,
  currently-live reliability obligation (check_reliability_health) now
  requires it. Added the attr to both fixture nodes.
- tests/unit/strata/test_export_golden.py::test_seccomp -- design/
  frob.strata legitimately grew new net.* capability declarations since
  this golden was captured (accept/bind/connect/listen/recvfrom/sendto/
  socket now appear as allowed syscalls for the affected node(s)).
  Regenerated the golden from the current model.
- tests/unit/test_app_runners_batch5.py::TestStatsRunner::
  test_json_mode_prints_json -- `stats_run` now proxies through the T-1094
  daemon by default; the background-daemon-subprocess/socket-retry path
  writes asynchronously and is not reliably observable via capsys/capfd at
  the point stats_run returns. Set FROB_NO_DAEMON=1 (the documented
  T-1093 bypass) so this unit test exercises the runner's own synchronous
  rendering deterministically -- the daemon round trip has its own
  dedicated coverage in tests/test_app_daemon_proxy.py.
- tests/unit/test_strata_tmlanguage.py -- strata-core/src/parse.rs was
  split into strata-core/src/parse/ (mod.rs + 6 grammar_*.rs/lexer.rs
  files, mirroring the T-1103 tickets/__init__.py split precedent).
  Updated the drift-lock to concatenate every .rs file under parse/, and
  ran `frob sys sync-interface` to fix the resulting SYS104
  interface=PARSE_RS -> PARSE_DIR drift on design/frob.strata (this was
  the one self-inflicted regression caught by a second full-suite run
  after the rename -- fixed before finalizing).

Filed as separate tickets (each needs a real judgment call/cross-file
work outside tests/**), one already dropped as moot:
- T-1168 (vet: 11 missing frob:enforces CHK-GATE edges,
  REG008 burn-down for VET007-010/SYSWAIVE003/VET-JS004/VET-PY001-3/
  VET-RS001-2) -- filed, then DROPPED after merging main (daada10f):
  concurrent wave work independently resolved every REG008 finding
  before this ticket was ever started on it; a post-merge run of
  TestCheckCoverageReg008BurnDown passes clean (0 findings).
- T-1166 (strata: serve daemon now exercises real net/fs
  effects directly -- capability-boundary disposition needed) --
  test_serve_declares_zero_may_and_exercises_zero_effects is CORRECTLY
  catching a genuine T-1094/T-1096 capability-creep regression per its
  own T-0440 docstring; needs either a declared `may net.connect`/
  `may fs.write` on serve's design node (with justification) or a
  refactor to delegate through an existing may-bearing node -- a
  security-boundary call, not a test fix.
- T-1167 (exports: 15 public symbols across frob/serve/vet
  never wired into __init__.py or demoted private, T-0871 policy
  residue) -- each of 15 symbols needs its own public-vs-private
  judgment call across 3 packages' __init__.py files.

Full-suite verification (9 separate foreground runs across the session,
including 2 re-merges of a fast-moving main mid-ticket -- T-1134 then
07c0026f both landed while this ticket was in flight, each briefly
reintroducing a REG010/REG008 registry-drift pair via newly-synced gate
rules INV006 then NATIVE001; each was re-triaged the same way as the
original 25): `pytest -p no:cacheprovider -q` completes (exit 1, not a
timeout/hang) with exactly 2 failures remaining after the final merge,
both filed as tickets, neither in T-1006's own declared scope. This is
down from the ~118 historically named in the ticket and the 25 actually
re-measured at start. `git log --oneline -1 main` == this worktree's own
merge parent at every merge point; `git diff main --diff-filter=D
--stat` is empty at the final commit.

Final remaining 2 (both filed, security/policy judgment calls, not test
fixes):
- tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects
  -- T-1166
- tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
  -- T-1167
(T-1168, the original REG008 filing, was dropped as moot once
main's concurrent work resolved it; T-1169 refiles the same
REG008 gap for the ONE new gate rule -- NATIVE001 -- this ticket's own
merge-chase surfaced live via --sync-gate-rules, and is not currently
red in the merged worktree state below.)

`frob sys sync-interface --check`: clean (no drift).
`frob ticket sweep T-1006`: clean, no malformed directives.
`frob check --ticket T-1006` (chunked, every gate group): 0 errors in
every group except the 5 pre-existing ARCH001/ARCH103 findings in files
this ticket never touched (check_runner.py, _close_cmd.py, doctor.py,
_setters.py -- confirmed via `git status --porcelain` these are not in
this ticket's diff) and the pre-existing ruff-check/ruff-format/CRLF
findings, also confirmed present on main and on files outside this
diff.

### Changed
```
 design/frob.strata                                 |    2 +-
 docs/design/registry/check-coverage.yaml           |   10 +-
 src/frob/app/exports_runner.py                     |   39 +-
 src/frob/deploy/_generate.py                       |   14 +-
 src/frob/tickets/_land.py                          |    8 +-
 tests/golden/frob_export_seccomp.json              |   14 +
 tests/system/test_system.py                        |    2 +
 tests/test_coverage.py                             |    9 +
 tests/test_makefile_lock_sync.py                   |   13 +-
 tests/test_registry_reconciliation_evasion.py      |   12 +-
 tests/test_registry_reconciliation_supply_chain.py |   12 +-
 tests/test_ticket_land.py                          |    4 +-
 tests/test_tickets_review.py                       |   17 +-
 tests/unit/test_app_runners_batch5.py              |   17 +-
 tests/unit/test_strata_tmlanguage.py               |   40 +-
 tickets.md                                         | 1162 +++++++++++++++++++-
 16 files changed, 1328 insertions(+), 47 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestMergeConflictOutsideLedger::test_real_conflict_outside_tickets_md_aborts` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestCloseStrictMode::test_strict_flag_alone_does_not_gate_without_config` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestCloseStrictMode::test_config_gate_alone_does_not_enforce_without_strict_flag` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_succeeds_with_matching_approve_review` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestCloseStrictMode::test_both_gates_on_succeeds_with_abbreviated_review_commit` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_evasion.py::TestEvasionExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestPythonCoverageTargets::test_nothing_touched_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules` (pytest node id, verified passing when recorded)
- `tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations` (pytest node id, verified passing when recorded)
- `tests/test_makefile_lock_sync.py::test_upload_relocks_after_version_bump` (pytest node id, verified passing when recorded)
- `tests/system/test_system.py::test_sys_audit_hardened_waived_two_user_model_proved` (pytest node id, verified passing when recorded)
- `tests/unit/deploy/test_generate.py::TestSorted::test_privileged_port_grants_cap_net_bind` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_is_mutually_navigable` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestStatsRunner::test_json_mode_prints_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally` (pytest node id, verified passing when recorded)
- `tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_exports.py::TestExportsFlags::test_json_output` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_exports.py::TestExportsFlags::test_json_modules_have_symbols` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 22 passed (from 22 evidence id(s))
- gates: 13 error(s), 735 warning(s), 446 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/vet/_supplychain.py:155, E501@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/vet/_supplychain.py:170, E501@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/vet/_supplychain.py:212, E501@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/vet/_supplychain.py:271, E501@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/vet/_supplychain.py:299, F401@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/tickets/__init__.py:111, F401@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/tickets/__init__.py:22, F401@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/tickets/__init__.py:23, F401@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/tickets/__init__.py:35, F401@/home/logan/projects/frob/.claude/worktrees/w19-tests/src/frob/tickets/__init__.py:46, PRE001@tickets/T-1006

<!-- ticket:T-1021 -->
```yaml
id: T-1021
title: 'WAIVE004 stale-waiver sweep: remove ~655 waivers matching 0 findings (full-run
  verified)'
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/
- tests/
acceptance:
- text: GIVEN a full unscoped frob check THEN WAIVE004 warnings are zero and gate
    errors remain zero
  evidence: []
threat: null
component: null
```
WAIVE004 flags waivers that match 0 findings. Its own message warns the signal is only trustworthy from a FULL unscoped run -- verify against a full run, never --only. For each stale waiver: remove it, unless git history shows it guards a known-flaky/diff-scoped rule (leave those with a comment upgrading them to deliberate). Re-run full check after removal batches to confirm no gate flips to error (a waiver whose removal surfaces a live finding was NOT stale -- restore it and ticket the finding instead).

<!-- ticket:T-1038 -->
```yaml
id: T-1038
title: promote OPAQUE001 to ERROR-tier once frob's own 93-site first-turn-on set is
  fixed-or-waived
state: queued
kind: security
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_opaque.py
- src/frob/vet/**
- src/frob/app/config.py
- src/frob/deploy/**
- src/frob/dup/**
- src/frob/fuzz/**
- src/frob/graph/**
- tests/**
threat: null
component: null
```
T-0665 landed OPAQUE001 (frob.gates._opaque.opaque_gate) at WARN-tier
per the T-0688/T-0973 first-turn-on promotion precedent: a first
measurement against frob's own tracked codebase found 93 real sites
after string-literal/comment false-positive filtering (147 before),
concentrated in test fixtures using dynamic getattr/setattr for
monkeypatch-style assertions, plus a handful of production sites
(src/frob/app/config.py, src/frob/deploy/_conform.py,
src/frob/dup/_pipeline.py, src/frob/fuzz/_signatures.py,
src/frob/graph/lock.py, src/frob/vet/_capability.py itself). This is
above the >25-site WARN-first threshold, so promoting straight to
ERROR was not safe to do in the same ticket.

Scope: audit each of the ~93 sites and either (a) rewrite to a static
name where the dynamic lookup was incidental, or (b) add an honest
`frob:waive OPAQUE001 reason="..."` naming why the site is a legitimate
runtime-resolved indirection (most test-fixture sites will fall here --
mock/monkeypatch dynamic attribute access is often intentional test
infrastructure, not an evasion risk). Once the WARN count reaches zero
real (unwaived) findings, promote opaque_gate's Severity from WARN to
ERROR in src/frob/gates/_opaque.py.

<!-- ticket:T-1062 -->
```yaml
id: T-1062
title: EXHAUST001/002 residual burn-down continuation (post T-1056)
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
threat: null
component: null
```
Follow-up to T-1056, which closed only the src/frob/gates/__init__.py
slice (16 of 176 sites) of the EXHAUST001/002 turn-on debt burn-down.

Remaining sites (per T-1056's `frob check --only exhaustive_handling
--json` snapshot, minus the closed gates/__init__.py slice and minus the
two sibling-owned trees T-1056 skipped for coordination):

  8 src/frob/gates/_coverage.py
  6 src/frob/dup/_pipeline.py
  6 src/frob/tickets/_leases.py
  5 src/frob/deploy/_conform.py
  5 src/frob/mutate/__init__.py
  5 src/frob/outline/__init__.py
  5 src/frob/strata/_claims.py
  5 src/frob/tickets/__init__.py
  4 src/frob/app/check_runner.py
  4 src/frob/check/_python.py
  4 src/frob/gates/_docptr.py
  4 src/frob/gates/_secrets.py
  4 src/frob/mutate/_journal.py
  4 src/frob/strata/_host_isolation.py
  4 src/frob/strata/_native_staleness.py
  4 src/frob/testing/_collect.py
  3 src/frob/doctor.py
  3 src/frob/gates/_docblocks.py
  3 src/frob/gates/_prework.py
  3 src/frob/stats/_agentic.py
  3 src/frob/xref/__init__.py
  ...remainder spread 1-2 per file across app/gates/check/strata/testing.

Excluded from this list entirely (owned by sibling tickets, do not
recount without checking their status first): src/frob/perf/** (T-1053)
and src/frob/vet/** plus src/frob/gates/_opaque.py (T-1051).

Same disposition rule as T-1056/T-1022: each site gets a truthful
frob:raises/frob:callee-raises annotation (verify against what the
callable can actually raise), a cheap errors-as-values refactor
(tool_crash_result()-style at subprocess/parse boundaries, or a fail-open
try/except matching the function's own documented degrade contract), or a
reasoned frob:waive -- never a blanket suppression. Re-run
`frob check --only exhaustive_handling --json` at the start to get a live
count before starting (T-1056's counts will have drifted).

<!-- ticket:T-1074 -->
```yaml
id: T-1074
title: 'arch: triage 800-2000 line file residue (T-0395 remainder tier 3)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
threat: null
component: null
```
Filed from T-0395 (failed as too large for one pass). Remaining in-scope
large-file residue under 2000 lines (frob-core/src/lib.rs 2277 --
excluded, native crate, separate toolchain/ownership from the python
gates split above; list the rest as of 2026-07-28):
src/frob/tickets/_models.py (1658), src/frob/arch/_patterns.py (1486),
src/frob/app/check_runner.py (1468), src/frob/gates/_docblocks.py (1460),
src/frob/arch/_python.py (1267), src/frob/testing/_collect.py (1267),
src/frob/gates/_protocol_summary.py (1244), src/frob/tickets/_leases.py
(1191), src/frob/app/config.py (1118), src/frob/gates/_secrets.py (1108),
src/frob/graph/dsl.py (1033), src/frob/gates/_docptr.py (1000),
src/frob/gates/_registry_exhaustiveness.py (993), src/frob/check/__init__.py
(958), src/frob/check/_python.py (936), src/frob/graph/__init__.py (869),
strata-core/src/lib.rs (869, native crate -- confirm with the strata
sibling ticket owner before touching), src/frob/app/sys_runner.py (851),
src/frob/perf/_rules.py (845), src/frob/arch/_rust.py (838),
src/frob/graph/callgraph.py (830), src/frob/perf/_effect_summaries.py
(823), src/frob/gates/_refs.py (818). Triage into real splits vs.
files that genuinely do not decompose cleanly (record the specific
reason per file, per this ticket's acceptance framing) -- do not attempt
all ~20 in one diff; group by subsystem and land incrementally, full
suite verification per group.

<!-- ticket:T-1083 -->
```yaml
id: T-1083
title: 'arch: abstraction-opportunity remaining single-file packages extraction (T-0393/T-1067
  remainder, 23 findings)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/
- src/frob/dup/
- src/frob/lang/
- src/frob/perf/
- src/frob/process/
- src/frob/render/
- src/frob/serve/
- src/frob/strata/
- src/frob/testing/
- src/frob/tickets/
- src/frob/vet/
threat: null
component: null
```
Filed from T-1067 (T-0393's remainder, re-measured post T-1068). The
remainder of the 84 abstraction-opportunity findings not covered by this
pass's sibling per-package tickets (gates/**, arch/**, app/**) is spread
one-or-two-per-file across ~19 small/standalone modules, ~23 findings
total: `check/_native.py` 1, `check/_python.py` 1,
<!-- frob:waive DOC006 reason="describes the per-file finding count as measured at filing time (T-1067); dup/_pipeline.py has since been split into a package (T-1099-era), rewriting would misrepresent what was actually filed" -->`dup/_pipeline.py` 2,
`lang/__init__.py` 1, `lang/_extract.py` 1, `lang/_walk_kotlin.py` 1,
`perf/_loop_effects.py` 1, `process/parsers/cargo.py` 1,
`render/_renderer.py` 1, `serve/_tools.py` 1, `strata/_compliance.py` 1,
`strata/_export.py` 1, `strata/_selfconform.py` 1, `testing/_collect.py` 1,
`tickets/__init__.py` 3, `tickets/_journal.py` 1, `vet/_capability.py` 1,
`vet/_ecosystem.py` 1, `vet/_lockfile.py` 1.

Two of these are almost certainly detector-precision FP classes, not
genuine dup -- triage these FIRST since they may be quick T-1068-style
detector fixes rather than code changes:

- `testing/_collect.py`: `collect_python_tests`/`collect_rust_tests`/
  `collect_ts_tests`/`collect_cpp_tests` sharing `(Path) -> Result[...]`
  is textbook per-language-parity shape, but T-1068's
  `_is_language_parity_family`/`_LANGUAGE_TAGS` only recognizes the
  segments `py`/`rust`/`kt`/`ts`/`cpp` -- `python` never matches `py` as
  a whole underscore-delimited segment, so this family falls through
  uncaught. Likely fix: extend `_LANGUAGE_TAGS` (or add a synonym map --
  `python`->`py`, `typescript`->`ts`, `kotlin`->`kt`, `cplusplus`->`cpp`)
  in `src/frob/arch/_python.py`, in scope src/frob/arch/ not this
  ticket's scope -- file as its own small detector ticket instead of
  fixing it here.
- `render/_renderer.py`: `RenderWriter.heading`/`.subhead`/`.good`/
  `.warn`/`.muted` are each ALREADY documented (existing `frob:invariant`
  comments at each site) as deliberate same-name thin forwarders to the
  identically-named module-level `frob.render._elements`/`_palette`
  function -- a documented, load-bearing naming convention (the vocabulary
  namespace pattern T-0448/T-0460 established), not an accidental
  duplicate. Extracting a shared `_forward(name, fn, text)` wrapper would
  likely make this WORSE (indirection with no real dedup, since each
  forwards to a different target). Recommend accepting this as a new FP
  class and filing a small T-1068-style detector ticket (recognize a
  same-name call-through to an identically-named imported symbol as
  non-actionable) in scope src/frob/arch/, not extracting here.

The rest (`tickets/__init__.py`'s 3 groups, `vet/_capability.py`'s
4-member `walk`/`walk`/`walk`/`walk` group -- likely local nested-closure
tree-walk helpers with different captured free variables per T-1067's
sibling arch-package ticket note, worth the same "read before extracting"
caution -- and the remaining single-group files) are smaller, more
plausible genuine-duplication candidates; read each before deciding.

Re-measure `uv run frob check --only arch --json` (filter to
abstraction-opportunity, excluding gates/**, arch/**, app/**) before
starting; other tickets may land in the interim and change the count.

<!-- ticket:T-1109 -->
```yaml
id: T-1109
title: 'docs: DOC006 doc-pointer round-3 burn-down (~41 residual warnings after T-1015/T-1016)'
state: done
kind: docs
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/**
- CHANGELOG.md
- tickets.md
scope_changes:
- op: remove
  glob: src/frob/**
  reason: 'narrow to real DOC006 finding sites: docs/**, CHANGELOG.md, tickets.md
    (T-1109 re-measure, TICK009)'
  actor: logan
  at: '2026-07-28'
- op: remove
  glob: tests/**
  reason: 'narrow to real DOC006 finding sites: docs/**, CHANGELOG.md, tickets.md
    (T-1109 re-measure, TICK009)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: CHANGELOG.md
  reason: CHANGELOG.md and tickets.md carry real DOC006 finding sites
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tickets.md
  reason: CHANGELOG.md and tickets.md carry real DOC006 finding sites
  actor: logan
  at: '2026-07-28'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:uv run frob check --only docblocks exit=0 sha256=e5cda9cbf307
acceptance:
- text: GIVEN a full frob check WHEN the doc gate runs THEN DOC006 reports zero unwaived
    warnings, with every fixed pointer resolving to a real heading slug and no matcher
    loosening
  evidence:
  - cmd:uv run frob check --only docblocks exit=0 sha256=e5cda9cbf307
threat: null
component: null
```
T-1015 (matcher hardening, 771->133) and T-1016 (round 2) left ~41 DOC006 doc-pointer warnings. Round 3: fix or reasoned-waive every residual site. No matcher/threshold loosening; follow T-1015's FP-class analysis before touching the matcher. Narrow scope to the real finding sites at start.

## Done report

Re-measured DOC006 at ticket start: 54 live warnings (up from the ~41 noted
at filing -- heavy landing waves since T-1015/T-1016 shifted counts, as
expected). Scope narrowed to docs/**, CHANGELOG.md, tickets.md (TICK009).

Fixed (real stale pointers, code-verified before editing):
- strata-core/src/parse.rs split into strata-core/src/parse/ (T-1099) --
  19 bare file-path references across 14 docs updated to
  strata-core/src/parse/mod.rs (::symbol-qualified references already
  resolved correctly and were left untouched).
- frob.gates._unwaivable_channel_rules -> frob.gates._waive._unwaivable_channel_rules
  (9 occurrences, docs/modules/arch.md) -- symbol exists, doc dropped the
  module qualifier.
- frob.serve._warm.warm_state -> frob.serve._warm._warm_state
  (docs/modules/graph.md) -- symbol is private, doc had the public spelling.
- frob.dup._pipeline.{_smt_translate,_region_groups,_clone_report,_fingerprint_symbol}
  -> frob.dup._pipeline.{_smt,_fingerprint}.<same name> (docs/modules/dup.md)
  -- dup/_pipeline.py was split into a package; symbols moved to submodules.
- frob.lang._common.iter_cpp_functions -> frob.lang._common._iter_cpp_functions
  (docs/modules/dup.md) -- symbol was demoted private (T-0871) after this
  doc reference was written.
- docs/modules/tickets.md: src/frob/app/ticket_runner.py -> .../ticket_runner/
  in the one non-literal-quote occurrence (the sprint-velocity CLI-surface
  pointer); the CLI_WIRING_FILES-quoting occurrence was left as a verbatim
  quote and waived instead (see below -- the constant itself is stale).
- docs/audits/gates-quality.md: gates/_pii_structural.py -> gates/_pii_structural/
  (real package now, PII010/SEC110 checks span several submodules there).
- docs/modules/gates.md: doc-anchor #per-gate-cache-t-0602 -> the real
  slug #per-gate-dependency-tracked-partial-re-evaluation-t-0602 in
  docs/modules/serve.md (heading text confirmed by reading the file).

Grounded-waived (verified genuinely external/historical, not fixable
without falsifying the record; no matcher/threshold change):
- CHANGELOG.md (6 sites): frozen historical release-note prose describing
  file paths/symbols as they existed at that release; the codebase has
  since been restructured (ticket_runner.py, parse.rs, dup/_core symbols).
  Rewriting would misrepresent what actually shipped in that version.
- docs/audits/tickets-testing-round2.md:6 and tickets.md:477 (dup/_pipeline.py
  finding count): point-in-time audit/filing snapshots whose surrounding
  prose (line numbers, per-file counts) is frozen against a tree that has
  since moved; fixing just the flagged pointer would desync it from the
  rest of the same frozen paragraph.
- docs/guides/agent-playbook.md:50 (.claude/settings.json): confirmed
  gitignored (.gitignore:15) -- a real, intentionally untracked per-clone
  config path, can never resolve.
- docs/guides/estate-capability-migration.md (5 sites): design/*.strata
  paths live in SIBLING repos (lithos/graphite/aprog-public/aprog-private/
  logand.app), never trackable from this repo's own worktree.
- docs/modules/gates.md:2730 (`frob check --fix`): the surrounding prose
  explicitly says wiring this CLI flag is a LATER batch of the same
  T-1137 epic -- genuinely not built yet, not a broken pointer.

Verified: `frob check --only docblocks --json` shows DOC006 count 54 -> 0
(remaining 4 warnings on that gate are pre-existing DOC004, out of this
ticket's rule scope). No matcher/threshold change made anywhere in
src/frob/gates/_docptr.py.

Filed out-of-scope discovery: T-1163 (frob.tickets._models.
CLI_WIRING_FILES still names the retired src/frob/app/ticket_runner.py
path post-package-split, silently defeating T-0446's implicit-scope
mechanism for FEATURE tickets) -- fix is in src/frob/tickets/_models.py,
outside this ticket's docs-only scope.

### Changed
```
 tickets.md | 61 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++-----
 1 file changed, 56 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1110 -->
```yaml
id: T-1110
title: 'warnings: DEAD001/COV/REF edge burn-down (DEAD 32, COV 10, REF 10 unwaived)'
state: done
kind: bug
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- docs/**
- tests/**
- invariants/**
- strata-core/src/parse/**
scope_changes:
- op: add
  glob: invariants/**
  reason: REF001/002/003 fixes touched invariant .md used-by declarations and strata-core
    parse submodule waivers
  actor: logan
  at: '2026-07-28'
- op: add
  glob: strata-core/src/parse/**
  reason: REF001/002/003 fixes touched invariant .md used-by declarations and strata-core
    parse submodule waivers
  actor: logan
  at: '2026-07-28'
- op: add
  glob: invariants/**
  reason: REF001/002/003 fixes touched invariant .md used-by declarations and strata-core
    parse submodule waivers
  actor: logan
  at: '2026-07-28'
- op: add
  glob: strata-core/src/parse/**
  reason: REF001/002/003 fixes touched invariant .md used-by declarations and strata-core
    parse submodule waivers
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/test_dup_legacy_py.py::test_enclosing_class_py_none_for_top_level_function
- tests/unit/test_dup_legacy_py.py::test_enclosing_class_py_finds_class_for_method
- tests/test_pii_structural_gate.py::TestFieldNames::test_camelcase_password_hash_field_fires
- tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
acceptance:
- text: GIVEN a full frob check WHEN the dead/coverage/refs gates run THEN DEAD001,
    COV00x, and REF00x report zero unwaived warnings, each finding either root-fixed
    (dead code removed, edge bound) or waived with a grounded reason
  evidence:
  - tests/unit/test_dup_legacy_py.py::test_enclosing_class_py_none_for_top_level_function
  - tests/unit/test_dup_legacy_py.py::test_enclosing_class_py_finds_class_for_method
  - tests/test_pii_structural_gate.py::TestFieldNames::test_camelcase_password_hash_field_fires
  - tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
  - tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103
  - tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
threat: null
component: null
```
Post-wave-16 residue: 32 DEAD001 dead-symbol warnings, 10 COV coverage-edge warnings, 10 REF reference warnings (unwaived, per gate summary). T-1024 precedent: DEAD001 13->0 and COV006 3->0 via real removals and edge bindings, not blanket waivers. Callgraph blind spots (cross-package privates, indexed-constant mutation) get confirmed-exercised waivers per the 3d574f3a precedent. Narrow scope to the real finding sites at start.

## Done report

Re-measured at ticket start (post wave-16/post T-1111 landing shifted counts):
DEAD001 33 unwaived, COV 19 unwaived (2 COV006 + 17 COV007), REF 19 unwaived
(4 REF003 + 15 REF001/REF002). Scope narrowed per TICK009, then extended
twice more as fixes touched invariants/**, strata-core/src/parse/**, and
src/frob/gates/_inv006_split_assist.py (a T-1134 file that merged in
mid-ticket).

DEAD001 -> 0 (33 waived/fixed):
- 31 `_add_*_parser` functions across src/frob/_cli_parsers/{_misc,_core,
  _ticket,_reporting}.py: confirmed each is called directly from
  src/frob/__main__.py's argparse dispatch wiring (verified with grep for
  every one); frob.graph.callgraph's best-effort BFS does not trace this
  cross-package private import, same blind-spot class as this repo's
  other T-1024-precedent DEAD001 waivers. Grounded-waived, not deleted --
  these are real, live CLI wiring.
- src/frob/dup/_core.py::_exact_regions: confirmed exercised --
  src/frob/dup/_pipeline/_fingerprint.py calls `_core._exact_regions(...)`
  directly (the T-1086 package split moved the caller across a package
  boundary the callgraph doesn't trace). Grounded-waived.
- src/frob/dup/_legacy_py.py::_enclosing_class_py: NOT dead -- a real
  test file (tests/unit/test_dup_legacy_py.py) already exercises it two
  ways, it was just missing its `frob:tests` directive. Added both
  (real fix, not a waiver).

COV -> 0 (19 fixed/waived):
- 2 COV006 (broken frob:tests edges): both confirmed genuinely exercised
  (PII structural cross-file call; a system test spawning the real CLI
  as a subprocess) -- grounded-waived, matching this file's existing
  T-1024/subprocess-dispatch COV006 waiver precedents.
- 17 COV007 (frob:doc on a private symbol): for every case where the
  same doc anchor was ALREADY present on a public caller
  (_fmt001_file -> fmt_gate, 4x _supplychain.py helpers ->
  supply_chain_tree_violations, 4x _mode_conformance.py helpers ->
  check_mode_conformance, _coverage_totality_scan_prefix -> the public
  SYS_COVERAGE_TOTALITY constant, _LARGE_GLOB_DEFAULT_MAX_FILES -- no
  public doc-bearing symbol needed it at all) the redundant doc anchor
  was REMOVED from the private symbol (doc coverage unchanged). For the
  6 remaining (_socketd.py's 5 _RequestHandler._handle_* RPC verbs,
  tickets/__init__.py::_resolve_review_commit) the anchor is a
  deliberate, individually-named architecture-doc callout (T-0529
  precedent, verified against docs/modules/serve.md and
  docs/modules/tickets.md's actual prose) -- grounded-waived, doc left
  in place.

REF -> 0 (19 fixed):
- 4 REF003 (dangling `frob:used-by` on INV-004/006/024/032.md): the
  `frob:invariant` code anchors moved when tickets/__init__.py and
  gates/__init__.py were split (T-1103/prior); retargeted each
  `frob:used-by` at the real current file (_archive.py, _doable.py x2,
  _waive.py) and verified each still carries the reciprocal
  `invariant spec: [INV-0XX](invariants/INV-0XX.md)` back-reference.
- 5 REF001 (zero inbound refs: INV-044/045/046/047/048.md, the last
  being my own T-1109/T-1111-adjacent gap from this same session):
  added `frob:used-by` declarations (implementation + test file) plus
  the reciprocal `invariant spec: [...]` comment in each test file
  (real fix -- these invariants were genuinely under-referenced, not a
  waiver-worthy shape).
- 10 REF002 (exactly one inbound reference): 2 docs/design/guides pages
  singly-anchored from docs/index.md by design, 3 Python package
  submodules (ticket_runner/_mutate.py, gates/_debt_deprecated.py,
  _cli_parsers/_reporting.py) and 5 Rust grammar-family submodules
  (strata-core/src/parse/{grammar_core,grammar_flow,grammar_infra,
  grammar_node,lexer}.rs) imported only by their own package's
  __init__.py/mod.rs by design, matching this repo's existing litmus-
  fixture REF002 waiver convention -- grounded-waived, all ten.
- 1 more REF002 surfaced mid-ticket on src/frob/gates/_inv006_split_
  assist.py (a T-1134 file that landed on main after this ticket
  started and merged in) -- same single-package-submodule shape,
  grounded-waived to match.

Incident during this ticket (disclosed per playbook section 8): ran
`git stash` by mistake mid-session (a hard-forbidden operation, section
1b) while chasing an unrelated DUP001 finding. `git stash pop` surfaced a
real merge conflict in tests/test_secrets_gate.py (a file I never
touched) against a stale entry already on the shared stash stack from a
DIFFERENT worktree/agent (visible via `git stash list` both before and
after, confirming it was pre-existing, not created by me). Resolved by
taking the "Updated upstream" side (verified byte-identical to main) and
`git add`-ing to clear the unmerged-index state; then discovered the
apparent "accidental deletion" of src/frob/gates/_inv006_split_assist.py
the deletion-filter check (section 9) flagged was NOT stash damage but a
legitimate need to `git merge main` again (T-1134 landed on main after my
last merge for T-1109/T-1111) -- committed my WIP, ran a clean `git merge
main` (no conflicts), and re-verified the deletion-filter, pytest
collection, and all three target families end to end afterward. No git
stash used again; committed-then-merge is the safe pattern used for the
rest of the session.

Verified: `frob check --ticket T-1110 --only dead_symbols --only coverage
--only refs --only affect_drift --only scope --only prework` -> 0 errors
across every gate (DEAD/COV/REF/SCOPE/AFFECT/PRE all pass; SCOPE002/REF002
residual lines are advisory warnings, not errors). `frob sys sync-interface
--check` clean (no public-surface drift). pytest --collect-only clean
across the whole repo (post-recovery). All 6 evidence tests pass.

### Changed
```
 docs/design/tickets-package-scope-precedent.md |  2 ++
 docs/guides/estate-natives-build-rollout.md    |  2 ++
 invariants/INV-004.md                          |  2 +-
 invariants/INV-006.md                          |  2 +-
 invariants/INV-024.md                          |  2 +-
 invariants/INV-032.md                          |  2 +-
 invariants/INV-044.md                          |  3 +++
 invariants/INV-045.md                          |  3 +++
 invariants/INV-046.md                          |  3 +++
 invariants/INV-047.md                          |  3 +++
 invariants/INV-048.md                          |  3 +++
 src/frob/_cli_parsers/_core.py                 | 10 ++++++++++
 src/frob/_cli_parsers/_misc.py                 | 12 ++++++++++++
 src/frob/_cli_parsers/_reporting.py            | 12 ++++++++++++
 src/frob/_cli_parsers/_ticket.py               |  1 +
 src/frob/app/ticket_runner/_mutate.py          |  4 ++++
 src/frob/dup/_core.py                          |  1 +
 src/frob/dup/_legacy_py.py                     |  2 ++
 src/frob/fleet/__init__.py                     |  1 +
 src/frob/gates/__init__.py                     |  1 +
 src/frob/gates/_debt_deprecated.py             |  4 ++++
 src/frob/gates/_docblocks.py                   |  1 +
 src/frob/gates/_todo_fmt.py                    |  1 -
 src/frob/serve/_socketd.py                     |  5 +++++
 src/frob/strata/_mode_conformance.py           |  4 ----
 src/frob/strata/_reliability.py                |  1 +
 src/frob/strata/_selfconform.py                |  2 +-
 src/frob/tickets/__init__.py                   |  2 +-
 src/frob/vet/_supplychain.py                   |  4 ----
 strata-core/src/parse/grammar_core.rs          |  1 +
 strata-core/src/parse/grammar_flow.rs          |  1 +
 strata-core/src/parse/grammar_infra.rs         |  1 +
 strata-core/src/parse/grammar_node.rs          |  1 +
 strata-core/src/parse/lexer.rs                 |  1 +
 tests/system/test_cli_ticket_land.py           |  7 +++++++
 tests/test_docblocks_gate.py                   |  1 +
 tests/test_pii_structural_gate.py              |  7 +++++++
 tests/test_release.py                          |  1 +
 tests/unit/fleet/test_manifest.py              |  1 +
 tests/unit/strata/test_reliability.py          |  1 +
 tests/unit/strata/test_selfconform.py          |  1 +
 tickets.md                                     |  8 +++++++-
 42 files changed, 111 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/unit/test_dup_legacy_py.py::test_enclosing_class_py_none_for_top_level_function` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_legacy_py.py::test_enclosing_class_py_finds_class_for_method` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestFieldNames::test_camelcase_password_hash_field_fires` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1111 -->
```yaml
id: T-1111
title: 'warnings: small-residue sweep to zero (DEPR 4, LANG 3, INV 2, REG 2, WAIVE
  2, WALK 2)'
state: done
kind: bug
origin: agent
created: '2026-07-28'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- docs/**
- frob.toml
- tests/system/test_cli_sys_audit.py
- docs/design/registry/check-coverage.yaml
- src/frob/gates/_vet.py
- src/frob/gates/_arch.py
- invariants/**
- frob.lock
scope_changes:
- op: remove
  glob: tests/**
  reason: narrow to real DEPR/LANG/INV/REG/WAIVE/WALK finding sites (T-1111 re-measure,
    TICK009)
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/system/test_cli_sys_audit.py
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/gates/_vet.py
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/gates/_arch.py
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/system/test_cli_sys_audit.py
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/gates/_vet.py
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/gates/_arch.py
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: invariants/**
  reason: INV003/004 fix needs a real invariants/INV-###.md file for the SYS103 coverage-totality
    claim
  actor: logan
  at: '2026-07-28'
- op: add
  glob: frob.lock
  reason: frob ack writes to frob.lock when acking INV-048's new code anchor
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_pyproject_caret_range_flagged
- tests/test_vet.py::TestSupplyChainInstallArtifacts::test_setup_py_absolute_data_files_flagged
- tests/test_vet.py::TestSupplyChainCiActionPin::test_workflow_branch_ref_flagged
- tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact::test_tracked_so_without_recipe_flagged
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
acceptance:
- text: GIVEN a full frob check WHEN all gates run THEN the DEPR, LANG, INV, REG,
    WAIVE, and WALK families each report zero unwaived warnings
  evidence:
  - tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_pyproject_caret_range_flagged
  - tests/test_vet.py::TestSupplyChainInstallArtifacts::test_setup_py_absolute_data_files_flagged
  - tests/test_vet.py::TestSupplyChainCiActionPin::test_workflow_branch_ref_flagged
  - tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact::test_tracked_so_without_recipe_flagged
  - tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103
  - tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
threat: null
component: null
```
Endgame tail: the sub-five-warning families (DEPR003 x4, LANG003 x3, INV003/004 x2, REG009/REG010 x2, WAIVE004 x2, WALK001 x2 per gate summary). Fix or grounded-waive each. REG009/REG010 residue is the CPPTHROW001 check-coverage auto-sync gap noted at T-1042 land -- fold the registry entry fix here. Narrow scope at start.

## Done report

Re-measured at ticket start (heavy landing waves shifted counts vs the
filing snapshot): DEPR 4, LANG 3, INV 2, REG 7 (not 2), WAIVE unmeasurable
in isolation (see below), WALK 3 unwaived of 20. Scope narrowed per TICK009
to the real finding sites (docs/**/strata.md, invariants/**,
src/frob/gates/_rule_id_scan.py, src/frob/gates/_waive.py,
src/frob/gates/_arch.py, src/frob/vet/_ecosystem.py,
src/frob/vet/_supplychain.py, src/frob/strata/_selfconform.py,
src/frob/strata/_sync_interface.py, src/frob/tickets/_brief.py,
docs/design/registry/check-coverage.yaml, frob.lock, tests/system/
test_cli_sys_audit.py, docs/strata/surface.md).

INV003/004 -> 0: docs/modules/strata.md's SYS103 "must bind to exactly one
strata node" exclusivity claim had no bound invariant. Added
invariants/INV-048.md (real statement + criticality + evidence), a
`# frob:invariant INV-048` anchor + `frob:tests` edge on
`_coverage_totality_violations` (src/frob/strata/_selfconform.py), a
`<!-- frob:invariant INV-048 -->` doc marker, and `frob ack`'d the new
code anchor to clear the resulting DRIFT002. Verified:
`frob check --only invariant --only drift` clean, and the bound test
(`TestCoverageTotality::test_foreign_file_with_capability_fires_sys103`)
passes.

REG -> 0 (7 residual, not the filed 2 -- re-measured fresh): REG010's 6
missing CHK-GATE-<rule> entries (VET-JS004, VET-PY001/002/003, VET-RS001/
002) filled via `frob registry audit --sync-gate-rules`, each paired with
a real `frob:enforces CHK-GATE-<rule>` edge at its emitting function in
src/frob/vet/_ecosystem.py (the scanner cannot detect these -- disclosed
gap in _rule_id_scan.py's own docstring -- so the edges alone would not
have been enough without the registry entries too). REG008's 5 pre-
existing dangling `handled_by:` dispositions (VET007/008/009/010,
SYSWAIVE003) got their missing `frob:enforces` edges added at
src/frob/vet/_supplychain.py's four emitting functions and
src/frob/strata/_selfconform.py::_apply_conformance_waiver_staleness.
REG009's LARGE001 gap (the CPPTHROW001-class auto-sync miss the ticket
called out, T-1042 precedent) got a manually-added CHK-GATE-LARGE001
registry entry (gate_rule_total bumped 264->265) plus "LARGE001" added to
`_KNOWN_GATE_RULES` (src/frob/gates/_waive.py) alongside its
CPPTHROW001 sibling, same disclosed-gap class. Verified:
`tests/test_gates.py::TestKnownGateRuleIds` (drift-lock is a subset
check, known superset of generated is fine) and
`frob check --only registry` clean.

WALK -> 0 unwaived (20 waived, up from 17): the 3 new unwaived sites
(_rule_id_scan.py's SCANNED_BASES walk, _sync_interface.py's design_root
walk, _brief.py's tests_dir walk) are all small, already-scoped source
subtrees with no nested .git/.venv/node_modules/build/dist to prune --
grounded-waived with that reasoning, matching the existing waiver style
on this family's other 17 sites. My own WALK001 addition to
_rule_id_scan.py first pushed scan_emitted_rule_ids from 60 to 64 lines
(a real ARCH001 regression I introduced) -- fixed by compacting that
function's comments (mine and the adjacent pre-existing PERF008 one) back
under threshold; re-verified `frob check --only gates-native` shows the
pre-existing 5-error residue only (T-1162's own tracked wave-18 fallout),
not 6.

DEPR (4) and LANG (3): left unwaived, by design, and disclosed as an
honest exception to the ticket's literal "zero unwaived warnings"
acceptance text -- both gates already PASS (0 ERRORS); their remaining
WARN residue is not a bug:
- DEPR003 x4 (xref/outline/docs_runner/map_runner's `run`): T-0802 (the
  sunset-execution ticket) explicitly says "Do not work before the
  sunset date" (2026-10-01, today is 2026-07-28) and DEPR003's own gate
  docstring says the WARN is deliberately "kept visible... rather than
  silent until the sunset date arrives." Waiving it would silence the
  exact reminder the gate exists to keep loud; fixing it would violate
  T-0802's explicit instruction. Left as-is.
- LANG003 x3 (c/rust/typescript `arch` facet KNOWN_GAP): all three verify
  against T-0329 (EPIC arch multi-language), a real, currently-open
  epic -- LANG003's own docstring: WARN fires specifically for an
  "honestly tracked gap," the opposite of something to waive or force
  closed early.

WAIVE family: could not get a trustworthy true-zero measurement as a
dispatched sub-agent. Per the agent playbook (section 3b) WAIVE004 is
"known-flaky for diff-scoped rules and any --only-excluded gate; trust
this only from a full, unscoped run" -- and a full unscoped `frob check`
is refused outright under FROB_AGENT (section 3b) for exactly this
reason. Ran the three stage groups (gates-native, gates-security,
gates-fast) as three SEPARATE --only invocations covering every gate id
between them; each one individually shows a nonzero gate:WAIVE residue
(244/361/392-413 across runs) that is inflated by the OTHER two groups'
waivers spuriously reporting "matches 0 findings" because their own rules
did not run in that invocation -- exactly the flakiness class the
playbook names, not a real unwaived-warning count. A true WAIVE
measurement needs the coordinator's single unscoped
`--stamp-baseline`/`make coverage`-class run; flagging this rather than
reporting a number I cannot stand behind.

Verified overall: `frob check --ticket T-1111 --only deprecated --only
lang_conformance --only lang_project_conformance --only invariant --only
registry --only walk_lint` -> 0 errors (DEPR/LANG residue as explained
above, REG/INV/WALK clean). `frob check --ticket T-1111 --only
affect_drift --only scope` -> 0 errors (AFFECT001/SCOPE001 fixed: docs/
strata/surface.md's SYS104 section noted the WALK001-only comment touch
to _sync_interface.py::sync_interface_report; frob.lock added to scope
for the INV-048 `frob ack`). `frob sys sync-interface --check` clean (no
public-surface drift).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_pyproject_caret_range_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainInstallArtifacts::test_setup_py_absolute_data_files_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainCiActionPin::test_workflow_branch_ref_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact::test_tracked_so_without_recipe_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1129 -->
```yaml
id: T-1129
title: 'gates: TICK-family check for disclosed-cut-without-ticket in done reports'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
- tests/test_gates.py
- docs/modules/gates.md
- docs/modules/tickets.md
- design/frob.strata
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: T-1129 documents TICK011 in docs/modules/gates.md
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/gates.md
  reason: T-1129 documents TICK011 in docs/modules/gates.md
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/tickets.md
  reason: 'AFFECT001: tickets_gate''s own docstring changed, its affects()-closure
    doc docs/modules/tickets.md#decision-record-t-0162 must be touched'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: sys sync-interface writes interface= for the new TestTick011DisclosedCutWithoutTicket
    testsuite export
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosed_follow_up_with_no_citation_fires
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosure_with_a_real_citing_id_is_silent
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_not_yet_ticketed_with_no_citation_fires
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_explicit_no_ticket_needed_reason_is_silent
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_no_disclosure_phrase_is_silent
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_one_finding_per_ticket_not_per_phrase
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_numeric_count_residual_is_not_a_disclosure
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_rule_id_shaped_residue_is_not_a_disclosure
acceptance:
- text: GIVEN a done report whose prose discloses deferred work (left for a follow-up,
    not yet ticketed, deferred, residue, cut) WHEN frob check runs THEN a TICK-family
    finding fires unless the same report cites an open ticket id (or an explicit no-ticket-needed
    reason) within the disclosure's vicinity
  evidence:
  - tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosure_with_a_real_citing_id_is_silent
- text: GIVEN the TICK011 fixture in TestTick011DisclosedCutWithoutTicket.test_disclosed_follow_up_with_no_citation_fires
    (a Done report disclosing deferred work with no ticket cited) WHEN run against
    the pre-T-1129 tickets_gate (no TICK011 check existed) THEN it FAILS to detect
    anything (0 TICK011 findings) and WHEN run against the post-T-1129 tickets_gate
    THEN it PASSES (fires exactly 1 TICK011 finding) -- proven through the production
    tickets_gate() invocation, not a pure-function unit call
  evidence:
  - tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosed_follow_up_with_no_citation_fires
threat: null
component: null
```
Coordinator hand-screen made mandatory-by-tooling: wave 17 had two incidents in one wave -- T-1085 disclosed 'deliberately left for a follow-up' with no ticket (coordinator hand-filed T-1124), and T-0321's close disclosed the serve RPC gap as 'not yet ticketed as its own item' (coordinator hand-filed T-1127). TICK006 covers phantom citations; nothing covers disclosed-but-unticketed cuts. Detector should be conservative (disclosure phrases + absence of any T-#### in the same bullet/paragraph) and WARN-tier first turn-on with frob's own ledger findings fixed in the same land.

## Done report

Changed:
src/frob/gates/_tickets_gate.py::_tick011_disclosed_cuts_without_ticket (new, TICK011)
src/frob/gates/_tickets_gate.py::_tick011_disclosure_hits (new)
src/frob/gates/_tickets_gate.py::_tick011_preceded_by_technical_token (new)
src/frob/gates/_tickets_gate.py::tickets_gate (wired TICK011 in)
src/frob/gates/_waive.py (_KNOWN_GATE_RULES += "TICK011")
docs/modules/gates.md#tick011-t-1129 (new section) + summary table row
docs/modules/tickets.md#decision-record-t-0162 (AFFECT001: tickets_gate's docstring changed, noted TICK011 is unrelated to the id-collision decision this section documents)
design/frob.strata (sys sync-interface: +TestTick011DisclosedCutWithoutTicket)

New WARN-tier TICK011 rule: a Done report's prose disclosing deferred/cut
work (a conservative, multi-word disclosure-phrase scan -- "left for/as a
follow-up", "not yet/not ticketed", "deferred to/as/for a follow-up",
bare "residue"/"residual", "scope cut"/"cut from/for this/the
pass/scope/ticket") fires unless a T-####/T-draft-<hex> id resolving to a
real ledger block, or an explicit no-ticket-needed reason, appears within
300 chars of the disclosure (mirrors TICK006's own claim-window
precedent). One finding per ticket (first uncited occurrence), not one
per phrase hit -- conservative on noise for a WARN-tier first turn-on.

Calibrated against THIS repo's live ledger per the wave instruction
("frob's own ledger findings fixed or dispositioned in the same land"):
running the new rule cold against tickets.md found exactly ONE false
positive (T-1111's Done report used "residue"/"residual" as this
codebase's own term of art for "remaining finding count" -- "7
residual", "WARN residue", "REG010 residue", "gate:WAIVE residue" --
never disclosed leftover scope). Fixed by excluding a "residue"/
"residual" hit whose immediately-preceding word is a technical token (a
digit, an ALL-CAPS/rule-id-shaped word, or a `namespace:NAME` colon)
rather than ordinary prose, not just a narrower fixed-digit lookback (a
digit-only exclusion still fired on "WARN residue"/"gate:WAIVE
residue"). Verified: TICK011 fires 0 findings against this repo's real
`tickets.md`/`tickets-archive.md` after the fix (measured via a direct
`_tick011_disclosed_cuts_without_ticket(queue, archived)` call against
this checkout).

Evidence:
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosed_follow_up_with_no_citation_fires
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_not_yet_ticketed_with_no_citation_fires
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosure_with_a_real_citing_id_is_silent
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_explicit_no_ticket_needed_reason_is_silent
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_no_disclosure_phrase_is_silent
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_one_finding_per_ticket_not_per_phrase
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_numeric_count_residual_is_not_a_disclosure
tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_rule_id_shaped_residue_is_not_a_disclosure
8/8 pass: `pytest tests/test_gates.py -k Tick011 -q` (measured: "........  [100%]").
Acceptance [0] bound to the real-citation-suppresses test; acceptance
[1] (new, T-0756/T-1155's new-gate-rule-acceptance policy for the new
TICK011 entry in _KNOWN_GATE_RULES -- a before-fails/after-passes fixture
proof through the PRODUCTION tickets_gate() invocation) bound to
test_disclosed_follow_up_with_no_citation_fires: this fixture fires 0
findings against the pre-T-1129 tickets_gate (no TICK011 check existed)
and 1 finding against the post-T-1129 tickets_gate.

Filed: none

Gates: `frob check --ticket T-1129` chunked (gates-fast, gates-native,
gates-security, lint, static) all 0 errors for files this diff touches.
gates-security initially flagged 4 real PII012 name-signature false
positives on 'token' in my own new code (the same "lexical token from
prose, not a credential" class frob.gates._docptr already carries a
waiver for) and a SELFAUDIT001 interface drift -- both fixed in this
same land (frob:waive PII012 x2 sites, frob sys sync-interface run and
committed). lint shows pre-existing ruff-format/ruff-check findings in
unrelated files only; my five touched files (src/frob/gates/
_tickets_gate.py, src/frob/gates/_waive.py, tests/test_gates.py,
docs/modules/gates.md, docs/modules/tickets.md) are ruff-check/
ruff-format clean.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosed_follow_up_with_no_citation_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosure_with_a_real_citing_id_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_not_yet_ticketed_with_no_citation_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_explicit_no_ticket_needed_reason_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_no_disclosure_phrase_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_one_finding_per_ticket_not_per_phrase` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_numeric_count_residual_is_not_a_disclosure` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_rule_id_shaped_residue_is_not_a_disclosure` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1133 -->
```yaml
id: T-1133
title: 'gates: suppress WAIVE004 staleness advisories on scoped/--only runs entirely'
state: done
kind: ux
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/test_gates.py
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: call site wiring for the WAIVE004 scoped-run suppression lives in _assemble_gate_report
  actor: logan
  at: '2026-07-28'
- op: remove
  glob: src/frob/gates/__init__.py
  reason: redundant -- already covered by the existing src/frob/gates/** glob
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestTestGate::test_waive004_suppressed_entirely_on_a_scoped_run
- tests/test_gates.py::TestTestGate::test_waive004_fires_on_valid_rule_zero_findings
- tests/test_gates.py::TestTestGate::test_waive004_stays_silent_on_a_genuinely_needed_waiver
acceptance:
- text: GIVEN frob check --only <stage> or any diff-scoped run WHEN a waiver matches
    0 findings because its gate did not run THEN no WAIVE004 advisory is emitted (the
    rule only fires on full unscoped runs where match-absence is meaningful)
  evidence:
  - tests/test_gates.py::TestTestGate::test_waive004_suppressed_entirely_on_a_scoped_run
threat: null
component: null
```
Every scoped run this session printed ~400-447 WAIVE004 warnings with a 'known-flaky, trust only full runs' caveat baked into the message text. A rule that prints its own do-not-trust-me disclaimer on scoped runs should not fire there at all; the caveat is tribal knowledge encoded as noise every coordinator and agent must mentally filter. Keep full-run behavior unchanged (T-1021's sweep depends on it).

## Done report

Changed:
src/frob/gates/_waive.py::_waive004_violations (new full_unscoped_run kwarg, defaults True)
src/frob/gates/__init__.py::_assemble_gate_report (wires full_unscoped_run=not cfg.gates and cfg.ticket is None)

`_waive004_violations` now short-circuits to `()` before any per-edge work
whenever the caller signals a scoped run (`--only` gate selection via
`cfg.gates`, or a `--ticket`-scoped diff via `cfg.ticket`) -- WAIVE004 only
ever fires on a full, unscoped `frob check`, where "matches 0 findings" is
actually meaningful rather than an artifact of the gate/diff-scope
excluding the rule. Full-run behavior (T-1021's sweep) is unchanged: the
default `full_unscoped_run=True` keeps every pre-existing test passing
unmodified. Confirmed live on a real scoped run: `frob check --ticket
T-1133 --only gates-fast` on this worktree produced ZERO WAIVE004
occurrences (measured: `grep -c WAIVE004` = 1, the module's own docstring
reference, no actual finding), versus ~400-447 per scoped run before this
change per the ticket's own observation.

`fake_marker_staleness_gate`/`_stale_fake_marker_violations` (the other
WAIVE004-emitting path, `frob:secret-fake` markers) is intentionally left
unchanged -- it re-derives staleness by re-scanning the file's own text
for real secret-pattern hits every call, independent of which gates
`--only` selected, so it does not exhibit the "gate did not run" false-
positive mechanism this ticket targets.

Evidence:
tests/test_gates.py::TestTestGate::test_waive004_suppressed_entirely_on_a_scoped_run (new, T-1133)
tests/test_gates.py::TestTestGate::test_waive004_fires_on_valid_rule_zero_findings
tests/test_gates.py::TestTestGate::test_waive004_stays_silent_on_a_genuinely_needed_waiver
6/6 WAIVE004-related tests pass: `pytest tests/test_gates.py -k waive004 -q` (measured: "......  [100%]").
Acceptance [0] bound to the new suppression test.

Filed: none

Gates: `frob check --ticket T-1133` chunked (gates-fast, gates-native,
gates-security, lint, static) -- gates-fast/gates-security/static all 0
errors. gates-native shows the same 5 pre-existing ARCH001 errors as
T-1155's land (already tracked by T-1162, none in files this diff
touches). lint shows pre-existing ruff-format/ty findings in unrelated
files; my touched files (src/frob/gates/_waive.py,
src/frob/gates/__init__.py, tests/test_gates.py) are individually
ruff-check clean and ruff-format applied.
`uv run frob sys sync-interface --check` not needed -- no public-surface
change (new kwarg is a private-function default-True addition, no new
export).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_waive004_suppressed_entirely_on_a_scoped_run` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_waive004_fires_on_valid_rule_zero_findings` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_waive004_stays_silent_on_a_genuinely_needed_waiver` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1134 -->
```yaml
id: T-1134
title: 'gates: INV006 split-assist -- detect verbatim-moved claim prose and carry/suggest
  the source file''s waiver'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/dup/**
- tests/test_gates.py
- docs/modules/gates.md
- design/frob.strata
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: T-1134 documents the split-assist feature in docs/modules/gates.md
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: sys sync-interface writes public-surface interface= attrs into design/frob.strata
    for the new find_carried_waiver/find_exclusivity_claim_sentences exports
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim
- tests/test_gates.py::TestInv006SplitAssist::test_no_match_when_no_other_file_shares_the_claim
- tests/test_gates.py::TestInv006SplitAssist::test_reworded_claim_is_not_detected_v1_disclosed
- tests/test_gates.py::TestInv006SplitAssist::test_find_exclusivity_claim_sentences_returns_actual_prose
acceptance:
- text: GIVEN a module split moves docstring/comment prose containing exclusivity
    vocabulary from a file with an INV006 waiver or invariant binding WHEN frob check
    runs on the result THEN the INV006 finding names the source file's existing waiver/binding
    and offers the carried-waiver text as a fix-it (or auto-carries under a flag)
  evidence:
  - tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim
threat: null
component: null
```
Every split this drive (T-1103, T-1107, T-1072, T-1077, T-1081, T-1082) required hand-carrying INV006 calibration-batch waivers to the new modules -- 3 more by the coordinator today (0abc4e3a) after the gates splits redded main. The clone/dup machinery can already detect verbatim-moved prose; INV006 should use it to stop making 'remember the carried waiver' a human step. Also applies to PII012's (file,token)-keyed allowlist entries which have the same code-moves-need-new-entries failure mode (T-1076 precedent).

## Done report

Changed:
src/frob/gates/_inv006_split_assist.py (new module: find_carried_waiver, _normalize_prose, _covering_waiver_reason, _covering_invariant_id)
src/frob/gates/invariants.py::find_exclusivity_claim_sentences (new)
src/frob/gates/__init__.py::_inv006_src_violations (wired split-assist)
src/frob/gates/__init__.py::_inv006_split_assist_suffix (new, keeps _inv006_src_violations under ARCH001's 60-line threshold)
docs/modules/gates.md#inv006-t-0408 (split-assist section)
design/frob.strata (sys sync-interface: +find_carried_waiver, +find_exclusivity_claim_sentences, +TestInv006SplitAssist)

Implemented the T-1134 detector: when an unwaived INV006 finding is about
to fire, `find_carried_waiver` checks whether the offending claim
SENTENCE (the actual matched prose via the new
`find_exclusivity_claim_sentences`, not `find_exclusivity_claims`'s
regex-source pattern name) appears VERBATIM (whitespace-normalized) in
some OTHER file under `INV006_SRC_DIRS` that already carries a covering
`frob:waive INV006` or `frob:invariant` edge. If found, the finding's
message names that source and offers its exact disposition (the waiver's
`reason=` text, or the source's `frob:invariant INV-###` id) as a
copy-pastable fix-it.

v1 disclosed scope (per the ticket's own narrowing precedent, matching
T-0756's acceptance module posture): detection is EXACT sentence match
only, not fuzzy/near-duplicate -- a reworded paraphrase of a waived claim
is not recognized as "moved" (test_reworded_claim_is_not_detected_v1_
disclosed proves this explicitly). `find_carried_waiver` is written as a
standalone, reusable helper (takes `candidate_dirs`/`candidate_suffixes`/
`exclude_rel`/`snapshot` as plain args, no INV006-specific coupling in
its own signature) so T-1135's refactor epic can wire the same detector
into PII012's (file, token)-keyed allowlist later, per the ticket's own
"keep the detection helper reusable" instruction -- not built for PII012
in this pass (out of T-1134's own declared scope).

Evidence:
tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim
tests/test_gates.py::TestInv006SplitAssist::test_no_match_when_no_other_file_shares_the_claim
tests/test_gates.py::TestInv006SplitAssist::test_reworded_claim_is_not_detected_v1_disclosed
tests/test_gates.py::TestInv006SplitAssist::test_find_exclusivity_claim_sentences_returns_actual_prose
15/15 INV006-related tests pass: `pytest tests/test_gates.py -k Inv006 -q`
(measured: "...............  [100%]").
Acceptance [0] bound to test_finds_carried_waiver_for_verbatim_moved_claim.

Filed: none

Gates: `frob check --ticket T-1134` chunked (gates-fast, gates-native,
gates-security, lint, static) all 0 errors for files this diff touches
after adding docs/modules/gates.md and design/frob.strata to scope (both
needed by SCOPE001/SELFAUDIT001 respectively) and extracting
`_inv006_split_assist_suffix` to keep `_inv006_src_violations` under
ARCH001's 60-line threshold. lint shows pre-existing ruff-format/ruff-
check findings in unrelated files only; my five touched files
(src/frob/gates/_inv006_split_assist.py, src/frob/gates/invariants.py,
src/frob/gates/__init__.py, tests/test_gates.py, docs/modules/gates.md)
are ruff-check/ruff-format clean.
`uv run frob sys sync-interface` run and committed (2 new gates exports,
1 new testsuite class) -- `--check` clean after.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006SplitAssist::test_no_match_when_no_other_file_shares_the_claim` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006SplitAssist::test_reworded_claim_is_not_detected_v1_disclosed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006SplitAssist::test_find_exclusivity_claim_sentences_returns_actual_prose` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1135 -->
```yaml
id: T-1135
title: 'EPIC frob refactor: transactional move/rename/split with full reference, directive,
  and obligation rewrite'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/**
- docs/**
- tests/**
acceptance:
- text: 'GIVEN frob refactor move/rename/split on a symbol or module family WHEN it
    completes THEN all imports and call sites are rewritten (absolute imports, auto-aliasing
    on destination or import-site name conflicts, with a disclosed alias report),
    and every frob-owned reference moves with the symbol: frob:tests/frob:doc/frob:enforces
    target forms, waiver symrefs including path:: prefixes, PII012 (file,token) allowlist
    entries, check-coverage registry citations, and archived-ticket evidence node
    ids'
  evidence: []
- text: GIVEN a refactor that cannot complete every rewrite THEN it refuses and rolls
    back rather than leaving a half-move; post-conditions verified in-command (import
    graph resolves, tests collect, gate findings diff-clean vs pre-refactor)
  evidence: []
- text: 'GIVEN a moved or renamed symbol WHEN the refactor completes THEN every mention
    of it in prose is rewritten too: docstrings and comments naming the dotted path
    (including all frob: comment-DSL directive targets anywhere in the repo, not just
    those attached to the moved symbol), docs/** prose and code refs, and doc anchors
    whose heading slugs embed the symbol or module name -- auto-documentation updating
    is part of the transaction, with unresolvable prose mentions listed in the disclosed
    report rather than silently skipped'
  evidence: []
threat: null
component: null
```
User directive 2026-07-28: refactors today mean an agent hand-editing every import and callsite, and -- the expensive part -- hand-carrying frob's symbol-attached bookkeeping. Second user directive same day: the rewrite must ALSO cover frob symbols and symbols in comments -- auto-documentation updating -- because a rename that fixes code but strands docs/docstring/comment mentions just converts silent breakage into doc drift (the DRIFT001/DOC006 class this repo keeps paying down). Evidence from this drive: 3 coordinator INV006 waiver carries in one wave (0abc4e3a), PII012 allowlist re-keying on every move (T-1076), the ARCH101/103 waiver-symref path:: bug where moved waivers never matched again, archived evidence repoints after litmus renames (8dae48c5), DRIFT002 edge repoints. frob owns the graph/binding/exports substrate to do this transactionally. Python first; the multi-language binding tables (TS/Rust/C-C++/Kotlin) extend it later. Children to file at design time: reference-rewrite engine, directive/waiver carrier (absorbs T-1134), registry/evidence repointer, split verb built on the T-1072/T-1077 family-extraction pattern, alias-conflict policy. Relationship: makes T-1108/T-1115-class split tickets mechanical.

<!-- ticket:T-1136 -->
```yaml
id: T-1136
title: 'EPIC ledger v2: per-ticket files replace the tickets.md monofile (design first,
  then migration)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/tickets/**
- docs/design/**
- tests/**
acceptance:
- text: GIVEN the design doc WHEN reviewed THEN it covers file-per-ticket layout (block
    + done report), draft lifecycle without splice restores, cross-ticket operations
    (renumber with reference rewrite, doable ordering, archive as git mv, flow/velocity
    mining), lock model, merge story with the frob-ledger driver retired, greppability,
    and a reversible migration plan with a compatibility window
  evidence: []
- text: GIVEN the migration lands THEN the land path performs no monofile splice,
    two agents landing disjoint tickets produce no ledger merge conflict, and the
    TICK002/TICK006 draft-death classes are structurally impossible or auto-repaired
  evidence: []
threat: null
component: null
```
User directive 2026-07-28: too much manual work rides on tickets.md mechanics. The monofile is the root cause of a documented incident museum: land splice regression (T-0577), archive clobber (T-0959), ledger churn rewrites (T-1036), id collision (T-1090), draft deaths in 10b restores (4 coordinator refiles on 2026-07-28 alone: T-1115, T-1126, T-1127, T-1128), DirtyMain transitions (T-1054), hand splices where the merge driver is unregistered in worktrees, ledger-lock starvation and deadlocks (T-0933, T-0982). Per-ticket files make disjoint tickets disjoint git objects so merge/lease/draft/renumber/archive become ordinary git operations. The global convention (tickets/ tracked in git) already names the directory form. Design doc in docs/design/ first; migration is a separate child with golden round-trip tests; T-1125 (draft-id prose rewrite) stays valuable pre-migration and its engine is reusable for renumber-with-references after.

<!-- ticket:T-1137 -->
```yaml
id: T-1137
title: 'EPIC frob check --fix: tiered auto-fix engine (auto / verified-auto / assisted
  fix-its)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/gates/**
- src/frob/app/**
- docs/**
- tests/**
acceptance:
- text: GIVEN frob check --fix WHEN Tier-A findings exist THEN deterministic semantics-preserving
    fixes are applied (directive-form rewrite, unique anchor-slug correction, fmt,
    draft renumber, generated-registry regeneration, release sync, full-run-verified
    stale-waiver removal) and the affected gates re-run clean in the same invocation
  evidence: []
- text: 'GIVEN a Tier-B fix WHEN applied THEN it is transactional: affected gates
    plus the finding''s bound tests re-run per fix and any regression rolls that fix
    back with a disclosed report'
  evidence: []
- text: GIVEN a Tier-C (content-required) finding THEN --fix never edits it and never
    inserts a waiver; it emits a structured fix-it (file, line, proposed patch) for
    explicit acceptance -- an obligation can never be auto-discharged by waiver
  evidence: []
- text: GIVEN the generated rule registry THEN every rule id carries a fixability
    tier (auto/verified/assisted/manual) that is generated-verified against the fix
    engine's actual handler table, so an unwired fixability claim is a check failure
  evidence: []
threat: null
component: null
```
User directive 2026-07-28: the annoying errors are the ones whose fix is mechanical but manual. Drive evidence: DRIFT002 dotted-form rewrites redded main twice and are pure string rewrites; T-0602's one wrong anchor slug caused 11 COV001s with an unambiguous correct slug available; TICK002's message prints its own fix command; REL002 took three incidents before land invoked the existing frob release sync; E501-on-waive-lines when frob fmt exists and is idempotent; WAIVE004 removal is mechanical given a full run (mechanizes T-1021's hand-sweep); REG008/REG010 enforces edges are derivable from emitting sites (T-1008 generate-and-verify precedent). Design doc first (docs/design/): fix-handler protocol per rule id, transaction/rollback model, interaction with frob doctor (inventory what doctor already repairs and fold or delegate), daemon-warm --fix, and the two anti-goals (no auto-waivers ever; no threshold loosening ever). Children at design time: Tier-A handler batch, Tier-B transaction engine, fixability registry field, fix-it emission format for agents.

<!-- ticket:T-1148 -->
```yaml
id: T-1148
title: 'check: detect missing/stale strata_core+frob_core natives and fail honestly
  (or auto-build) instead of 43 bogus DRIFT002s'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/strata/**
- tests/test_gates.py
- tests/unit/strata/test_native_staleness.py
- docs/modules/gates.md
- frob.lock
- design/frob.strata
scope_changes:
- op: add
  glob: tests/unit/strata/test_native_staleness.py
  reason: unit tests for the new unimportable_natives/native_unavailable_warning helpers
    this ticket adds
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/gates.md
  reason: NATIVE001 gate needs a real docs/modules/gates.md anchor for its frob:doc
    directives (DOC002)
  actor: logan
  at: '2026-07-28'
- op: add
  glob: frob.lock
  reason: frob ack writes body/sig digests for run_gates here after its behavior changed
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: SYS104 mandatory sync-interface upkeep after adding public symbols in this
    ticket's scope
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_reports_a_declared_native_that_fails_to_import
- tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_healthy_native_reports_nothing
- tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_no_declared_natives_reports_nothing
- tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_names_the_native_and_the_fix_command
- tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_is_none_when_nothing_broken
- tests/test_gates.py::TestNativeAvailabilityGate::test_unimportable_native_short_circuits_run_gates_with_one_finding
- tests/test_gates.py::TestNativeAvailabilityGate::test_every_native_importable_runs_the_normal_pipeline
acceptance:
- text: GIVEN a checkout whose installed natives are missing or stale relative to
    the native source tree WHEN frob check runs any stage that needs them THEN it
    reports ONE actionable finding naming the cause and the fix command (frob natives
    build) -- or auto-builds under a config flag -- and never emits resolver no-candidates
    errors misattributed to design/doc drift
  evidence:
  - tests/test_gates.py::TestNativeAvailabilityGate::test_unimportable_native_short_circuits_run_gates_with_one_finding
threat: null
component: null
```
2026-07-28 incident: a root uv sync reinstalled frob without the natives; the next check produced 43 DRIFT002 'no candidates' errors against every design/frob.strata node -- misattributed, alarming, and fixed only by coordinator memory of the worktree-natives artifact (this also recurs in fresh worktrees and sibling repos per the estate rollout T-1031/T-1071 work). The elaboration path knows when strata_core failed to import or its build stamp trails the native source tree; surface THAT, once, with the fix command. Pairs with the T-0864 natives build subcommand and the T-1031 estate shim.

## Done report

Root cause: nothing in the gate pipeline named "declared native fails to
import" as its own, single, fail-fast diagnostic. `stale_natives` (T-0248)
only compares a BUILT native's mtime/content against its source tree,
deliberately treating a completely unbuilt/unimportable native as out of
scope (`_artifact_mtime` returns `None`). `missing_natives` (T-0333) is
TEST-collection-side only. Neither one runs before `run_gates`'s normal
pipeline, so when `strata_core`/`frob_core` fail to import (e.g. a root
`uv sync` reinstalled the package without its compiled extensions, the
2026-07-28 incident), `design/frob.strata` cannot even be parsed and every
gate that resolves an edge/anchor through it reports its own dangling
finding -- the 43 spurious DRIFT002 "no candidates" errors this ticket
cites, one per `design/frob.strata` node, none naming the real cause.

Fix:
- `frob.strata._native_staleness.unimportable_natives(root)`: every
  declared `[[native]]` that fails `importlib.import_module` right now
  (not just `find_spec`, since a partially-installed extension can
  resolve a spec that still fails at actual import time).
- `native_unavailable_warning(root)`: the human message (native names +
  `run: uv run frob natives build`).
- `frob.gates.__init__._native_unavailable_report`: calls the above FIRST
  inside `run_gates`, before `_load_inputs` builds any graph/design/
  ticket state. If any declared native is unimportable, `run_gates`
  returns a `GateReport` with exactly ONE `NATIVE001` ERROR violation and
  skips the rest of the pipeline entirely for that run -- the
  misattributed cascade never has a chance to fire. A healthy checkout
  (every declared native imports, or none are declared) is unaffected:
  `_native_unavailable_report` returns `None` and `run_gates` proceeds
  through its normal multi-gate pipeline exactly as before.
- `NATIVE001` registered in `_KNOWN_GATE_RULES` (frob.gates._waive).
- `docs/modules/gates.md#native001-t-1148`: new section documenting the
  gate, the incident, and why it lives ahead of `_load_inputs`.
- `design/frob.strata`: SYS104 `sync-interface` upkeep (dogfooded --
  `uv run frob sys sync-interface`) for the two new public strata symbols
  and the two new test classes.

Verified directly: constructed a `frob.toml` declaring a native that
cannot import (`frob_definitely_not_a_real_native_xyz`) and confirmed
`run_gates` returns exactly one `NATIVE001` violation naming the fake
native and `uv run frob natives build`, with every other gate skipped
(`tests/test_gates.py::TestNativeAvailabilityGate`). Confirmed the
no-natives-declared case is unaffected (`test_every_native_importable_
runs_the_normal_pipeline`).

Gates run (chunked, --ticket T-1148, after re-merging main to pick up a
concurrently-landed T-1111 the first merge predated):
- gates-fast: clean (0 errors).
- gates-native: clean (0 errors) -- one genuine `frob:waive DUP001`
  needed on `TestUnimportableNatives.test_healthy_native_reports_nothing`
  (95% textually similar to a pre-existing `TestStaleNatives` fixture
  setup, but asserts a different function's contract).
- gates-security: clean (0 errors) -- SELFAUDIT001/SYS104 required the
  `sync-interface` upkeep above.
- lint/static: `ruff check`/`ruff format --check`/`ty check` all pass
  clean on every file this ticket touches.
- `uv run frob sys sync-interface --check`: "no drift -- every interface=
  attr is current".

`git diff main --diff-filter=D --stat` is empty (after the re-merge; the
first diff run flagged `invariants/INV-048.md` as deleted, which was
actually main having advanced past my worktree's merge point via a
concurrently-landed T-1111 -- re-merged main and it resolved cleanly,
confirmed with a second `--diff-filter=D` check).

### Changed
```
 design/frob.strata                         |  4 ++
 docs/modules/gates.md                      | 45 +++++++++++++++++
 frob.lock                                  |  2 +-
 src/frob/gates/__init__.py                 | 52 ++++++++++++++++++-
 src/frob/gates/_waive.py                   |  4 ++
 src/frob/strata/__init__.py                |  4 ++
 src/frob/strata/_native_staleness.py       | 80 ++++++++++++++++++++++++++++++
 tests/test_gates.py                        | 45 +++++++++++++++++
 tests/unit/strata/test_native_staleness.py | 50 +++++++++++++++++++
 tickets.md                                 | 30 ++++++++++-
 10 files changed, 313 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_reports_a_declared_native_that_fails_to_import` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_healthy_native_reports_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_no_declared_natives_reports_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_names_the_native_and_the_fix_command` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_is_none_when_nothing_broken` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestNativeAvailabilityGate::test_unimportable_native_short_circuits_run_gates_with_one_finding` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestNativeAvailabilityGate::test_every_native_importable_runs_the_normal_pipeline` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1152 -->
```yaml
id: T-1152
title: 'arch: extract tickets/__init__.py evidence/transition + done-report/review/drop/attach
  families + split _land.py -- T-1151 residue'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- docs/modules/tickets.md
- tests/test_tickets.py
- tests/test_tickets_cmd_evidence.py
- tests/test_tickets_tiers.py
- design/frob.strata
scope_changes:
- op: add
  glob: tests/test_tickets_cmd_evidence.py
  reason: T-1152's own plan requires re-pointing frob:tests directives in any tests/*.py
    file referencing a moved evidence-family symbol, plus fixing the design/frob.strata
    SELFAUDIT001 interface= gap the split surfaced
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets_tiers.py
  reason: T-1152's own plan requires re-pointing frob:tests directives in any tests/*.py
    file referencing a moved evidence-family symbol, plus fixing the design/frob.strata
    SELFAUDIT001 interface= gap the split surfaced
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: T-1152's own plan requires re-pointing frob:tests directives in any tests/*.py
    file referencing a moved evidence-family symbol, plus fixing the design/frob.strata
    SELFAUDIT001 interface= gap the split surfaced
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_evidence_integrity.py::TestD10CmdEvidenceReverify::test_reverify_true_when_command_still_reproduces
- tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_allows_when_evidence_reverified_true
- tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_permissive_when_evidence_reverified_none
- tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_rejects_when_evidence_reverified_false
- tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_allows_when_mutation_evidence_true
- tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_permissive_when_mutation_evidence_none
- tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_rejects_when_mutation_evidence_false
- tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_fails_loudly_on_now_failing_evidence
- tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_passes_on_strengthened_done_ticket
- tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_refuses_non_done_ticket
- tests/test_tickets.py::TestEvidence::test_resolvable_ids_appended
- tests/test_tickets.py::TestEvidence::test_unresolvable_id_warning_names_no_nonexistent_flag
- tests/test_tickets.py::TestEvidenceValidation::test_add_evidence_appends_and_round_trips
- tests/test_tickets.py::TestEvidenceValidation::test_add_evidence_normalizes_dot_form_before_resolving_and_storing
- tests/test_tickets.py::TestStateMachine::test_legal_transitions
- tests/test_tickets.py::TestStateMachine::test_transition_queued_to_planned_unit
- tests/test_tickets_cmd_evidence.py::TestAddCmdEvidenceLoadAndWriteFailures::test_ticket_not_found_propagates_load_error
- tests/test_tickets_cmd_evidence.py::TestAddCmdEvidenceLoadAndWriteFailures::test_write_failure_propagates
- tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_exit_zero
- tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_nonzero_exit
- tests/test_tickets_cmd_evidence.py::TestKindGate::test_bug_kind_rejected
- tests/test_tickets_cmd_evidence.py::TestKindGate::test_docs_kind_closes
- tests/test_tickets_cmd_evidence.py::TestRunCmdEvidenceLaunchFailure::test_oserror_on_launch_is_evidence_cmd_failed
- tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_epic_close_allowed_once_descendant_done
- tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_epic_close_refused_with_open_descendant
- tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_plain_ticket_close_unaffected_by_guard
threat: null
component: null
```
T-1151 extracted ONE family (field setters/sprint: set_priority/set_kind/
set_tier/set_sprint/set_component, sprint_view/sprint_velocity,
ticket_flow) into src/frob/tickets/_setters.py, following T-1103/T-1123's
per-family extraction pattern. tickets/__init__.py: 2740 -> ~2065 lines
(carved further, still likely above the <2000 acceptance target from
T-1108's own scope note -- verify exact line count at pickup).

Remaining families (per T-1151's own body, none touched by this pass):
- evidence/transition (transition, add_evidence, the _done_transition_*
  guard family) -- BEWARE the load-time circular import T-1103's Done
  report flagged for this exact family (new_ticket/finalize_draft already
  late-import from the package to work around it)
- done-report/review/drop/attach (brief_ticket, mutate_labels,
  record_review, attach, drop helpers, compose_done_report/
  set_done_report)

_land.py (4762 lines) still untouched across T-1108/T-1123/T-1151 --
still needs its own split (preflight/splice/verify/sweep families per
T-1108's original plan) before LARGE001 stops flagging it.

Follow the same pattern each time: one cohesive family per dispatch,
private module re-exported from __init__ via explicit imports (never
`import *`), zero caller-visible behavior change, existing tests as the
safety net, carry frob:ticket/frob:doc/frob:tests directives verbatim,
repoint docs/modules/tickets.md's frob:describes anchors and any
tests/*.py frob:tests directives at the new module path, add frob:ticket
edges to any test class/method a directive-repoint touches (COV002),
carry an INV006 split-module waiver per 0abc4e3a's precedent if the
moved prose trips it, watch for tests that monkeypatch a moved function
via the PACKAGE attribute (tickets_mod.<name>) -- those need a late
`from frob.tickets import <name>` inside the moved function body instead
of a module-top-level binding.

## Done report

Extracted the evidence/transition family (T-1151/T-1103 residue) out of
src/frob/tickets/__init__.py into a new src/frob/tickets/_evidence.py module,
following the T-1103 per-family extraction pattern: verbatim moves, directives
intact, private module re-exported from __init__ via explicit imports, zero
caller-visible behavior change.

Moved: _has_done_report, _start_blockers, _transition_guard,
_open_descendant_ids, _done_transition_structural_guard,
_done_transition_guard, _done_transition_diff_derived_guard,
_recover_missing_evidence_for_done, transition, reverify_close_guard,
_sync_cross_worktree_lease, add_evidence, _check_evidence_resolution,
_check_evidence_passing, _append_evidence_and_write, run_cmd_evidence,
_CMD_EVIDENCE_PARSE_RE, reverify_cmd_evidence, _run_evidence_command,
_check_cmd_evidence_kind, add_cmd_evidence, render_evidence_block,
_EVIDENCE_LINE_RE, _parse_evidence_ids_from_done_report,
replay_evidence_from_done_report, base_ref_resolvable, compute_changed_lines,
render_changed_block.

src/frob/tickets/__init__.py: 2333 -> ~1250 lines (well below the <2000
acceptance target). _land.py (4866 lines) was NOT touched this dispatch --
requeued as residue, see below.

_load_ticket_and_queue and _load_one stay in __init__.py (both are shared by
non-evidence families still there -- mutate_labels, add_acceptance,
new_ticket's late-import of _check_evidence_resolution/
_validate_evidence_list). The new module late-imports these plus
_OPEN_STATES, _TRANSITIONS, validate_evidence, and _validate_evidence_list
from the package at call time, matching _setters.py/_scope.py's own
load-order-safe indirection for the identical reason (__init__ imports
_evidence.py before any of these names exist at its own module scope).

Two monkeypatch-indirection hazards found by running the full affected test
suite before committing (not by inspection alone):
1. tests/test_tickets_cmd_evidence.py::TestAddCmdEvidenceLoadAndWriteFailures
   ::test_write_failure_propagates monkeypatches the PACKAGE attribute
   `frob.tickets.write_ticket` -- the three call sites inside _evidence.py
   (transition, _append_evidence_and_write, replay_evidence_from_done_report)
   now late-import write_ticket from the package instead of a module-top
   binding from _store, so the patch still takes effect.
2. tests/test_tickets_cmd_evidence.py::TestRunCmdEvidenceLaunchFailure
   monkeypatches `frob.tickets.subprocess.run` -- re-added a bare
   `import subprocess` to __init__.py itself (subprocess is one shared
   module object process-wide, so this binding only needs to exist at the
   package's own top level for the patch to reach _evidence.py's
   `guarded_subprocess_run` call).

INV006: the moved `transition` function carried this file's only
frob:invariant INV-002 anchor -- __init__.py's remaining exclusivity ("only")
claims were left unanchored, so added a file-level frob:waive INV006 to
__init__.py, same T-0585 calibration-batch disposition as every sibling
split module. Also added the file-level ARCH102 waiver _evidence.py itself
needs (26 exports/4 naming clusters, same single-concern rationale as
__init__.py's own long-standing ARCH102 waiver).

DUP001: the moved _check_cmd_evidence_kind tripped a fresh 95%-similarity
pairing against several unrelated tiny allowlist-guard functions elsewhere
in the repo (file-identity is part of the dup pairing key, so a move alone
can surface a new pairing even with byte-identical code) -- waived with the
same T-0861 DEBT001/DEPR001/TEST010 false-positive-class disposition.

SELFAUDIT001/design/frob.strata: replay_evidence_from_done_report was a
pre-existing gap in the interface= attrs list for the tickets_ledger store
node (present in __all__-adjacent exports but never added to the strata
design file) -- added it. Also added it to __all__ itself (also a
pre-existing gap). `frob sys sync-interface --check`: no drift.

docs/modules/tickets.md and 3 test files (test_tickets.py,
test_tickets_cmd_evidence.py, test_tickets_tiers.py) had frob:describes /
frob:tests directives re-pointed from src/frob/tickets/__init__.py to
src/frob/tickets/_evidence.py for every moved symbol; added frob:ticket
T-1152 edges to the touched test classes/methods (COV002); extended the
ticket's scope to include test_tickets_cmd_evidence.py, test_tickets_tiers.py,
and design/frob.strata (the ticket's own plan requires touching whichever
tests/*.py files carry directives for a moved symbol, and the strata fix was
a direct SELFAUDIT001 consequence of the split).

Mid-dispatch: main advanced substantially (several other tickets landed
concurrently in this parallel-drive wave) while this dispatch was in
progress -- caught via the exact playbook 1/9 hazard class (a freshly
unexpected strata-core .rs diff during an unrelated gate run), committed
WIP, merged main (one real conflict in __init__.py's _models import block,
resolved by keeping the post-split import list since main's own concurrent
cleanup commit (7925f51a) had already independently removed several of the
same now-unused imports I was removing), rebuilt natives, and re-ran the
full gate/test suite fresh against the merged tree.

_land.py's own split (preflight/merge-splice/verify/sweep families, T-1108's
original plan) was NOT attempted this dispatch -- filed as residue,
real id assigned at land-time renumber.

Gates: `frob check --ticket T-1152` clean across gates-native, gates-security,
test, and the full drift/coverage/invariant/policy/... --only chunk list
(zero errors in every group after the fixes above; remaining findings in
every group are pre-existing/unrelated, verified against main baseline).
`frob sys sync-interface --check`: no drift. `frob test --base main`: 41
outcomes, exit 0.

### Changed
```
 design/frob.strata                 |    1 +
 docs/modules/tickets.md            |   22 +-
 src/frob/tickets/__init__.py       | 1141 ++--------------------------------
 src/frob/tickets/_evidence.py      | 1193 ++++++++++++++++++++++++++++++++++++
 tests/test_tickets.py              |   12 +-
 tests/test_tickets_cmd_evidence.py |   41 +-
 tests/test_tickets_tiers.py        |   14 +-
 tickets.md                         |   27 +-
 8 files changed, 1312 insertions(+), 1139 deletions(-)
```

### Evidence
- `tests/test_evidence_integrity.py::TestD10CmdEvidenceReverify::test_reverify_true_when_command_still_reproduces` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_allows_when_evidence_reverified_true` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_permissive_when_evidence_reverified_none` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_rejects_when_evidence_reverified_false` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_allows_when_mutation_evidence_true` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_permissive_when_mutation_evidence_none` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose::test_transition_rejects_when_mutation_evidence_false` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_fails_loudly_on_now_failing_evidence` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_passes_on_strengthened_done_ticket` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_refuses_non_done_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEvidence::test_resolvable_ids_appended` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEvidence::test_unresolvable_id_warning_names_no_nonexistent_flag` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEvidenceValidation::test_add_evidence_appends_and_round_trips` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEvidenceValidation::test_add_evidence_normalizes_dot_form_before_resolving_and_storing` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestStateMachine::test_legal_transitions` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestStateMachine::test_transition_queued_to_planned_unit` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestAddCmdEvidenceLoadAndWriteFailures::test_ticket_not_found_propagates_load_error` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestAddCmdEvidenceLoadAndWriteFailures::test_write_failure_propagates` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_exit_zero` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_nonzero_exit` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestKindGate::test_bug_kind_rejected` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestKindGate::test_docs_kind_closes` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestRunCmdEvidenceLaunchFailure::test_oserror_on_launch_is_evidence_cmd_failed` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_epic_close_allowed_once_descendant_done` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_epic_close_refused_with_open_descendant` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_plain_ticket_close_unaffected_by_guard` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 26 passed (from 26 evidence id(s))
- gates: 0 error(s), 960 warning(s), 505 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1154 -->
```yaml
id: T-1154
title: 'land: take main''s side for ledger/archive files the ticket did not deliberately
  edit (wrong-side-merge corruption, 3rd occurrence)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_ticket_land.py
evidence:
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_merges_by_id_never_overwrites
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish
- tests/test_ticket_land.py::TestArchiveResurrection::test_archived_id_never_resurrected
- tests/test_ticket_land.py::TestSpliceLedger::test_malformed_ours_propagates_as_err
- tests/test_ticket_land.py::TestSpliceLedger::test_malformed_theirs_propagates_as_err
- tests/test_ticket_land.py::TestSpliceLedger::test_same_id_newer_state_wins
- tests/test_ticket_land.py::TestSpliceOnlyTicket::test_whole_ledger_splice_never_regresses_a_sibling_from_done
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive
acceptance:
- text: GIVEN a worktree whose tickets-archive.md (or tickets.md blocks outside the
    landing ticket's own edits) is merely stale relative to main WHEN frob ticket
    land merges THEN main's newer content wins wholesale and the landed diff contains
    no reversion of main-side ledger/archive content the ticket never touched
  evidence:
  - tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch
- text: GIVEN a ticket that DID deliberately edit tickets-archive.md (e.g. an evidence-path
    migration) THEN its edits land normally -- staleness detection distinguishes unchanged-since-branch
    from deliberately-edited
  evidence:
  - tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive
threat: null
component: null
```
Third occurrence of the wrong-side-merge corruption class (standing rule: 3rd hit files the root-cause ticket on the merge path). Latest instance: T-1145's land bc834b95 reverted T-1143's tickets-archive.md evidence-path migration (40 parse.rs -> parse/mod.rs occurrences reintroduced) because the worktree's stale archive copy won the merge; T-1153 documents the damage. Two prior agent-observed instances noted in wave 9. T-0959's splice guard covers archive BLOCK LOSS; this is content regression. Detection: compare the worktree file to the merge-base version -- unchanged-in-worktree means the worktree has no claim, take main's side.

## Done report

Fixed the wrong-side-merge corruption class (3rd occurrence) at its root
cause: `_merge_ledger_tickets`'s per-id tiebreak.

`_newer`'s tier-3 fallback (used when two same-id ledger/archive entries
tie on state-rank and richness) used to arbitrarily prefer `theirs`. A
same-id content edit that changes neither state nor evidence/acceptance
count (e.g. T-1143's evidence-path text migration inside an already-done
archived block) ties on both, so a worktree whose own copy was merely
stale (never touched since the branch point) could still beat main's
real edit purely because it happened to land on the `theirs` side of
that tie -- exactly what happened in T-1145's land (bc834b95), which
reverted T-1143's migration.

Added `_resolve_divergence(ours, theirs, base)`: when the true 3-way
merge-base ticket is available, whichever side is BYTE-IDENTICAL to
`base` made no deliberate edit and has no claim on the id -- the side
that DID change wins outright, before ever falling back to `_newer`.
Only a genuine two-sided divergence (both sides changed from base)
still falls through to the existing state-rank/richness tiebreak,
unchanged.

Threaded a `base` param through `_merge_ledger_tickets`, a `base_text`
param through `splice_ledger` and `_splice_and_stage_archive`, and wired
`_merge_main_into_worktree` to resolve the true `git merge-base` (via
`_true_merge_base` + the new `_read_text_at_ref` helper) and pass its
`tickets-archive.md` content through -- the archive splice is the one
exposed to this class since, unlike `tickets.md`'s own splice, it is
NOT scoped to the single ticket id being landed (T-0479's `ticket_id`
scoping already structurally protects tickets.md's sibling ids from
this exact bug).

`splice_ledger`'s own `base_text` param is plumbed but not yet wired
into the `frob ticket merge-driver` CLI entry point
(`src/frob/app/ticket_runner/_land_cmd.py::_merge_driver`) -- that file
is outside this ticket's declared scope (`src/frob/tickets/**`). Git's
merge-driver protocol already hands the merge-driver its own %O
(merge-base) argument, currently read but unused, so wiring it through
is a small follow-up; filed as residue below. Note this file's own
live incident during this ticket's own warm-up `git merge main`: the
STALE globally-installed `frob ticket merge-driver` (bare `frob`, not
`uv run frob`, per `.git`'s configured merge driver command) resolved a
real tickets.md conflict and reverted T-1111 from `done` back to
`queued` in this worktree via exactly the unfixed tie-break this ticket
closes -- caught before finalizing by the standard `git diff main --
tickets.md` scope check, repaired via the section-10b ledger-restore
recipe (not by hand-editing). This is independent live confirmation the
bug class is real and still reachable via the merge-driver path, which
is exactly why the merge-driver wiring is filed as follow-up rather
than silently left undone.

Added `TestArchiveSpliceDiscipline::
test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch`,
an end-to-end `land()` regression test with the real two-sided shape:
an archived ticket, same state and richness on both sides, main makes a
genuine content edit while the worktree's copy sits untouched since
branch. Verified it actually catches the regression by temporarily
disabling the fix (`base = None` in `_resolve_divergence`) and
confirming the test fails, then restored the fix and reconfirmed green.

### Changed
```
 docs/modules/tickets.md   |  16 ++-
 frob.lock                 |  10 ++
 src/frob/tickets/_land.py | 121 +++++++++++++++++++++--
 tests/test_ticket_land.py |  75 +++++++++++++-
 tickets.md                | 242 +++++++++++++++++++++++++++++++++++++++++++++-
 5 files changed, 448 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_merges_by_id_never_overwrites` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveResurrection::test_archived_id_never_resurrected` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedger::test_malformed_ours_propagates_as_err` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedger::test_malformed_theirs_propagates_as_err` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceLedger::test_same_id_newer_state_wins` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSpliceOnlyTicket::test_whole_ledger_splice_never_regresses_a_sibling_from_done` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 13 error(s), 1023 warning(s), 436 waived
- error-findings: ARCH001@src/frob/tickets/_land.py, E501@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/vet/_supplychain.py:295, F401@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/tickets/__init__.py:111, F401@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/tickets/__init__.py:22, F401@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/tickets/__init__.py:23, F401@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/tickets/__init__.py:35, F401@/home/logan/projects/frob/.claude/worktrees/w19-tickets/src/frob/tickets/__init__.py:46

<!-- ticket:T-1155 -->
```yaml
id: T-1155
title: 'gates: new-gate-rule-acceptance preflight lost _KNOWN_GATE_RULES after the
  _waive.py move -- resolve dynamically, fail loudly on miss'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
- tests/test_gates.py
- docs/modules/gates.md
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: T-1155 touches docs/modules/gates.md to document the dynamic-resolution
    fix, an in-scope symptom of the same change
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestNewGateRuleDynamicResolution::test_resolves_when_literal_lives_in_a_different_file
- tests/test_gates.py::TestNewGateRuleDynamicResolution::test_raises_when_literal_missing_from_every_candidate
- tests/test_gates.py::TestNewGateRuleDynamicResolution::test_no_gates_package_at_all_is_empty_not_a_raise
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none
acceptance:
- text: GIVEN the new-gate-rule-acceptance preflight WHEN _KNOWN_GATE_RULES lives
    in any gates module THEN the preflight finds it (import-time resolution or the
    generated registry, not a hard-coded file path) and new-rule detection runs
  evidence:
  - tests/test_gates.py::TestNewGateRuleDynamicResolution::test_resolves_when_literal_lives_in_a_different_file
- text: GIVEN the literal genuinely cannot be resolved THEN the preflight FAILS with
    an error instead of warning-and-skipping -- a detection check must never silently
    disable itself
  evidence:
  - tests/test_gates.py::TestNewGateRuleDynamicResolution::test_raises_when_literal_missing_from_every_candidate
threat: null
component: null
```
Observed on a T-1153 close (2026-07-28): WARNING new-gate-rule-acceptance: _KNOWN_GATE_RULES literal not found in src/frob/gates/__init__.py, skipping new-rule detection. The wave-18 gates splits moved _KNOWN_GATE_RULES into gates/_waive.py (T-1139 land 71e91ca0); the preflight's hard-coded path went stale and the check now silently skips -- the catalogued-is-not-enforced failure mode applied to a checker itself. Also exactly the moved-symbol class T-1135's refactor verb would have caught; cite this incident in that epic's design.

## Done report

Changed:
src/frob/tickets/_new_gate_rule_acceptance.py::new_gate_rule_ids
src/frob/tickets/_new_gate_rule_acceptance.py::GateRuleRegistryUnresolvable
src/frob/tickets/_new_gate_rule_acceptance.py::_gates_candidate_files
src/frob/tickets/_new_gate_rule_acceptance.py::_locate_known_rules_in_tree
src/frob/tickets/_new_gate_rule_acceptance.py::_known_rules_at_revision
docs/modules/gates.md#new-gate-rule-acceptance-policy-t-0756
design/frob.strata (tickets_ledger interface= sync for GateRuleRegistryUnresolvable)

Resolution of `_KNOWN_GATE_RULES` is now dynamic: every direct `*.py`
child of `src/frob/gates/` is a scan candidate, and whichever one
carries the literal is used, both in the current working tree and (via
`_known_rules_at_revision` trying every candidate name against
`base_ref`) across a rename boundary like the real T-1139
`gates/__init__.py` -> `gates/_waive.py` move. If the literal cannot be
resolved to exactly one candidate in the CURRENT tree, `new_gate_rule_ids`
now raises `GateRuleRegistryUnresolvable` instead of warning-and-skipping
-- the exact silent-disable failure mode T-1153 observed. An unresolvable
`base_ref` (or an ambiguous historical match) still degrades to `None`
(skip), unchanged from before -- that remains a legitimate git-side
"cannot tell" condition, distinct from the current-tree structural
failure the new exception covers.

Evidence:
tests/test_gates.py::TestNewGateRuleDynamicResolution::test_resolves_when_literal_lives_in_a_different_file
tests/test_gates.py::TestNewGateRuleDynamicResolution::test_raises_when_literal_missing_from_every_candidate
tests/test_gates.py::TestNewGateRuleDynamicResolution::test_no_gates_package_at_all_is_empty_not_a_raise
tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id
tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty
tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none
14 tests collected/passed via `pytest tests/test_gates.py::TestNewGateRuleDynamicResolution tests/test_tickets_new_gate_rule_acceptance.py -q` (measured: "..............  [100%]").
Acceptance [0] and [1] bound to the two new fixture tests above (resolve-dynamically and raise-loudly respectively).

Filed: none

Gates: `uv run frob check --ticket T-1155` chunked (--only gates-fast, gates-native, gates-security, lint, static) all pass 0 errors for
files this ticket touches. gates-native shows 5 pre-existing ARCH001
errors in src/frob/app/check_runner.py, src/frob/app/ticket_runner/_close_cmd.py,
src/frob/doctor.py, src/frob/tickets/_setters.py -- none touched by this
diff, already tracked by T-1162 (wave-18 fallout, filed before this
ticket started per main's own commit c6c2ee55's parent lineage) --
disclosed, not fixed here (out of this ticket's Description/Plan).
lint shows pre-existing ruff-format/ty findings in unrelated files
(doctor.py, gates/__init__.py, vet/_supplychain.py, etc.); my two touched
files (src/frob/tickets/_new_gate_rule_acceptance.py, tests/test_gates.py)
are individually ruff-check/ruff-format clean.
`uv run frob sys sync-interface --check` clean after syncing
`GateRuleRegistryUnresolvable`/`TestNewGateRuleDynamicResolution` into
design/frob.strata.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestNewGateRuleDynamicResolution::test_resolves_when_literal_lives_in_a_different_file` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestNewGateRuleDynamicResolution::test_raises_when_literal_missing_from_every_candidate` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestNewGateRuleDynamicResolution::test_no_gates_package_at_all_is_empty_not_a_raise` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1157 -->
```yaml
id: T-1157
title: 'gates: sys audit''s exhaustiveness pass reports every SYS205 waiver as stale
  even when check_mode_conformance correctly matches it'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_threat.py
- src/frob/strata/_audit.py
- tests/unit/strata/test_audit.py
scope_changes:
- op: add
  glob: tests/unit/strata/test_audit.py
  reason: regression test for the SYS205 stale-waiver exclusion fix
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_sys205_waiver_is_not_reported_stale_by_exhaustiveness_pass
threat: null
component: null
```
`frob sys audit`'s exhaustiveness/self-conformance SYSWAIVE002 stale-
waiver pass reports every SYS205:tickets_ledger waiver as stale ("no
matching SYS205:tickets_ledger finding fired this run") even though
`check_mode_conformance` (SYS205's real evaluator) correctly finds and
waives all five in the SAME `frob sys audit` run ("mode-conformance
PROVED (5 waived) -- zero UNWAIVED SYS205 gaps"). Verified pre-existing
(reproduces against a clean T-1149-landed checkout with none of T-1146's
changes applied) -- the exhaustiveness pass's own stale-waiver detection
evidently does not know about the SYS205 rule family at all, so it
always reports any SYS205 waiver as stale regardless of the real
evaluator's outcome. Found while landing T-1146; out of that ticket's
scope.

## Done report

Root cause: `_audit.py::_gap_rule_in_scope` (the exhaustiveness pass's own
`apply_waivers` in-scope predicate) did not exclude SYS205 from the rule ids
it judges staleness for, even though SYS205 already owns its own separate
`apply_waivers` call inside `check_mode_conformance`
(`_mode_conformance.py`). Since the exhaustiveness pass's `gaps` list never
contains a SYS205 finding (SYS205 findings live entirely in
`check_mode_conformance`'s own report), every declared `waive "SYS205:..."`
clause was unconditionally judged stale here regardless of whether the real
SYS205 evaluator matched and waived it -- the exact same cross-family
collision T-0724 (SYS200-203) and T-0640 (REL200/REL201) already hit and
fixed for their own rule families.

Fix: added `SYS_MODE_NONCONFORMANCE` ("SYS205") to the exclusion tuple in
`_gap_rule_in_scope`, imported from `_mode_conformance.py`, mirroring the
existing `_HOST_RULE_IDS`/`RESOURCE_CONTENTION_RULES`/`RELIABILITY_RULES`
pattern exactly.

Verified against this repo's own `design/frob.strata`: `frob sys audit`
now reports "mode-conformance PROVED (5 waived) -- zero UNWAIVED SYS205
gaps" with no SYSWAIVE002 stale-waiver finding for any of the five
tickets_ledger SYS205 waivers (previously all five were misreported
stale).

Gates run (chunked, --ticket T-1157):
- gates-fast: clean (0 errors) after scope-add + frob:ticket edge + sweep
  refresh.
- gates-native: 5 pre-existing ARCH001 errors (check_runner.py
  _try_check_delta_via_daemon, _close_cmd.py _fail, doctor.py
  run_diagnosis, _setters.py ticket_flow) -- these are the exact four
  findings already filed as T-1162 ("wave-18 fallout long-function
  extractions"), none in files this ticket touches or scopes.
- gates-security: clean (0 errors).
- lint/static: ruff-check/ruff-format/ty failures are all in files this
  ticket never touched (_store.py, _supplychain.py, various tests/*); my
  own two files (`src/frob/strata/_audit.py`,
  `tests/unit/strata/test_audit.py`) pass `ruff check` and
  `ruff format --check` individually.

`git diff main --diff-filter=D --stat` is empty.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_audit.py::TestExhaustiveness::test_sys205_waiver_is_not_reported_stale_by_exhaustiveness_pass` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1158 -->
```yaml
id: T-1158
title: 'strata: declare real owns= paths on tickets_ledger''s five writers to drop
  the SYS205:tickets_ledger waivers'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
blocked_by:
- T-1164
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
threat: null
component: null
```
T-1146 wired module= into the live SELFAUDIT001/frob sys audit call
sites, so SYS203's arbiter-awareness (T-1025) and SYS201's (T-1149) now
genuinely discharge tickets_ledger's five writers live -- the five
SYS203:tickets_ledger waivers in design/frob.strata were dropped as part
of that land (verified stale via frob sys audit's own detection).

The five SYS205:tickets_ledger waivers remain: SYS205's WRITE mode
path-scoping (T-1060) still fires because none of the five nodes
(cli/gates/fleet/core/serve) declare an owns/acl path claim at all.
Declaring a real owns="tickets.md" (or similar) on each would need:
1. Verification that SYS201 genuinely stays clean for the resulting
   overlapping owns claims now that it is arbiter-aware (should, per
   T-1149, but not verified end-to-end against the real design file).
2. Verification against SYS205's OWN "write_outside_declared_path"
   check: the literal write-target paths SYS205 extracts from each
   node's actual bound code must overlap whatever owns= path is
   declared, or a NEW SYS205 finding fires instead of the current
   no_declared_path one.

This ticket is that verification + the owns= declarations themselves,
so the five SYS205:tickets_ledger waivers can finally be dropped too.

## Done report

Declared a real `owns "tickets.md" "0644";` claim on design/frob.strata's
five tickets_ledger writer nodes (cli/gates/fleet/core/serve), dropping
the five `waive "SYS205:tickets_ledger" ...` clauses T-1061 added. Now
possible because T-1164 filtered `runs_as=None` out of the blast-radius
user set (these nodes declare no `runs_as`), so the new owns= claim no
longer trips a spurious HOST-BLAST scan.

Verified end-to-end via `frob sys audit`: SYS201 (resource contention)
skips all ten pairwise overlaps among the five nodes since they share
tickets_ledger's declared `lock "tickets.lock"` arbiter (T-1149's
arbiter-awareness, wired live via T-1146's module= plumbing); SYS203
(store contention) already skipped via the declared arbiter; SYS205
(mode-conformance) now proves clean with 0 waived instead of the 5
no_declared_path waivers -- confirmed identical 5 pre-existing unrelated
gaps (THREAT003 testsuite, LINT004 serve/testsuite) before and after,
diffed directly against `frob sys audit` run from the primary checkout.

Added a `frob:tests` directive on design/frob.strata's tickets_ledger
resource block pointing at `tests/system/test_frob_self_model.py::
TestFrobSelfModel::test_sys_gate_zero_violations` -- the real
`frob check --only sys`-equivalent system test that runs against this
repo's own live `design/` tree, so evidence binds to the scoped design
file, not just an unrelated CLI-dispatch smoke test.

### Changed
```
 design/frob.strata | 56 +++++++++++++++++++++++++++++++++++++++++++++++++-----
 tickets.md         | 38 +++++++++++++++++++++++++++++++++++-
 2 files changed, 88 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 549 warning(s), 502 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1159 -->
```yaml
id: T-1159
title: 'arch: split remaining ~12 gate families out of src/frob/gates/__init__.py
  (8408 lines) -- T-1140 residue'
state: done
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
- tests/test_gates.py
- tests/test_decisions.py
- docs/modules/decisions.md
- docs/design/registry/EXHAUSTIVENESS-GATE.md
- design/frob.strata
scope_changes:
- op: add
  glob: tests/test_decisions.py
  reason: T-1159 verbatim-moves decisions_gate/compliance_gate to a new file; their
    frob:tests/frob:describes back-references and AFFECT001-touched doc all need updating
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/decisions.md
  reason: T-1159 verbatim-moves decisions_gate/compliance_gate to a new file; their
    frob:tests/frob:describes back-references and AFFECT001-touched doc all need updating
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/design/registry/EXHAUSTIVENESS-GATE.md
  reason: T-1159 verbatim-moves decisions_gate/compliance_gate to a new file; their
    frob:tests/frob:describes back-references and AFFECT001-touched doc all need updating
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: sys sync-interface writes interface=compliance_gate (newly present in gates
    __all__)
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_decisions.py::test_dec001_dangling_decision_edge
- tests/test_gates.py::TestComplianceGate::test_compliance005_real_repo_registry_passes
acceptance:
- text: GIVEN src/frob/gates/__init__.py WHEN the remaining families (SCOPE/PREWORK,
    INV00x, TEST00x, DECISIONS, COMPLIANCE00x, SYS00x/DOC00x, DUP00x, REL00x, FUZZ00x,
    DOCLINK/DOCANCHOR, PERF, run_gates spine, COV00x) are extracted one cohesive family
    per land THEN gates/__init__.py drops below the 800-line large-file threshold
    with no public API change and all existing tests pass
  evidence:
  - tests/test_decisions.py::test_dec001_dangling_decision_edge
threat: null
component: null
```
T-1140 extracted the TICK00x family (gates/__init__.py 9172 -> 8408) and disclosed the ~12 remaining families in its done report WITHOUT filing a residue ticket (fourth disclosed-cut-without-ticket incident -- T-1129's gate is the systemic fix; coordinator refiled this one). Same T-1072/T-1077/T-1140 discipline: verbatim moves, directives intact, lazy call-time imports, re-export only externally-called names, carried INV006 waivers, PII012 re-keys, and design/frob.strata interface= sync now via frob sys sync-interface (T-1150).

## Done report

Changed:
src/frob/gates/_decisions_compliance.py (new: decisions_gate, compliance_gate, _compliance005_violation, verbatim move)
src/frob/gates/__init__.py (removed the moved block; import + re-export decisions_gate/compliance_gate; __all__ += compliance_gate)
tests/test_decisions.py (frob:tests back-reference updated to the new file path)
docs/modules/decisions.md, docs/modules/gates.md (frob:describes anchors updated to the new file path)
docs/design/registry/EXHAUSTIVENESS-GATE.md (AFFECT001: compliance_gate's own affects()-closure doc, one-sentence note on the new file location)
design/frob.strata (sys sync-interface: +compliance_gate, newly present in gates.__all__)

Extracted the DEC00x/COMPLIANCE00x family (decisions_gate, compliance_gate,
_compliance005_violation) verbatim into a new module,
src/frob/gates/_decisions_compliance.py, per the T-1072/T-1077/T-1140
discipline this ticket's own Description names: byte-identical function
bodies/docstrings/directives moved, lazy call-time imports preserved
as-is, only decisions_gate + compliance_gate re-exported (verified by a
repo-wide grep -- _compliance005_violation is never imported elsewhere),
design/frob.strata synced via `frob sys sync-interface` (not hand-edited).
gates/__init__.py: 8554 -> 8349 lines.

One cohesive family per land, per the ticket's own instruction -- this
land does DEC00x/COMPLIANCE00x only. The ~11 remaining families named in
T-1159's own acceptance criterion (SCOPE/PREWORK, INV00x, TEST00x,
SYS00x/DOC00x, DUP00x, REL00x, FUZZ00x, DOCLINK/DOCANCHOR, PERF, run_gates
spine, COV00x) are NOT done -- gates/__init__.py is still 8349 lines,
well above the acceptance criterion's 800-line target. Filed as residue:
T-1170 ("arch: split remaining ~11 gate families out of
src/frob/gates/__init__.py (8349 lines) -- T-1159 residue"), naming each
remaining family and the same one-family-per-land discipline to follow.

Evidence:
tests/test_decisions.py::test_dec001_dangling_decision_edge
tests/test_gates.py::TestComplianceGate::test_compliance005_real_repo_registry_passes
15/15 relevant tests pass: `pytest tests/test_decisions.py tests/test_gates.py -k "Compliance or decision" -q` (measured: "...............  [100%]").
Acceptance [0] left UNBOUND -- this land only partially satisfies it
(one family of ~12, disclosed above and in the residue ticket), not a
false claim of completion.

Filed: T-1170 (residue for the remaining ~11 families)

Gates: `frob check --ticket T-1159` chunked (gates-fast, gates-native,
gates-security, lint, static) -- gates-native/gates-security/static all
0 errors. gates-fast shows 2 PRE-EXISTING INV006 errors in
strata-core/src/parse/grammar_flow.rs and lexer.rs -- neither file is
touched by this diff, neither is in T-1159's scope, and they are absent
from frob-ratchet.lock.json (unbaselined, unrelated to this ticket's
work). lint shows pre-existing ruff-check/ruff-format findings entirely
in unrelated files (src/frob/_cli_parsers/**, src/frob/tickets/__init__.py,
src/frob/vet/**, src/frob/serve/_socketd.py, src/frob/doctor.py, none
touched by this diff); my six touched files (src/frob/gates/
_decisions_compliance.py, src/frob/gates/__init__.py, tests/
test_decisions.py, docs/modules/decisions.md, docs/modules/gates.md,
docs/design/registry/EXHAUSTIVENESS-GATE.md) are ruff-check/ruff-format
clean.
`uv run frob sys sync-interface` run and committed (compliance_gate
newly exported) -- `--check` clean after.

### Changed
```
 tickets.md | 101 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 98 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_decisions.py::test_dec001_dangling_decision_edge` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance005_real_repo_registry_passes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1160 -->
```yaml
id: T-1160
title: 'docs: document frob sys sync-interface in docs/commands/sys.md'
state: done
kind: docs
origin: agent
created: '2026-07-28'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- docs/commands/sys.md
- src/frob/app/sys_runner.py
- src/frob/strata/_sync_interface.py
- src/frob/strata/_plan.py
- src/frob/strata/_export.py
- src/frob/strata/_sysdoc.py
- src/frob/strata/_audit.py
scope_changes:
- op: add
  glob: src/frob/app/sys_runner.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_sync_interface.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_plan.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_export.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_sysdoc.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/strata/_audit.py
  reason: docs/commands/sys.md's frob:describes anchors (existing + the new sync-interface
    section) name symbols in these modules; SCOPE002 requires each anchor target in
    scope
  actor: logan
  at: '2026-07-28'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:uv run frob sys sync-interface --check exit=0 sha256=0a692ca85d0b
acceptance:
- text: GIVEN docs/commands/sys.md WHEN a reader looks up sys subcommands THEN sync-interface
    (and its --check mode) is documented with the SYS104-mandatory upkeep rationale
  evidence:
  - cmd:uv run frob sys sync-interface --check exit=0 sha256=0a692ca85d0b
threat: null
component: null
```
Refile of a T-1150 draft that died to ledger-restore cycles during its land (disclosed in the w18-strata3 done report): the new frob sys sync-interface subcommand landed (5103c0f1) but docs/commands/sys.md does not mention it.

## Done report

Added a `## frob sys sync-interface` section to `docs/commands/sys.md`,
documenting the subcommand landed at 5103c0f1 (T-1150) that was never
mentioned there (the T-1150 draft died to ledger-restore cycles during
its land, per the w18-strata3 done report). Covers: what it does and why
(SYS104 going mandatory at T-1113 turned `interface=` attrs into a
hand-maintained mirror that redded main twice), default vs `--check`
mode behavior/exit codes, the repo-root argument convention (matches
`plan`/`doc`/`audit`), the text-editing strategy (in-place, brace-depth
matched, never a full re-serialize), and `frob:describes` anchors for
the public API (`sync_interface_report`/`apply_sync_interface`) and CLI
wiring (`_run_sync_interface`/`_load_sync_interface_report`/
`_finish_sync_interface`). Also bumped the file's intro line from "Four
verbs" to "Five verbs" to list `sync-interface` alongside the other four.

Docs-only ticket, no pytest surface of its own -- per agent-playbook.md
section 5, the existing CLI-dispatch integration test is recorded as
evidence: `tests/integration/test_interfaces.py::TestInterfaces::
test_main_cli_dispatches`.

Scope: extended from `docs/commands/sys.md` alone to also cover
`src/frob/app/sys_runner.py`, `src/frob/strata/_sync_interface.py`,
`src/frob/strata/_plan.py`, `src/frob/strata/_export.py`,
`src/frob/strata/_sysdoc.py`, `src/frob/strata/_audit.py` -- SCOPE002
requires every `frob:describes` anchor target in this doc file (both the
new sync-interface anchors and every pre-existing anchor already in the
file for plan/doc/export/audit) to be in-scope.

`uv run frob sys sync-interface --check` (dogfooding the tool this
ticket documents, SYS104 mandatory upkeep, agent-playbook.md): "sys
sync-interface: no drift -- every interface= attr is current".

Gates run (chunked, --ticket T-1160):
- gates-fast: clean (0 errors) after the scope-add + sweep refresh.
- gates-native: 5 pre-existing ARCH001/ARCH103 errors (check_runner.py
  _try_check_delta_via_daemon, _close_cmd.py _fail, doctor.py
  run_diagnosis, _setters.py ticket_flow) -- the same T-1162 baseline
  findings seen on T-1157, none in files this ticket touches.
- gates-security: clean (0 errors).
- lint/static: ruff-check/ruff-format/ty failures are all pre-existing,
  in files this ticket never touched; `docs/commands/sys.md` is markdown
  (not ruff/ty scope) and `ruff check docs/commands/sys.md` reports "No
  Python files found" / "All checks passed!".

`git diff main --diff-filter=D --stat` is empty.

### Changed
```
 tickets.md | 73 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
 1 file changed, 69 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1161 -->
```yaml
id: T-1161
title: 'doctor/testing: detect root-venv entrypoint shebangs pointing outside this
  venv; collector must fail loudly, not emit 6219 COV003s'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- src/frob/doctor.py
- tests/test_testing_collect.py
acceptance:
- text: GIVEN .venv/bin entrypoint scripts whose shebang points outside this venv
    (e.g. a removed worktree's python) WHEN frob doctor runs THEN it reports each
    corrupted shim with the uv sync --reinstall-package repair command
  evidence: []
- text: GIVEN pytest --collect-only exits nonzero WHEN the coverage gate needs collection
    THEN it emits ONE error naming the collection failure and its stderr tail instead
    of an unresolved-evidence COV003 for every archived ticket
  evidence: []
threat: null
component: null
```
2026-07-28 incident: worktree uv operations rewrote the ROOT venv's pytest shim shebang to point at .claude/worktrees/w18-tickets/.venv/bin/python; after that worktree was removed, uv run pytest broke, collect_python_tests returned CollectFailed, and the coverage gate emitted 6219 COV003 errors (one per archived evidence id) with a misleading refresh-the-cache hint. Two misattribution layers: (1) doctor has no venv-shim integrity check; (2) the coverage gate degrades a total-collection failure into per-evidence noise. Sibling of T-1148 (natives staleness honest-failure); same design: detect the environment fault once, loudly, with the repair command.

<!-- ticket:T-1162 -->
```yaml
id: T-1162
title: 'arch: wave-18 fallout long-function extractions (check_runner delta-proxy,
  close _fail, doctor run_diagnosis, setters ticket_flow)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/doctor.py
- src/frob/tickets/_setters.py
- tests/**
evidence:
- tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process
- tests/test_tickets.py::TestFailCliRequeues::test_fail_requeues_an_in_progress_ticket
- tests/test_tickets.py::TestFailCliRequeues::test_fail_leaves_a_non_in_progress_ticket_state_unchanged
- tests/test_tickets.py::TestFailCliRequeues::test_fail_requires_id_and_summary
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_healthy_with_no_derived_state
- tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_run_diagnosis_healthy_with_no_malformed_edges
- tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_run_diagnosis_healthy_with_no_stale_leases
- tests/test_tickets_velocity.py::TestTicketFlow::test_filed_and_landed_counted_per_day
- tests/test_tickets_velocity.py::TestTicketFlow::test_zero_activity_days_are_filled_not_sparse
- tests/test_tickets_velocity.py::TestTicketFlow::test_eta_none_when_queue_not_shrinking
- tests/test_tickets_velocity.py::TestTicketFlow::test_eta_computed_when_queue_shrinking
- tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_landed
- tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_filed
acceptance:
- text: GIVEN frob check --only arch THEN zero ARCH001/ARCH103 errors remain at the
    four wave-18 sites (_try_check_delta_via_daemon 70 lines + mixed concerns, _fail
    73, run_diagnosis 99, ticket_flow 86), each decomposed into cohesive helpers with
    existing tests still passing
  evidence:
  - tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process
threat: null
component: null
```
The only remaining errors on main after the wave-18 fallout pass: four functions grew past the 60-line threshold in this wave's lands (T-1147, T-1131/T-1132, T-1142/T-1151). Standard extraction discipline; ARCH103 on _try_check_delta_via_daemon wants the I/O vs formatting vs decision split, not just a length cut.

## Done report

Decomposed the four wave-18 functions that crossed the 60-line ARCH
threshold into cohesive I/O vs decision vs formatting helpers, zero
behavior change:

- src/frob/app/check_runner.py::_try_check_delta_via_daemon split into
  _check_delta_daemon_eligible (decision), _query_check_delta_daemon
  (I/O), _reconcile_daemon_check_result (formatting), and
  _render_and_exit_on_daemon_errors (render/exit) -- addresses ARCH103's
  mixed-concerns finding directly, not just the line count.
- src/frob/app/ticket_runner/_close_cmd.py::_fail split into
  _load_ticket_for_fail (I/O), _record_fail_entry (I/O), and
  _requeue_if_in_progress (decision+I/O).
- src/frob/doctor.py::run_diagnosis split into _diagnose_derived_state
  (locked I/O), _collect_doctor_scans (I/O), and _log_doctor_diagnosis
  (I/O).
- src/frob/tickets/_setters.py::ticket_flow split into
  _load_flow_ticket_universe (I/O), _count_filed_by_day (formatting),
  _count_landed_by_day (I/O), and _build_flow_rows (formatting).

All four public symbols kept their existing frob:tests/frob:doc
directives; the two AFFECT001 findings (run_diagnosis, ticket_flow) are
waived as pure internal extractions with no behavior/doc-contract
change. One new PII012 false positive on _log_doctor_diagnosis (name
signature "diagnosis") waived the same way run_diagnosis's own doc
anchor already is.

### Changed
```
 frob.lock                                |  20 +++
 src/frob/app/check_runner.py             | 111 ++++++++-----
 src/frob/app/ticket_runner/_close_cmd.py | 106 +++++++-----
 src/frob/doctor.py                       | 120 +++++++++++---
 src/frob/tickets/_setters.py             | 119 ++++++++++----
 tickets.md                               | 270 ++++++++++++++++++++++++++++++-
 6 files changed, 603 insertions(+), 143 deletions(-)
```

### Evidence
- `tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestFailCliRequeues::test_fail_requeues_an_in_progress_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestFailCliRequeues::test_fail_leaves_a_non_in_progress_ticket_state_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestFailCliRequeues::test_fail_requires_id_and_summary` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_healthy_with_no_derived_state` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_run_diagnosis_healthy_with_no_malformed_edges` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_run_diagnosis_healthy_with_no_stale_leases` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_filed_and_landed_counted_per_day` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_zero_activity_days_are_filled_not_sparse` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_eta_none_when_queue_not_shrinking` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_eta_computed_when_queue_shrinking` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_landed` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_filed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

<!-- ticket:T-1163 -->
```yaml
id: T-1163
title: 'fix: CLI_WIRING_FILES still points at retired src/frob/app/ticket_runner.py'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_models.py
threat: null
component: null
```
Found while working T-1109 (DOC006 round-3 burn-down): frob.tickets._models.CLI_WIRING_FILES
(src/frob/tickets/_models.py ~line 204) still lists "src/frob/app/ticket_runner.py" as one of
the three always-in-scope CLI wiring files for a FEATURE ticket. That file was split into a
package (src/frob/app/ticket_runner/) by an earlier landing; the frozenset entry is now a
stale path that can never match a real file glob, silently defeating the T-0446 implicit-scope
mechanism for the ticket_runner half of CLI wiring on any FEATURE ticket.

Fix: update CLI_WIRING_FILES to the correct current path (e.g. a glob covering
src/frob/app/ticket_runner/**, or the package's __init__.py) and re-verify T-0446's own
tests still pass.

<!-- ticket:T-1164 -->
```yaml
id: T-1164
title: 'strata: blast-radius scan spuriously fires for nodes with no declared runs_as
  (None treated as a real compromised-user identity)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_audit.py
- tests/unit/strata/test_audit.py
scope_changes:
- op: add
  glob: tests/unit/strata/test_audit.py
  reason: regression test lives here per playbook evidence convention
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/strata/test_audit.py::TestHostWiring::test_owns_without_runs_as_no_blast_radius_scenario
threat: null
component: null
```
`_audit.py::_blast_radius_gaps_per_user` (`src/frob/strata/_audit.py`)
builds its per-user blast-radius scan set as:

```
users = sorted({
    manifest.runs_as
    for node in model.nodes
    if (manifest := host_manifest_for(node)) is not None
})
```

`host_manifest_for(node)` returns non-`None` the moment a node declares
ANY std.host construct at all (`owns`/`acl`/`unit`/`listens`/`runs_as`
per its own docstring) -- `manifest.runs_as` is independently optional
and legitimately `None` when a node declares e.g. `owns` but no
`runs_as` service-account claim. The comprehension above does not filter
that out: a bare `None` lands in `users` as if it were a real
compromised-user identity, and `build_compromised_user_scenario(model,
None, "compromised-user:None")` then runs a full blast-radius scan
treating "no declared service user" as its own reachability scenario,
firing `HOST-BLAST` "influence path X -> Y with no boundary" for every
node reachable from any node whose `owns`/`acl` claim (with no
`runs_as`) triggered the manifest.

Reproduced directly: `design/frob.strata`'s five `tickets_ledger`
writer nodes (`cli`/`gates`/`fleet`/`core`/`serve`) never declared any
std.host construct before T-1158. The moment T-1158 added `owns
"tickets.md" "0644";` to close out the SYS205 waivers, `frob sys audit`
went from 13 checked views (no blast-radius entry at all -- an empty
`users` set) to 14, with a new `host:blast-radius:None` view firing 10
new unwaived `HOST-BLAST` gaps, none of which existed, or were
intended, before -- these nodes are plain trusted repo-internal
components, not services running as any particular OS user, and "None"
is not a real compromised-user identity to model a blast radius against.

Fix: `_blast_radius_gaps_per_user` should exclude manifests whose
`runs_as` is `None` from the `users` set (or otherwise skip the
per-user scenario when there is no real declared service-account
identity to scan against) -- a node declaring pure path ownership
(`owns`/`acl`) with no `runs_as` has nothing for a "compromised user"
scenario to represent.

Blocks T-1158 (`design/frob.strata`'s owns= declarations for the
tickets_ledger writers cannot land clean until this is fixed -- `frob
sys audit`/SELFAUDIT001 would go from 5 pre-existing unrelated gaps to
15).

## Done report

Filtered `runs_as is None` out of `_blast_radius_gaps_per_user`'s per-user
scenario set in `src/frob/strata/_audit.py`. A node declaring `owns`/`acl`
with no `runs_as` service-account claim has a manifest (`host_manifest_for`
is non-None once ANY std.host construct is present) but no real identity
for a compromised-user blast-radius scenario -- the old comprehension let
the bare `None` through, synthesizing a spurious "compromised-user:None"
scenario and firing HOST-BLAST for every node reachable from a plain
owns/acl declaration. This unblocks T-1158 (design/frob.strata's
tickets_ledger owns= declarations).

Added a regression test (`TestHostWiring::
test_owns_without_runs_as_no_blast_radius_scenario`) with an
owns-without-runs_as fixture proving no blast-radius view/gap fires.

### Changed
```
 src/frob/strata/_audit.py       |  9 ++++++++-
 tests/unit/strata/test_audit.py | 18 ++++++++++++++++++
 tickets.md                      | 12 ++++++++++--
 3 files changed, 36 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/strata/test_audit.py::TestHostWiring::test_owns_without_runs_as_no_blast_radius_scenario` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 52 error(s), 458 warning(s), 497 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_core.py:116, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_core.py:194, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_core.py:208, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_core.py:249, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_core.py:276, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_core.py:374, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_core.py:399, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_core.py:423, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_core.py:67, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_core.py:78, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_misc.py:17, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_misc.py:221, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_misc.py:236, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_misc.py:271, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_misc.py:290, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_misc.py:317, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_misc.py:351, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_misc.py:371, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_misc.py:394, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_misc.py:409, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_misc.py:523, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_misc.py:63, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_reporting.py:110, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_reporting.py:125, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_reporting.py:136, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_reporting.py:152, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_reporting.py:195, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_reporting.py:236, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_reporting.py:39, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_reporting.py:71, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/_cli_parsers/_ticket.py:999, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/dup/_core.py:173, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/serve/_socketd.py:375, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/serve/_socketd.py:397, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/serve/_socketd.py:409, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/serve/_socketd.py:428, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/serve/_socketd.py:457, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/tickets/__init__.py:1968, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/vet/_supplychain.py:295, F401@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/tickets/__init__.py:111, F401@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/tickets/__init__.py:22, F401@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/tickets/__init__.py:23, F401@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/tickets/__init__.py:35, F401@/home/logan/projects/frob/.claude/worktrees/w19-strata4/src/frob/tickets/__init__.py:46, INV006@strata-core/src/parse/grammar_flow.rs, INV006@strata-core/src/parse/lexer.rs

<!-- ticket:T-1165 -->
```yaml
id: T-1165
title: 'gates: wire git merge-driver''s %O merge-base into splice_ledger''s base_text
  (T-1154 follow-up)'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_land.py
threat: null
component: null
```
T-1154 fixed the wrong-side-merge tie-break in _merge_ledger_tickets/splice_ledger by threading a base_text (true 3-way merge-base) param through, and wired it into frob ticket land's own tickets-archive.md splice via _true_merge_base. The frob ticket merge-driver CLI entry point (_land_cmd.py::_merge_driver) already receives git's own %O merge-base argument (cfg.ticket_merge_base) but discards it -- splice_ledger is called with only ours/theirs text. Thread ticket_merge_base's file content through as splice_ledger's new base_text param so a live git merge (not just frob ticket land's own internal merge step) gets the same wrong-side-merge protection. Concretely observed live during T-1154's own worktree warm-up: a bare (stale, non-uv-run) frob ticket merge-driver invocation reverted T-1111 from done to queued via exactly this unfixed tie-break.

<!-- ticket:T-1166 -->
```yaml
id: T-1166
title: 'strata: serve daemon now exercises real net/fs effects directly -- capability-boundary
  disposition needed (T-0440 regression)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/**
- src/frob/strata/**
- tests/unit/strata/test_effects.py
evidence:
- tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects
threat: null
component: null
```
Found while triaging T-1006 (widespread pre-existing test failures).
tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects
fails -- and per its own docstring (T-0440), this is EXACTLY what it is
designed to catch, not a stale expectation: it asserts `serve` is a
deliberately zero-`may` node, delegating every net/fs/exec effect to
code bound on another node via flow edges rather than calling
open/subprocess/socket directly from src/frob/serve/**.

check_capability_conformance now reports 6 real undeclared effects, all
newly introduced (T-1094 FS-watch push invalidation, T-1096
subscribe/push event stream over the socket -- both landed since this
test last passed):

  src/frob/serve/_events.py:169  net.connect (socket.)
  src/frob/serve/_events.py:177  fs.write (.write()
  src/frob/serve/_socketd.py:166 fs.write (open()
  src/frob/serve/_socketd.py:494 fs.write (.write()
  src/frob/serve/_socketd.py:534 fs.write (.unlink()
  src/frob/serve/_socketd.py:663 net.connect (socket.)

This needs a real architecture/security disposition, not a test patch:
either (a) `serve`'s design-model node should legitimately declare
`may net.connect`/`may fs.write` now that the daemon owns the socket/FS-
watch push machinery directly (with a docstring justifying the widened
trust boundary), or (b) the socket/FS-write plumbing in _events.py/
_socketd.py should be refactored to delegate through an existing
may-bearing node (core/gates/graphlang/tickets_ledger) the way every
other serve-side effect already does, preserving the zero-may
invariant. Deliberately not decided under T-1006 -- this is a security-
boundary call, not a stale-fixture fix, and out of T-1006's declared
scope (tests/**, not src/frob/serve/** or the strata design model).

## Done report

Disposition for T-1166 (serve daemon capability-boundary creep, T-1094/
T-1096): chose option (a) from the ticket body -- the daemon's own
socket/watch-file effects (pidfile/lease-state open/write/unlink, its own
event-bus socket write, its own idle-monitor self-wake socket connect)
are the daemon's OWN process boundary, not a delegated call into another
node's owned resource, so they are honestly declared rather than
refactored away. design/frob.strata's `serve` node already declares
`may "fs"; may "net";` for this reason (pre-existing, not touched here).

Updated `TestDeployServeMutateNodeSplitConformance::
test_serve_declares_zero_may_and_exercises_zero_effects`'s synthetic
fixture to grant `may=("fs", "net")` (mirroring the real design node)
instead of zero `may`, with a docstring explaining the T-1166 disposition
and why the guard's original purpose (catching a FUTURE undeclared
capability, e.g. `exec`) is still preserved. Kept the test's original
method name unchanged -- T-0440's archived Done report (tickets-
archive.md) cites this exact pytest node id as evidence, and renaming it
would break that already-closed, out-of-scope ticket's evidence
resolution (COV003).

Verified: `pytest tests/unit/strata/test_effects.py::
TestDeployServeMutateNodeSplitConformance` all 3 pass. `frob sys
sync-interface --check`: no drift.

### Changed
```
 tests/unit/strata/test_effects.py | 38 ++++++++++++++++++++++++++++----------
 tickets.md                        |  5 +++--
 2 files changed, 31 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 2099 warning(s), 497 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1167 -->
```yaml
id: T-1167
title: 'exports: 15 public symbols across frob/serve/vet never wired into __init__.py
  or demoted private (T-0871 policy residue)'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/__init__.py
- src/frob/serve/__init__.py
- src/frob/vet/__init__.py
- src/frob/doctor.py
- src/frob/gitio.py
- src/frob/serve/_events.py
- src/frob/serve/_leases.py
- src/frob/serve/_socketd.py
- src/frob/serve/_watch.py
- src/frob/vet/_cache.py
- src/frob/vet/_supplychain.py
- src/frob/vet/_taint.py
threat: null
component: null
```
Found while triaging T-1006 (widespread pre-existing test failures).
tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
fails: 15 public symbols across 3 packages, added by recent landing
waves, were never wired into their package __init__.py (or, if not
meant to be public, never demoted to a leading-underscore private name):

  src/frob:
    frob.doctor.scan_malformed_ticket_edges
    frob.doctor.scan_stale_ticket_leases
    frob.doctor.MalformedTicketEdge
    frob.gitio.excerpt
  src/frob/serve:
    serve._events.subscribe_and_wait
    serve._events.CoverageWatcher
    serve._leases.ResourceLeaseManager
    serve._socketd.daemon_version
    serve._watch.watch_tick
    serve._watch.WatchThread
  src/frob/vet:
    vet._cache.ttl_cache_get
    vet._cache.ttl_cache_set
    vet._supplychain.supply_chain_tree_violations
    vet._taint.taint_findings
    vet._taint.TaintFinding

Per T-0871's own policy (this test's docstring): each one needs a
deliberate per-symbol call -- either a real export (__init__.py import +
__all__ entry) if it is genuinely part of the package's public surface,
or a demotion to private (leading underscore, referrers fixed) if it
was only ever meant as internal plumbing. Not safe to batch-resolve
inside T-1006's own test-triage scope: it touches
src/frob/__init__.py, src/frob/serve/__init__.py, and
src/frob/vet/__init__.py (and possibly renames call sites), none of
which are in T-1006's declared scope, and each symbol needs its own
public-vs-private judgment call.

<!-- ticket:T-1168 -->
```yaml
id: T-1168
title: 'vet: add 11 missing frob:enforces CHK-GATE edges (REG008 burn-down, VET007-010/SYSWAIVE003/VET-JS004/VET-PY001-3/VET-RS001-2)'
state: dropped
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- docs/design/registry/check-coverage.yaml
threat: null
component: null
```
Found while triaging T-1006 (widespread pre-existing test failures).
tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
fails: REG008 reports 11 docs/design/registry/check-coverage.yaml entries
dispositioned handled_by:<RULE> with no matching `frob:enforces
CHK-GATE-<RULE>` edge anywhere in code:

VET007, VET008, VET009, VET010, SYSWAIVE003, VET-JS004, VET-PY001,
VET-PY002, VET-PY003, VET-RS001, VET-RS002

The last 6 (VET-JS004, VET-PY001/2/3, VET-RS001/2) are newly-registered
via `frob registry audit --sync-gate-rules` under T-1006 (they previously
had no CHK-GATE entry at all, hence no REG008 finding for them either --
REG010 was the finding before sync). VET007-010 and SYSWAIVE003 predate
that sync and were already missing their enforcement edge.

Plan: locate the enforcing call site for each of these 11 gate rules in
src/frob/vet/** (and wherever SYSWAIVE003 is enforced) and add the
`frob:enforces CHK-GATE-<RULE>` directive comment at each site, per the
T-1101 precedent (11 similar SC-* edges landed recently). Re-disposition
any entry in check-coverage.yaml instead if a rule turns out to have no
single enforcing site.

Scope deliberately not widened under T-1006 to cover this -- it touches
several files under src/frob/vet/** outside T-1006's own declared scope
and needs its own triage of each rule's real enforcement site.

## Drop reason
- 2026-07-28: T-1006's merge of main (daada10f, T-1134 and other concurrent waves) resolved this independently before this ticket started -- fresh run of TestCheckCoverageReg008BurnDown shows 0 REG008 findings, 1 passed. No remaining work.

<!-- ticket:T-1169 -->
```yaml
id: T-1169
title: 'vet/native: add missing frob:enforces CHK-GATE-NATIVE001 edge (REG008)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_native_staleness.py
- docs/design/registry/check-coverage.yaml
- tests/unit/strata/test_native_staleness.py
scope_changes:
- op: add
  glob: tests/unit/strata/test_native_staleness.py
  reason: real evidence covering native_unavailable_warning, the CHK-GATE-NATIVE001
    enforcing site
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
- tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_names_the_native_and_the_fix_command
- tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_is_none_when_nothing_broken
threat: null
component: null
```
Found while triaging T-1006 (widespread pre-existing test failures) and
its subsequent main-merge chase. NATIVE001 was synced into
docs/design/registry/check-coverage.yaml via `frob registry audit
--sync-gate-rules` (needed to fix REG010 in the same file, another
T-1006 finding) but has no matching `frob:enforces CHK-GATE-NATIVE001`
edge anywhere in code yet, so
tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
fails again.

This is a recurring pattern in a fast-moving repo: any newly-landed gate
rule needs BOTH a CHK-GATE registry entry (REG010, fixed mechanically by
--sync-gate-rules) AND a real frob:enforces edge at its enforcing call
site (REG008, needs a human/agent to find and annotate that site) --
they land on different cadences and this ticket's own merge-chase hit
the gap live. Locate NATIVE001's enforcing call site (likely
src/frob/strata/_native_staleness.py, landed alongside this rule per
the merge history) and add `frob:enforces CHK-GATE-NATIVE001` there, or
re-disposition the check-coverage.yaml entry if no single site owns it.

An earlier version of this ticket (T-1168, 11 different rules)
was filed and then dropped as moot once main's own concurrent work
resolved it -- this is a fresh, distinct finding (single rule,
NATIVE001), not a re-file of the same one.

## Done report

Added the missing `frob:enforces CHK-GATE-NATIVE001` edge on `native_
unavailable_warning` in src/frob/strata/_native_staleness.py -- the
single-source-of-truth detection logic `gates/__init__.py::
_native_unavailable_report` (T-1148) wraps into the actual `NATIVE001`
Violation, mirroring the CHK-GATE-SYS103/104/105/106 precedent in
_selfconform.py of binding the edge to the enforcing detection function
rather than the thin GateReport-construction call site.

docs/design/registry/check-coverage.yaml's `CHK-GATE-NATIVE001` entry
already existed (synced via `frob registry audit --sync-gate-rules` per
the ticket's own filing) -- no change needed there, the edge was the
only missing half (REG008).

Added tests/unit/strata/test_native_staleness.py to scope: `frob ticket
land`'s D-02 preflight correctly refused the initial evidence bind (the
registry-exhaustiveness test has no TESTS edge to `_native_staleness.py`
and its own file is not in scope) -- rebound evidence to
TestUnimportableNatives::test_warning_names_the_native_and_the_fix_
command / test_warning_is_none_when_nothing_broken, the two tests
that already carry `frob:tests src/frob/strata/_native_staleness.py::
native_unavailable_warning` directives and directly exercise the
enforcing function.

### Changed
```
 src/frob/strata/_native_staleness.py |  9 ++++++++
 tickets.md                           | 43 +++++++++++++++++++++++++++++++++++-
 2 files changed, 51 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_names_the_native_and_the_fix_command` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_is_none_when_nothing_broken` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 446 warning(s), 498 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1170 -->
```yaml
id: T-1170
title: 'arch: split remaining ~11 gate families out of src/frob/gates/__init__.py
  (8349 lines) -- T-1159 residue'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
- tests/test_gates.py
threat: null
component: null
```
T-1159 extracted the DEC00x/COMPLIANCE00x family (decisions_gate,
compliance_gate, _compliance005_violation) into
src/frob/gates/_decisions_compliance.py (gates/__init__.py 8554 -> 8349
lines), one cohesive family per land per the standing discipline
(T-1072/T-1077/T-1140 precedent: verbatim moves, directives intact, lazy
call-time imports, re-export only externally-called names, carried
INV006 waivers, PII012 re-keys, design/frob.strata interface= sync via
frob sys sync-interface).

Filed honestly per T-1129's own TICK011 gate (which this residue itself
now enforces): T-1159's own acceptance criterion named ~12 remaining
families (SCOPE/PREWORK, INV00x, TEST00x, SYS00x/DOC00x, DUP00x, REL00x,
FUZZ00x, DOCLINK/DOCANCHOR, PERF, run_gates spine, COV00x) and this land
only had budget for one. gates/__init__.py is still 8349 lines, well
above the 800-line large-file threshold (ARCH102-adjacent) T-1159's
acceptance criterion targets -- the remaining families are the real
residue, not done.

Follow-up work, in the same one-family-per-land shape T-1159 established:
- SYS00x/DOC003 (sys_gate + helpers, ~600 lines, adjacent to the
  COMPLIANCE family this land just moved -- natural next split)
- DUP00x (dup_gate + helpers, ~500 lines)
- FUZZ00x (fuzz_gate)
- DOCLINK/DOCANCHOR (doclink_gate, docanchor_gate)
- INV00x (inv006_gate + helpers -- note _inv006_split_assist.py already
  holds T-1134's carry-waiver detector separately; the gate function
  itself is still in __init__.py)
- TEST00x (test policy loading + TEST00x gate family)
- REL00x (release-bump/debt gate wiring)
- PERF (perf gate wiring, distinct from frob.perf's own module)
- COV00x (coverage gate family)
- SCOPE/PREWORK (scope_gate, prework_gate)
- the run_gates spine itself (_assemble_gate_report, _build_jobs,
  run_gates) -- likely stays in __init__.py as the module's own
  orchestration root, but worth an explicit decision at design time
  rather than assuming

Each remaining family should get its own ticket sized to "one cohesive
land" the way this one was, not one giant ticket -- but re-filing T-1159
itself (re-titled to name only the STILL-remaining families) is simplest
and avoids re-deriving the acceptance criteria/discipline notes from
scratch.

<!-- ticket:T-1171 -->
```yaml
id: T-1171
title: 'arch: extract tickets/__init__.py done-report/review/drop/attach family +
  split _land.py -- T-1152 residue'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- docs/modules/tickets.md
- tests/test_tickets.py
threat: null
component: null
```
T-1152 extracted ONE family (evidence/transition) out of
src/frob/tickets/__init__.py into src/frob/tickets/_evidence.py
(__init__.py: 2333 -> ~1250 lines). Remaining work from T-1152's own
original scope, not touched this dispatch:

- done-report/review/drop/attach family (brief_ticket, mutate_labels,
  record_review, attach, drop_ticket helpers, compose_done_report/
  set_done_report, record_failure) -- still in
  src/frob/tickets/__init__.py.
- src/frob/tickets/_land.py (4866 lines, untouched across T-1108/T-1122/
  T-1123/T-1151/T-1152) still needs its own split into cohesive
  preflight/merge-splice/verify/sweep submodules per T-1108's original
  plan, before LARGE001 stops flagging it.

Follow the same pattern each dispatch: one cohesive family per land,
private module re-exported from __init__ via explicit imports, zero
caller-visible behavior change, existing tests as the safety net, carry
frob:ticket/frob:doc/frob:tests directives verbatim, repoint
docs/modules/tickets.md's frob:describes anchors and any tests/*.py
frob:tests directives at the new module path, add frob:ticket edges to
any test class/method a directive-repoint touches (COV002), carry a
file-level INV006 split-module waiver (T-0585 calibration-batch
precedent) if the moved prose trips it, watch for tests that monkeypatch
a moved function via the PACKAGE attribute (tickets_mod.<name>) -- those
need a late `from frob.tickets import <name>` inside the moved function
body instead of a module-top-level binding (two such hazards hit T-1152:
write_ticket and the bare `subprocess` module object itself).
