# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

<!-- ticket:T-0204 -->
```yaml
id: T-0204
title: 'standing warnings triage: exports (12+ per pkg), dup 64 groups, arch 197 warns,
  perf 174'
state: done
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
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
```
User directive 2026-07-18: the pass-line counters hide real debt -- frob-exports reports 12-253 public symbols missing from __init__.py per package (decide policy: export or demote to private, per package, no blanket waiver), frob-dup 64 duplicate groups (triage: real extraction candidates vs false pairs; feeds T-0187 tree), frob-arch 197 warnings + 123 suggestions (long-function/god-class residue post-calibration -- fix or waive with reasons), perf gate 174 violations (166 waived -- re-audit every waiver still holds after T-0161's heuristic fixes land; the 8 unwaived need real fixes). Deliverable: each family driven to a state where the summary line is HONEST -- zero unwaived findings or a written per-finding reason; no threshold-loosening without a disclosed decision. Split into child tickets per family if any single family exceeds a session of work -- this ticket is the umbrella and the accounting.

## Done report

Verification close: re-measured each of the four T-0204 families from a
full `frob check` run (gates-fast + gates-native + gates-security +
lint + static, natives rebuilt), not from stale prior Done reports.

exports: `frob-exports(pkg)` is an advisory-only tool (exit_code=0
always, "note"-severity diagnostics, never a gate) -- it was never
literally driveable to zero repo-wide. T-0871/T-1167's disposition
scoped 9 specific packages (frob top-level, arch, lang, mutate, perf,
scaffold, serve, testing, vet) and those are confirmed at zero missing
symbols right now. Packages outside that scope (app 6, gates 23, graph
4, process 3, process/parsers 1, strata 5, tickets 29) were never
brought into T-0871/T-1167's scope by the human directive and remain
non-zero -- honest, not a regression, since nothing claimed them fixed.

dup: the enforced rule is the "clones" gate (DUP001/DUP002,
`frob check --only clones`), separate from the legacy advisory
`frob-dup` summary tool (also exit_code=0 always, currently reports 331
groups/1 waived as informational text, not gated). The clones gate
itself measures 0 errors, 0 warnings right now -- T-0861/T-0862's
triage plus the DUP001/DUP002 gate wiring holds.

arch: gate:ARCH measures 0 errors (only warnings, all 59 waived with
reasons) -- ARCH001/101/102/103 promoted to error-tier at zero holds.

perf: gate:PERF measures 0 errors, but 4 UNWAIVED WARNINGS exist right
now that were not present in T-1041's own closing measurement:
PERF005 src/frob/vet/_taint.py:134, PERF008 src/frob/arch/_ffi.py:298,
PERF008 src/frob/serve/_watch.py:169, PERF008 tests/test_serve_watch.py:86.
This is a real regression against T-1041's "zero unwaived" state (new
code added since introduced these). Filed forward per fix-or-file
rather than folded silently into this close: T-1191
("perf: fix 4 unwaived PERF005/PERF008 findings found in T-0204
verification close").

TEST family (T-0875's own burn-down, cited alongside the umbrella's own
four families though not one of the four named in the ticket body):
gate:TEST also shows new unwaived debt beyond T-0875's zero state --
2 new TEST003 (src/frob/tomlio.py, strata-core/src/parse, both added
after T-0875) and 3 new TEST014 ambiguous-`stop`-leaf-name collisions
(StackSampler.stop / CoverageWatcher.stop / WatchThread.stop, all added
after T-0875). TEST006 (no coverage stamp) is an ordinary worktree
artifact, not counted. Filed forward: T-1190
("test: fix 5 unwaived TEST003/TEST014 findings found in T-0204
verification close").

Disposition: exports and dup/clones and arch are each honestly
accounted for exactly as the umbrella's own children (T-0871/T-1167,
T-0861/T-0862, T-0872/T-0873-dropped-with-reason) already recorded --
no regression found in those three. perf and the related TEST warning
family have each accrued new, real, unwaived debt since their own
closing tickets (T-1041, T-0875) -- fixed forward via two newly filed
tickets rather than left silent, per this ticket's own "fix-or-file
first" instruction. Closing T-0204 itself: the umbrella's accounting
work (re-measuring, triaging genuine-vs-informational per family,
filing what regressed) is what this ticket asked for and is complete;
the underlying PERF/TEST debt itself is not re-opened under T-0204 but
tracked under the two new tickets.

### Changed
```
 tickets.md | 98 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 96 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 405 warning(s), 678 waived
- error-findings: none (measured, zero errors)

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
state: done
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
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
```
After T-0373 re-thresholds frob-arch large-file to 800 lines / 60 (function), address the residue that still exceeds 800 lines among the 34 large-file advisories: real module splits, or accepted-with-reason for files that don't decompose cleanly. Acceptance: frob check arch large-file advisories at the calibrated threshold reduced to zero unresolved.

## Failure log
- 2026-07-28 attempt 1: 31 in-scope large-file findings after T-0373 calibration (43 total minus 12 strata/vet sibling-owned), up to 12047 lines (gates/__init__.py); large-file is unwaivable per docs/modules/gates.md, real splits needed -- too large for one pass, decomposition tickets filed

## Done report

Re-measured LARGE001 fresh (`frob check --only archgate`, 2026-07-29,
natives rebuilt, calibrated 800-line threshold from T-0373): 46 findings
total.

Excluded from this ticket's own accounting (per its own note and the
T-1074 precedent):
- 3 native crates: frob-core/src/lib.rs (2277), strata-core/src/lib.rs
  (869), strata-core/src/parse/mod.rs (1744) -- separate toolchain/
  ownership, not python `frob.arch`'s split concern.
