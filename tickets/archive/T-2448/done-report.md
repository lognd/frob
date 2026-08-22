## Done report

Changed:
- src/frob/gates/_rule_id_scan.py (new gate_rule_registry_violations:
  find_unregistered_rule_ids run repo-wide, T-2391 fail-loudly UNRESOLVED
  for a missing src/ layout or any scan crash, never a silent 0)
- src/frob/gates/_sys.py (sys_gate: wired GATERULE001 in BEFORE the
  design/ early-return -- a registry-completeness check that must not be
  gated behind strata design-language presence, unlike SELFAUDIT001)
- src/frob/gates/_waive.py (_KNOWN_GATE_RULES: registered GATERULE001)
- tests/gates/test_rule_id_scan_branches.py (TestGateRuleRegistryGate,
  4 new tests: clean-repo silence, a real unregistered-id finding, the
  missing-src/-dir UNRESOLVED positive control, and a scan-crash
  UNRESOLVED positive control)

THE PATTERN, NAMED (per coordinator instruction): this is the THIRD
instance today of detection that exists, is tested, and works, but is
wired somewhere nobody looks -- the three inert CLI flags (T-2387,
caught only by a unit test nobody ran), the inert frob:waive directives
(T-2438), and now find_unregistered_rule_ids (T-1937): built, tested,
proven correct by its own drift-lock test, but only ever consulted
scope-limited at one ticket's own close/land preflight. All three share
the same shape -- the mechanism exists and is CORRECT, but nothing
routes attention to its output until something else already broke.
Worth a name and a standing item to grep for the shape ("does this
detector have a caller that runs unconditionally, or only on request"),
not just three independently-discovered instances.

Wiring decision, and why it deviates from the ticket's original scope:
T-2390's epic-decomposition series held a near-continuous live lease on
gates/__init__.py (_ALL_GATES/_CANONICAL_GATE_ORDER/_build_thread_jobs/
_STAGE_GROUPS) for most of this ticket's session -- registering a new
TOP-LEVEL gate there was going to mean an indefinite wait. Wired through
the ALREADY-registered "sys" gate (src/frob/gates/_sys.py::sys_gate)
instead: zero changes needed to gates/__init__.py. GATERULE001 runs
BEFORE sys_gate's `design/` early-return specifically because it is a
_KNOWN_GATE_RULES completeness concept, independent of whether a repo
uses the strata design language -- gating it the same way SELFAUDIT001
is gated would silently skip a real check on every repo without a
design/ dir.

Confirmed working end-to-end (not just unit-tested): `frob check --only
sys` against this repo's own real tree reports GATERULE001 on the
pre-existing COV0011 false positive (filed separately as T-2458 --
docstring prose in _gates_schema.py that LOOKS like a rule id, not a
real construction site) -- direct proof the standing gate fires against
production code, and the exact kind of gap it exists to catch.

T-2384 portability: gate_rule_registry_violations resolves `root/src`
at call time from whatever root the caller passes (the normal `frob
check` root resolution, unchanged) -- no hardcoded path or package
name. The one hardcoded-layout assumption (a top-level src/ directory)
lives in the underlying scan_candidate_rule_id_literals
(frob.gates._rule_id_scan, pre-existing, out of this ticket's scope to
remove) -- this ticket's own contribution is making that assumption's
FAILURE explicit (UNRESOLVED) rather than silent, not removing it.

T-2391 fail-loudly, the coordinator's two constraints:
1. A missing src/ (this scan's own coverage boundary) reports
   Severity.UNRESOLVED naming exactly what could not be scanned, not an
   empty/clean result -- pinned by
   test_missing_src_dir_is_unresolved_not_silent_zero.
2. Per-repo, this gate's own scan is now unconditional and complete (no
   partial-coverage lower-bound inside ONE repo run) -- the "4 stale
   worktrees on an old frob version" caveat from the earlier manual
   fleet audit is a DIFFERENT axis (which worktrees CAN run this
   scanner's CODE at all, a frob-version question, not a within-repo
   coverage question) and remains true: any fleet-wide count still
   needs those 4 to upgrade before a "clean" fleet claim is honest. This
   ticket's gate makes every UP-TO-DATE worktree self-check going
   forward; it does not retroactively cover stale ones.

Filed:
- T-2447 DROPPED (not filed by this ticket, but resolved by it): the
  CLAUDE001 gap was already fixed independently by T-1969 (landed
  earlier, unrelated to this session) -- confirmed via a fresh
  find_unregistered_rule_ids(main) scan before touching anything, per
  the coordinator's instruction to check liveness first. The
  rule-bookkeeping worktree T-2447 named was 8 days stale with no live
  process; not touched.
- T-2458: the COV0011 false-positive this ticket's own gate surfaced
  (docstring prose in _gates_schema.py matching the rule-id-shaped
  pattern) -- a pre-existing scanner gap, unrelated to this change,
  confirmed failing on a clean main checkout before any T-2448 edit.

Gates: tests/gates/test_rule_id_scan_branches.py 17/17 pass locally
(excluding test_real_repo_registry_is_complete, which fails on CLEAN
MAIN due to T-2458, unrelated to this ticket). tests/test_gates.py -k
"sys_gate or waive" 60/60 pass. `frob check --only sys` runs cleanly
(reports the known, tracked T-2458 finding, nothing else new).

### Changed
```
 src/frob/gates/_rule_id_scan.py           | 99 +++++++++++++++++++++++++++++++
 src/frob/gates/_sys.py                    | 21 ++++++-
 src/frob/gates/_waive.py                  |  9 +++
 tests/gates/test_rule_id_scan_branches.py | 73 +++++++++++++++++++++++
 tickets/T-2448/ticket.md                  | 21 ++++++-
 5 files changed, 219 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/gates/test_rule_id_scan_branches.py::TestGateRuleRegistryGate::test_clean_repo_is_silent` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestGateRuleRegistryGate::test_unregistered_id_reported_as_error` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestGateRuleRegistryGate::test_missing_src_dir_is_unresolved_not_silent_zero` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestGateRuleRegistryGate::test_scan_crash_is_unresolved_not_silently_swallowed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/gates/_sys.py, ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2448/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2448/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2448/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2448/src/frob/gates/_rule_id_scan.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2448/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2448/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2448, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
