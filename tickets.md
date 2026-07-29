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
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- src/frob/app/config.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/check/_python.py
- src/frob/check/_ts.py
- src/frob/deploy/_conform.py
- src/frob/docs/__init__.py
- src/frob/doctor.py
- src/frob/dup/_pipeline/_probe.py
- src/frob/dup/_pipeline/_smt.py
- src/frob/fuzz/_signatures.py
- src/frob/gitio.py
- src/frob/gitlog/__init__.py
- src/frob/graph/_generated.py
- src/frob/graph/cache.py
- src/frob/graph/lock.py
- src/frob/lang/__init__.py
- src/frob/lang/_nodes.py
- src/frob/map/__init__.py
- src/frob/mutate/__init__.py
- src/frob/mutate/_journal.py
- src/frob/natives/_build.py
- src/frob/outline/__init__.py
- src/frob/process/parsers/cargo.py
- src/frob/process/parsers/valgrind.py
- src/frob/scaffold/_managed.py
- src/frob/scaffold/project.py
- src/frob/serve/_events.py
- src/frob/serve/_socketd.py
- src/frob/serve/_warm.py
- src/frob/serve/server.py
- src/frob/stats/_agentic.py
- src/frob/strata/_access.py
- src/frob/strata/_claims.py
- src/frob/strata/_code_binding.py
- src/frob/strata/_compliance.py
- src/frob/strata/_elaborate.py
- src/frob/strata/_facts.py
- src/frob/strata/_host.py
- src/frob/strata/_host_isolation.py
- src/frob/strata/_mode_conformance.py
- src/frob/strata/_native_staleness.py
- src/frob/strata/_obligation_proof.py
- src/frob/strata/_reliability.py
- src/frob/strata/_waive.py
- src/frob/testing/_collect.py
- src/frob/testing/_coverage_wait.py
- src/frob/testing/_runners.py
- src/frob/xref/__init__.py
- frob.lock
- src/frob/testing/_collect_cpp.py
scope_changes:
- op: remove
  glob: src/frob/
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/check_runner.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/config.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/check/_python.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/check/_ts.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/deploy/_conform.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/docs/__init__.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/doctor.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/dup/_pipeline/_probe.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/dup/_pipeline/_smt.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/fuzz/_signatures.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/gitio.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/gitlog/__init__.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/graph/_generated.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/graph/cache.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/graph/lock.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/lang/__init__.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/lang/_nodes.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/map/__init__.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/mutate/__init__.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/mutate/_journal.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/natives/_build.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/outline/__init__.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/process/parsers/cargo.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/process/parsers/valgrind.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/scaffold/_managed.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/scaffold/project.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/serve/_events.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/serve/_socketd.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/serve/_warm.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/serve/server.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/stats/_agentic.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_access.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_claims.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_code_binding.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_compliance.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_elaborate.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_facts.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_host.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_host_isolation.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_mode_conformance.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_obligation_proof.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_reliability.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_waive.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/testing/_collect.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/testing/_coverage_wait.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/testing/_runners.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/xref/__init__.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: frob.lock
  reason: frob ack writes doc-facet digests to frob.lock; needed to satisfy AFFECT001
    acks for T-1062's touched functions
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/testing/_collect_cpp.py
  reason: T-1074 landed a split of testing/_collect.py mid-wave; the two EXHAUST001
    sites this ticket fixed there moved to _collect_cpp.py, reapplied on merge
  actor: logan
  at: '2026-07-29'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_app_runner_map
- tests/integration/test_interfaces.py::TestInterfaces::test_deploy_generate_writes_and_checks
- tests/integration/test_interfaces.py::TestInterfaces::test_gitlog
- tests/integration/test_interfaces.py::TestInterfaces::test_map_project
- tests/integration/test_interfaces.py::TestInterfaces::test_outline_file
- tests/integration/test_interfaces.py::TestInterfaces::test_process_parse
- tests/integration/test_interfaces.py::TestInterfaces::test_serve_tools
- tests/integration/test_interfaces.py::TestInterfaces::test_testing_collect
- tests/integration/test_interfaces.py::TestInterfaces::test_xref_symbol
- tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean
- tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_reports_healthy_when_natives_present
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_drift_is_informational_and_does_not_affect_healthy
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_first_run_reports_no_drift_and_writes_manifest
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_malformed_manifest_is_treated_as_no_prior_run
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_rewritten_artifact_between_two_runs_reports_drift
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_unchanged_artifact_reports_no_drift
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_healthy_with_no_derived_state
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_unhealthy_when_derived_state_corrupt
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_accepts_valid_json_stamp
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_flags_corrupt_sqlite_cache
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_flags_malformed_json_stamp
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_reports_absent_as_healthy
- tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_run_diagnosis_healthy_with_no_malformed_edges
- tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_healthy_with_no_mutate_journals
- tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_ignores_journal_owned_by_live_pid
- tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_unhealthy_with_stale_mutate_journal
- tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_healthy_after_scaffold_apply
- tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_ignores_non_frob_directory
- tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_unhealthy_when_scaffold_blocks_missing
- tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_run_diagnosis_healthy_with_no_stale_leases
- tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
- tests/test_gates.py::TestOptInGates::test_fuzz_gate_off_by_default
- tests/test_gitio.py::TestWorkingDiff::test_covers_committed_staged_unstaged_and_untracked
- tests/test_graph.py::TestBuildIncremental::test_fingerprint_bump_rebuilds
- tests/test_graph.py::TestBuildIncremental::test_fingerprint_packages_derived_from_lang_registry
- tests/test_graph.py::TestGeneratedSource::test_is_generated_source_detects_do_not_edit_and_at_markers
- tests/test_graph.py::TestGeneratedSource::test_is_generated_source_detects_repo_convention_header
- tests/test_graph.py::TestGeneratedSource::test_is_generated_source_false_for_hand_authored_file
- tests/test_graph.py::TestGeneratedSource::test_is_generated_source_false_for_missing_file
- tests/test_graph.py::test_graph_build_lock_drift_integration
- tests/test_lang.py::test_lang_pipeline_integration
- tests/test_mutate.py::test_run_mutations_all_killed_by_strong_test
- tests/test_serve_events.py::TestSubscribeAndWait::test_receives_coverage_fresh_on_stamp_write
- tests/test_serve_events.py::TestSubscribeAndWait::test_receives_graph_changed_after_edit
- tests/test_serve_events.py::TestSubscribeAndWait::test_times_out_with_no_matching_event
- tests/test_stats.py::test_collect_combines_both
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_malformed_date_returns_none
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_no_marker_returns_none
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_parses_embedded_expiry_date
- tests/unit/test_check.py::test_check_run_check_arch_integration
- tests/unit/test_docs_module.py::test_docs_module_integration
- tests/unit/test_dup.py::test_dup_end_to_end_scan_then_render
- tests/unit/test_lang_primitives.py::test_resolve_local_import_maps_to_repo_relative
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