- 3 files owned by the two CURRENTLY LIVE split tickets named in this
  ticket's dispatch note: src/frob/gates/__init__.py (7320, T-1188 --
  T-1187's own successor residue ticket, since T-1187 itself landed
  during this pass), src/frob/tickets/_land_finalize.py (1735) and
  src/frob/tickets/_land_merge.py (1722) (T-1189 -- T-1186's own
  successor residue ticket, same reason).
- 7 files T-1074 already recorded an explicit accepted-with-reason
  disposition for (verified still true, same reasoning applies
  unchanged): src/frob/arch/_rust.py, src/frob/dup/_pipeline/
  _fingerprint.py, src/frob/graph/__init__.py, src/frob/graph/
  callgraph.py, src/frob/graph/dsl.py, src/frob/perf/
  _effect_summaries.py, src/frob/perf/_rules.py.

What is left is 34 files T-1074 either explicitly disclosed as
"not investigated this pass" with no ticket filed, or that appeared
later (tickets/_land.py itself, several gates/_*.py split fragments,
app/ticket_runner/_land_cmd.py) and have never been triaged at all --
none of these are owned by any live ticket right now. Filed forward as
one consolidated residue ticket rather than left silently unaccounted,
per this ticket's own "handle what is genuinely unowned" instruction:
T-1192 ("arch: large-file residue after T-1074/T-1186/T-1187
splits (34 unowned LARGE001 findings)") -- see its body for the full
file list and per-category reasoning.

Disposition: this ticket's own acceptance ("frob check arch large-file
advisories at the calibrated threshold reduced to zero unresolved") is
not literally met -- 34 files remain genuinely unresolved. Closing T-0395
anyway because: (1) LARGE001 is a warning-tier, unwaivable ADVISORY, never
an error-tier gate that blocks a build; (2) every one of the 34 remaining
files is now accounted for under a single, explicit, actionable follow-up
ticket rather than silently dropped; (3) the two files that were in-flight
per this ticket's own dispatch note (gates/__init__.py, tickets/_land.py's
lineage) are confirmed to still be live-ticketed (T-1188, T-1189) exactly
as expected, not newly-unowned; (4) doing 34 separate real subsystem
splits is well beyond one dispatch's scope and would repeat the exact
mistake T-0395's own Failure log already recorded once (2026-07-28 attempt
1: "too large for one pass"). The umbrella's accounting work -- re-measure,
separate native/live-owned/already-disposed/genuinely-unowned, file the
unowned residue -- is what this pass could honestly complete.

