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

<!-- ticket:T-1181 -->
```yaml
id: T-1181
title: 'arch: language-parity exclusion synonym map missing python/typescript/kotlin/cplusplus
  spellings'
state: done
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
evidence:
- tests/unit/test_arch.py::TestLanguageParityExclusion::test_long_form_language_spellings_normalize_to_short_tag
- tests/unit/test_arch.py::TestLanguageParityExclusion::test_long_and_short_form_parity_group_not_flagged
acceptance:
- text: GIVEN same-signature groups whose member names differ only by language tag
    WHEN the language-parity family exclusion runs THEN the synonym map recognizes
    python/typescript/kotlin/cplusplus alongside the short forms, measured before/after
    on the T-1083 finding set
  evidence:
  - tests/unit/test_arch.py::TestLanguageParityExclusion::test_long_form_language_spellings_normalize_to_short_tag
  - tests/unit/test_arch.py::TestLanguageParityExclusion::test_long_and_short_form_parity_group_not_flagged
threat: null
component: null
```
Refile from the w20-arch T-1083 disposition pass (draft died with the fail-log; full record on branch w20-arch commit a8085d7f): _is_language_parity_family's synonym map lacks the long-form language spellings, so genuinely-parity families with those tags escape the exclusion and pollute abstraction-opportunity counts.

## Done report

Extended _LANGUAGE_TAG_SYNONYMS mapping (python->py, typescript->ts,
kotlin->kt, cplusplus->cpp) and folded it into _LANGUAGE_TAG_RE / a
normalizing _language_tag so long-form language spellings resolve to the
same canonical short tag as their short-form counterpart before
_is_language_parity_family's distinctness check runs.

Measured before/after via `frob check --only arch --json`, counting
"abstraction-opportunity" occurrences: 66 -> 65 (frob.testing._collect*.py's
collect_python_tests/collect_typescript_tests/collect_kotlin_tests/
collect_cpp_tests family no longer false-positives).

### Changed
```
 tickets.md | 10 +++++++---
 1 file changed, 7 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestLanguageParityExclusion::test_long_form_language_spellings_normalize_to_short_tag` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestLanguageParityExclusion::test_long_and_short_form_parity_group_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 453 warning(s), 678 waived
- error-findings: none (measured, zero errors)

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

<!-- ticket:T-1185 -->
```yaml
id: T-1185
title: 'arch: fix-or-waive the last 3 gates/** OPAQUE001 sites and promote to ERROR
  tier'
state: queued
kind: security
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_docblocks.py
- src/frob/gates/_opaque.py
- frob.toml
threat: null
component: null
```
T-1038 fixed or waived 90 of the T-0665 first-turn-on 93-site OPAQUE001 set, but src/frob/gates/__init__.py:7536 (getattr) and src/frob/gates/_docblocks.py:396-397 (importlib.import_module/getattr) were out of T-1038's declared scope (owned by a concurrent sibling ticket that wave). Dispose those 3 the same way (real fix or reasoned frob:waive), then promote OPAQUE001 from Severity.WARN to Severity.ERROR in src/frob/gates/_opaque.py (opaque_gate's Violation construction) and add OPAQUE001 = "error" to frob.toml's [gates.severity] table, in the SAME land that zeroes the repo-wide unwaived count -- the T-0973/T-0976 promote-at-zero precedent T-1038's own Done report follows.

<!-- ticket:T-1186 -->
```yaml
id: T-1186
title: 'arch: split tickets/_land.py (4973 lines) -- T-1171 residue'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- docs/modules/tickets.md
threat: null
component: null
```
T-1171 landed the __init__.py half of its own scope (the done-report/
review/drop/attach family, extracted into src/frob/tickets/_reporting.py:
mutate_labels, brief_ticket, compose_done_report/_capture_done_report_
claims/set_done_report, record_failure, _resolve_review_commit/
record_review/has_approved_review_for_commit, drop_ticket, and the
attach/_attachment_bytes/_next_attachment_path/_record_attachment
quartet -- __init__.py: 1266 -> ~640 lines).

The _land.py half of T-1171's own scope was NOT touched this dispatch,
budget did not allow both in one land: src/frob/tickets/_land.py is
still 4973 lines (unchanged across T-1108/T-1122/T-1123/T-1151/T-1152/
T-1171), still triggering LARGE001, and still needs the preflight/
merge-splice/verify/sweep submodule split T-1108's original plan called
for.

