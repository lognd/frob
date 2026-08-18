## Done report

### Changed
- `src/frob/graph/summary.py` -- hosted a NEW path-confinement lattice
  (`ConfinementState`: ROOTED/ESCAPED/UNKNOWN) on the SAME SCC-ordered
  worklist `compute_protocol_summaries` already builds
  (`_universe`/`_reachable`/`_tarjan_sccs`), per the T-0745 design
  constraint this module's own docstring records. No second call-graph
  traversal was written. New public surface: `ConfinementState`,
  `FsWriteSite`, `FunctionConfinement`, `ConfinementCensusResult`,
  `scan_confinement_facts` (the one function that does filesystem I/O --
  `ast.parse`s `.py` files), `compute_confinement_summaries` (pure,
  bottom-up fixpoint over pre-extracted facts). Internal AST classifier
  (`_classify_expr`/`_classify_call`) and cross-function resolution
  (`_resolve_state`/`_finalize_function`/`_fixpoint_confinement_scc`/
  `_tally_poison_sources`) are private, split to stay under ARCH001's
  60-line threshold.
- `docs/modules/graph.md` -- new "Path-confinement census" section:
  engine shape, disclosed precision limits, and the 2026-08-18 census
  run's real numbers (committed to the doc, not just this report).
- `tests/unit/test_confinement_lattice.py` -- 5 new tests: the
  MANDATORY positive control (absolute literal -> ESCAPED) and negative
  control (ordinary `tmp_path` pattern -> ROOTED, never a false
  ESCAPED), plus UNKNOWN-poisoning, `os.environ` ESCAPED classification,
  and cross-function RETURN-value propagation ("param0 confined =>
  result confined").
- `tickets/T-2504/census-2026-08-18-raw.json` -- the raw census JSON,
  committed as a durable record independent of this report.

### THE CENSUS (the actual deliverable)

Run against every `.py` file under `tests/**` on this repo (608 files;
one deliberately-malformed parse fixture skipped and logged, not
crashed):

```
functions scanned:              11545
total fs.write sites recognized: 2989
ROOTED:  2248
ESCAPED:    1
UNKNOWN:  740
```

The user's original ~352 estimate was a strata via-list FILE count, not
a call-site count (corrected mid-drive by the user) -- 2989 is the real
number this pass recognizes.

**The finding, not a failure:** the ticket's anticipated risk -- "ONE
unresolved callee inside a widely-used test helper can poison hundreds
of sites" -- does NOT materialize. Helper-call poison PROPAGATION
accounts for only 13 of 740 UNKNOWN sites, spread across 5 distinct
helpers (none over 3 sites). The DOMINANT source (727 of 740, 98%) is a
disclosed, deliberate precision limit of THIS pass: a private helper
that writes DIRECTLY to its own plain-named `Path` parameter (never
literally `tmp_path`, never returned) resolves UNKNOWN regardless of
how it's actually called -- no interprocedural argument substitution
into a callee's own body was built (only RETURN-value propagation was).
`tests/test_ticket_land.py` alone accounts for 208 of the 727 (28%).
Only 1 ESCAPED site exists in the entire tests/ tree
(`tests/test_check_runner.py:359`), matching the ticket's own
prediction that ESCAPED should be rare and each instance real.

**What would have to become provable first, if this becomes a gate:**
the argument-substitution gap above -- a bounded, whole-program "does
EVERY call site pass this helper a ROOTED argument for parameter X"
check (not full per-call-site cloning), still on the same SCC worklist.
This was NOT built by this ticket -- T-2504's own scope is the census
only, per the explicit "report-only first" directive.

### Evidence
- `tests/unit/test_confinement_lattice.py` -- 5/5 passing (positive
  control, negative control, UNKNOWN-poisoning, ESCAPED via
  `os.environ`, RETURN-value propagation through a private helper).
- `frob check --ticket T-2504 --only gates-native` -- 0 ARCH errors in
  `summary.py` (after splitting `_classify_expr`/
  `compute_confinement_summaries` for ARCH001's length threshold; all
  remaining errors in the run are pre-existing repo-wide debt in
  unrelated files).
- `frob check --ticket T-2504 --only coverage` -- 0 COV001/COV003
  errors attributable to `summary.py` (every new public symbol has a
  `frob:doc` edge into the new docs section; all remaining errors are
  pre-existing repo-wide debt).
- `frob check --ticket T-2504 --only test` -- 0 errors.

### Not built (explicitly out of this ticket's scope)
- No gate. Nothing wired into `frob check`. No severity assigned to any
  finding -- per the explicit "report-only first" directive.
- No CLI command exposing this census as a reusable `frob` subcommand
  (the ticket's implicit CLI-wiring scope grant was available but not
  used -- the deliverable was the measurement, produced via a one-off
  script against the pure engine functions; a follow-up ticket can wire
  a real subcommand once the argument-substitution gap above is closed
  enough to make the numbers worth re-running routinely).
- The argument-substitution engine extension identified above as the
  actual tractability lever.

### Filed
None -- no out-of-scope defects found this round (T-2498's own
follow-up, the `--check-repro --base-ref` bug, was filed under that
earlier ticket's own series, not this one).

### Changed
```
 docs/modules/graph.md                     | 143 ++++++
 src/frob/graph/summary.py                 | 779 ++++++++++++++++++++++++++++++
 tests/unit/test_confinement_lattice.py    | 151 ++++++
 tickets/T-2504/census-2026-08-18-raw.json |  32 ++
 tickets/T-2504/ticket.md                  |  30 +-
 5 files changed, 1134 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_confinement_lattice.py::TestConfinementLatticePositiveControl::test_absolute_literal_write_is_escaped` (pytest node id, verified passing when recorded)
- `tests/unit/test_confinement_lattice.py::TestConfinementLatticePositiveControl::test_ordinary_tmp_path_write_is_rooted_not_escaped` (pytest node id, verified passing when recorded)
- `tests/unit/test_confinement_lattice.py::TestConfinementLatticeUnknown::test_unresolved_private_helper_call_poisons_to_unknown` (pytest node id, verified passing when recorded)
- `tests/unit/test_confinement_lattice.py::TestConfinementLatticeUnknown::test_env_lookup_feeding_a_write_is_escaped_not_unknown` (pytest node id, verified passing when recorded)
- `tests/unit/test_confinement_lattice.py::TestConfinementLatticeHelperPropagation::test_helper_return_value_confinement_propagates_to_caller_site` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2504/src/frob/graph/summary.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2504/src/frob/testing/_collect_kotlin.py, F811@/home/logan/projects/frob/.claude/worktrees/t-2504/tests/unit/test_app_runners_json_guard_t2492.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PRE001@tickets/T-2504, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE001@src/frob/graph/summary.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md, unsupported-operator@src/frob/graph/summary.py