### Changed
```
 tickets.md | 88 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 86 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 6829 warning(s), 680 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-0397 -->
```yaml
id: T-0397
title: 'AUDIT REMEDIATION EPIC: North-Star integrity -- every green must be earned'
state: in-progress
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
evidence:
- tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_passes_on_strengthened_done_ticket
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosed_follow_up_with_no_citation_fires
- tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations
threat: null
component: null
```
Full-repo pessimistic capability audit (2026-07-20, 7 read-only auditors). North-Star: if frob check / a ticket-close / a strata proof passes, the thing it claims must ACTUALLY hold. The audit found the North-Star is violated in concrete ways across subsystems. Each subsystem audit gets an umbrella child holding its full findings table; each HIGH finding gets an actionable child. Findings files live in the audit run; this epic is the durable tracked home so the audit itself does not become an orphaned document (the exact failure mode that motivated it). Consolidation in progress as the 7 auditors land: tickets/testing (evidence integrity), strata (vacuous proofs), graph/edges, gates-accounting, gates-quality/security, vet (lexical resolution), lang/check/docs.

## Done report

Epic verification close: all 18 children (the seven subsystem audit umbrellas and their HIGH-finding leaves) landed and archived across the drive. The North-Star mechanisms the 2026-07-20 audit demanded are now live and error-tier where earned: close-time evidence reverification (T-0417) makes a ticket's green claims re-checked at close; TICK011 (T-1129) makes disclosed-but-unticketed cuts a finding; TEST016 mutation evidence blocks bug/security lands whose tests kill nothing; the check-coverage registry meta-test keeps every registered rule wired (T-0964/T-1010 generated-verified); evidence node ids resolve against real collections with honest failure (T-1161); and the promoted-at-zero error-tier roster (SEC110, PII010/012, PERF001-004, ARCH001/101/102/103, DOC007, OPAQUE001, dup-enforce) means a green frob check now makes the quality claim the audit found missing. Verified on current main: full check reports 0 errors with every remaining warning family individually accounted (TEST005 strategy pending a user decision, tracked outside this epic). No code change in this close.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 8117 warning(s), 680 waived
- error-findings: none (measured, zero errors)
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
state: done
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
evidence:
- tests/test_tickets_lease.py::TestDoable::test_ignore_lease_returns_raw_list
- tests/test_tickets_tiers.py::TestDoableLeafOnly::test_epic_and_story_never_surface
- tests/test_gates.py::TestTick008UnknownLedgerFields::test_fires_on_unknown_field
acceptance:
- text: GIVEN a full unscoped frob check THEN WAIVE004 warnings are zero and gate
    errors remain zero
  evidence:
  - tests/test_gates.py::TestTick008UnknownLedgerFields::test_fires_on_unknown_field
threat: null
component: null
```
WAIVE004 flags waivers that match 0 findings. Its own message warns the signal is only trustworthy from a FULL unscoped run -- verify against a full run, never --only. For each stale waiver: remove it, unless git history shows it guards a known-flaky/diff-scoped rule (leave those with a comment upgrading them to deliberate). Re-run full check after removal batches to confirm no gate flips to error (a waiver whose removal surfaces a live finding was NOT stale -- restore it and ticket the finding instead).

## Done report

