## Done report

T-4520 -- generate the explore/quality/design/ops group parsers from the
flat parsers so they cannot diverge

WHAT CHANGED

src/frob/_cli_parsers/_design.py
  _add_design_parser's sys subparser now calls all seven
  _add_sys_*_parser helpers (_add_sys_plan_and_export_parsers,
  _add_sys_doc_and_audit_parsers, _add_sys_trace_parser,
  _add_sys_threats_parser, _add_sys_capacity_parser,
  _add_sys_shrink_parser, _add_sys_init_parser) instead of only the
  first two. This is exactly the flat _add_sys_parser's (_misc.py, out
  of scope) own call list, in the same order.

src/frob/_cli_parsers/_ops.py
  Extracted _populate_process_actions(process_sub) out of the inline
  "process reap" block in _add_ops_parser. Added a new flat top-level
  _add_process_parser(sub) that calls the same populate function --
  "frob ops process reap" used to be the only form; "frob process reap"
  is now its flat twin.

src/frob/_cli_parsers/_explore.py
  Added _mirror_subparser(dest_sub, flat_sub, name): registers an
  already-built flat ArgumentParser object directly into a group's own
  _SubParsersAction.choices/_choices_actions bookkeeping, so the group
  leaf IS the flat parser (identical option strings, help, dispatch
  dest by construction). Used for map/outline/xref (whose flat
  definitions in _core.py are inline add_argument calls with no
  _populate_* helper to call a second time -- _core.py is out of this
  ticket's scope to restructure) and for the new docs-search flat
  twin. Added _add_docs_search_parser(sub) (flat) and
  _populate_docs_search_args(search_p) (shared helper); "frob
  explore docs-search" used to be the only form.

src/frob/_cli_parsers/_root.py
  Imported _add_docs_search_parser and _add_process_parser directly
  from their owning submodules (frob._cli_parsers._explore /
  frob._cli_parsers._ops), not through the package __init__.py --
  that file is owned by a concurrent ticket (the --skip ticket) for
  the duration of this one, so it was left untouched.
  Reordered _add_analysis_subparsers so _add_outline_parser,
  _add_map_parser, _add_xref_parser, and the new
  _add_docs_search_parser run BEFORE _add_explore_parser -- required
  because _add_explore_parser now mirrors their already-built parser
  objects; they have to exist in `sub` first.
  Added _add_process_parser(sub) to _add_workflow_subparsers, next to
  _add_sys_parser.

docs/design/cli-regrouping.md
  Added a "Generation rule -- groups are DERIVED, never hand-mirrored
  (T-4520)" section: records the 2026-09-16 owner decision (keep the
  groups, generate from the flat parsers, option b), the measured
  divergence numbers from the ticket body, the two generation
  mechanisms used (call-the-same-helpers vs mirror-the-parser-object)
  and which verbs use which and why, the docs --search exception, and
  a note that frob --help's top-level listing text is unchanged.

tests/unit/test_cli_group_parity.py (new)
  Walks _root._build_parser()'s live tree. For every member of
  explore/quality/design/ops, asserts the group leaf's option strings
  and (recursively) subcommand set are identical to its flat twin.
  Explicit tests for: design sys carrying all nine flat subverbs
  (plan, export, doc, audit, trace, threats, capacity, shrink, init);
  design docs being a documented subset of flat docs (missing exactly
  --search); ops process reap and explore docs-search each having a
  flat twin now that group-only leaves are gone.

MEASURED NUMBERS

Before: design sys wired 2 of 7 helper calls (4 of 9 counted subverbs
per the ticket's audit -- audit and doc are one helper call each, so
"4 subverbs from 2 calls" plus 5 missing subverbs from 5 missing
calls). ops process reap and explore docs-search had no flat form.
map/outline/xref were hand-redeclared a second time in _explore.py,
byte-for-byte matching _core.py's inline declarations by luck, not by
construction.

After: 30 new pytest cases (test_cli_group_parity.py) all pass,
confirming every group leaf across all four groups is either
identical to its flat twin or (docs only) an intentionally documented
subset. design sys now has all 9 subverbs under the group. ops
process and explore docs-search both have flat twins.

VERIFICATION RUN (all inside the worktree, PYTHONPATH=<WT>/src)

pytest -q -p no:cacheprovider -p no:xdist tests/unit/test_cli_group_parity.py
  30 passed

pytest -q -p no:cacheprovider -p no:xdist tests/unit/test_main_entry.py
  48 passed

pytest -q -p no:cacheprovider -p no:xdist tests/unit/test_app_runners_process.py tests/unit/test_process_reap.py
  52 passed

Combined run (test_cli_group_parity + test_main_entry +
test_app_runners_process + test_process_reap): 130 passed, 0 failed.

ruff check <touched files>: All checks passed.
ruff format --check <touched files>: all formatted (one file needed
  `ruff format` applied once, then verified clean).