Follow the same verbatim-move pattern as _evidence.py/_reporting.py:
private module(s) re-exported from _land.py or __init__ via explicit
imports, zero caller-visible behavior change, existing tests as the
safety net, carry frob:ticket/frob:doc/frob:tests directives verbatim,
repoint docs/modules/tickets.md's frob:describes anchors and any
tests/*.py frob:tests directives at the new module path(s), add
frob:ticket edges to any test class/method a directive-repoint touches
(COV002), carry a file-level INV006 split-module waiver (T-0585
calibration-batch precedent) if the moved prose trips it, watch for
tests that monkeypatch a moved function via the PACKAGE attribute
(land_mod.<name> or tickets_mod.<name>) -- those need a late `from
frob.tickets import <name>` / `from frob.tickets._land import <name>`
inside the moved function body instead of a module-top-level binding
(the same write_ticket/bare-subprocess hazards T-1152 hit).

Given the file's size (4973 lines), this is likely its OWN multi-land
series rather than one land -- consider splitting the plan itself into
2-3 tickets (e.g. preflight+merge-splice as one family, verify+sweep as
another) rather than one ticket trying to move the whole file at once.

<!-- ticket:T-1187 -->
```yaml
id: T-1187
title: 'arch: split remaining ~8 gate families out of src/frob/gates/__init__.py (7960
  lines) -- T-1183 residue'
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
- docs/strata/surface.md
scope_changes:
- op: add
  glob: docs/strata/surface.md
  reason: T-1187's sys_gate split leaves this doc's frob:describes edge pointing at
    the old __init__.py location; a 1-line symref fix, same class as the tests/test_gates.py
    fixes already in scope
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_gates.py::TestSysGate::test_noop_no_design_dir
- tests/test_gates.py::TestSysGate::test_sys001_dangling
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_selfconform_violation
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations
threat: null
component: null
```
T-1183 extracted ONE more cohesive family (FUZZ001/002/003 -- fuzz_gate
plus its private helpers _fuzz_enforce/_fuzz_gate_violations) into
src/frob/gates/_fuzz.py (gates/__init__.py 8015 -> 7960 lines),
continuing the T-1072/T-1140/T-1159/T-1170/T-1174 one-family-per-land
discipline. Budget did not allow the other ~8 remaining families this
ticket's own body named. gates/__init__.py is still 7960 lines, well
above the large-file threshold.

Still remaining, in the same one-family-per-land shape:
- SYS00x/DOC003 (sys_gate + helpers, ~600 lines)
- INV00x (inv006_gate + helpers)
- TEST00x (test policy loading + TEST00x gate family)
- REL00x (release-bump/debt gate wiring)
- PERF (perf gate wiring, distinct from frob.perf's own module)
- COV00x (coverage gate family)
- SCOPE/PREWORK (scope_gate, prework_gate)
- the run_gates spine itself (_assemble_gate_report, _build_jobs,
  run_gates) -- likely stays in __init__.py as the module's own
  orchestration root, but worth an explicit decision at design time

Re-filed (not re-derived from scratch) rather than letting T-1183 close
with silent residue, per TICK011.

## Done report

Extracted the SYS00x/DOC003/SELFAUDIT001 family (sys_gate + its private
helpers: _load_systems/_load_test_config, _design_dir, _sys001-004,
_selfaudit_violation(s), _claims_markers and friends, _log_sys_gate_summary)
into src/frob/gates/_sys.py, following the _fuzz.py (T-1183) precedent.
gates/__init__.py: 7960 -> 7309 lines. sys_gate and _load_test_config are
re-exported from frob.gates unchanged; _DEFAULT_DESIGN_DIR, _claims_markers,
and _design_dir are also re-exported (tests/test_gates.py's direct-call
surface plus _waive_comments.py's existing `from frob.gates import
_design_dir` cross-reference).

DRIFT002 fallout from the move (5 tests/test_gates.py `frob:tests` comments
plus one docs/strata/surface.md `frob:describes` marker pointing at the
old __init__.py::sys_gate location) fixed by updating the symref text in
place, same as T-1183's precedent for _fuzz.py. docs/strata/surface.md was
not in T-1187's original scope; added it via `frob ticket scope --add`
(SCOPE001's own suggested remedy) since the 1-line fix is a direct,
unavoidable consequence of this ticket's own file move, not new work.

Only ONE family extracted this land (one-family-per-land discipline
continues); the other 7 named in T-1187's body (INV00x, TEST00x, REL00x,
PERF, COV00x, SCOPE/PREWORK, run_gates spine) are still outstanding.
Re-filed as a fresh residue ticket per TICK011 rather than closed silently.

### Changed
```
 docs/strata/surface.md     |   2 +-
 src/frob/gates/__init__.py | 659 +------------------------------------------
 src/frob/gates/_sys.py     | 690 +++++++++++++++++++++++++++++++++++++++++++++
 tests/test_gates.py        |  10 +-
 tickets.md                 |  16 +-
 5 files changed, 718 insertions(+), 659 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestSysGate::test_noop_no_design_dir` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSysGate::test_sys001_dangling` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_selfconform_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 672 warning(s), 679 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1188 -->
```yaml
id: T-1188
title: 'arch: split remaining ~7 gate families out of src/frob/gates/__init__.py (7309
  lines) -- T-1187 residue'
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
T-1187 extracted ONE more cohesive family (SYS00x/DOC003/SELFAUDIT001 --
sys_gate plus its private helpers) into src/frob/gates/_sys.py
(gates/__init__.py 7960 -> 7309 lines), continuing the
T-1072/T-1140/T-1159/T-1170/T-1174/T-1183/T-1187 one-family-per-land
discipline. Budget did not allow the other ~7 remaining families this
ticket's own body named. gates/__init__.py is still 7309 lines, well
above the large-file threshold.

Still remaining, in the same one-family-per-land shape:
- INV00x (inv006_gate + helpers, inv003_gate/inv004_gate/invariant_gate)
- TEST00x (test policy loading + TEST00x gate family)
- REL00x (release-bump/debt gate wiring)
- PERF (perf gate wiring, distinct from frob.perf's own module)
- COV00x (coverage gate family)
- SCOPE/PREWORK (scope_gate, prework_gate)
- the run_gates spine itself (_assemble_gate_report, _build_jobs,
  run_gates) -- likely stays in __init__.py as the module's own
  orchestration root, but worth an explicit decision at design time

Re-filed (not re-derived from scratch) rather than letting T-1187 close
with silent residue, per TICK011.