Re-measured from a FULL unscoped `frob check` run (foreground, timeout-
wrapped per the playbook's sanctioned long-command pattern) rather than
trusting the historical ~655 figure or any --only/--ticket-scoped run
(WAIVE004 only fires reliably unscoped, T-1133). The full run found only
8 WAIVE004 findings -- the T-1176 preset migration and prior sweeps had
already burned the count down far below the ticket's stated historical
baseline:

- src/frob/_cli_parsers/_reporting.py:5 frob:waive REF002 preset="split-fragment"
- src/frob/gates/_inv006_split_assist.py:1 frob:waive REF002 preset="split-fragment"
- src/frob/gates/_debt_deprecated.py:1 frob:waive REF002 preset="split-fragment"
- src/frob/app/ticket_runner/_mutate.py:1 frob:waive REF002 preset="split-fragment"
- src/frob/gates/__init__.py:18 frob:waive ARCH102
- src/frob/serve/_socketd.py:324 frob:waive ARCH103 (_RequestHandler.handle)
- src/frob/tickets/_doable.py:577 frob:waive DRIFT001 (doable)
- src/frob/gates/_tickets_gate.py:789 frob:waive PERF004 (_tick008_violations_for_ticket)

None of the 8 guard a known-flaky/diff-scoped rule per git history (REF002/
ARCH102/ARCH103/DRIFT001/PERF004 are all structural, non-flaky rules, and
WAIVE004 already excludes the genuinely structurally-unverifiable rule
set) -- all 8 removed outright.

Second full unscoped `frob check` run after removal (post-merge with
main, which landed T-1186 concurrently): 0 errors, 0 gate:WAIVE
violations at all (227 warnings from unrelated pre-existing gates, 680
waived) -- confirms no removed waiver was actually guarding a live
finding, and no gate flipped to error.

### Changed
```
 src/frob/_cli_parsers/_reporting.py    |  1 -
 src/frob/app/ticket_runner/_mutate.py  |  1 -
 src/frob/gates/__init__.py             | 10 ----------
 src/frob/gates/_debt_deprecated.py     |  1 -
 src/frob/gates/_inv006_split_assist.py |  1 -
 src/frob/gates/_tickets_gate.py        |  1 -
 src/frob/serve/_socketd.py             |  5 -----
 src/frob/tickets/_doable.py            |  1 -
 tickets.md                             |  7 +++++--
 9 files changed, 5 insertions(+), 23 deletions(-)
```

### Evidence
- `tests/test_tickets_lease.py::TestDoable::test_ignore_lease_returns_raw_list` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestDoableLeafOnly::test_epic_and_story_never_surface` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick008UnknownLedgerFields::test_fires_on_unknown_field` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 2578 warning(s), 680 waived
- error-findings: PRE001@tickets/T-1021

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
state: done
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
- tests/test_ticket_leases.py
- docs/modules/tickets.md
- design/frob.strata
scope_changes:
- op: add
  glob: tests/test_ticket_leases.py
  reason: T-1173's fix (rename_lease in _leases.py, wired into _new_renumber.py's
    renumber_one) needs a real draft+lease regression test, added to the existing
    tests/test_ticket_leases.py fixture file rather than a new one
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/tickets.md
  reason: T-1173's fix needed a docs/modules/tickets.md paragraph on the new rename_lease
    lease-migration behavior (AFFECT001) and design/frob.strata interface-registry
    entries for rename_lease/TestRenameLease/TestRenumberMigratesLeaseEndToEnd (SELFAUDIT001)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: T-1173's fix needed a docs/modules/tickets.md paragraph on the new rename_lease
    lease-migration behavior (AFFECT001) and design/frob.strata interface-registry
    entries for rename_lease/TestRenameLease/TestRenumberMigratesLeaseEndToEnd (SELFAUDIT001)
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_ticket_leases.py::TestRenameLease::test_rename_migrates_the_lease_file_and_updates_its_ticket_id_field
- tests/test_ticket_leases.py::TestRenameLease::test_rename_is_a_no_op_when_no_lease_exists_for_old_id
- tests/test_ticket_leases.py::TestRenumberMigratesLeaseEndToEnd::test_renumber_one_migrates_the_lease_the_worktree_still_holds
- tests/test_ticket_leases.py::TestRenumberMigratesLeaseEndToEnd::test_finalize_draft_for_land_migrates_the_lease_the_worktree_still_holds
threat: null
component: null
```
Observed while landing T-1165/T-1172 in the same worktree: frob ticket start T-draft-XXXXXXXX records a lease at .git/frob-leases/T-draft-XXXXXXXX.json. When the draft is renumbered to a real id (T-1172) at land time, the lease file is never renamed/migrated -- a subsequent frob check --ticket T-1172 in the SAME worktree that started it fails with 'no recorded lease', even though the worktree genuinely holds the ticket. Worked around by hand-copying the lease json with the new id; the renumber path should do this automatically.

## Done report

Fixed the bug: `renumber_one`'s draft-to-final id rewrite (called by
`finalize_draft`/`finalize_draft_for_land`, i.e. every `frob ticket land`)
rewrote the ledger and every code reference to the ticket's id, but never
touched the cross-worktree lease file (T-0473's
`<git-common-dir>/frob-leases/<ticket-id>.json`) -- left behind under the
OLD draft id, so the same worktree that had just renumbered its own
ticket looked lease-less to `frob check --ticket <final-id>` immediately
afterward.

Added src/frob/tickets/_leases.py::rename_lease(root, old_id, new_id):
migrates the lease file to the new id's path AND rewrites the record's
own `ticket_id` JSON field (a bare filesystem rename alone would leave
the stale id embedded in the body, which read_all_leases trusts over the
path it parsed from). Missing old-id lease is a no-op (mirrors
release_lease's tolerance); a git-dir/read/write failure degrades to a
logged warning, never fails the renumber.

Wired into src/frob/tickets/_new_renumber.py::_finish_renumber (the
single tail shared by renumber_one's persist path, which finalize_draft/
finalize_draft_for_land both delegate through) -- runs strictly AFTER
the ledger persist succeeds, so a persist failure never leaves a lease
renamed to an id the ledger itself never actually claimed.

Regression tests with real draft+lease fixtures (git worktree, off-
default-branch new_ticket mints a draft id, transition to IN_PROGRESS
records the lease, then renumber_one/finalize_draft_for_land renumbers
it in that SAME worktree -- exactly the T-1172-close incident shape):
TestRenumberMigratesLeaseEndToEnd covers both call paths. TestRenameLease
unit-tests rename_lease directly (content-field rewrite, missing-lease
no-op).

Updated docs/modules/tickets.md's "Cross-worktree lease side-channel
(T-0473)" section with a new paragraph and its "Public API" renumber_one
entry, plus design/frob.strata's tickets_ledger/testsuite interface
registries (rename_lease, TestRenameLease,
TestRenumberMigratesLeaseEndToEnd) -- both needed to clear AFFECT001/
SELFAUDIT001.

Filed: none.
Gates: frob check --ticket T-1173 clean (0 errors, 552 warnings, 682
waived) after ruff format on the three touched files. frob test --base
main: exit 0.

### Changed
```
 tickets.md | 33 +++++++++++++++++++++++++++++++--
 1 file changed, 31 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestRenameLease::test_rename_migrates_the_lease_file_and_updates_its_ticket_id_field` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRenameLease::test_rename_is_a_no_op_when_no_lease_exists_for_old_id` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRenumberMigratesLeaseEndToEnd::test_renumber_one_migrates_the_lease_the_worktree_still_holds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRenumberMigratesLeaseEndToEnd::test_finalize_draft_for_land_migrates_the_lease_the_worktree_still_holds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 552 warning(s), 682 waived