ty check <touched files>: All checks passed (0 diagnostics) -- one
  narrowing issue in the new test file (choices access on a
  _SubParsersAction | None union) was fixed by an early return instead
  of the ternary-to-None pattern.

OUT OF SCOPE / FOUND BUT NOT FIXED

- src/frob/_cli_parsers/_core.py's _add_map_parser/_add_outline_parser/
  _add_xref_parser build flags as inline add_argument calls rather than
  a _populate_*_args(parser) helper the way docs/exports/scaffold do.
  This forced the object-reuse (_mirror_subparser) mechanism for
  explore's map/outline/xref instead of the simpler call-the-same-
  helper mechanism used for design sys. Not fixed here: _core.py is
  outside T-4520's declared scope. A follow-up ticket to split those
  three into _populate_map_args/_populate_outline_args/
  _populate_xref_args (matching the docs/exports precedent) would let
  a future ticket drop _mirror_subparser's private-API argparse
  bookkeeping entirely in favor of the simpler shared-function
  pattern used everywhere else in this package. Not filed as a new
  ticket per the amended instructions for this dispatch (no frob
  ticket verbs were run beyond ticket work/start).
- design sys's "call every _add_sys_*_parser helper" mechanism is not
  FULLY automatic: adding an eighth helper to the flat _add_sys_parser
  (_misc.py) still requires a matching added call in _design.py, since
  _misc.py is out of this ticket's scope to restructure into a
  registry _design.py could import and iterate. The parity test is the
  safety net that turns a missed addition into a loud test failure
  instead of a silent one -- documented explicitly in
  docs/design/cli-regrouping.md's new section.

DID NOT TOUCH src/frob/_cli_parsers/_check.py or
src/frob/_cli_parsers/__init__.py, per the dispatch note that another
agent is editing those two files.

git -C /home/logan/projects/frob/.claude/worktrees/t-4520 status --short
  (empty -- everything committed, HEAD ac2a6a4e9)

READY.

### Changed
```
 docs/design/cli-regrouping.md       |  73 ++++++++++++
 src/frob/_cli_parsers/_design.py    |  24 +++-
 src/frob/_cli_parsers/_explore.py   | 102 ++++++++++-------
 src/frob/_cli_parsers/_ops.py       |  36 +++++-
 src/frob/_cli_parsers/_root.py      |  20 +++-
 tests/unit/test_cli_group_parity.py | 220 ++++++++++++++++++++++++++++++++++++
 tickets/T-4520/done-report.md       | 160 ++++++++++++++++++++++++++
 tickets/T-4520/ticket.md            |  15 ++-
 8 files changed, 602 insertions(+), 48 deletions(-)
```

### Evidence
- `tests/unit/test_cli_group_parity.py::TestDesignGroupParity::test_sys_carries_every_flat_subverb` (pytest node id, verified passing when recorded)
- `tests/unit/test_cli_group_parity.py::TestDesignGroupParity::test_full_member_matches_its_flat_twin` (pytest node id, verified passing when recorded)
- `tests/unit/test_cli_group_parity.py::TestOpsGroupParity::test_process_reap_has_a_flat_twin` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 32 error(s), 4955 warning(s), 979 waived
- error-findings: ARCH103@src/frob/app/config.py, ARCH103@src/frob/doctor.py, CROSSTICKET001@docs/commands/check.md, CROSSTICKET001@docs/modules/app.md, CROSSTICKET001@docs/modules/tickets-landing.md, CROSSTICKET001@src/frob/__main__.py, CROSSTICKET001@src/frob/_cli_parsers/_check.py, CROSSTICKET001@src/frob/app/_config_external.py, CROSSTICKET001@src/frob/app/check_runner.py, CROSSTICKET001@src/frob/app/config.py, CROSSTICKET001@src/frob/app/ticket_runner/_verify.py, CROSSTICKET001@src/frob/gates/__init__.py, CROSSTICKET001@src/frob/tickets/_land.py, CROSSTICKET001@src/frob/tickets/_land_git_ops.py, CROSSTICKET001@src/frob/tickets/_leases.py, CROSSTICKET001@tests/unit/test_land_merge_conflict_drop.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC012@docs/commands/, MILE001@tickets.md, PERF004@src/frob/doctor.py, PERF004@tests/unit/test_cli_group_parity.py, PRE001@tickets/T-4520, REF002@src/frob/vet/_capability_registry/_dotnet_bcl.py, TICK010@/home/logan/projects/frob/.git/frob-leases/T-3232.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-3259.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4524.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4550.json, WIRE001@tests/unit/test_cli_group_parity.py, WIRE002@src/frob/dup/_legacy_cs.py, invalid-argument-type@tests/unit/test_ticket_runner_land_cmd_flags.py, unresolved-attribute@tests/unit/test_land_stackdump.py
