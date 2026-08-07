## Done report

Changed:
- src/frob/strata/_plan.py (new): `plan_obligations`, `PlannedTicket`,
  `PlanResult`, `MARKER_PREFIX`; frontier = unrefined abstract nodes
  (surface.md's "unrefined frontier is exactly the planning frontier"),
  `Verdict.REFUTED` claims (`evaluate_claims` reuse), `THREAT003`
  fired-but-undischarged obligations (`evaluate_threats` reuse), unbound
  boundary/secret constructs (SYS002-style, computed locally since
  `frob.gates` is out of scope for this ticket -- see the module's
  `_UNBOUND_REQUIRED_KINDS` docstring for why the two-line constant is
  duplicated rather than imported).
- src/frob/strata/__init__.py: export `plan_obligations`, `PlannedTicket`,
  `PlanResult`, `MARKER_PREFIX`.
- src/frob/app/sys_runner.py (new): `frob sys plan` CLI runner --
  loads+merges design models, builds/loads the graph snapshot for the
  unbound check, diffs planned markers against every marker already in
  the ticket ledger (`_existing_markers`), and either prints (dry-run
  default) or writes (`--apply`) exactly the delta, parents before
  children so a child's `parent`/`blocked_by` resolves to the parent's
  freshly allocated id.
- src/frob/app/app.py, src/frob/app/config.py, src/frob/__main__.py:
  `sys` subcommand group wired (`frob sys plan [path] [--apply]`),
  mirroring the `graph`-group CLI idiom (T-0046 style).
- docs/commands/sys.md (new) + docs/index.md: command reference, linked
  from the per-command table.
- tests/unit/strata/test_plan.py, tests/system/test_cli_sys_plan.py (new).

Marker design: every planned ticket's body carries exactly one
`sys-plan:<construct-qualname>:<obligation-kind>` line (e.g.
`sys-plan:api:unrefined`, `sys-plan:c1:refuted`, `sys-plan:b1:unbound`).
`_plan.py` is a pure model -> tickets compiler with no I/O; the runner
diffs the freshly compiled marker set against every marker already
present in some ticket body (open OR closed, so a discharged obligation's
ticket is never re-created) before writing anything. Verified: two
consecutive `frob sys plan --apply` runs against an unchanged fixture
repo produce byte-identical `tickets.md` on the second run
(`test_second_apply_is_a_noop`), and `test_idempotent_markers` pins the
same property at the `plan_obligations` unit level.

Frontier semantics:
- unrefined: `Node` with `"abstract"` in `.attrs` and no matching
  `refine` (surface.md's elaboration-time WARNING). Parent ticket
  "Refine abstract component X" + child "Decompose X via refine block",
  `blocked_by` wiring the child on the parent.
- refuted: `evaluate_claims` result with `verdict == Verdict.REFUTED`.
  Scope is the union of `code=` globs for every node named in the
  claim's counterexample path.
- threat: `evaluate_threats(..., view="owasp-top-10")` violations with
  `rule == "THREAT003"` (fired capability, no discharging claim at
  the required rung).
- unbound: boundary/secret construct ids from `load_design_ids` with no
  `frob:channel/boundary/secret`-directive graph edge of the matching
  kind anywhere in the repo (requires a graph snapshot; degrades
  gracefully -- logged WARNING, that one obligation kind is skipped --
  if the graph cannot be built/loaded).

Evidence: 9 pytest node ids recorded via `frob ticket evidence T-0084`
(6 unit, 3 system -- see `evidence:` above).

Filed: none (no out-of-scope work discovered).

Gates: `frob sys plan`'s own new code (src/frob/strata/_plan.py,
src/frob/app/sys_runner.py, tests/unit/strata/test_plan.py) is clean
under `frob check` -- zero COV001/PERF violations attributable to these
files (3 PERF003/PERF004 findings addressed with `frob:waive` directives,
matching the codebase's existing waiver style for bounded/non-join
sort-in-loop patterns; COV001 fixed by adding a `frob:doc` anchor to
`MARKER_PREFIX`). `frob sys plan --apply` end to end against a tmp-repo
fixture with an unrefined abstract node and a REFUTED noflow claim
correctly compiles + writes both tickets and is a no-op on rerun. Full
suite green (`uv run pytest -q`).

## Review round 2 (REJECT -> addressed)

Merged main first (`git merge main --no-edit`, T-0134/T-0135 landed:
`src/frob/gates/__init__.py`, `src/frob/strata/_facts.py`/`_parse.py`/
`_errors.py` moved; tickets.md auto-merged clean, T-0084's own section
unaffected). Rebuilt the native extension (`make core`) and the graph
cache (`frob graph build .`) after the merge.

1. **Marker-detection duplication (blocker).** `_frontier_unbound`'s
   SYS002 join was a line-for-line copy of `frob.gates._sys002`'s
   detection loop. Extracted the shared ~20-line join into ONE neutral
   home: `frob.strata._design_load.unbound_constructs(design_ids,
   snapshot, kinds=UNBOUND_REQUIRED_KINDS) -> tuple[tuple[EdgeKind, str],
   ...]` (raw `(kind, construct_id)` pairs, no output shape baked in).
   Both consumers now call it and render their own output: `_plan.
   _frontier_unbound` builds `PlannedTicket`s, `gates._sys002` builds
   `Violation`s (import kept lazy inside `_sys002`, matching
   `_sys003_one_model`'s existing pattern -- T-0135's note on why
   `sys_gate` must not import `frob.strata` at module scope, since a repo
   with no design dir must never pay the `strata_core` native-extension
   cost). Widened T-0084's `scope` to include
   `src/frob/gates/__init__.py` for exactly this one-function swap
   (removed the now-dead `_SYS002_REQUIRED_KINDS` constant, replaced the
   duplicated body with the shared call). New unit tests:
   `tests/unit/strata/test_design_load.py::TestUnbound` (bound vs.
   unbound construct join, 2 tests).
2. **Threat-frontier test.** Added
   `TestPlanObligations::test_threat_frontier` in
   tests/unit/strata/test_plan.py: a `Node(may=("html_render",))` with no
   discharging claim fires `THREAT003`/CWE-79 (same fixture shape as
   `test_threat.py::TestDischargeCompleteness
   .test_fired_obligation_with_no_claim_is_a_violation`); asserts
   `plan_obligations` emits the `sys-plan:Web:CWE-79:threat` ticket,
   bound via `frob:tests` on `_plan.py::plan_obligations`.
3. **Dropped-ticket preservation test.** Added
   `TestSysPlanCli::test_dropped_ticket_is_not_recreated` in
   tests/system/test_cli_sys_plan.py: `sys plan --apply`, drop the
   `sys-plan:c1:refuted` ticket (`frob.tickets.transition(...,
   TicketState.DROPPED)`), re-plan `--apply`, assert the ledger is
   byte-identical post-drop (the dropped marker is not recreated) and
   the ticket is still exactly one row, still `DROPPED` -- pins the
   module docstring's "a marker match suppresses re-creation regardless
   of the matched ticket's state" claim.
4. Fixed two directive bugs the review's own checks caught along the
   way: a `Class::method` (should be `Class.method`) frob:tests typo on
   the new `unbound_constructs` directives, and a stale graph cache
   (`frob graph build .`) after renaming test classes/methods -- both
   were DRIFT002 gate failures, now clean.

Re-verification: full suite green (`uv run pytest -q`, exit 0, 18 new/
touched-file tests all passing individually and together with
`test_gates.py -k sys002`); `ruff check`/`ruff format --check` clean;
`uv run frob check` now exits 0 (PASS) end to end -- `gates` moved from
FAIL (88 violations, 27 waived) to PASS (84 violations, 30 waived; the
remaining 84 are pre-existing repo-wide findings in files this ticket
never touched -- `frob-arch`/`frob-exports`/`frob-dup` advisories and
PERF findings in `_scenarios.py`/`_threat.py`/`_typosquat.py`/etc., all
already waived or already `pass`-classified before this ticket started;
no stash/checkout comparison was needed since the tool's own severity
classification distinguishes PASS from FAIL directly). Evidence: 13
pytest node ids total (9 from round 1 + 4 new: `test_threat_frontier`,
`TestUnbound::test_unbound_pair`, `TestUnbound::test_bound_excluded`,
`test_dropped_ticket_is_not_recreated`).