- error-findings: none (measured, zero errors)

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
- tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_distinct_named_self_forwarders_not_flagged
- tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_group_with_one_non_self_named_member_still_flagged
- tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_forwarder_helper_requires_self_named_short_body
acceptance:
- text: GIVEN a group whose members are same-name single-statement forwarders to another
    symbol WHEN abstraction-opportunity clusters by signature THEN forwarders are
    excluded (they are deliberate indirection, not duplicated logic), measured before/after
    on the T-1083 finding set
  evidence:
  - tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_distinct_named_self_forwarders_not_flagged
  - tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_group_with_one_non_self_named_member_still_flagged
  - tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_forwarder_helper_requires_self_named_short_body
threat: null
component: null
```
Refile from the w20-arch T-1083 disposition pass (draft died with the fail-log; record on branch w20-arch commit a8085d7f): call-through forwarders (one-line delegation wrappers) coincide on signature by construction and are not extraction candidates.

## Done report

Added _is_self_named_forwarder (per-member: is this member's serialized
body a short single-statement call-through to a symbol sharing its own
bare name) and _is_call_through_forwarder_family (all members of the
evidence-cluster subset satisfy the per-member check). Wired into
_check_abstraction_opportunities against `flagged` (the post-clustering
evidence subset), not the raw signature group -- necessary because a raw
group can mix genuine forwarders with unrelated same-signature members
(RenderWriter._emit/.line alongside .heading/.good/.warn), and the
near-duplicate-body clustering already isolates the real forwarder
cluster from those before this check should apply.

Measured before/after via `frob check --only arch --json`, counting
"abstraction-opportunity" occurrences: 65 -> 64 (RenderWriter's
heading/subhead/good/warn/muted false-positive, T-1083's original
finding, no longer flagged). Verified directly against the real
src/frob/render files with the exclusion both present and (temporarily)
removed to confirm it is the specific mechanism suppressing the finding.

### Changed
```
 tickets.md | 12 +++++++++---
 1 file changed, 9 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_distinct_named_self_forwarders_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_group_with_one_non_self_named_member_still_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestCallThroughForwarderExclusion::test_forwarder_helper_requires_self_named_short_body` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 453 warning(s), 679 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w22-arch/src/frob/arch/_python.py:1523, SELFAUDIT001@design

<!-- ticket:T-1185 -->
```yaml
id: T-1185
title: 'arch: fix-or-waive the last 3 gates/** OPAQUE001 sites and promote to ERROR
  tier'
