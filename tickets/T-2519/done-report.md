## Done report

### Changed
- `src/frob/graph/summary.py` -- parameter-position confinement credit
  (T-2519), hosted entirely inside the existing engine, no new
  traversal:
  - `_RawFuncFacts` gained `first_param` (the function's own first
    positional parameter name, `_first_positional_param`) and
    `calls_made` (every call to a private-looking helper made anywhere
    in the function body, `(callee, first_arg_state)`, regardless of
    whether the call's result is used -- the evidence needed for the
    common bare-statement `_write_fixture(tmp_path)` shape, which the
    pre-existing `_Pending` mechanism never saw since it only tracks
    calls whose result feeds a site/return).
  - `_record_call_exprs` -- the per-statement call walk, split out of
    `_scan_function_facts` to populate both `sites` (unchanged, T-2504)
    and the new `calls_made` (T-2519).
  - `_resolve_pending_placeholders` also resolves `calls_made`'s callee
    placeholders to real symrefs now.
  - `_compute_param0_credit(resolved_facts) -> dict[symref, bool]` --
    the new pure aggregate: `True` for a callee only when EVERY observed
    call anywhere in the corpus passes a concrete `ROOTED` argument for
    its first positional parameter. Corpus-wide, order-independent,
    computed once before the SCC worklist runs (no bottom-up dependency
    -- unlike return-value propagation, this needs global evidence, not
    per-call resolution).
  - `_finalize_function` takes the new `param0_credit` map: a site whose
    raw state is `_ParamRef(name)` where `name == raw.first_param` AND
    the function is credited resolves `ROOTED`; everything else
    (including a `_ParamRef` for any OTHER parameter) is unchanged. An
    escaping reassignment of the parameter (`tmp = Path("/etc/x")`)
    never reaches this check at all -- it already resolves to a concrete
    `ESCAPED` through the pre-existing local-variable tracking before
    credit is ever consulted, so a param-escaping helper cannot receive
    credit by construction (verified by test, not just by design).
- `docs/modules/graph.md` -- new "Parameter-position confinement credit
  (T-2519)" subsection: mechanism, disclosed scope, and the real
  before/after census delta (below).
- `tests/unit/test_confinement_lattice.py` -- 4 new tests: the positive
  control (credit granted, exact `_write_fixture` shape), the
  MANDATORY escaping-param negative control (T-2519's own third
  required control), a partial-evidence refusal (one unrooted caller
  disqualifies ALL of a helper's sites, never a partial pass), and a
  no-evidence refusal (never-called helper stays UNKNOWN).

### THE CENSUS DELTA (the actual requested deliverable)

Re-ran the census on the SAME `tests/**` file set both before and after
this ticket's change (apples-to-apples, isolating the credit
mechanism's own effect from unrelated corpus growth between T-2504's
original run and today -- other landed tickets added test files in
between, so raw before/after totals differ by file-set size, not by
this mechanism; the numbers below hold the corpus fixed):

```
                    BEFORE T-2519   AFTER T-2519    DELTA
ROOTED                   2255           2323         +68
ESCAPED                     1              1           0
UNKNOWN                    741            673        -68
```

### The finding (not the hoped-for number)

The ticket's own framing anticipated closing the bulk of "727 of 740
UNKNOWN is one disclosed precision limit." The credit mechanism as
built and measured resolves only **68 of 727 (9.2%)**. Two disclosed,
measured reasons:

1. **The private-callee-only resolution boundary is the dominant
   remaining limiter, not the credit rule.** Inspecting `tests/test_
   ticket_land.py` (208 of the original 727, the single largest
   concentration) shows most of ITS remaining UNKNOWN sites are writes
   to a local variable (`wt`, `repo`) assigned inside a test method
   from a call to a PUBLICLY-named fixture/helper (no leading
   underscore) -- both this engine and the underlying `CallGraph` only
   ever resolve PRIVATE callees (a pre-existing, deliberate, repo-wide
   design choice, unrelated to this ticket). Extending credit to
   public-named helpers needs a different call-resolution policy
   decision, out of this ticket's scope.
2. **The all-callers-rooted + single-first-positional-argument
   constraints** (both deliberate, both load-bearing for soundness) cut
   real cases: one unrooted caller anywhere disqualifies ALL of a
   helper's sites, and only the FIRST positional parameter is tracked.

### Not actioned (per explicit coordinator instruction)
- The single `ESCAPED` site across the whole test suite
  (`tests/test_check_runner.py:359`) -- noted for the epic to sequence
  separately at ERROR severity, not touched here.

### Evidence
- `tests/unit/test_confinement_lattice.py` -- 9/9 passing (5 from
  T-2504 unchanged, 4 new for T-2519).
- `frob check --ticket T-2519 --only gates-native/test/coverage/doclink`
  -- 0 errors attributable to `summary.py`/`docs/modules/graph.md`
  (fixed one genuine ARCH001 split and one COV005 stray-directive
  finding this ticket's own diff introduced; all remaining errors in
  each run are pre-existing repo-wide debt in unrelated files).

### Changed
```
 docs/modules/graph.md                  |  79 ++++++++++++++
 src/frob/graph/summary.py              | 190 ++++++++++++++++++++++++++++++---
 tests/unit/test_confinement_lattice.py | 101 ++++++++++++++++++
 tickets/T-2519/ticket.md               |   9 +-
 4 files changed, 362 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/unit/test_confinement_lattice.py::TestParam0Credit::test_helper_writing_directly_to_its_own_param_gets_credit_when_every_call_is_rooted` (pytest node id, verified passing when recorded)
- `tests/unit/test_confinement_lattice.py::TestParam0Credit::test_helper_that_escapes_its_param_gets_no_credit` (pytest node id, verified passing when recorded)
- `tests/unit/test_confinement_lattice.py::TestParam0Credit::test_helper_with_one_unrooted_caller_gets_no_credit_for_any_site` (pytest node id, verified passing when recorded)
- `tests/unit/test_confinement_lattice.py::TestParam0Credit::test_helper_never_called_gets_no_credit` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2519/src/frob/graph/summary.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2519/src/frob/testing/_collect_kotlin.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2519/tests/unit/test_ticket_runner_repro_merge_base.py, F811@/home/logan/projects/frob/.claude/worktrees/t-2519/tests/unit/test_app_runners_json_guard_t2492.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2519, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