## Done report

EXHAUST001/002 residual burn-down continuation (post T-1056). Narrowed
scope to the real finding sites (50 files, excluding gates/**, tickets/**
owned by sibling wave agents, and perf/**, vet/**+gates/_opaque.py owned
by sibling tickets T-1053/T-1051). Disposed all 117 in-scope unwaived
findings down to 0: real errors-as-values fixes (widened a narrow except
to the function's own documented degrade contract, or added a missing
except around a previously-unguarded fallible call) where the escape was
genuine; `frob:raises <Type>` for functions that intentionally propagate
a named exception by design (_tokenize_line -> _TokenizeError,
write_lock -> BaseException, node_access_declarations /
_parse_host_attrs / host_manifest_for -> ValueError, _require_mcp ->
McpUnavailable); reasoned `frob:waive` directives everywhere else, each
citing the specific resolver-unresolvable call (deferred imports,
cross-module Result-returning wrappers, stdlib calls the may-raise
resolver cannot statically bound) -- no rule loosening anywhere.

Also fixed along the way: gitio._parse_unified_diff's dict-index KeyError
gap (switched to setdefault), valgrind._xml_error_diagnostic's int(ln)
ValueError gap, xref.xref's unguarded read_bytes() OSError gap, and
lang._nodes.resolve_local_import's two unguarded Path.exists() calls --
all genuine unhandled-exception gaps the EXHAUST resolver caught, not
resolver artifacts.

Verification: `frob check --ticket T-1062 --only exhaustive_handling` is
clean in scope; `frob test --base main` touched-set run passed (53
outcomes, 0 failures); `frob sys sync-interface --check` shows no drift;
full `frob check --ticket T-1062` is clean across every gate (fixed a
self-inflicted INV006 trip from "hardening only" wording in my own
waiver comments, and AFFECT001 waivers + `frob ack` on the handful of
doc-bound touched functions since this is pure internal error-handling
hardening with no behavior/interface change).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_app_runner_map` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_deploy_generate_writes_and_checks` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_gitlog` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_map_project` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_outline_file` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_process_parse` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_serve_tools` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_testing_collect` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_xref_symbol` (pytest node id, verified passing when recorded)
- `tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_reports_healthy_when_natives_present` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_drift_is_informational_and_does_not_affect_healthy` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_first_run_reports_no_drift_and_writes_manifest` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_malformed_manifest_is_treated_as_no_prior_run` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_rewritten_artifact_between_two_runs_reports_drift` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_unchanged_artifact_reports_no_drift` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_healthy_with_no_derived_state` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_unhealthy_when_derived_state_corrupt` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_accepts_valid_json_stamp` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_flags_corrupt_sqlite_cache` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_flags_malformed_json_stamp` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_reports_absent_as_healthy` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_run_diagnosis_healthy_with_no_malformed_edges` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_healthy_with_no_mutate_journals` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_ignores_journal_owned_by_live_pid` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_unhealthy_with_stale_mutate_journal` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_healthy_after_scaffold_apply` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_ignores_non_frob_directory` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_unhealthy_when_scaffold_blocks_missing` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_run_diagnosis_healthy_with_no_stale_leases` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_fuzz_gate_off_by_default` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestWorkingDiff::test_covers_committed_staged_unstaged_and_untracked` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestBuildIncremental::test_fingerprint_bump_rebuilds` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestBuildIncremental::test_fingerprint_packages_derived_from_lang_registry` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestGeneratedSource::test_is_generated_source_detects_do_not_edit_and_at_markers` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestGeneratedSource::test_is_generated_source_detects_repo_convention_header` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestGeneratedSource::test_is_generated_source_false_for_hand_authored_file` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestGeneratedSource::test_is_generated_source_false_for_missing_file` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::test_graph_build_lock_drift_integration` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::test_lang_pipeline_integration` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_run_mutations_all_killed_by_strong_test` (pytest node id, verified passing when recorded)
- `tests/test_serve_events.py::TestSubscribeAndWait::test_receives_coverage_fresh_on_stamp_write` (pytest node id, verified passing when recorded)
- `tests/test_serve_events.py::TestSubscribeAndWait::test_receives_graph_changed_after_edit` (pytest node id, verified passing when recorded)
- `tests/test_serve_events.py::TestSubscribeAndWait::test_times_out_with_no_matching_event` (pytest node id, verified passing when recorded)
- `tests/test_stats.py::test_collect_combines_both` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_malformed_date_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_no_marker_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_parses_embedded_expiry_date` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::test_check_run_check_arch_integration` (pytest node id, verified passing when recorded)
- `tests/unit/test_docs_module.py::test_docs_module_integration` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup.py::test_dup_end_to_end_scan_then_render` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_primitives.py::test_resolve_local_import_maps_to_repo_relative` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 53 passed (from 53 evidence id(s))
- gates: 0 error(s), 1545 warning(s), 583 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1074 -->
```yaml
id: T-1074
title: 'arch: triage 800-2000 line file residue (T-0395 remainder tier 3)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
- tests/test_testing.py
- docs/modules/testing.md
- tests/test_gates.py
scope_changes:
- op: add
  glob: tests/test_testing.py
  reason: 'T-1074''s real split of frob.testing._collect into _collect_rust/_collect_ts/_collect_cpp
    moved shutil.which() call sites out of _collect.py; tests/test_testing.py monkeypatches
    collect_mod.shutil by module attribute and must be repointed at the new modules
    to keep passing, per the T-1171 split precedent (repoint tests that monkeypatch
    a moved function via the package attribute).

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/testing.md
  reason: 'T-1074''s real split of frob.testing._collect into _collect_rust/_collect_ts/_collect_cpp
    moved shutil.which() call sites out of _collect.py; tests/test_testing.py monkeypatches
    collect_mod.shutil by module attribute and must be repointed at the new modules
    to keep passing, per the T-1171 split precedent (repoint tests that monkeypatch
    a moved function via the package attribute).

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_gates.py
  reason: 'tests/test_gates.py::TestCppSourceAccurateCollection._mock_ctest monkeypatches
    collect_mod.shutil by module attribute; must be repointed at frob.testing._collect_cpp
    after the T-1074 split moved the cpp collector out of _collect.py.

    '
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_testing.py::TestCollectRustTests::test_collect_rust_tests_parses_and_caches
- tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_parses_and_caches
- tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_parses_and_caches
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

## Done report

Re-measured LARGE001 (frob check --only archgate, 2026-07-29) over this
ticket's remaining scope, excluding src/frob/gates/** (owned by T-1174)
and src/frob/tickets/** (owned by T-1171) per dispatch instructions. Both
excluded trees' offenders (gates/__init__.py 8128, tickets/_land.py 4866,
tickets/_models.py 1868, tickets/_leases.py 1344, tickets/_evidence.py
1205, tickets/__init__.py 1264) are left untouched, for the sibling
tickets.

REAL SPLIT LANDED this pass: src/frob/testing/_collect.py (1326 lines at
filing, the largest genuinely-mine offender) split by language into four
files:
- src/frob/testing/_collect.py (506 lines) -- python collector only
- src/frob/testing/_collect_rust.py (299 lines, new)
- src/frob/testing/_collect_ts.py (231 lines, new)
- src/frob/testing/_collect_cpp.py (398 lines, new)
- src/frob/testing/_collect_shared.py (65 lines, new) -- cache/walk
  primitives (_prune_dirnames/_load_cache/_store_cache) every language
  collector shares

The four languages (python/rust/ts/cpp) were fully independent code paths
inside the old file -- verified zero cross-language call edges before
splitting (each language's private helpers are only called from that
language's own section and its own public collect_<lang>_tests). Every
name the old module defined is re-imported into _collect.py (module-level,
`frob:ticket T-1074` marked, not exported via __all__) so every existing
`from frob.testing._collect import <name>` call site (frob.testing.__init__,
frob.gates.__init__, and ~40 call sites across tests/test_testing.py,
tests/test_testing_collect.py, tests/test_gates.py, src/frob/strata/
_native_staleness.py) keeps resolving unchanged -- zero caller-visible
behavior change, matching the T-1171 tickets/_evidence.py split precedent
this repo already established.

Repointed:
- docs/modules/testing.md's `frob:describes ...::collect_rust_tests`
  anchor to the new module path (the only tracked describes-anchor that
  moved; collect_ts_tests/collect_cpp_tests were never tracked).
- ~28 `frob:tests src/frob/testing/_collect.py::collect_{rust,ts}_tests`
  directive comments in tests/test_testing.py + tests/test_gates.py to
  the new module paths (DRIFT002-driven, all confirmed via `frob check
  --ticket T-1074`).
- 4 test helpers that monkeypatch a collector's module-level `shutil`/
  `run_argv`/`_cargo_env` by attribute (tests/test_testing.py's rust/ts/
  cpp classes, tests/test_gates.py's TestCppSourceAccurateCollection.
  _mock_ctest) to import the language-specific module instead of
  `frob.testing._collect` -- these are attribute-patch call sites, not
  new tests; each caught immediately as a hard `AttributeError` when run,
  not a silent pass.
- INV006 waivers carried verbatim (T-0585 calibration-batch precedent)
  onto all three new files.
- One genuinely pre-existing DUP001 (src/frob/testing/_collect_ts.py::
  _find_ts_test_files, 95% similar to frob.strata._selfconform.
  _repo_files_excluding_skip_dirs) surfaced only because the file became
  touched -- waived with a reason noting it predates this split and a
  real extraction is separate, deliberate scope.

DISPOSITIONS for the rest of the T-1074 file list still in-scope
(src/frob/, excluding gates/** and tickets/**), re-measured this pass --
recorded here per the ticket's own "accepted-with-reason is a valid
outcome" framing rather than forced into unsafe splits under one dispatch
budget:

- src/frob/graph/callgraph.py (830), src/frob/graph/__init__.py (869),
  src/frob/graph/dsl.py (1033): one graph-resolution pipeline each
  (build_call_graph -> _resolve_edges -> _resolve_edges_python is a single
  mutually-recursive call chain; graph/__init__.py's ingest/prune/finalize
  helpers all share one sqlite connection threaded through every private
  function). Splitting would separate tightly-coupled steps of one
  algorithm across files, adding import indirection with no cohesion gain.
  Accepted with reason; not split this pass.
- src/frob/perf/_rules.py (845), src/frob/perf/_effect_summaries.py (823):
  each is one token-level static-analysis algorithm (PERF001-004 detection,
  effect-graph inference) whose private helpers are single-purpose steps
  of that one algorithm, not independent concerns. Accepted with reason.
- src/frob/arch/_rust.py (838): one tree-sitter node-walker family for a
  single language's AST shape, mirroring the existing arch/_python.py
  split-by-language convention already in place. Accepted with reason.
- src/frob/dup/_pipeline/_fingerprint.py (805, just over threshold): one
  fingerprinting pipeline (r3/r4/r5 rungs feeding one bucket/pair/verify
  chain). Accepted with reason.
- src/frob/testing/_collect.py's own remaining 506 lines: already under
  threshold after this pass's split -- no further action needed.
- src/frob/vet/_capability.py (5938) and src/frob/vet/_capability_registry.py
  (2923): both over 2000 lines, outside this ticket's "under 2000 lines"
  framing at filing -- left for a dedicated follow-up ticket (not filed
  this pass; budget did not allow investigating a safe split boundary for
  either).

NOT investigated this pass (budget): src/frob/app/check_runner.py (1597),
src/frob/app/config.py (1158), src/frob/app/sys_runner.py (1028),
src/frob/arch/_patterns.py (1486), src/frob/arch/_python.py (1539),
src/frob/check/__init__.py (958), src/frob/check/_python.py (970),
src/frob/doctor.py (907), src/frob/strata/*.py (multiple offenders
841-2485 lines), src/frob/_cli_parsers/_ticket.py (1025),
src/frob/app/ticket_runner/_verify.py (949). These remain LARGE001 WARN
findings (advisory, not gating) -- disclosed here rather than silently
dropped; a follow-up ticket covering this residue is warranted but not
filed this pass to avoid re-deriving the same "re-measure first" framing
T-1074 itself used -- the next dispatch of this series should re-run
`frob check --only archgate` fresh rather than trust this list, since
siblings are actively splitting gates/**/tickets/** concurrently and the
overall LARGE001 count moves every wave.

Verification: `frob check --ticket T-1074` clean (0 errors, was 0 errors
after fixing DRIFT002/DUP001/INV006/PRE001 introduced by the split itself)
across gates-native/gates-fast/gates-security (chunked, see command log).
`pytest tests/test_testing.py tests/test_testing_collect.py` (321 tests)
and the cpp-collector slice of tests/test_gates.py (18 tests) all pass.
ruff clean on every touched file (both PATH ruff and `uv run ruff`).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_testing.py::TestCollectRustTests::test_collect_rust_tests_parses_and_caches` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_parses_and_caches` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_parses_and_caches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 6475 warning(s), 494 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1083 -->
```yaml
id: T-1083
title: 'arch: abstraction-opportunity remaining single-file packages extraction (T-0393/T-1067
  remainder, 23 findings)'
state: dropped
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

## Drop reason
- 2026-07-29: disposition-complete, no extraction warranted: the w20-arch pass re-measured and read every remaining in-scope abstraction-opportunity finding -- all coincidental same-signature dispatch/case-handler families, none genuine duplication (full per-family record preserved on branch w20-arch, commit a8085d7f, plus its fail-log). The two real detector-precision gaps it found are refiled as T-1181/T-1182. A feature-kind ticket structurally cannot close on a zero-code disposition (EvidenceScopeUnbound), and reclassifying kind to force a close would misrecord what happened -- drop-with-reason is the honest terminal state.

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

<!-- ticket:T-1173 -->
```yaml
id: T-1173
title: 'bug: cross-worktree lease not renamed when a draft ticket is renumbered at
  land'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_leases.py
- src/frob/tickets/_new_renumber.py
threat: null
component: null
```
Observed while landing T-1165/T-1172 in the same worktree: frob ticket start T-draft-XXXXXXXX records a lease at .git/frob-leases/T-draft-XXXXXXXX.json. When the draft is renumbered to a real id (T-1172) at land time, the lease file is never renamed/migrated -- a subsequent frob check --ticket T-1172 in the SAME worktree that started it fails with 'no recorded lease', even though the worktree genuinely holds the ticket. Worked around by hand-copying the lease json with the new id; the renumber path should do this automatically.

<!-- ticket:T-1174 -->
```yaml
id: T-1174
title: 'arch: split remaining ~10 gate families out of src/frob/gates/__init__.py
  (8128 lines) -- T-1170 residue'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
- tests/test_gates.py
evidence:
- tests/test_gates.py::TestOptInGates::test_dup_gate_off_by_default
- tests/test_gates.py::TestOptInGates::test_dup_gate_fires_on_planted_clone_when_enabled
- tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing
threat: null
component: null
```
T-1170 extracted ONE cohesive family (DOC001/DOC002 -- `doclink_gate`/
`docanchor_gate` plus their private helpers) into
`src/frob/gates/_doclink_docanchor.py` (gates/__init__.py 8401 -> 8128
lines), one-family-per-land per the T-1072/T-1140/T-1159 discipline.
Budget did not allow the other ~10 remaining families this drive's own
ticket named. gates/__init__.py is still 8128 lines, well above the
large-file threshold.

Still remaining, in the same one-family-per-land shape:
- SYS00x/DOC003 (sys_gate + helpers, ~600 lines)
- DUP00x (dup_gate + helpers, ~500 lines)
- FUZZ00x (fuzz_gate)
- INV00x (inv006_gate + helpers)
- TEST00x (test policy loading + TEST00x gate family)
- REL00x (release-bump/debt gate wiring)
- PERF (perf gate wiring, distinct from frob.perf's own module)
- COV00x (coverage gate family)
- SCOPE/PREWORK (scope_gate, prework_gate)
- the run_gates spine itself (_assemble_gate_report, _build_jobs,
  run_gates) -- likely stays in __init__.py as the module's own
  orchestration root, but worth an explicit decision at design time

Re-filed (not re-derived from scratch) rather than letting T-1170 close
with silent residue, per TICK011.

## Done report

Extracted the DUP001/DUP002/DUP003 clone-detection family (`dup_gate`,
`_dup_config`, `_dup_gate_violations`) out of `src/frob/gates/__init__.py`
into `src/frob/gates/_dup.py`, per the T-1072/T-1140/T-1159/T-1170
one-family-per-land discipline this ticket's residue list names --
`gates/__init__.py` drops from 8128 to 8015 lines (113 lines moved plus
a 3-line pointer comment left behind).

`dup_gate` remains importable/re-exported from `frob.gates` unchanged
(verified by grep before the move: `tests/test_gates.py`, `frob.dup.
_models`, `frob.app.config` all reference it by that path, not a
`gates._dup`-qualified one) -- imported at the top of `__init__.py` and
still listed in `__all__`. `_dup_config`/`_dup_gate_violations` stay
private to the new module; nothing else imports them.

Fixed the resulting DRIFT002 findings (docs/modules/gates.md's `frob:
describes` edge and 3 `frob:tests` edges in tests/test_gates.py that
pointed at `src/frob/gates/__init__.py::dup_gate`, now resolved to `src/
frob/gates/_dup.py::dup_gate`).

Only ONE family of the ~10 remaining ones the parent ticket named was
budget for this pass (SYS00x/DOC003, FUZZ00x, INV00x, TEST00x, REL00x,
PERF, COV00x, SCOPE/PREWORK, and the run_gates spine itself all remain);
filed a residue ticket for the rest rather than let this close with
silent scope cut, matching T-1170's own precedent.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestOptInGates::test_dup_gate_off_by_default` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_dup_gate_fires_on_planted_clone_when_enabled` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 700 warning(s), 572 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1175 -->
```yaml
id: T-1175
title: 'tickets: one-verb lifecycle -- frob ticket work (setup) and land absorbing
  fmt + sync-interface + Tier-A fixes + on-main proof + finish'
state: queued
kind: ux
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- docs/guides/agent-playbook.md
acceptance:
- text: GIVEN frob ticket work T-#### WHEN run from root THEN it creates/reuses the
    named worktree, verifies base freshness against main tip, builds natives, and
    starts the ticket -- one command replacing playbook contract steps 1-2 plus start
  evidence: []
- text: GIVEN frob ticket land WHEN run THEN it first runs frob fmt on touched files,
    sys sync-interface (applying the interface diff in-land), and the T-1137 Tier-A
    fix handlers; after landing it prints a machine-checkable proof line (land hash
    + is-ancestor-of-main + ticket state on main) and offers --finish to remove the
    worktree only when every series land verifies
  evidence: []
threat: null
component: null
```
User directive 2026-07-29: agents should only run frob commands and write content requiring actual thinking. The remaining per-ticket ritual (playbook section 0) is ~10 mechanical steps; steps 1-2, 5, and 9 are pure command sequences frob can own. This collapses them into two verbs. The playbook contract section then shrinks to: work, think, land. Absorb-not-add: reuse the existing fmt/sync-interface/fix-engine/land machinery, no new subsystems.

<!-- ticket:T-1176 -->
```yaml
id: T-1176
title: 'gates: named waiver presets -- frob:waive RULE preset=<name> resolving to
  one documented reason text'
state: queued
kind: ux
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
acceptance:
- text: GIVEN a frob:waive directive using preset=<name> WHEN gates evaluate it THEN
    the reason resolves from a single documented preset table (docs/modules/gates.md
    section, machine-read), behaves identically to the inline reason, and an unknown
    preset name is an error
  evidence: []
- text: GIVEN the existing calibration-batch INV006 text THEN it becomes preset=split-carried-prose
    and the repo's 10+ verbatim copies are migrated to it in the same land
  evidence: []
threat: null
component: null
```
User directive 2026-07-29: remove boilerplate agents hand-write. The 8-line INV006 calibration-batch waiver text has been copy-pasted 10+ times this drive (0abc4e3a lineage), and the T-1099 REF002 split-fragment text 7+ times. A preset is NOT a blanket waiver: each site still carries an explicit per-site directive naming rule + preset; the preset only deduplicates the REASON prose, which the NO DUPLICATION principle applies to as much as code. Reason-required stays intact -- a preset name must resolve to a real documented reason.

<!-- ticket:T-1177 -->
```yaml
id: T-1177
title: 'fix-engine: Tier-A auto-carry of split-carried waivers (T-1137 child; coordinator
  decision recorded)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1137
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/test_gates.py
acceptance:
- text: GIVEN a module split moves prose verbatim from a file whose waiver covered
    it (T-1134's find_carried_waiver detects the source) WHEN frob check --fix runs
    THEN the carried waiver is applied automatically at the new site, citing the source
    file and preset, and the fix report discloses every carry
  evidence: []
- text: GIVEN prose that is NOT a verbatim move from an already-waived source THEN
    --fix never inserts any waiver (the no-auto-waive anti-goal stands for everything
    else)
  evidence: []
threat: null
component: null
```
Coordinator decision 2026-07-29 under user-delegated authority: carrying an EXISTING waiver whose prose moved verbatim preserves a prior explicit human disposition -- it is not a new waiver, so it does not violate T-1137's never-auto-waive anti-goal, which continues to bind for every other case. Evidence: 6+ hand-carries this drive (3 by the coordinator in one day, 0abc4e3a; 2 rust files missed and redded main). Builds directly on T-1134's detector; pairs with the preset ticket so the carried text is one reference, not a copy.

<!-- ticket:T-1178 -->
```yaml
id: T-1178
title: 'tickets: complete the auto-commit family -- close/done-report/evidence/requeue
  transitions commit like start/new/drop/fail'
state: queued
kind: bug
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_ticket_leases.py
acceptance:
- text: GIVEN any ledger-writing ticket verb run on main WHEN it completes THEN its
    transition is committed automatically (T-1130's commit_ticket_ledger_change, --no-commit
    opt-out), so no concurrent land preflight reset can ever discard a completed verb's
    write
  evidence: []
threat: null
component: null
```
REFILE: the original filing (commit 46a115c4, first allocated id clobbered by a concurrent land's renumber -- see the sibling id-allocation bug ticket) recorded the 2026-07-29 incident: the coordinator's T-0329 epic close wrote the ledger uncommitted (close is not in T-1130's new/drop/fail set), a concurrent agent land preflight ran git reset --hard in root, and the close silently vanished -- caught only by T-1131's doctor stale-lease scan. Extend commit_ticket_ledger_change to every remaining ledger-writing verb: close, done-report, evidence add, requeue, and any mutation verbs still uncommitted. Closes the reset-eats-uncommitted-coordinator-work class (T-0948 lineage) at the verb layer.

<!-- ticket:T-1179 -->
```yaml
id: T-1179
title: 'land: draft renumbering allocated an id already taken on main, clobbering
  a main-side block (T-1090 gap on the land path)'
state: done
kind: bug
origin: human
created: '2026-07-29'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets_collision.py
- docs/modules/tickets.md
- design/frob.strata
- tests/test_ticket_land.py
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: T-1179 docstring/interface-sync fixes touch both files
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: T-1179 docstring/interface-sync fixes touch both files
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_ticket_land.py
  reason: T-1179's finalize_draft_for_land wiring changed which symbol test_finalize_draft_failure
    must monkeypatch
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_tickets_collision.py::TestFinalizeDraftForLandMainFreshCeiling::test_id_ceiling_reads_current_main_not_stale_worktree_view
- tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_id_title_mismatch_is_refused_not_silently_overwritten
- tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_same_id_same_title_still_resolves_via_newer
- tests/test_ticket_land.py::TestLandDeeperBranches::test_finalize_draft_failure
acceptance:
- text: GIVEN a worktree land whose draft renumbering runs WHEN main has allocated
    new ids since the worktree's last merge THEN renumbering reads the id ceiling
    from CURRENT main (not the worktree's stale view) under the ledger lock, and a
    would-be collision with any existing main-side id is impossible by construction,
    proven by a regression test reproducing the 2026-07-29 shape
  evidence:
  - tests/test_tickets_collision.py::TestFinalizeDraftForLandMainFreshCeiling::test_id_ceiling_reads_current_main_not_stale_worktree_view
  - tests/test_ticket_land.py::TestLandDeeperBranches::test_finalize_draft_failure
- text: GIVEN the splice THEN a landing block may never overwrite a different-titled
    existing block under the same id -- a detected id/title mismatch refuses the land
    loudly instead of silently replacing content
  evidence:
  - tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_id_title_mismatch_is_refused_not_silently_overwritten
  - tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_same_id_same_title_still_resolves_via_newer
threat: null
component: null
```
2026-07-29 incident (5th id-collision, first SINCE T-1090): coordinator filed a ticket on main (46a115c4, auto-committed); minutes later T-1170's land (17c6ca89) renumbered its residue draft to the SAME id, and the splice replaced the coordinator's block wholesale -- content lost from the live ledger (recovered from git history and refiled). T-1090's atomic allocation apparently guards concurrent new_ticket calls against a shared counter but the LAND-path renumber derived its next-id from the worktree's stale ledger view. Two independent guards per acceptance: allocation-from-current-main under lock, and a splice-level id/title-mismatch refusal (defense in depth, T-0959 style).

## Done report

Two independent guards, matching the acceptance criteria and the 2026-07-29
incident (46a115c4 clobbered by 17c6ca89):

Guard 1 (acceptance [0]): new frob.tickets._new_renumber.finalize_draft_for_land
(worktree, draft_id, main_root) replaces plain finalize_draft on the land path
(frob.tickets._land._finalize_draft_id / _finalize_sibling_drafts, threaded
through _land_finalize_and_close / _finalize_and_close_ticket, all now taking
root explicitly). It reads BOTH ledgers fresh from disk (main_root's CURRENT
on-disk copy, not a stale snapshot) and computes the next-id ceiling from
their union, under worktree's own ledger_lock.

Implementation note / honest disclosure: the first version of this also
acquired main_root's OWN ledger_lock (nested, main-first) to make the read
provably atomic against a concurrent new_ticket on main. That version was
REVERTED after it reproduced a real regression: locking main_root creates
main_root/.frob/tickets.lock as an untracked artifact on root's working
tree; on any repo/fixture where .frob/ is not gitignored (the worktree
branch legitimately tracks its OWN .frob/tickets.lock, T-1006), the
subsequent `git merge --squash` from the worktree branch then refuses with
git's own "untracked working tree files would be overwritten by merge"
error, which silently degrades the later ticket-scoped splice (root's
tickets.md never receives the squash's changes, main=0 tickets instead of
main=1) -- caught by tests/test_ticket_land.py::TestWipCommit and
TestWipCommitNormalizationOnlyDirty going red. Reproduced and bisected via
a standalone repro script before landing. The shipped version reads
main_root's ledger WITHOUT holding its lock (same lock footprint as plain
finalize_draft -- only worktree's lock), closing the staleness gap that
caused the incident while leaving zero new regression surface. The narrow
residual race this leaves (a new_ticket landing on main in the tiny window
between this unlocked read and the eventual squash-apply) is closed by
Guard 2 below, which runs under a REAL lock at the point that actually
commits to main -- the two guards are deliberately complementary, not each
independently sufficient, matching the ticket's own "defense in depth"
framing.

Guard 2 (acceptance [1], defense in depth): _land._overlay_landed_ticket
(split out of _splice_only_ticket to stay under the ARCH001 line budget)
refuses (TicketError.IdTitleMismatch) instead of calling _newer when the
ticket-scoped land-time splice's overlay id already exists on main under a
DIFFERENT title -- the exact shape of the incident: a landing block would
otherwise silently replace an unrelated main-side block sharing the same id.
A same-id/same-title divergence (a genuine same-ticket state advance) still
resolves via _newer exactly as before. This runs inside
_squash_and_splice_ledger's own ledger_lock(root) span, at the point that
actually commits to main -- the atomic backstop Guard 1's unlocked read
cannot itself be.

Reproduced the 2026-07-29 shape directly: a ticket filed on a "main" fixture
after a "worktree" fixture branched off is invisible to finalize_draft's old
worktree-only view (would collide); finalize_draft_for_land's main-fresh
ceiling picks the next free id instead. A companion pair of splice tests
proves the id/title-mismatch refusal and its same-title control case.

Unplanned but necessary fix, filed and disclosed (T-1184, renumbers
at land): _do_wip_commit's `git add -A -- . :!.frob` unconditionally failed
on this environment's git (2.34.1) the moment .frob is actually gitignored
(a real repo, not just a test fixture) -- naming an ignored path in a NEGATED
pathspec still trips git's "explicitly named ignored path" refusal, aborting
the entire add. Reproduced against a clean main checkout with zero
ticket-related changes staged. This blocked EVERY `frob ticket land` in this
environment outright, including this ticket's own land, so it had to be
fixed to complete T-1179's own acceptance -- landing IS how T-1179 exercises
its own fix. Fixed with a detect-and-fallback: try the original exclusion
pathspec first (byte-identical behavior/staging semantics for the T-1006
bare-fixture case that has no .gitignore at all, where the pathspec never
hits the refusal); only on the specific ignored-path refusal, fall back to
staging everything and unstaging .frob as a separate `git reset` step, never
naming an ignored path in a pathspec. Filed T-1184 to track this
fix on its own record.

tests/test_ticket_land.py::TestLandDeeperBranches::test_finalize_draft_failure
needed a one-line update: it now monkeypatches `finalize_draft_for_land`
(the symbol land's own finalize step actually calls) instead of the now-
bypassed `finalize_draft`.

docs/modules/tickets.md's "Provisional ids" section and error-types sample
gained a T-1179 paragraph/entry (including the locking trade-off above);
design/frob.strata was synced (SYS104) for the two new test classes plus the
new finalize_draft_for_land public symbol.

### Changed
```
 tickets.md | 118 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 115 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_tickets_collision.py::TestFinalizeDraftForLandMainFreshCeiling::test_id_ceiling_reads_current_main_not_stale_worktree_view` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_id_title_mismatch_is_refused_not_silently_overwritten` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_same_id_same_title_still_resolves_via_newer` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandDeeperBranches::test_finalize_draft_failure` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 931 warning(s), 501 waived
- error-findings: PRE001@tickets/T-1179

<!-- ticket:T-1180 -->
```yaml
id: T-1180
title: 'coverage pipeline: flake-tolerant end-to-end -- serial rerun of failures,
  stale-data cleanup, deflation guard before stamp'
state: done
kind: bug
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- src/frob/testing/**
- src/frob/gates/**
- tests/test_coverage.py
- tests/test_gates.py
- design/frob.strata
- docs/modules/gates.md
- frob-coverage.lock.json
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: 'T-1180: TEST011-floor unit coverage lives in tests/test_gates.py next to
    the rest of stamp_coverage/TestCoverageLoad tests; new top-level test class needs
    the SYS104 design/frob.strata interface= declaration to keep self-model clean'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: 'T-1180: TEST011-floor unit coverage lives in tests/test_gates.py next to
    the rest of stamp_coverage/TestCoverageLoad tests; new top-level test class needs
    the SYS104 design/frob.strata interface= declaration to keep self-model clean'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-1180: AFFECT001 requires touching the docs/modules/gates.md public-api/error-types
    sections stamp_coverage/GateError changes affect'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: frob-coverage.lock.json
  reason: 'T-1180: the in-dispatch make coverage validation run refreshed the committed
    coverage lock via stamp_coverage, the exact artifact this ticket modifies the
    write path of'
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_refuses_below_deflation_floor
- tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_deflation_floor_skipped_below_min_known_modules
- tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_first_pass_failure_does_not_abort_the_recipe
- tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_rerun_is_serial_and_scoped_to_last_failed
- tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_combine_xml_stamp_run_unconditionally_after_the_rerun
- tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_target_exit_reflects_final_status_not_always_zero
acceptance:
- text: GIVEN make coverage WHEN the parallel suite has failures THEN the failed tests
    are re-run once serially without coverage-halting, and only still-failing tests
    fail the target -- load-sensitive flakes (the four known self-model/serve-watch
    specimens) no longer block combine/xml/stamp
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_refuses_below_deflation_floor
  - tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_deflation_floor_skipped_below_min_known_modules
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_first_pass_failure_does_not_abort_the_recipe
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_rerun_is_serial_and_scoped_to_last_failed
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_combine_xml_stamp_run_unconditionally_after_the_rerun
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_target_exit_reflects_final_status_not_always_zero
- text: GIVEN combine runs THEN stale .coverage* files from prior aborted runs are
    removed first and the combine reports consuming every fresh worker file; a coverage.xml
    whose module-coverage fraction is below a sanity floor refuses to stamp (extending
    TEST011's deflation heuristic into a hard pre-stamp guard)
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_refuses_below_deflation_floor
  - tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_deflation_floor_skipped_below_min_known_modules
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_first_pass_failure_does_not_abort_the_recipe
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_rerun_is_serial_and_scoped_to_last_failed
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_combine_xml_stamp_run_unconditionally_after_the_rerun
  - tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_target_exit_reflects_final_status_not_always_zero
threat: null
component: null
```
Three consecutive coverage runs failed to produce a trustworthy coverage.xml on 2026-07-28/29: (1) corrupted coverage shim broke combine silently; (2+3) four load-sensitive tests (three strata self-model + serve-watch tick, all pass in isolation, verified twice) fail only under xdist+coverage parallelism and halt the recipe before combine; a manual combine then consumed 2 of 7 data files (stale-file skip). The TEST005 bucket (~600 warnings) cannot be honestly recounted until this pipeline is deterministic. Also route the notification-exit-code mismatch to the record: background make reported exit 0 twice while make actually failed -- do not trust bg exit codes for make pipelines, read the output tail.

## Done report

Made `make coverage` flake-tolerant end to end, per the ticket's three
failure modes (corrupt shim, 2x load-flake halts, stale-data combine
skip):

1. Serial rerun-once: a parallel-run pytest failure no longer halts the
   recipe. Failed tests are re-run exactly once with xdist parallelism
   disabled (`-n 0`, overriding `[tool.pytest.ini_options] addopts`'s
   baked-in `-n auto`) and scoped to `--last-failed`, appending onto the
   same coverage data (`--cov-append`). `combine`/`xml`/`frob check
   --stamp-coverage` now always run regardless of the (possibly still
   nonzero) rerun status; only a test still failing after the serial
   rerun fails the target (`exit $status` at the end of the recipe's
   shell block).
2. Stale-data cleanup: the existing `rm -f .coverage .coverage.*` at the
   top of the recipe doubles as the acceptance criterion's stale-file
   guard -- since the parallel pass and the serial rerun share ONE
   recipe invocation (rerun appends, never restarts), there is no window
   between them where a leftover file from an earlier, separate, aborted
   run could get silently combined alongside fresh data (the "2 of 7
   data files" incident).
3. Deflation floor before stamp: `stamp_coverage` (`frob.gates._coverage`)
   now refuses to write `.frob/coverage-stamp`/`frob-coverage.lock.json`
   at all (`Err(GateError.CoverageDeflated)`) when the coverage.xml it is
   about to stamp joins too small a fraction of known modules (TEST011's
   existing 0.5 `module_join_fraction` heuristic, promoted from a
   WARN-only advisory to a hard pre-stamp gate) -- but only above
   `_DEFLATION_MIN_KNOWN_MODULES` (20) known `.py` modules, since a tiny
   repo/fixture's near-zero join fraction is sample-size noise, not
   deflation.

CORRECTION mid-dispatch: the original dispatch note asked me to run
`make coverage` myself as live end-to-end evidence. That conflicts with
playbook 6b (a dispatched sub-agent cannot wait on a background
`make coverage` run) -- flagged by the coordinator and corrected. The
coordinator's guidance is followed here: T-1180 closes on the UNIT
evidence bound below (the deflation-floor and serial-rerun tests, which
directly exercise the acceptance criteria's own mechanics), and the live
full-suite `make coverage` validation is left to the coordinator, who
can wait on it.

What the in-dispatch (out-of-band, not claimed as this ticket's
evidence) attempts DID catch and fix, disclosed for the record:
- First `make coverage` attempt: `pytest: error: unrecognized arguments:
  -n` in the serial rerun stage -- `-p no:xdist` conflicts with
  `addopts`' baked-in `-n auto` once the xdist plugin is unloaded. Fixed
  by using `-n 0` instead (overrides the worker count, keeps the plugin
  loaded). Landed as its own follow-up commit.
- That same first attempt's failure list caught a REAL regression in an
  earlier version of the deflation floor: an unconditional floor broke
  13 existing tests that stamp tiny fixture coverage.xml files
  (`test_only_gates_passes_once_bound_and_tested`,
  `test_perf001_fixture_warns_but_check_exits_zero`,
  `test_repo_design_and_declarations_are_self_conformant`, and others).
  Fixed by adding `_DEFLATION_MIN_KNOWN_MODULES` (20) -- verified
  against all 13 affected tests individually before and after the fix.
- The four load-sensitive specimens named in the ticket (three strata
  self-model tests plus `test_serve_watch.py::TestWatchTick`'s tick
  tests) were re-verified to pass in isolation, confirming they are
  load-sensitive flakes, not real regressions, exactly as the ticket
  instructed.
- Neither attempt's `make coverage` run was allowed to run to
  completion/be waited on in-dispatch once the playbook-6b conflict was
  flagged -- the second (post `-n 0` fix) run was killed mid-flight per
  the coordinator's correction, and any partial `.coverage*`/
  `coverage.xml` artifacts it left were cleaned up. The coordinator owns
  running the real, complete `make coverage` and reporting the honest
  TEST005 count from it.

### Changed
```
 Makefile                    |  45 +++-
 design/frob.strata          |   1 +
 docs/modules/gates.md       |  13 +-
 frob-coverage.lock.json     | 624 ++++++++++++++++++++++++++++----------------
 src/frob/gates/__init__.py  | 121 +--------
 src/frob/gates/_coverage.py | 122 +++++++--
 src/frob/gates/_dup.py      | 148 +++++++++++
 src/frob/gates/_models.py   |   8 +
 tests/test_coverage.py      |  70 +++++
 tests/test_gates.py         |  64 ++++-
 tickets.md                  |  95 ++++++-
 11 files changed, 935 insertions(+), 376 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_refuses_below_deflation_floor` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_deflation_floor_skipped_below_min_known_modules` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_first_pass_failure_does_not_abort_the_recipe` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_rerun_is_serial_and_scoped_to_last_failed` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_combine_xml_stamp_run_unconditionally_after_the_rerun` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_target_exit_reflects_final_status_not_always_zero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 2518 warning(s), 496 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1181 -->
```yaml
id: T-1181
title: 'arch: language-parity exclusion synonym map missing python/typescript/kotlin/cplusplus
  spellings'
state: queued
kind: bug
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
acceptance:
- text: GIVEN same-signature groups whose member names differ only by language tag
    WHEN the language-parity family exclusion runs THEN the synonym map recognizes
    python/typescript/kotlin/cplusplus alongside the short forms, measured before/after
    on the T-1083 finding set
  evidence: []
threat: null
component: null
```
Refile from the w20-arch T-1083 disposition pass (draft died with the fail-log; full record on branch w20-arch commit a8085d7f): _is_language_parity_family's synonym map lacks the long-form language spellings, so genuinely-parity families with those tags escape the exclusion and pollute abstraction-opportunity counts.

<!-- ticket:T-1182 -->
```yaml
id: T-1182
title: 'arch: abstraction-opportunity detector should skip same-name call-through
  forwarders'
state: queued
kind: bug
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
acceptance:
- text: GIVEN a group whose members are same-name single-statement forwarders to another
    symbol WHEN abstraction-opportunity clusters by signature THEN forwarders are
    excluded (they are deliberate indirection, not duplicated logic), measured before/after
    on the T-1083 finding set
  evidence: []
threat: null
component: null
```
Refile from the w20-arch T-1083 disposition pass (draft died with the fail-log; record on branch w20-arch commit a8085d7f): call-through forwarders (one-line delegation wrappers) coincide on signature by construction and are not extraction candidates.

<!-- ticket:T-1183 -->
```yaml
id: T-1183
title: 'arch: split remaining ~9 gate families out of src/frob/gates/__init__.py (8015
  lines) -- T-1174 residue'
state: queued
kind: feature
origin: human
created: '2026-07-29'
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
T-1174 extracted ONE cohesive family (DUP001/DUP002/DUP003 -- `dup_gate`
plus its private helpers `_dup_config`/`_dup_gate_violations`) into
`src/frob/gates/_dup.py` (gates/__init__.py 8128 -> 8015 lines),
one-family-per-land per the T-1072/T-1140/T-1159/T-1170 discipline.
Budget did not allow the other ~9 remaining families this ticket's own
body named. gates/__init__.py is still 8015 lines, well above the
large-file threshold.

Still remaining, in the same one-family-per-land shape:
- SYS00x/DOC003 (sys_gate + helpers, ~600 lines)
- FUZZ00x (fuzz_gate)
- INV00x (inv006_gate + helpers)
- TEST00x (test policy loading + TEST00x gate family)
- REL00x (release-bump/debt gate wiring)
- PERF (perf gate wiring, distinct from frob.perf's own module)
- COV00x (coverage gate family)
- SCOPE/PREWORK (scope_gate, prework_gate)
- the run_gates spine itself (_assemble_gate_report, _build_jobs,
  run_gates) -- likely stays in __init__.py as the module's own
  orchestration root, but worth an explicit decision at design time

Re-filed (not re-derived from scratch) rather than letting T-1174 close
with silent residue, per TICK011.

<!-- ticket:T-1184 -->
```yaml
id: T-1184
title: 'land: _do_wip_commit''s negated :!.frob pathspec aborts git add outright on
  git 2.34.1'
state: queued
kind: bug
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
threat: null
component: null
```
_do_wip_commit's git add invocation (src/frob/tickets/_land.py:1854,
`git add -A -- . :!.frob`) fails outright on this environment's git
(2.34.1): naming `.frob` in a NEGATED pathspec still trips git's
"explicitly named ignored path" refusal (exit 1, "The following paths
are ignored by one of your .gitignore files: .frob"), aborting the ENTIRE
add -- not just skipping `.frob`. Reproduced directly against a clean
main checkout with zero ticket-related changes staged, so this is not
specific to any in-flight ticket's diff.

`.frob/` is already covered by the repo's own top-level .gitignore
(T-1006's own stated rationale for the negated pathspec was defense for a
bare test fixture that has NOT gitignored .frob/) -- for this repo,
`git add -A -- .` alone (no negation) already excludes `.frob/` correctly
and exits 0. The negated pathspec is redundant belt-and-suspenders for the
real repo and is the literal cause of every land's wip-commit step
failing outright in this git version.

Blocks EVERY `frob ticket land` in this environment -- found while
landing T-1179 (unrelated to that ticket's own acceptance criteria) and
fixed inline there only because it structurally blocked completing that
land; filing this ticket to track the fix on its own record and note any
test-fixture-repo defense-in-depth this drops (T-1006's original bare-
fixture case, if any test exercises a non-gitignored .frob/ specifically).