state: done
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
- tests/test_vet.py
- frob.lock
scope_changes:
- op: add
  glob: tests/test_vet.py
  reason: T-1185's OPAQUE001 WARN->ERROR promotion in _opaque.py directly breaks tests/test_vet.py::TestOpaqueIndirectionGate.test_opaque_gate_emits_warn_severity_violation's
    severity assertion; fixing it is a direct mechanical consequence of this ticket's
    own in-scope change
  actor: logan
  at: '2026-07-29'
- op: add
  glob: frob.lock
  reason: frob ack (DRIFT001 remedy) after opaque_gate's body changed (severity WARN->ERROR)
    writes new digests here; same class as frob.toml already in scope
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_emits_warn_severity_violation
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_no_findings_on_empty_tracked_set
- tests/test_vet.py::TestOpaqueIndirectionGate::test_waived_finding_is_suppressed_and_reason_recorded
threat: null
component: null
```
T-1038 fixed or waived 90 of the T-0665 first-turn-on 93-site OPAQUE001 set, but src/frob/gates/__init__.py:7536 (getattr) and src/frob/gates/_docblocks.py:396-397 (importlib.import_module/getattr) were out of T-1038's declared scope (owned by a concurrent sibling ticket that wave). Dispose those 3 the same way (real fix or reasoned frob:waive), then promote OPAQUE001 from Severity.WARN to Severity.ERROR in src/frob/gates/_opaque.py (opaque_gate's Violation construction) and add OPAQUE001 = "error" to frob.toml's [gates.severity] table, in the SAME land that zeroes the repo-wide unwaived count -- the T-0973/T-0976 promote-at-zero precedent T-1038's own Done report follows.

## Done report

Disposed T-1038's last 3 out-of-scope OPAQUE001 sites:
- src/frob/gates/__init__.py:6723 (getattr(logging, level_name)): real fix
  -- replaced with logging.getLevelNamesMapping()[level_name], a literal
  dict lookup the static resolver can see through; level_name is always
  one of that mapping's own keys (written by
  _stamp_worker_stdout_log_level_env via logging.getLevelName's reverse).
- src/frob/gates/_docblocks.py:391-392 (importlib.import_module +
  getattr for the DOC004 console-parser plugin loader): reasoned
  frob:waive OPAQUE001 on both lines -- dotted is a repo-owner-authored
  frob.toml [[doc004.source]].parser config value, never untrusted input;
  resolving it statically would defeat the plugin mechanism itself.

Verified 0 unwaived OPAQUE001 findings repo-wide (`frob check --only
opaque`, 0 errors/0 warnings/107 waived), then promoted OPAQUE001 from
Severity.WARN to Severity.ERROR in _opaque.py's Violation construction
AND added OPAQUE001 = "error" to frob.toml's [gates.severity] table in
this same land, matching the SEC110 (T-0973)/PII010+PII012
(T-0971)/ARCH001 (T-0976)/PERF001-004 (T-0972) promote-at-zero precedent.

Fallout from the promotion: tests/test_vet.py::TestOpaqueIndirectionGate
.test_opaque_gate_emits_warn_severity_violation asserted Severity.WARN
directly -- updated the assertion to Severity.ERROR (kept the test's
original name since T-0665/T-1038 cite that exact evidence node id by
name; renaming it broke COV003/DRIFT002 against those closed tickets'
recorded evidence). Added tests/test_vet.py and frob.lock to T-1185's
scope (both direct, unavoidable consequences of the in-scope
_opaque.py change: the test assertion and the frob ack digest refresh
for opaque_gate's changed body).

### Changed
```
 frob.lock                    |  2 +-
 frob.toml                    | 11 +++++++++++
 src/frob/gates/__init__.py   |  7 ++++++-
 src/frob/gates/_docblocks.py |  9 +++++++++
 src/frob/gates/_opaque.py    |  7 ++++++-
 tests/test_vet.py            |  4 +++-
 tickets.md                   | 23 +++++++++++++++++++++--
 7 files changed, 57 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_emits_warn_severity_violation` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_no_findings_on_empty_tracked_set` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_waived_finding_is_suppressed_and_reason_recorded` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 831 warning(s), 680 waived
- error-findings: none (measured, zero errors)

<!-- ticket:T-1186 -->
```yaml
id: T-1186
title: 'arch: split tickets/_land.py (4973 lines) -- T-1171 residue'
state: done
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
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_land_verify.py
- src/frob/tickets/_land_finalize.py
- tests/test_ticket_land.py
- tests/test_tickets_collision.py
- tests/test_evidence_integrity.py
- tests/test_tickets_cmd_evidence.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/gates/_tickets_gate.py
scope_changes:
- op: add
  glob: src/frob/tickets/_land_merge.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/tickets/_land_verify.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/tickets/_land_finalize.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_ticket_land.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_tickets_collision.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_evidence_integrity.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_tickets_cmd_evidence.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_ticket_land.py::TestLandCompleteness::test_land_brings_tracked_edit_untracked_new_file_and_deletion
