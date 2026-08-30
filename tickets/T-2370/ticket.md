---
id: T-2370
title: Burn COV006/COV007 WARN gates to zero, then promote to error
state: dropped
kind: bug
origin: agent
created: '2026-08-17'
priority: medium
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: rollup epic burning COV006/COV007 to zero then promoting
  WARN->error; batched per T-2359/T-2373 precedent into child tickets, each with its
  own real scope
body_changes:
- mode: append
  reason: record the measured REAL GAP / HONEST WAIVE / DETECTOR BUG split so the
    next agent does not re-derive it, and so the promotion half is not attempted while
    132 findings remain
  actor: logan
  at: '2026-08-18'
  old_length: 1314
  new_length: 4507
- mode: append
  reason: re-measured unbudgeted post-T-2810; characterized COV006 (single collapsible
    class, matches T-2550, never promotable) vs COV007 (24 distinct files, per-symbol
    genuine documentation, REG008-shape not REF001-shape); recording before any further
    batching per coordinator directive
  actor: logan
  at: '2026-08-21'
  old_length: 4507
  new_length: 7583
- mode: append
  reason: re-measured unbudgeted post-T-2810; characterized COV006 (single collapsible
    class, matches T-2550, never promotable) vs COV007 (24 distinct files, per-symbol
    genuine documentation, REG008-shape not REF001-shape); recording before any further
    batching per coordinator directive
  actor: logan
  at: '2026-08-21'
  old_length: 7583
  new_length: 10659
- mode: set
  reason: dedupe accidental double-append caused by a body-mirror retry after a LandInProgress
    refusal; content unchanged, just the duplicate block removed
  actor: logan
  at: '2026-08-21'
  old_length: 10659
  new_length: 7583
- mode: append
  reason: re-measured COV006/COV007, burned COV006 to zero via 4 waivers, fully characterized
    remaining 19 COV007 files, requeuing
  actor: logan
  at: '2026-08-22'
  old_length: 7583
  new_length: 14139
designated_repro_test: null
acceptance:
- text: given the family's WARN codes, when frob check --json runs, then zero findings
    remain
  evidence: []
- text: given the family's gate module, when its severity is read, then it is ERROR
    not WARNING
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage,
no BUDGET001 deferral) piped through `scripts/check_summary.py`, 2026-08-18.

WARN-tier finding count, this family (doc/test coverage secondary checks): 64 across codes COV006, COV007.

Do NOT hand-count with grep -- this repo has measured false zeros that way, including
one tonight. Re-measure with the same command above before starting and before
claiming done; treat any disagreement with the number in this body as the tree
having moved, not as your measurement being wrong.

Closure is two-part per the epic (T-0969):
1. Zero findings for every code above, verified via the same
   `frob check --json --budget 500 | python3 scripts/check_summary.py` command.
2. Each code above promoted from warning to error severity in its gate module
   (grep the gate module for its severity constant/mapping) -- a burn-down that
   stops at zero and leaves the gate advisory lets the debt silently reaccumulate.
   DOC012 and the T-1662 arc both closed correctly today by doing both; follow
   that shape, not a zero-only burn-down.

Narrow `scope` to the actual files this family's findings live in once you've
run the gate and can see them -- do not take a broad blanket scope; this keeps
you disjoint from sibling children of T-0969.


TRIAGE RESULT (2026-08-18, every live finding sorted into exactly one
category; measured unbudgeted via `frob check --only coverage --json`,
counting severity="warning" only -- "note" is the already-waived tier and
counting it inflates the bucket from 157 to 344).

Starting count 157 (COV007 139, COV006 18). The coordinator's older
figures (COV007 105, COV006 18) were stale by 34 on COV007.

  REAL GAP .......  0
  HONEST WAIVE ... 36
  DETECTOR BUG ... 121  (3 classes)

DETECTOR BUG, class 1 -- COV007 vs strata clearance: 25. FIXED AND
LANDED as T-2549 (ef519d6a0). `RawSymbol.public` for a `.strata` symbol
is the node's declared SECURITY CLEARANCE (`_walk_strata._build_symbol`,
T-2410), not API privacy, so every `trusted`/`internal` component read as
a private helper. `_cov007` now skips non-python src files, mirroring
`_cov006_edge_violation`'s existing non-python skip. Count after: 132.

