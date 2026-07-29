# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

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

<!-- ticket:T-1189 -->
```yaml
id: T-1189
title: 'arch: split _land_merge.py/_land_finalize.py further -- T-1186 residue'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_land_finalize.py
threat: null
component: null
```
## Description

T-1186 split src/frob/tickets/_land.py (4973 lines) into
_land.py/_land_merge.py/_land_verify.py/_land_finalize.py. _land_merge.py
(~1720 lines) and _land_finalize.py (~1730 lines) still individually
exceed LARGE001's 800-line threshold -- T-1186's own note anticipated
this ("likely its own multi-land series ... consider splitting the plan
into 2-3 tickets"), and budget only allowed the first cut in that land.

## Plan

Split _land_merge.py further along its own natural seams (e.g. the
union-zone conflict-resolution family vs the ledger-merge/newest-wins
family vs the wip-commit family), and _land_finalize.py similarly (e.g.
draft-finalization/sibling-renumbering vs squash-apply/close vs the
release-bump/uv.lock/native-rebuild family), following the same verbatim-
move pattern (zero caller-visible behavior change, frob:ticket/frob:tests
directives carried verbatim, watch for tests monkeypatching a moved
function via the module attribute directly -- T-1186's Done report has
the exact per-site verification recipe that caught this).

<!-- ticket:T-1190 -->
```yaml
id: T-1190
title: 'test: fix 5 unwaived TEST003/TEST014 findings found in T-0204 verification
  close'
state: in-progress
kind: bug
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tomlio.py
- strata-core/src/parse/**
- src/frob/perf/_sampler.py
- src/frob/serve/_events.py
- src/frob/serve/_watch.py
threat: null
component: null
```
T-0204 verification close (2026-07-29) found gate:TEST is NOT honestly at
zero unwaived right now, despite T-0875's burn-down: 5 unwaived findings
exist (a 6th, TEST006 no-coverage-stamp, is an ordinary worktree artifact
of not having run `make coverage` here, not real debt):

- TEST003 src/frob/tomlio.py -- 0 integration test(s), below
  min_integration=1.
- TEST003 strata-core/src/parse -- 0 integration test(s), below
  min_integration=1.
- TEST014 src/frob/perf/_sampler.py::StackSampler.stop and
  src/frob/serve/_events.py::CoverageWatcher.stop share leaf name 'stop',
  both credited to the same convention-matched test -- ambiguous credit.
- TEST014 src/frob/perf/_sampler.py::StackSampler.stop and
  src/frob/serve/_watch.py::WatchThread.stop, same ambiguity.
- TEST014 src/frob/serve/_events.py::CoverageWatcher.stop and
  src/frob/serve/_watch.py::WatchThread.stop, same ambiguity.

These are new since T-0875 (not present in its own closing measurement)
-- new modules (tomlio, strata-core/parse, the perf/serve stop-method
trio) added afterward never got their own `frob:tests` edges. Add each
missing integration test (or a reasoned `frob:waive TEST003`), and
disambiguate the three TEST014 `stop` collisions with explicit
`frob:tests ... kind="unit"` edges naming which test actually exercises
each `.stop`, then re-verify `frob check --only gates-fast` shows 0
unwaived TEST findings again (TEST006 aside, which only ever clears via
`make coverage` at land, never in a worktree).
<!-- ticket:T-1191 -->
```yaml
id: T-1191
title: 'perf: fix 4 unwaived PERF005/PERF008 findings found in T-0204 verification
  close'
state: queued
kind: bug
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_taint.py
- src/frob/arch/_ffi.py
- src/frob/serve/_watch.py
- tests/test_serve_watch.py
threat: null
component: null
```
T-0204 verification close (2026-07-29) found gate:PERF is NOT honestly at
zero unwaived right now, despite T-1041's residue burn-down: 4 unwaived
findings exist on current main-plus-this-branch:

- PERF005 src/frob/vet/_taint.py:134 -- recursive call to
  `_assigned_names` with no provable termination measure.
- PERF008 src/frob/arch/_ffi.py:298 -- `pat.search(...)` inside a loop
  with loop-invariant arguments (reaches `frob.excludes.walk_pruned`, a
  fs-walk effect).
- PERF008 src/frob/serve/_watch.py:169 -- `watch_tick(...)` inside a loop
  with loop-invariant arguments (reaches
  `frob.process._guard.guarded_subprocess_run`, a spawn effect).
- PERF008 tests/test_serve_watch.py:86 -- `_warm._repo_dirty_key(...)`
  inside a loop with loop-invariant arguments (same spawn-effect chain).

These are new since T-1041 (not present in its own closing measurement)
-- either real code added afterward introduced them, or they are newly
detected by a PERF008 rule refinement. Either way this is live,
unwaived PERF debt today: fix each site (add a termination measure, or
hoist/memoize the loop-invariant call) or add a reasoned
`frob:waive PERF005`/`frob:waive PERF008` per site, then re-verify
`frob check --only gates-native` shows 0 unwaived PERF findings again.

<!-- ticket:T-1192 -->
```yaml
id: T-1192
title: 'arch: large-file residue after T-1074/T-1186/T-1187 splits (34 unowned LARGE001
  findings)'
state: queued
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
threat: null
component: null
```
T-0395 verification close (2026-07-29) re-measured LARGE001 (`frob check
--only archgate`, calibrated 800-line threshold) and found this genuinely
unowned residue after excluding: native crates (frob-core/src/lib.rs,
strata-core/src/lib.rs, strata-core/src/parse/mod.rs -- separate
toolchain/ownership per the T-1074 precedent), the two currently-live
split tickets (T-1188 owns src/frob/gates/__init__.py, T-1189 owns
src/frob/tickets/_land_merge.py + _land_finalize.py), and the 7 files
T-1074 already recorded an explicit accepted-with-reason disposition for
(src/frob/arch/_rust.py, src/frob/dup/_pipeline/_fingerprint.py,
src/frob/graph/__init__.py, src/frob/graph/callgraph.py,
src/frob/graph/dsl.py, src/frob/perf/_effect_summaries.py,
src/frob/perf/_rules.py).

Remaining genuinely unowned LARGE001 findings (current line counts):
- src/frob/_cli_parsers/_ticket.py (1102)
- src/frob/app/check_runner.py (1597)
- src/frob/app/config.py (1167)
- src/frob/app/sys_runner.py (1023)
- src/frob/app/ticket_runner/_land_cmd.py (907)
- src/frob/app/ticket_runner/_verify.py (973)
- src/frob/arch/_patterns.py (1486)
- src/frob/arch/_python.py (1635)
- src/frob/check/__init__.py (953)
- src/frob/check/_python.py (977)
- src/frob/doctor.py (918)
- src/frob/gates/_docblocks.py (1465)
- src/frob/gates/_docptr.py (1000)
- src/frob/gates/_protocol_summary.py (1244)
- src/frob/gates/_registry_exhaustiveness.py (988)
- src/frob/gates/_secrets.py (1088)
- src/frob/gates/_tickets_gate.py (953)
- src/frob/gates/_waive.py (1424)
- src/frob/strata/__init__.py (941)
- src/frob/strata/_audit.py (1055)
- src/frob/strata/_compliance.py (1058)
- src/frob/strata/_elaborate.py (1401)
- src/frob/strata/_host_isolation.py (1281)
- src/frob/strata/_infra.py (837)
- src/frob/strata/_mode_conformance.py (867)
- src/frob/strata/_selfconform.py (1621)
- src/frob/strata/_threat.py (2485)
- src/frob/tickets/_evidence.py (1201) -- its prior owner T-1171 is done;
  the exclusion no longer applies.
- src/frob/tickets/_land.py (1178) -- T-1186's own split left this file
  itself still over threshold; not in T-1189's scope (which covers only
  the two NEW files T-1186 produced), so it is unowned residue too.