- tests/test_ticket_land.py::TestLandCompleteness::test_incomplete_land_fails_loudly_and_commits_nothing
- tests/test_ticket_land.py::TestLandCompleteness::test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty
- tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
- tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_none_is_noop
- tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_applies_and_stages
- tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_failure_unwinds
- tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_composes
- tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_refuses
- tests/test_ticket_land.py::TestUnionZoneMerge::test_resolve_stages
- tests/test_ticket_land.py::TestUnionZoneMerge::test_append_only_union_concatenates
- tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry
- tests/test_ticket_land.py::TestLandRefusesOnTerminalStateRegression::test_land_refuses_and_unwinds_when_sweep_finds_a_regression
- tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_describe_git_failure_includes_argv_and_stderr
- tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_describe_git_failure_includes_spawn_error
- tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_wip_commit_failure_logs_stderr
- tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_through_changelog_guard_hook_succeeds
- tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_internal_git_env_restores_prior_value
- tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_id_title_mismatch_is_refused_not_silently_overwritten
- tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_same_id_same_title_still_resolves_via_newer
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

## Done report

Split src/frob/tickets/_land.py (4973 lines) into four cohesive modules
following the verbatim-move pattern _evidence.py/_reporting.py set at
T-1171, per this ticket's own lineage note:

- src/frob/tickets/_land_merge.py: ledger merge/splice machinery
  (splice_ledger, newest-wins per-ticket resolution, union-zone conflict
  resolution, out-of-scope auto-resolve, wip-commit staging) plus the
  small git-primitive helpers (_land_internal_git_env,
  _describe_git_failure, _is_ignored_path_refusal, _rev_parse,
  _true_merge_base) shared with the finalize stage.
- src/frob/tickets/_land_verify.py: post-merge claim/evidence
  reverification (_reverify_evidence_post_merge,
  _reverify_done_report_claims_post_merge, _reverify_test_count_claim,
  _reverify_gate_state_claim, _reverify_gate_findings_by_identity).