DETECTOR BUG, class 2 -- COV006 call-graph blindness: 18. Filed as
T-2550. All 18 test bodies were read individually. `build_call_graph`
never records an edge into a PUBLIC callee, and the compensating rescue
only covers a public wrapper in the TARGET'S OWN FILE called by name from
the test body. Every finding is outside that shape: (a) the test reaches
the private target through a public entry in a different file/package
re-export several hops out (test_vet.py, test_ticket_land.py), or (b) the
test calls that entry from a TEST-CLASS HELPER METHOD rather than the
test body (all six test_lang.py findings). Zero are unexercised bindings.

DETECTOR BUG, class 3 -- COV007 mis-scoped for files with no public
surface: 78. Filed as T-2551. scripts/fleet_status.py (40) and three
.claude/hooks/*.py (38) are standalone executables whose entire surface
is `main()` plus private helpers by design; the rule's remedy ("move it
onto the public caller") is unperformable there, and performing it would
collapse per-symbol doc obligations onto one symbol and destroy the
digest bindings AFFECT001/DRIFT001 depend on.

HONEST WAIVE: 36 -- private helpers in src/frob/** carrying a DELIBERATE
per-symbol doc anchor that names them (e.g. `_refuse_over_broad_scope_on_
start` -> tickets-data-storage.md#mega-glob-scope-refused-at-start-t-1866,
`_attribute_new_findings` -> tickets-verify-sweep.md#symbolic-attribution
-t-1690, `_widen_node_grants` -> strata/surface.md#fragments-t-2502). The
rule's own docstring names this as legitimate and asks for human
confirmation, i.e. a waiver. NOT yet written: 36 individually-reasoned
waivers are worth writing only after T-2551 decides whether the rule is
being narrowed anyway, and the repo already carries ~100 near-identical
COV007 waiver texts (T-1636/T-0871), which is itself evidence the rule
wants redesign rather than more boilerplate.

PROMOTION IS BLOCKED, and specifically must not be done for COV006 even
at zero: its own docstring states WARN is deliberate because
`frob.graph.callgraph` is an explicitly best-effort name-based resolver.
Promoting a heuristic built on an unsound graph to a land-blocking ERROR
is the same mistake class this repo already paid for once.

REMAINING TO ZERO: 132 = 18 (T-2550) + 78 (T-2551) + 36 (waivers).



RE-MEASURED 2026-08-22 (unbudgeted, `frob check --only coverage --json`,
fresh worktree, post T-2810 land): exit 1, gate-summary present (real
measurement, not a budget abort).

  COV006: 5 live warnings (up from 2 at T-2810's time -- tree moved, new
          tests added since; same root-cause class, not a new class)
  COV007: 37 live warnings across 24 files (down from 44 -- exactly
          44 - 7 = 37, consistent with T-2810 removing 7 duplicate
          anchors from _multifile.py; no other file changed since)

CHARACTERIZATION (read every live finding's file, not just counted):

COV006 -- ONE collapsible class, matches T-2550 exactly. All 5 are the
land pipeline driving a private helper (`_land_merge.py::_validate_
closeable`, `_fix_engine.py::_resolve_via_git_rename`) through a public
entry point several hops out (`land()` -> ... -> the private target),
the identical "cross-file public entry, several hops out" shape T-2550
already diagnosed and closed as a genuine call-graph-blindness gap, not
an unexercised binding. New count vs old count is new TEST CASES hitting
the same known-blind shape, not a new bug class. Per COV006's own
docstring (frob.graph.callgraph is deliberately best-effort/name-based),
this code must NEVER be promoted to ERROR regardless of count -- these 5
are individual-waiver candidates citing T-2550, not fixes, and not
promotion material.

COV007 -- NOT a single collapsible class. Sampled 5 of the 24 files
directly (_rapid_sweep.py, _lifecycle.py, _ledger_mirror.py, _worker.py,
_store_migrate.py) by reading the target doc's `frob:describes` block for
each flagged symbol. Unlike T-2810's file (duplicate anchor already
covered by a public sibling), these are GENUINELY individually documented:
e.g. docs/modules/tickets-verify-sweep.md:545-546 `frob:describes` both
`_attribute_new_findings` and `_ticket_is_open` BY NAME, each with its own
prose section -- this is the deliberate per-helper pattern (matching
vet.md's precedent T-2810 explicitly declined to touch), not duplication.
24 distinct files, ~30 distinct private symbols, each carrying its own
individually-authored doc anchor -- the REG008 shape (many distinct
emitting symbols needing per-entry waivers), not the REF001 shape (one
glob change collapsing hundreds). A full pass still needs to check the
remaining ~19 unsampled files for the T-2810 duplicate-anchor pattern
before waiving each (some may yet collapse), but the majority sampled so
far are genuine per-symbol documentation, not bugs.

DISPOSITION: neither code is at zero; promotion stays blocked on both
(COV006 permanently per its own docstring, COV007 pending the remaining
per-file waiver/fix pass). Not closing or promoting this batch --
requeuing with this measurement recorded so the next batch does not
re-triage from scratch. Suggested next batches: (1) sweep the remaining
19 COV007 files for the T-2810 duplicate-anchor shape before waiving
anything, (2) write the 5 COV006 + confirmed-genuine COV007 waivers
citing their doc anchors / T-2550, narrow scope per batch as T-2810 did.


RE-MEASURED 2026-08-22 (unbudgeted, `frob check --only coverage --json`, worktree
t-2370, natives freshly built): exit 1, gate-summary present.

Starting point this batch: COV006 4 live warnings (down from 5; tree moved
again -- one of the previously-flagged test edges is no longer present, not a
new class), COV007 37 live warnings across 24 files (unchanged from the prior
batch's re-measurement).

COV006 -- confirmed the gate's own docstring (`frob/gates/__init__.py::
_cov006`) states WARN severity is deliberate: `frob.graph.callgraph` is an
explicitly best-effort, name-based resolver, so a miss is "a prompt to double
check, not proof the binding is wrong." This is unconditional -- there is no
count-based exception. COV006 MUST NOT be promoted to ERROR, ever, regardless
of how many times it is burned to zero. Confirmed this is the same class
T-2550 already diagnosed (public entry point several hops from the private
target, invisible to the name-based call graph).

Wrote 4 individual `frob:waive COV006` comments, one per live finding, each
citing the T-2550 class and confirming direct-read reachability:
  - tests/test_gates.py::TestCoverageGate.test_cov006_third_file_reachable_chases_relative_import_reexport
    -> src/frob/gates/__init__.py::_cov006_resolve_relative_module
  - tests/test_gates.py::TestFixEngineTierA.test_tick006_renamed_draft_resolved_via_git_not_refiled
    -> src/frob/gates/_fix_engine.py::_resolve_via_git_rename
  - tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty.test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
    -> src/frob/tickets/_land_git_ops.py::_do_wip_commit
  - tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr.test_wip_commit_failure_logs_stderr
    -> src/frob/tickets/_land_git_ops.py::_do_wip_commit

Re-measured after writing: COV006 warning count is 0 (34 note-tier, all
already/newly waived). Each waiver comment re-verified present with no
trailing space before its `\` continuation and no embedded quote in its
`reason=` string (T-2857 hazard). NOT promoting COV006's severity -- zero is
necessary but the docstring makes it permanently insufficient. This code stays
WARN forever; only the individual findings get burned down as they appear.

Adding the four `frob:ticket T-2370` edges these changes needed also
surfaced COV002 (symbol changed with no open-ticket edge) on the enclosing
test classes/methods -- fixed by placing `frob:ticket T-2370` directly above
each changed class/method (a blank-line-separated placement inside the class
body, after its docstring, did NOT satisfy COV002; the directive must
immediately precede the changed symbol).

COV007 -- completed the full-file pass across all 24 previously-partially-
sampled files (the prior batch sampled 5; this batch read the remaining 19
directly: graph_runner.py, _close_cmd.py, _mutate.py, _new.py, _query.py,
verify_runner.py, _arch_schema.py, _milestone.py, _support.py, _reap.py,
_coverage_refresh.py, tickets/__init__.py, _archive.py, _leases.py, _scope.py,
_backpressure.py, _quarantine.py, _selection.py, _worker.py,
_capability_python.py, plus re-confirming the previously-sampled
_rapid_sweep.py/_lifecycle.py/_ledger_mirror.py/_store_migrate.py).

Method: for each of the 37 flagged private symbols, read its own `frob:doc`
anchor, then grepped that anchor's target doc file for a `frob:describes`
directive individually naming the private symbol by its qualified path.
Result: about a third resolve to an individually-named `frob:describes`
anchor (e.g. `_scope_add_live_lease_conflict`, `_attribute_new_findings`,
`_worker_backpressure_reason`) -- unambiguous HONEST WAIVE candidates, no
further check needed.

The remaining ~two-thirds (e.g. everything in `_support.py`, `_backpressure.
py`, `_quarantine.py`, `_selection.py`, `_reap.py`, `_ledger_mirror.py`) do
NOT carry an individually-named `frob:describes` block, but ALSO do not
match the T-2810 duplicate-anchor bug shape: T-2810's fix removed a private
helper's `frob:doc` comment only where a PUBLIC sibling in the SAME FILE
already carried the IDENTICAL directive as a genuine, meaningless copy. Here
the pattern is different and consistent across every file checked: MANY
symbols -- public and private alike -- in the same file all cite the SAME
section-level anchor (one conceptual feature, e.g. "backpressure",
"quarantine circuit breaker", "adapter capability contract"), each comment
marking where in the code that piece of the section's behavior lives. This
is the same convention this repo already decided is legitimate for
`vet.md` (T-2810 explicitly declined to touch it) -- a REG008-shaped,
many-symbols-one-section documentation style, not a duplicate. No file in
the remaining 19 exhibited T-2810's actual bug shape (an exact-duplicate
directive on a private helper that a public sibling in the same file already
carries to the identical anchor with nothing left for the private one to
add).

DISPOSITION: COV006 batch closed out this session (0 live warnings, 4
waivers landed, promotion permanently refused per the gate's own docstring).
COV007 is NOT at zero (37 live warnings, unchanged) and stays open --
every one of the 24 files is now individually characterized as either (a)
an honest waive candidate with an individually-named `frob:describes`
anchor, or (b) an honest waive candidate under the many-symbols-one-section
convention this repo has already accepted (vet.md precedent). ZERO of the
37 need a code fix; zero exhibit the T-2810 bug. The remaining work is
writing 37 individually-reasoned `frob:waive COV007` comments (one per
symbol, citing its specific doc anchor) -- pure typing/attribution work, no
further triage needed. Suggested next batch: write those 37 waivers in
groups of ~8-10 per file cluster, re-measuring after each group per the
T-2857 silent-drop hazard, then re-run this same `--only coverage --json`
command for a true zero before considering COV007's promotion (COV007's own
docstring does NOT forbid promotion the way COV006's does -- it is fine to
promote once genuinely at zero).

Requeuing (not closing): COV006 is functionally done but the ticket's own
acceptance criteria bundle both codes, and COV006 can never satisfy
criterion [1] (promote to error) by design. Recommend splitting this ticket
in the next batch: close COV006's WARN-zero burn-down as ticket-scoped work
with an explicit `frob:waive` on acceptance criterion [1] citing this
docstring, and keep a separate ticket alive for COV007's waiver-writing
pass through to promotion.

## Failure log
- 2026-08-22 attempt 1: bundles two codes with incompatible closure shapes: COV006 can never satisfy a promote-to-error criterion (its own docstring forbids it permanently, best-effort name-based resolver) while COV007 needs a 37-item individual waiver pass; split into T-2865 (COV006 waivers, done in this worktree) and T-2866 (COV007 waiver pass plus promotion)
- 2026-08-30 attempt 2: Already split into T-2865 (COV006 waivers, DONE) and T-2866 (COV007: 37 individually-reasoned waivers across 24 files, then promote) per this ticket's own Failure log from a prior attempt. T-2370 itself can never satisfy its bundled acceptance (COV006 must NEVER promote per its own gate docstring) and the COV007 half is still open work tracked in T-2866, not something to re-attempt here.

## Drop reason
- 2026-08-30: Superseded: already split into T-2865 (COV006, done) and T-2866 (COV007 remainder + promotion, queued). T-2370 cannot close as written because COV006 must never be promoted per its gate docstring.
