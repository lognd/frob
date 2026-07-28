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
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/**
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

<!-- ticket:T-1012 -->
```yaml
id: T-1012
title: SCOPE002 private-helper direction is unusably noisy over flat top-level dirs
  (tests/)
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/callgraph.py
threat: null
component: null
```
`frob.graph.callgraph.scope_private_helper_gaps` (T-0998, SCOPE002
direction 5) narrows its `build_call_graph` candidate set to files sharing
a scoped file's PARENT DIRECTORY. For a flat top-level directory like
`tests/` (hundreds of files, one dir), this degrades to "every test file
in the whole tests/ tree" the moment any single test file is in scope --
observed live: scoping `tests/test_graph.py` alone produced 4000+ SCOPE002
"review the dependency" findings, almost all naming a same-named `_write`/
`_run` helper private to some unrelated sibling test file, not a real
under-capture signal.

WARN-only (never blocks), so this is noise, not a correctness bug -- but
noisy enough that a real agent would tune it out entirely rather than
read the real hits buried in it. Needs a narrower per-scope candidate-set
heuristic for large flat directories (e.g. cap candidate file count, or
require the SAME leaf-name collision to be genuinely ambiguous before
flagging, or scope the search to files matching the ticket's own SOURCE
directory conventions rather than a raw parent-dir match) before this
direction is trustworthy enough to read routinely. Filed instead of fixed
under T-0998's own scope/effort budget.

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

<!-- ticket:T-1025 -->
```yaml
id: T-1025
title: 'strata SYS203: make shared-store-write contention consult a resource''s declared
  arbiter, drop tickets_ledger waivers'
state: queued
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_contention.py
- tests/unit/strata/test_contention.py
- docs/strata/host.md
- design/frob.strata
- tickets.md
threat: null
component: null
```
T-0956 modeled the tickets_ledger's real single-writer-lock arbitration
using T-0700's grammar (resource tickets_ledger { lock "tickets.lock"; }
plus access "tickets_ledger" mode write; on cli/gates/fleet/core/serve),
verified clean via frob.strata._access.resource_contention_violations
(SYS204). SYS203 itself (src/frob/strata/_contention.py::
check_resource_contention) remains permanently mode-blind by design: it
has no code path that reads Module.resources or a node's access= attrs at
all, so it keeps firing on tickets_ledger's five writers regardless of the
now-modeled arbiter, and the five SYS203:tickets_ledger waivers (cli/
gates/fleet/core/serve in design/frob.strata) stay in place, permanently
justified rather than pending re-evaluation.

This ticket is the actual code-level follow-up: teach SYS203 (or a new,
narrower successor rule) to consult a resource's declared arbiter
(arbitrated_by/lock) the same way SYS204 already does, so a store with a
provably-safe declared arbiter stops being flagged by SYS203 at all,
letting the five tickets_ledger waivers above finally be dropped. Scope:
src/frob/strata/_contention.py, tests/unit/strata/test_contention.py,
docs/strata/host.md#resource-contention-sys2xx-t-0699, design/frob.strata
(dropping the five waivers once SYS203 itself discharges them),
tickets.md.

<!-- ticket:T-1029 -->
```yaml
id: T-1029
title: 'ticket CLI: add acceptance criteria to an existing ticket (only ticket new
  supports --acceptance)'
state: queued
kind: ux
origin: agent
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/
- tests/unit/test_ticket_runner_gate_findings.py
acceptance:
- text: GIVEN an existing queued ticket WHEN the new subcommand adds a criterion THEN
    ticket show displays it and the ledger write went through the CLI
  evidence: []
threat: null
component: null
```
T-0894's agent had to hand-edit tickets.md to add a before-fails/after-passes acceptance criterion required by the T-0756 new-gate-rule close gate, because no subcommand exists to append acceptance criteria to an existing ticket. Add e.g. 'frob ticket accept <id> --criterion ...' (or extend ticket scope-style editing) with the same validation as ticket new --acceptance, so the ledger is never hand-edited for this.

<!-- ticket:T-1031 -->
```yaml
id: T-1031
title: 'frob natives build: estate rollout of the Makefile core one-line shim across
  sibling repos'
state: queued
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/**
threat: null
component: null
```
T-0735's user directive named "estate rollout via fleet at close" as part of
the natives-build epic: every sibling repo's Makefile core target should be
converted to the one-line `uv run frob natives build` shim (T-0864's landed
subcommand) via `frob scaffold apply` (T-0865's landed scaffold template +
drift check), removing any lingering per-repo CARGO_TARGET_DIR/maturin-develop
cache logic at the wrong layer (the exact T-0732 drift class this epic exists
to retire).

This repo itself is already compliant (Makefile `core:` is the one-line shim,
verified at T-0735's close: `uv run frob natives build` runs successfully
using the git-common-dir-keyed shared CARGO_TARGET_DIR).

Fleet-level rollout across the other frob-enabled repos is out of THIS repo's
own scope -- draft follow-up for whichever fleet-facing ticket/process
actually walks the sibling-repo list and runs `frob scaffold apply` +
`frob doctor` per repo, plus a short docs note pointing at T-0864/T-0865/
T-0735 as the design precedent for anyone doing that rollout by hand in the
meantime.

<!-- ticket:T-1035 -->
```yaml
id: T-1035
title: 'frob-dup: nested-closure fragments cannot be individually waived (symref/binding
  mismatch)'
state: queued
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/_legacy.py
- src/frob/dup/_legacy_py.py
- src/frob/graph/dsl.py
- docs/modules/dup.md
threat: null
component: null
```
Found while working T-0862 (tests/**-only frob-dup group triage).

4 of the 154 unaccounted tests/**-only groups measured for T-0862 share a
single root cause that cannot be fixed from tests/** alone: a symref
mismatch between how `frob.dup._legacy` names a NESTED (closure) function
fragment and how `frob.graph.dsl` binds a preceding `frob:waive` comment.

`frob.dup._legacy._enclosing_class_py` (src/frob/dup/_legacy.py via
src/frob/dup/_legacy_py.py:198) walks ALL the way up a function's ancestor
chain looking for the nearest enclosing CLASS, ignoring any enclosing
FUNCTION in between. So a helper closure defined inside a test method
(e.g. `def _run_new():` nested inside
`TestArchiveRaceWithConcurrentNew.test_concurrent_new_ticket_survives_a_racing_archive`)
gets a dup fragment symbol of `TestArchiveRaceWithConcurrentNew._run_new`
-- qualified by the enclosing CLASS only, never the enclosing METHOD.

Meanwhile `frob.graph.dsl`'s directive-to-symbol binding (used to resolve
a `frob:waive DUP001 reason="..."` comment placed directly above a `def`)
only tracks top-level defs and class methods as declared symbols -- it has
no concept of a nested closure as an independently addressable symbol. A
comment placed directly above a nested `def` binds instead to the nearest
OUTER tracked symbol (the enclosing test method), not the nested function.

Net effect: `_dup_group_covering_waivers`'s full-coverage rule
(docs/modules/dup.md#T-0375) requires every fragment's symref -- as
`frob.dup` computes it -- to be covered by a matching `frob:waive` edge --
as `frob.graph.dsl` binds it. For a nested-closure fragment these two
symbol spaces disagree, so no comment placement can ever satisfy coverage
for that fragment. Confirmed by direct probe (calling
`frob.check._python._waive_edges_for_rule` and `frob.dup.find_duplicates`
against this repo): a `frob:waive DUP001` comment placed immediately above
`tests/test_tickets_ledger_concurrency.py`'s nested `_run_new` binds to
`TestArchiveRaceWithConcurrentNew.test_concurrent_new_ticket_survives_a_racing_archive`
(the outer test method), never to
`TestArchiveRaceWithConcurrentNew._run_new` (the fragment `frob.dup`
actually reports) -- so the waiver is silently ineffective no matter where
the comment is placed.

A second, related symptom: two SAME-NAMED nested closures in different
test methods of the same class collapse to the SAME symref (class-only
qualification loses the enclosing-method disambiguation), e.g.
`tests/test_ticket_runner_pytest_env.py`'s two `fake_guarded_subprocess_run`
closures in `TestRunPytestDirectlyStripsLeaseEnv` both report as
`TestRunPytestDirectlyStripsLeaseEnv.fake_guarded_subprocess_run` --
genuinely ambiguous fragment identity, independent of the waiver-binding
gap above.

The 4 residual groups from T-0862 (unfixable from tests/** alone):
- tests/test_tickets_ledger_concurrency.py:98,156 (nested `_run_new`
  in two different test methods of two different classes)
- tests/test_testing.py:1239,2124 (nested `fake_run_argv`)
- tests/test_gitio.py:29 + 8 sibling files, incl.
  tests/test_evidence_integrity.py's nested `git` (the pre-existing
  waiver there already has this exact problem -- it predates T-0862)
- tests/test_ticket_runner_pytest_env.py:40,71 (symref collision, not
  just a binding gap)

Fix direction (not evaluated in depth, needs design):
(a) `frob.dup._legacy`'s Python function-symbol resolution: qualify a
    nested closure's symbol by its full enclosing chain (or at minimum
    the nearest enclosing FUNCTION, not just the nearest enclosing CLASS)
    so two same-named closures in sibling methods no longer collide.
(b) `frob.graph.dsl`'s comment-to-symbol binding: either extend it to
    recognize nested function defs as independently waivable symbols
    (binding a directly-preceding comment to the nested def rather than
    falling through to the outer tracked symbol), or teach
    `_dup_group_covering_waivers` to accept a waiver bound to a fragment's
    nearest OUTER tracked symbol as sufficient coverage for a nested
    fragment (weaker, but matches what a human intuitively expects when
    they place the comment directly above the nested closure).

Scope for whoever picks this up: src/frob/dup/_legacy.py,
src/frob/dup/_legacy_py.py, src/frob/graph/dsl.py, plus
docs/modules/dup.md's T-0375 full-coverage writeup once resolved. The 4
groups above (and the pre-existing evidence_integrity.py waiver, which
should be re-verified once the binding is fixed) are this ticket's
regression fixtures.

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

<!-- ticket:T-1060 -->
```yaml
id: T-1060
title: 'SYS205 v1: alpha anti-pattern, arbitrated_by code-identity, write path-scoping'
state: queued
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_mode_conformance.py
- tests/unit/strata/test_mode_conformance.py
threat: null
component: null
```
T-0701's SYS205 mode-conformance check disclosed three v0 cuts (module
docstring, src/frob/strata/_mode_conformance.py):

1. ALPHA's "upgrade-deadlock ANTI-PATTERN" (acquiring a write while
   holding a plain read lock context on the same resource) is not
   detected -- needs per-lock-variable identity across nested `with`
   blocks (which lock guards which resource), the same lock-IDENTITY
   modeling problem `frob.arch._lock_ordering`'s T-0694
   `_collect_module_locks` solves for the cyclic lock-order check.
2. ALPHA/EXCLUSIVE code-checkable arbiter support is `lock`-only --
   an `arbitrated_by NODE` arbiter has no code-level identity resolved
   in this pass (no cross-node call-graph analysis).
3. WRITE mode is unrestricted in v0 -- the mandate's "only on declared
   paths" clause needs path-level identity between a declared resource
   id and a specific file/call site, which this v0 pass does not have
   (same class of cut `_effects.py`'s own capability-conformance join
   already discloses).

Each needs real design work (lock-identity modeling, cross-node call
resolution, or a first-class capability/resource-path grammar) rather
than a quick patch -- filed as its own ticket per T-0701's Done report
rather than approximated unreliably in that pass.

<!-- ticket:T-1061 -->
```yaml
id: T-1061
title: wire SYS205 mode-conformance into CLI dispatch + waiver channel + docs
state: queued
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/sys_runner.py
- src/frob/gates/**
- docs/strata/host.md
threat: null
component: null
```
T-0701 shipped `check_mode_conformance` (SYS205) as a pure, fully-tested
function in `src/frob/strata/_mode_conformance.py` -- CLI dispatch
(`frob sys audit`, `src/frob/app/sys_runner.py`) and the T-0174
`MULTI_INSTANCE_WAIVER_FAMILIES` waiver channel are both out of T-0701's
declared scope (`src/frob/strata/**`, `src/frob/vet/**`,
`tests/unit/strata/`), same disclosed-cut precedent
`_access.py`'s own SYS204 module docstring already used for T-0700. Also
wire the `docs/strata/host.md#resource-access-modes-t-0700` section (out
of scope for T-0701 too -- docs/strata/** is not in its scope globs) with
a new subsection documenting SYS205's per-mode semantics, the python-only
v0 detection scope, and the `lock`-only arbiter support.

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
total: `check/_native.py` 1, `check/_python.py` 1, `dup/_pipeline.py` 2,
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

<!-- ticket:T-1091 -->
```yaml
id: T-1091
title: 'strata: drop SYS103''s _PACKAGE_ROOT restriction now that the self-model covers
  tests/scripts/native trees (T-1079 follow-up)'
state: queued
kind: security
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_selfconform.py
- tests/unit/strata/test_selfconform.py
threat: null
component: null
```
T-1079 modeled tests/**, scripts/**, frob-core/src/**, strata-core/src/**
in design/frob.strata (testsuite, scripts_ops, strata_core_native,
frob_core_native nodes) so an unrestricted SYS103 scan against the model
now returns zero findings. `_coverage_totality_scan_prefix`
(src/frob/strata/_selfconform.py) itself was out of T-1079's declared
scope and still restricts the LIVE SELFAUDIT001 gate to _PACKAGE_ROOT
("src/frob") on frob's own tree -- now that the model covers the whole
repo with zero findings either way, that restriction can be dropped (or
narrowed to a real, disclosed exception) so the live gate actually
checks what the model now claims to cover, closing the gap for real
rather than just in a test harness.

<!-- ticket:T-1099 -->
```yaml
id: T-1099
title: 'strata-core: split parse.rs (4346 lines) into grammar-family modules'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/
- tests/unit/strata/
acceptance:
- text: given the strata-core crate, when the split lands, then parse.rs holds only
    the parser spine, grammar families live in their own modules, no file exceeds
    2000 lines, and cargo test plus the full strata litmus suite pass unchanged
  evidence: []
threat: null
component: null
```
parse.rs accreted the whole strata grammar across T-0629/T-0700/T-0702 and siblings (4346 lines). Split by grammar family per the T-1072/T-1086 discipline translated to Rust module conventions (mod files, pub(crate) surfaces re-exported from parse.rs or lib.rs so the python bindings and goldens stay byte-identical). Discovered alongside the large-file gate gap (T-1102); the split makes the Rust tree pass the ceiling that gate will enforce.

<!-- ticket:T-1100 -->
```yaml
id: T-1100
title: 'frob ticket flow: created/day vs landed/day vs net + naive burn-down ETA (one
  table, builds on T-0938 velocity mining)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner.py
- tests/test_tickets_velocity.py
- docs/modules/tickets.md
acceptance:
- text: 'given a frob-enabled repo, when frob ticket flow runs, then it prints per-day
    filed/landed/net counts (created: fields + ledger git history via the T-0938 transition
    miner), current open count, the trailing-3-day net rate, and a naive ETA line
    (open / trailing net rate) clearly labeled as extrapolation'
  evidence: []
threat: null
component: null
```
User request 2026-07-28: a simple ticket data-analysis command showing the rate tickets grow vs the rate they complete. Reuse sprint_velocity's git-history transition mining (T-0938) for the landed side and the created: fields for the filed side; plain render-layer table, no new storage. Keep it genuinely simple -- one table plus one ETA line.

<!-- ticket:T-1108 -->
```yaml
id: T-1108
title: 'arch: extract remaining ~8 verb families from tickets/__init__.py (3489) and
  split tickets/_land.py (4762) -- T-1103 residue'
state: queued
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- docs/modules/tickets.md
- tests/test_tickets.py
- tests/test_tickets_tiers.py
- tests/test_tickets_lease.py
- tests/test_tickets_lease_overlay.py
- tests/test_tickets_dispatch_stale.py
- frob.lock
scope_changes:
- op: add
  glob: tests/test_tickets_tiers.py
  reason: doable/leases/scope-breadth family split moved frob:tests-carrying functions
    across files owned by these test modules
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets_lease.py
  reason: doable/leases/scope-breadth family split moved frob:tests-carrying functions
    across files owned by these test modules
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets_lease_overlay.py
  reason: doable/leases/scope-breadth family split moved frob:tests-carrying functions
    across files owned by these test modules
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets_dispatch_stale.py
  reason: doable/leases/scope-breadth family split moved frob:tests-carrying functions
    across files owned by these test modules
  actor: logan
  at: '2026-07-28'
- op: add
  glob: frob.lock
  reason: frob ack re-acknowledges tickets/__init__.py::_recover_missing_evidence_for_done
    digest shift caused by this split
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_tickets.py::TestDoable::test_blocked_excluded
- tests/test_tickets_tiers.py::TestDoableLeafOnly::test_epic_and_story_never_surface
- tests/test_tickets_lease.py::TestDoable::test_ignore_lease_returns_raw_list
- tests/test_tickets_lease.py::TestShowBlocked::test_show_blocked_lists_reasons
- tests/test_tickets_lease.py::TestLeasedBy::test_precise_in_progress_does_not_hide_disjoint
- tests/test_tickets_lease.py::TestLeasedBy::test_real_source_scope_collision_is_hidden
- tests/test_tickets_lease.py::TestLeasedBy::test_over_broad_lease_demotes_to_warn_only
- tests/test_tickets_lease.py::TestLargeGlobWarnings::test_fires_on_broad_tests_glob
- tests/test_tickets_lease.py::TestLargeGlobWarnings::test_silent_on_precise_test_file
- tests/test_tickets_lease.py::TestBreadthPerf::test_computed_once_per_doable_call
- tests/test_tickets_lease.py::TestBreadthPerf::test_doable_blocked_also_shares_one_breadth_walk
- tests/test_tickets_lease.py::TestBreadthPerf::test_repo_files_git_kill_switch_refuses_without_spawning
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_live_lease_decorated
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_stale_lease_undecorated
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_ledger_in_progress_undecorated
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_no_root_never_decorates
- tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_live_lease_is_in_flight
- tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_no_lease_is_not_in_flight
- tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_no_root_never_in_flight
- tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_same_day_is_zero_hours
- tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_one_day_old_is_24_hours
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_past_threshold_alarms
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_under_threshold_no_alarm
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_medium_priority_never_alarms
acceptance:
- text: GIVEN the tickets package WHEN the remaining verb families (doable/leases/scope-breadth,
    scope mutation, field setters/sprint, evidence/transition, done-report/review/drop/attach)
    are extracted into per-family modules THEN tickets/__init__.py drops below 2000
    lines with no public API change and all existing tests pass
  evidence: []
- text: GIVEN tickets/_land.py at 4762 lines WHEN split into cohesive submodules (preflight,
    splice, verify, sweep families) THEN no single tickets/ module exceeds 2500 lines
    and LARGE001 no longer flags _land.py
  evidence: []
threat: null
component: null
```
T-1103 extracted archive + new/renumber families (tickets/__init__.py 4287->3489) and stopped on budget; per its done report the remaining ~8 families are doable/leases/scope-breadth, scope mutation, field setters/sprint, evidence/transition, done-report/review/drop/attach, and _land.py (4762 lines) was not touched. Continue the same extraction pattern: per-family private modules re-exported from __init__, zero behavior change, existing tests as the safety net. Beware the load-time circular import noted in T-1103's report (evidence family).

## Done report

Extracted the "doable/leases/scope-breadth" family named in T-1108's own
scope note out of tickets/__init__.py into a new src/frob/tickets/_doable.py
module, following T-1103's exact split pattern (private module re-exported
from __init__ via explicit imports, zero caller-visible behavior change).

Moved: _doable_candidates, _in_progress_leases, _cross_worktree_leases,
_all_leases, _is_excluded_breadth_path, _repo_files_git,
_repo_files_walk_fallback, _repo_files, scope_breadth_context,
_entry_to_glob, _over_broad_scope_entries, large_glob_warnings, leased_by,
display_state, has_live_lease, _DISPATCH_STALE_DEFAULT_HOURS,
_dispatch_stale_thresholds, dispatch_stale_hours, undispatched_stale,
doable, doable_blocked, _open_blockers.

tickets/__init__.py: 3489 -> 2918 lines (571 carved). Below the acceptance
criterion's <2000 target -- this is a PARTIAL land (T-1089 precedent):
one cohesive family this dispatch, remaining ~7 families (scope mutation,
field setters/sprint, evidence/transition, done-report/review/drop/attach)
plus the untouched _land.py (4762 lines) split are filed as residue
(T-1123, real id assigned at land-time renumber).

Hit two of T-1103's own flagged hazard classes directly:
1. `_doable_sort_key` (board_view's sort key too) and `_OPEN_STATES`
   (a module-wide constant) stay in __init__.py; the moved `doable`/
   `doable_blocked`/`_open_blockers` late-import both from the package at
   call time rather than binding them at module load, since __init__
   imports _doable.py before either name exists at __init__'s own module
   scope -- the exact load-order hazard T-1103's Done report named for
   `renumber_one`.
2. Monkeypatch indirection: `tests/test_tickets_lease.py::TestBreadthPerf`
   and `tests/test_tickets_dispatch_stale.py::TestHasLiveLease` /
   `tests/test_tickets_lease_overlay.py::TestDisplayState` monkeypatch
   `frob.tickets._repo_files` / `frob.tickets.read_all_leases` (the PACKAGE
   attribute) -- a plain module-top-level `import` binding in _doable.py
   would not see that patch. `scope_breadth_context` and `display_state`
   both late-import these from the package instead, same fix T-1103 applied
   for `renumber_one`/`finalize_draft`. Caught this by running the full
   affected test suite BEFORE committing, not by inspection alone -- 4
   tests failed on the first pass with exactly this symptom.

Also: re-ran `frob ack src/frob/tickets/__init__.py::_recover_missing_evidence_for_done`
-- moving ~570 lines out of the same file shifted this unrelated function's
digest, invalidating its pre-existing DRIFT001 ack (the same "reviewer
re-acks at land" pattern T-1103's Done report already named for this exact
symbol).

Confirmed via `git diff main -- <file>` that the two INV006 findings
(src/frob/gates/_todo_fmt.py, src/frob/gates/_waive_comments.py) and the
three TICK006 phantom-draft findings (T-1077/T-1084/T-1095's historical
Done reports) `frob check --ticket T-1108` still reports are unrelated,
pre-existing, and untouched by this diff.

One pre-existing, unrelated test failure noted for visibility, NOT part of
this ticket's scope (tests/test_tickets_review.py is untouched by this
diff, confirmed via `git diff main`): TestCloseStrictMode's 4 tests fail
because `frob ticket close`'s evidence re-validation spawns `uv run pytest
--collect-only` inside an isolated tmp_path fixture with no real project
layout, collecting 0 tests -- an environment/infra issue in the
evidence/close family, not the doable family this ticket touched.

### Changed
```
 docs/modules/tickets.md      |  14 +-
 frob.lock                    |   2 +-
 src/frob/tickets/__init__.py | 616 ++-------------------------------------
 src/frob/tickets/_doable.py  | 671 +++++++++++++++++++++++++++++++++++++++++++
 tests/test_tickets.py        |   2 +-
 tests/test_tickets_tiers.py  |   4 +-
 tickets.md                   |  39 ++-
 7 files changed, 738 insertions(+), 610 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestDoable::test_blocked_excluded` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestDoableLeafOnly::test_epic_and_story_never_surface` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestDoable::test_ignore_lease_returns_raw_list` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestShowBlocked::test_show_blocked_lists_reasons` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestLeasedBy::test_precise_in_progress_does_not_hide_disjoint` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestLeasedBy::test_real_source_scope_collision_is_hidden` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestLeasedBy::test_over_broad_lease_demotes_to_warn_only` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestLargeGlobWarnings::test_fires_on_broad_tests_glob` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestLargeGlobWarnings::test_silent_on_precise_test_file` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestBreadthPerf::test_computed_once_per_doable_call` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestBreadthPerf::test_doable_blocked_also_shares_one_breadth_walk` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestBreadthPerf::test_repo_files_git_kill_switch_refuses_without_spawning` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_live_lease_decorated` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_stale_lease_undecorated` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease_overlay.py::TestDisplayState::test_ledger_in_progress_undecorated` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease_overlay.py::TestDisplayState::test_no_root_never_decorates` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_live_lease_is_in_flight` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_no_lease_is_not_in_flight` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_no_root_never_in_flight` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_same_day_is_zero_hours` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_one_day_old_is_24_hours` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_past_threshold_alarms` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_under_threshold_no_alarm` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_medium_priority_never_alarms` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 24 passed (from 24 evidence id(s))
- gates: 8 error(s), 878 warning(s), 425 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:295, INV006@src/frob/gates/_todo_fmt.py, INV006@src/frob/gates/_waive_comments.py, TICK006@tickets.md

<!-- ticket:T-1109 -->
```yaml
id: T-1109
title: 'docs: DOC006 doc-pointer round-3 burn-down (~41 residual warnings after T-1015/T-1016)'
state: queued
kind: docs
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
acceptance:
- text: GIVEN a full frob check WHEN the doc gate runs THEN DOC006 reports zero unwaived
    warnings, with every fixed pointer resolving to a real heading slug and no matcher
    loosening
  evidence: []
threat: null
component: null
```
T-1015 (matcher hardening, 771->133) and T-1016 (round 2) left ~41 DOC006 doc-pointer warnings. Round 3: fix or reasoned-waive every residual site. No matcher/threshold loosening; follow T-1015's FP-class analysis before touching the matcher. Narrow scope to the real finding sites at start.

<!-- ticket:T-1110 -->
```yaml
id: T-1110
title: 'warnings: DEAD001/COV/REF edge burn-down (DEAD 32, COV 10, REF 10 unwaived)'
state: queued
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
acceptance:
- text: GIVEN a full frob check WHEN the dead/coverage/refs gates run THEN DEAD001,
    COV00x, and REF00x report zero unwaived warnings, each finding either root-fixed
    (dead code removed, edge bound) or waived with a grounded reason
  evidence: []
threat: null
component: null
```
Post-wave-16 residue: 32 DEAD001 dead-symbol warnings, 10 COV coverage-edge warnings, 10 REF reference warnings (unwaived, per gate summary). T-1024 precedent: DEAD001 13->0 and COV006 3->0 via real removals and edge bindings, not blanket waivers. Callgraph blind spots (cross-package privates, indexed-constant mutation) get confirmed-exercised waivers per the 3d574f3a precedent. Narrow scope to the real finding sites at start.

<!-- ticket:T-1111 -->
```yaml
id: T-1111
title: 'warnings: small-residue sweep to zero (DEPR 4, LANG 3, INV 2, REG 2, WAIVE
  2, WALK 2)'
state: queued
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
- tests/**
- frob.toml
acceptance:
- text: GIVEN a full frob check WHEN all gates run THEN the DEPR, LANG, INV, REG,
    WAIVE, and WALK families each report zero unwaived warnings
  evidence: []
threat: null
component: null
```
Endgame tail: the sub-five-warning families (DEPR003 x4, LANG003 x3, INV003/004 x2, REG009/REG010 x2, WAIVE004 x2, WALK001 x2 per gate summary). Fix or grounded-waive each. REG009/REG010 residue is the CPPTHROW001 check-coverage auto-sync gap noted at T-1042 land -- fold the registry entry fix here. Narrow scope at start.

<!-- ticket:T-1112 -->
```yaml
id: T-1112
title: 'arch: abstraction-opportunity check-registry-protocol detector exclusion'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
threat: null
component: null
```
Filed from T-1084 (triage of the 27 arch-package abstraction-opportunity
findings T-1067 handed off). After reading every one of the 27 groups'
member bodies (not just names), none warrant a manual extraction inside
`src/frob/arch/` -- they split into recognizable, already-reviewed shapes
the detector cannot yet tell apart from a real missing abstraction:

1. The check-function registry protocol itself: `_exceptions.py`'s 27-
   member `(NormalizedModule) -> list[ArchSuggestion]` group is not a
   coincidence -- it is literally every `check_*` detector across the
   whole `frob.arch` package (33 functions match `^def check_` under
   `src/frob/arch/*.py`; ~27 of them share the exact bare signature, the
   handful of others take an extra param). This is the package's own
   intentional common interface (every detector module registers this
   way), not duplicate logic to extract -- the exact same "protocol
   family" shape as T-0360's `_is_dispatch_family`/T-1068's language-tag
   exclusion already carve out for other signature-collision classes,
   just not yet generalized to "every function whose name matches
   `^check_` (or another package-wide naming convention) is exempt from
   this category, regardless of arity."
2. Per-construct mirrored builders: `_typescript.py`'s
   `_ts_build_class`/`_ts_build_interface`/`_ts_build_enum` (and the
   `_kotlin.py`-anchored cross-language equivalents T-1068 already
   partially covers) build genuinely DIFFERENT tree-sitter node types
   (`class_declaration` vs `interface_declaration` vs `enum_declaration`)
   into the same `NormalizedClass` return type -- distinct concerns that
   happen to share a return type, not one duplicated function.
3. Deliberately-kept-separate trivial one-liners: `_mayraise.py`,
   `_fallibility.py`, and `_exceptions.py` each define their own
   byte-identical `_bare_callee_name(callee: str) -> str`, and each
   docstring explicitly cross-references the sibling copy ("same
   convention as `frob.arch._fallibility._bare_callee_name`") -- a prior
   ticket (T-0686) already reviewed this exact tradeoff for the sibling
   `_qualname` duplicate and chose to keep the modules independent rather
   than share a one-line private helper across otherwise-unrelated check
   families. Re-deduplicating now would reverse that reviewed decision
   without a new instruction to do so.
4. Large mixed-concern groups (`_async_hazards.py`'s 32-member
   `(Node) -> bool` group, `_concurrency_model.py`'s 27-member
   `(Node) -> str | None` group, etc.): genuinely unrelated tree-walk
   predicates/extractors that only coincide on a common, very generic
   tree-sitter-node signature shape -- the class-1 "coincidental
   collision" case the parent ticket's own body already anticipated.

Add a `_is_check_registry_family` (or similarly named) exclusion to
`frob.arch._python._check_abstraction_opportunities` alongside
`_is_dispatch_family`/`_is_language_parity_family`: a same-signature group
is exempt when every member's bare name matches the package's own
detector-naming convention (`^check_[a-z_]+$`, mirroring how
`_is_dispatch_family`/`_is_language_parity_family` are both purely
name/structure-based, never raw text proximity). Re-measure
`abstraction-opportunity` count after landing and confirm the drop is
exactly the check-registry groups, mirroring T-1068's own before/after
methodology.

<!-- ticket:T-1113 -->
```yaml
id: T-1113
title: 'strata: promote SYS104/105/106 to mandatory + add CHK-GATE-SYS104/105/106
  registry entries'
state: queued
kind: security
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
- docs/design/registry/check-coverage.yaml
- src/frob/strata/_selfconform.py
threat: null
component: null
```
SYS104 (T-0668, src/frob/strata/_selfconform.py) only evaluates a node
that has already declared at least one `interface=` attr -- an opt-in
scope cut, disclosed in T-0668's Done report, because making it
mandatory repo-wide would require adding `interface=` declarations to
`design/frob.strata`, which was outside T-0668's declared scope
(`src/frob/strata/**`, `src/frob/graph/**`, `docs/modules/strata.md`,
`tests/unit/strata/**` -- not `design/frob.strata`).

Two follow-ups bundled here (same shape as SYS103's own T-1079-class
deferred work):
1. Add real `interface=` declarations to `design/frob.strata`'s nodes
   (measured against each node's actual public surface,
   `_module_public_symbols`), then flip SYS104 to fire on ANY node
   whose bound code has a public symbol, not just opt-in nodes.
2. Add `CHK-GATE-SYS104`/`CHK-GATE-SYS105`/`CHK-GATE-SYS106` entries to
   `docs/design/registry/check-coverage.yaml` and the corresponding
   `frob:enforces` directives on `check_self_conformance`, mirroring the
   `CHK-GATE-SYS103` precedent (T-0667's Done report's own deferred
   registry gap, `docs/modules/strata.md#known-gap-registry-cross-
   reference`) -- `docs/design/registry/**` was outside T-0668/T-0669/
   T-0670's declared scope.

<!-- ticket:T-1114 -->
```yaml
id: T-1114
title: 'arch: abstraction-opportunity gates package extraction (T-1082 remainder)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/
threat: null
component: null
```
Filed from T-1082's partial land: T-1082 consolidated the cross-cutting
`_tracked_files`/`git ls-files` duplicate (5 gate modules --
_opaque.py, _exclude_hazard.py, _refs.py, _secrets.py,
_cve_fingerprint_scan.py -- each defining a byte-for-byte identical
private helper) into one shared `frob.gates._tracked_files.tracked_files`
and inlined every call site, clearing that specific abstraction-
opportunity cluster entirely. It did NOT attempt the remaining 29
findings T-1082 was filed to cover (19 in gates/__init__.py, 1 each in
_baseline.py, _cve_fingerprint_scan.py, _docblocks.py,
_fmt_directives.py, _gate_cache.py, _waive.py/_waive_lease.py,
invariants.py, 3 in _pii_structural.py), nor the wider
`_tracked_python_files`-shaped duplication T-1082 named as likely
undercounted (_walk_lint.py, _pii_structural/_tracked.py, _docblocks.py,
_docptr.py all define their own git-ls-files-with-suffix-filter variant),
nor the new small cluster the consolidation itself introduced (the new
`frob.gates._tracked_files.tracked_files` now shares a `(Path, str) ->
tuple[str, ...]` signature with 4 functions in
src/frob/dup/_pipeline/_callgraph.py -- out of gates/ scope entirely).

Re-measure `uv run frob check --only arch --json` scoped to
`src/frob/gates/` before starting; other tickets may have landed in the
interim and changed the count from the 29 this ticket, and its
predecessor T-1082, were filed against.

<!-- ticket:T-1115 -->
```yaml
id: T-1115
title: 'arch: split remaining ~14 gate families out of src/frob/gates/__init__.py
  (~9802 lines) -- T-1077 residue refile'
state: queued
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
acceptance:
- text: GIVEN src/frob/gates/__init__.py WHEN the remaining gate families (DEBT/DEPR,
    SCOPE/PREWORK, INV00x, TEST00x, DECISIONS, TICK00x, COMPLIANCE00x, SYS00x/DOC00x,
    DUP00x, REL00x, FUZZ00x, DOCLINK/DOCANCHOR, PERF, run_gates spine, COV00x) are
    extracted one cohesive family per land THEN gates/__init__.py drops below the
    800-line large-file threshold with no public API change and all existing tests
    pass
  evidence: []
threat: null
component: null
```
Refile of T-1077's residue draft, which died at land (TICK006 phantom repaired by the coordinator). T-1077 extracted the TODO00x/FMT001 family (gates/__init__.py 10164 -> ~9802); the remaining families follow T-1072/T-1077's one-family-per-land discipline: verbatim moves with directives intact, lazy call-time imports back to frob.gates where init-time circularity threatens, re-export only externally-called names, split-carried INV006 waivers where prose moves.

<!-- ticket:T-1117 -->
```yaml
id: T-1117
title: 'test: test_every_deferred_entry_targets_an_open_ticket fails, zero deferred
  entries exist in weaknesses.yaml'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/weaknesses.yaml
- tests/test_registry_reconciliation_weaknesses.py
threat: null
component: null
```
Found while working T-1037: tests/test_registry_reconciliation_weaknesses.py
::TestWeaknessesExhaustiveness::test_every_deferred_entry_targets_an_open_
ticket fails on current main with:

  AssertionError: expected at least one deferred entry to check against

docs/design/registry/weaknesses.yaml currently has ZERO entries whose
disposition.kind is DispositionKind.DEFERRED (confirmed via direct grep
and via _load_weaknesses()/DispositionKind filtering in the test itself).
Either every previously-deferred entry has since been resolved to
checkable/duplicate-of/out-of-scope (in which case the test's own
precondition assertion is now stale and should be relaxed to skip rather
than fail when the deferred set is legitimately empty), or a deferred
entry was dropped/miscategorized somewhere along the way and the test is
correctly catching a real regression -- needs investigation to tell
these apart before deciding the fix.

Out of T-1037's declared scope (that ticket is specifically about REG011
out_of_scope-reason substantive-disclosure, already independently fixed
by T-1019 before this wave started -- confirmed zero REG011 violations
and the ticket's own named regression test passing on current main).

<!-- ticket:T-1118 -->
```yaml
id: T-1118
title: 'daemon: wire run_coverage_wait through the T-1097 daemon-owned coverage lease'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/_coverage_wait.py
- src/frob/app/_daemon_proxy.py
threat: null
component: null
```
T-1097 shipped a daemon-owned named resource lease/semaphore primitive
(frob.serve._leases.ResourceLeaseManager, frob_lease_acquire/frob_lease_
release RPC methods) with connection-liveness release, proven against
real socket clients directly.

It did NOT rewire frob.testing._coverage_wait.run_coverage_wait's own
subprocess flow to acquire the coverage lock THROUGH this daemon RPC
instead of its existing file-lock layers (T-0322's per-worktree
fcntl.flock, T-1095's shared per-digest fcntl.flock) -- that wiring
touches frob.app's CLI-proxy layer (_daemon_proxy.query), which was
contended with T-1106's own src/frob/app/ work this wave and out of
T-1097's src/frob/serve/**/src/frob/testing/** scope.

Follow-on: wire run_coverage_wait (or a new coverage-specific daemon
client call) to acquire/release the "coverage" resource lease via the
daemon RPC when a daemon is reachable, falling back to the existing
file-lock layers when it is not -- mirroring frob.app._daemon_proxy.
query's own Ok(daemon)/Err(fallback) shape.

<!-- ticket:T-1121 -->
```yaml
id: T-1121
title: 'test: test_every_deferred_entry_targets_an_open_ticket fails, zero deferred
  entries exist in weaknesses.yaml'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/weaknesses.yaml
- tests/test_registry_reconciliation_weaknesses.py
threat: null
component: null
```
Found while working T-1037: tests/test_registry_reconciliation_weaknesses.py
::TestWeaknessesExhaustiveness::test_every_deferred_entry_targets_an_open_
ticket fails on current main with:

  AssertionError: expected at least one deferred entry to check against

docs/design/registry/weaknesses.yaml currently has ZERO entries whose
disposition.kind is DispositionKind.DEFERRED (confirmed via direct grep
and via _load_weaknesses()/DispositionKind filtering in the test itself).
Either every previously-deferred entry has since been resolved to
checkable/duplicate-of/out-of-scope (in which case the test's own
precondition assertion is now stale and should be relaxed to skip rather
than fail when the deferred set is legitimately empty), or a deferred
entry was dropped/miscategorized somewhere along the way and the test is
correctly catching a real regression -- needs investigation to tell
these apart before deciding the fix.

Out of T-1037's declared scope (that ticket is specifically about REG011
out_of_scope-reason substantive-disclosure, already independently fixed
by T-1019 before this wave started -- confirmed zero REG011 violations
and the ticket's own named regression test passing on current main).

<!-- ticket:T-1123 -->
```yaml
id: T-1123
title: 'arch: extract remaining tickets/__init__.py families + split _land.py -- T-1108
  residue'
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
T-1108 extracted ONE family (doable/leases/scope-breadth: doable, doable_blocked,
leased_by, large_glob_warnings, has_live_lease, dispatch_stale_hours,
undispatched_stale, display_state, scope_breadth_context, and their private
helpers) into src/frob/tickets/_doable.py. tickets/__init__.py dropped from
3489 to 2918 lines (571 carved) -- still above the acceptance criterion's
<2000 target.

Remaining per T-1108's own scope note (~7 families now, one done):
- scope mutation (mutate_scope and its private helpers)
- field setters/sprint (set_priority/set_kind/set_tier/set_sprint/set_component,
  sprint_view/sprint_velocity)
- evidence/transition (transition, add_evidence, the _done_transition_* guard
  family) -- BEWARE the load-time circular import T-1103's Done report flagged
  for this exact family (new_ticket/finalize_draft already late-import from
  the package to work around it)
- done-report/review/drop/attach (brief_ticket, mutate_labels, record_review,
  attach, drop helpers)

_land.py (4762 lines) was not touched at all -- still needs its own split
(preflight/splice/verify/sweep families per T-1108's plan) before LARGE001
stops flagging it.

Follow the same pattern T-1103/T-1108 established: one cohesive family per
dispatch, private module re-exported from __init__ via explicit imports
(never `import *`), zero caller-visible behavior change, existing tests as
the safety net, watch for tests that monkeypatch a moved function via the
PACKAGE attribute (`tickets_mod.<name>`) -- those need a late
`from frob.tickets import <name>` inside the moved function body instead of
a module-top-level binding, or the monkeypatch silently stops taking effect.

<!-- ticket:T-1124 -->
```yaml
id: T-1124
title: 'arch: app runner abstraction-opportunity remainder (check_runner 2 groups,
  deploy_runner, perf_runner) -- T-1085 residue'
state: queued
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- src/frob/app/deploy_runner.py
- src/frob/app/perf_runner.py
- docs/modules/app.md
acceptance:
- text: GIVEN frob check --only arch scoped to src/frob/app WHEN the remaining abstraction-opportunity
    groups are extracted or dispositioned with grounded reasons THEN zero unaccounted
    findings remain in check_runner.py, deploy_runner.py, and perf_runner.py
  evidence: []
threat: null
component: null
```
T-1085 extracted the genuine _load_snapshot/_CACHE_REL duplicate into frob.app._snapshot and deliberately cut the rest to limit app/ contention during wave 17: check_runner.py's two ToolResult-builder groups (the skip/unavailable/disabled constructors look like a genuine extraction), deploy_runner.py's repeated-name (Path) -> str group, and perf_runner.py's _heat/_collect pair. Per T-1085's body: check the repeated-name groups FIRST for a literal same-file shadowing duplicate (possibly dead code) before assuming distinct functions. Re-measure counts before starting; T-1112's detector exclusion may change them.

<!-- ticket:T-1125 -->
```yaml
id: T-1125
title: 'land/renumber: rewrite draft-id references in ledger prose during renumbering'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets.py
acceptance:
- text: GIVEN a worktree ledger whose done-report prose cites T-draft-X WHEN frob
    ticket land renumbers T-draft-X to T-#### THEN every prose reference to T-draft-X
    in tickets.md is rewritten to the final id in the same splice, and a post-land
    full check reports zero TICK006 for it
  evidence: []
- text: GIVEN frob ticket renumber OLD NEW WHEN prose elsewhere in the ledger references
    OLD THEN those references are rewritten too (or the command errors listing them),
    never silently left stale
  evidence: []
threat: null
component: null
```
The dominant wave-17 fallout class (4 incidents in one wave): land renumbers draft BLOCKS but never rewrites prose citing them, so done reports either go TICK006-phantom (T-1077/T-1084/T-1095 reports citing drafts that died) or -- worse and invisible to TICK006 -- cite a WRONG real id (T-0668's agent wrote T-1109 guessing its draft's final id; real id was T-1113; 8 prose sites hand-repaired by the coordinator). renumber already computes the old->new mapping; apply it to prose occurrences of the draft id across tickets.md/tickets-archive.md in the same transaction. Coordinators should never hand-grep real ids again; agents should be free to cite draft ids in prose and have land fix them.

<!-- ticket:T-1126 -->
```yaml
id: T-1126
title: 'daemon: wire run_coverage_wait through the daemon-owned coverage lease RPC
  (T-1097 follow-up)'
state: queued
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/_coverage_wait.py
- src/frob/app/_daemon_proxy.py
- tests/test_coverage_wait_shared.py
- docs/modules/testing.md
acceptance:
- text: GIVEN a running daemon WHEN run_coverage_wait needs the coverage writer THEN
    it acquires via the frob_lease_acquire RPC (crash-released per T-1097) instead
    of its own file-lock layers, with the file-lock path kept only as the daemonless
    fallback
  evidence: []
threat: null
component: null
```
T-0321 epic close disclosed this cut: run_coverage_wait still uses its T-0322/T-1095 file-lock + shared-state layers directly; T-1097 shipped the daemon lease primitive (ResourceLeaseManager, frob_lease_acquire/release, connection-liveness release). Converge the two so coverage arbitration has ONE owner when a daemon is up.

<!-- ticket:T-1127 -->
```yaml
id: T-1127
title: 'serve: RPC surface for exports/stats proxying (T-1106 residual; outline/map/xref
  moot pending T-0802 sunset)'
state: queued
kind: feature
origin: agent
created: '2026-07-28'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/_tools.py
- src/frob/app/**
- docs/modules/serve.md
acceptance:
- text: GIVEN a running daemon WHEN frob exports or frob stats runs THEN it is served
    warm through the proxy with differential parity against in-process execution,
    matching the T-1093/T-1106 pattern
  evidence: []
threat: null
component: null
```
T-0321's close disclosed: outline/map/xref/exports/stats have no frob.serve._tools RPC surface at all, so T-1106 could not proxy them. outline/map/xref (and docs-search) are scheduled for REMOVAL by T-0802's 2026-10-01 navigation-command sunset -- do NOT build RPC for those; only exports and stats warrant a surface. If T-0802 executes first, re-scope to exports/stats only (already assumed here).

<!-- ticket:T-1128 -->
```yaml
id: T-1128
title: 'daemon: reconcile CLI payload shapes to proxy graph-query/check-delta/touched-tests/doable
  (T-1106 residual)'
state: queued
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/**
- src/frob/serve/_tools.py
- docs/modules/serve.md
acceptance:
- text: GIVEN a running daemon WHEN frob graph query, frob check --delta, frob test
    (touched-set), or frob ticket doable runs THEN each is served through the proxy
    with field-for-field differential parity against in-process execution
  evidence: []
threat: null
component: null
```
T-1106 wired frob graph affects and disclosed this residual: frob_graph_query/frob_check_delta/frob_run_touched_tests/frob_doable_tickets RPC methods EXIST server-side but each CLI payload needs field-for-field shape reconciliation with its _tools counterpart before proxying (docs/modules/serve.md Scope cut section). Coordinator refile: the original draft died to a 10b ledger restore.

<!-- ticket:T-1129 -->
```yaml
id: T-1129
title: 'gates: TICK-family check for disclosed-cut-without-ticket in done reports'
state: queued
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
acceptance:
- text: GIVEN a done report whose prose discloses deferred work (left for a follow-up,
    not yet ticketed, deferred, residue, cut) WHEN frob check runs THEN a TICK-family
    finding fires unless the same report cites an open ticket id (or an explicit no-ticket-needed
    reason) within the disclosure's vicinity
  evidence: []
threat: null
component: null
```
Coordinator hand-screen made mandatory-by-tooling: wave 17 had two incidents in one wave -- T-1085 disclosed 'deliberately left for a follow-up' with no ticket (coordinator hand-filed T-1124), and T-0321's close disclosed the serve RPC gap as 'not yet ticketed as its own item' (coordinator hand-filed T-1127). TICK006 covers phantom citations; nothing covers disclosed-but-unticketed cuts. Detector should be conservative (disclosure phrases + absence of any T-#### in the same bullet/paragraph) and WARN-tier first turn-on with frob's own ledger findings fixed in the same land.

<!-- ticket:T-1130 -->
```yaml
id: T-1130
title: 'tickets: ticket new/drop/fail auto-commit their ledger transition on main
  (parity with T-1054 start)'
state: queued
kind: ux
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets.py
acceptance:
- text: GIVEN a coordinator files, drops, or fails a ticket on main WHEN the verb
    completes THEN the ledger change is committed automatically (with an opt-out flag),
    so a subsequent agent dispatch or land preflight can never hit uncommitted coordinator
    ledger state
  evidence: []
threat: null
component: null
```
T-1054 made ticket start auto-commit its transition after DirtyMain incidents; new/drop/fail still leave tickets.md dirty and 'commit before dispatching' is coordinator memory (bit the T-1018 agent once; the playbook carries it as a must-remember). Same pattern, remaining verbs. Worktree-side behavior unchanged (worktree ledger edits reconcile at land).

<!-- ticket:T-1131 -->
```yaml
id: T-1131
title: 'tickets: fail/retire releases leases; doctor flags leases on nonexistent worktrees'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- tests/test_tickets.py
acceptance:
- text: GIVEN frob ticket fail records a dead end from a worktree WHEN the worktree
    is subsequently removed THEN the ticket does not stay in-progress holding a stale
    lease; frob doctor reports any lease whose worktree path no longer exists and
    offers requeue
  evidence: []
threat: null
component: null
```
T-1050 today: agent fail-logged a superseded ticket, removed its worktree, and the ticket sat in-progress with a lease on a nonexistent path until the coordinator hand-dropped it. Historical siblings: T-0906 stale lease investigation, wave-9 dead-agent requeues. The lease lifecycle should not depend on a coordinator remembering to sweep.

<!-- ticket:T-1132 -->
```yaml
id: T-1132
title: 'tickets: validate blocked_by/parent ids at write time; doctor scans for malformed
  edges'
state: queued
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets.py
acceptance:
- text: GIVEN a ticket write with an empty-string or non-T-#### blocked_by/parent
    entry WHEN the verb runs THEN it refuses with a clear error; frob doctor flags
    existing malformed edges in the ledger
  evidence: []
threat: null
component: null
```
T-0380 sat silently undoable for days because blocked_by contained an empty string alongside three real (done) blockers -- doable() treated it as an unresolvable blocker and nothing surfaced why. Schema validation at write time plus a doctor scan for the existing ledger.

<!-- ticket:T-1133 -->
```yaml
id: T-1133
title: 'gates: suppress WAIVE004 staleness advisories on scoped/--only runs entirely'
state: queued
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
acceptance:
- text: GIVEN frob check --only <stage> or any diff-scoped run WHEN a waiver matches
    0 findings because its gate did not run THEN no WAIVE004 advisory is emitted (the
    rule only fires on full unscoped runs where match-absence is meaningful)
  evidence: []
threat: null
component: null
```
Every scoped run this session printed ~400-447 WAIVE004 warnings with a 'known-flaky, trust only full runs' caveat baked into the message text. A rule that prints its own do-not-trust-me disclaimer on scoped runs should not fire there at all; the caveat is tribal knowledge encoded as noise every coordinator and agent must mentally filter. Keep full-run behavior unchanged (T-1021's sweep depends on it).

<!-- ticket:T-1134 -->
```yaml
id: T-1134
title: 'gates: INV006 split-assist -- detect verbatim-moved claim prose and carry/suggest
  the source file''s waiver'
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
- src/frob/dup/**
- tests/test_gates.py
acceptance:
- text: GIVEN a module split moves docstring/comment prose containing exclusivity
    vocabulary from a file with an INV006 waiver or invariant binding WHEN frob check
    runs on the result THEN the INV006 finding names the source file's existing waiver/binding
    and offers the carried-waiver text as a fix-it (or auto-carries under a flag)
  evidence: []
threat: null
component: null
```
Every split this drive (T-1103, T-1107, T-1072, T-1077, T-1081, T-1082) required hand-carrying INV006 calibration-batch waivers to the new modules -- 3 more by the coordinator today (0abc4e3a) after the gates splits redded main. The clone/dup machinery can already detect verbatim-moved prose; INV006 should use it to stop making 'remember the carried waiver' a human step. Also applies to PII012's (file,token)-keyed allowlist entries which have the same code-moves-need-new-entries failure mode (T-1076 precedent).

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