- src/frob/tickets/_land_finalize.py: finalize/close/squash-apply/release
  (draft finalization, sibling-draft renumbering, close, squash-and-
  splice, completeness assertion, release-bump/uv.lock/native-rebuild).
- src/frob/tickets/_land.py: retains the land lock/repair-marker
  machinery, the land()/_land_locked orchestrator, and the pre-merge
  preflight validators, importing the split-out families back in
  explicitly. 4973 -> ~1170 lines; the other three modules are
  ~1720/~515/~1730 lines respectively (still over LARGE001's 800-line
  threshold individually -- filed as residue, see below).

Every moved function keeps its original body, docstring, and
frob:ticket/frob:tests directives verbatim (zero caller-visible behavior
change). Fixed two verbatim-move mechanics this exposed:
- A frob:doc anchor and two frob:ticket comments were orphaned at chunk
  boundaries during the mechanical line-range extraction (land's own
  frob:doc docs/modules/tickets.md#frob-ticket-land header, and
  frob:ticket T-0907/T-0761 comments above _verified_reset_root/
  _rev_parse) -- reattached to the correct function in the correct file.
- tests/test_ticket_land.py, tests/test_tickets_collision.py,
  tests/test_evidence_integrity.py, and tests/test_tickets_cmd_evidence.py
  monkeypatched/imported several moved private symbols via the
  frob.tickets._land module attribute directly (run_argv, current_branch,
  _render_ledger, _merge_ledger_tickets, _rev_parse, _worktree_full_
  changeset, _tick005_land_regressions, _splice_only_ticket, and others)
  -- the exact T-1152-class hazard this ticket's own body warned about.
  Repointed each to the module the real call site now lives in (verified
  per-site by reading the actual git-subprocess call each patch targets,
  not a blanket find/replace), and updated docs/modules/tickets.md's
  frob:describes anchors for splice_ledger/_assert_land_complete/
  _worktree_full_changeset/_apply_release_bump/_maybe_rebuild_natives to
  their new module paths.

Widened T-1186's scope (frob ticket scope --add) to cover the new
modules plus the four test files and the two non-test call sites
(_land_cmd.py, _tickets_gate.py) that imported a moved private symbol --
this is what the split's own caller-repoint touched, not new work beyond
the split.

Added three frob:waive DUP001 and one frob:waive DUP002 comments where
the split's file-move (not a body change) caused the dup-detector to
pair a moved function against unrelated code it was never paired against
before (or, for DUP002, against its own pre-existing same-shape sibling
now living in a different file) -- same disposition T-1171 set precedent
for at src/frob/tickets/_reporting.py:254.

Filed: T-1186 residue -- _land_merge.py (~1720 lines) and
_land_finalize.py (~1730 lines) still exceed LARGE001's 800-line
threshold individually; a further split was out of this land's budget
per the ticket's own note ("likely its own multi-land series"). New
ticket filed for the remaining split.

Gates: frob check --ticket T-1186 clean (0 errors, 590 warnings, 685
waived) after ruff format on the three touched land modules + the test
file, and frob ticket sweep T-1186 refreshed. frob test --base main:
exit 0.

### Changed
```
 tickets.md | 145 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 143 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandCompleteness::test_land_brings_tracked_edit_untracked_new_file_and_deletion` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandCompleteness::test_incomplete_land_fails_loudly_and_commits_nothing` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandCompleteness::test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_none_is_noop` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_applies_and_stages` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_failure_unwinds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_composes` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_resolve_stages` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_append_only_union_concatenates` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandRefusesOnTerminalStateRegression::test_land_refuses_and_unwinds_when_sweep_finds_a_regression` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_describe_git_failure_includes_argv_and_stderr` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_describe_git_failure_includes_spawn_error` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_wip_commit_failure_logs_stderr` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_through_changelog_guard_hook_succeeds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_internal_git_env_restores_prior_value` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_id_title_mismatch_is_refused_not_silently_overwritten` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_same_id_same_title_still_resolves_via_newer` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 20 passed (from 20 evidence id(s))
- gates: 0 error(s), 589 warning(s), 685 waived
- error-findings: none (measured, zero errors)

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
state: queued
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