- src/frob/tickets/_leases.py (1339)
- src/frob/tickets/_models.py (1873)
- src/frob/tickets/_new_renumber.py (840)
- src/frob/vet/_capability.py (5944) -- T-1074 explicitly flagged this
  and the next file as needing a dedicated follow-up but did not file
  one ("budget did not allow investigating a safe split boundary for
  either") -- filing it now.
- src/frob/vet/_capability_registry.py (2918)
- src/frob/vet/_scan.py (901)

LARGE001 is a warning-tier, unwaivable advisory (per docs/modules/
gates.md) -- none of this blocks a gate today, but per T-0395/T-1074's
own framing it needs real splits or a recorded per-file accepted-with-
reason disposition, triaged in groups (one subsystem per land, full
verification per group), not one giant diff. Same discipline as
T-1072/T-1074/T-1186/T-1187/T-1188/T-1189: pick a cohesive subsystem
slice, split it, re-measure, re-file remaining residue rather than
closing silently.

<!-- ticket:T-1193 -->
```yaml
id: T-1193
title: 'post-audit residual themes: multi-language obligation gates, fail-open residue,
  gitignored-trust CI story (T-0397 successor)'
state: queued
kind: security
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- docs/design/registry/check-coverage.yaml
- docs/**
acceptance:
- text: GIVEN the six audit-concern rows this ticket tracks (python-only COV/DOC/DRIFT
    enforcement, fail-open residue incl second-lockfile and non-UTF-8 docs, gitignored
    .frob/ trust vs CI, DRIFT001 sig-facet body-blindness, non-python frob:tests execution,
    load_graph new-file snapshot completeness) WHEN each is either enforced by a real
    gate or re-dispositioned with evidence THEN the registry rows move from deferred
    to handled_by and this ticket closes
  evidence: []
threat: null
component: null
```
Successor to the T-0397 audit epic for the concern-family rows NOT yet closed by a landed mechanism (each row's residue verified at epic close 2026-07-29): CHK-THEME-PYTHON-ONLY (partial: arch multi-lang and capability tables landed; COV/DOC/DRIFT edges still python-pipeline-only), CHK-THEME-FAIL-OPEN (partial: PARSE001/002, NATIVE001, tool-unavailable ToolResults landed; second-lockfile scan and non-UTF-8 doc handling unverified), CHK-THEME-GITIGNORED-TRUST (open: coverage/stamp/baseline live gitignored, CI cannot verify), CHK-SUBSYS-GATES-ACCOUNTING (partial: collectors exist for rust/ts/cpp; DRIFT001 sig facet still body-blind), CHK-SUBSYS-LANG-CHECK-DOCS (same python-only class), CHK-SUBSYS-GRAPH-EDGES (unverified: load_graph new-file snapshot completeness, non-UTF-8 md crash).
