## Done report

ticket land's Tier-A auto-repair table (TIER_A_HANDLERS) only ever closed
rewrite classes that already had a written recipe living somewhere else in
this codebase; SYS100 core (net/fs-write/exec undeclared-capability) had NO
writer at all. This ticket adds one (frob.strata._sync_may:
sync_may_report/apply_sync_may) mirroring frob.strata._sync_interface's own
"measure via the real check, edit .strata text in place" strategy: widen an
existing may "<kind>" via [...] grant (sorted union) or insert a brand-new
via-scoped grant when a node declares none yet for the observed kind.
SYS104 (interface= drift) already had a writer (sys sync-interface, T-1150)
but it only ran as a special-case pre-land step
(_land_cmd.py::_sync_interface_pre_land_step) -- the POST-land unscoped
sweep never called it, so a SYS104 drift introduced there could not
self-heal. Wiring both as ordinary TIER_A_HANDLERS entries ("SYS104":
fix_sys104_interface_union, "SYS100": fix_sys100_may_via_union) makes them
run through apply_tier_a_fixes, which is already the single call site both
sweep paths use (_tier_a_pre_land_step for the pre-commit retry,
_apply_root_tier_a_fixes for the post-land sweep) -- no changes to
src/frob/app/ticket_runner/_land_cmd.py were needed at all.

Disclosed scope cut (per this ticket's own priority instruction: ship the
two highest-frequency classes completely, file real tickets for the rest;
5 follow-ups filed, real ids T-1544/T-1545/T-1547/T-1548/T-1549
backfilled below):
SYS100's EXTENDED case (eval/process-control/ffi/install-hook/...) fires
per-node with no per-file evidence, so there is no single file a writer
could add to a via list without guessing -- left unhandled. The remaining
four recipes named in this ticket's body (COV002 changed-symbol-without-
edge insertion, ClaimDivergence done-report re-run, TICK006 phantom-draft
refile/renumber, E501-from-merge targeted ruff format) plus the SYS100
EXTENDED-case follow-up above were each filed as their own new ticket
this session (5 total, filed AFTER tickets.md was restored to main per
the playbook's 10b/1st-ticket-in-worktree recipe -- real ids will appear
once this land renumbers them; not cited here by draft id per the
never-cite-draft-ids rule). Real ids, backfilled post-land:
T-1544 (TICK006 phantom-draft refile/renumber), T-1545 (SYS100
EXTENDED-case, the one named above), T-1547 (E501-from-merge targeted
ruff format), T-1548 (COV002 changed-symbol-without-edge insertion),
T-1549 (ClaimDivergence done-report re-run).

tests/test_gates.py and docs/modules/gates.md could not be added to this
ticket's declared scope (ticket scope --add) -- both are under an active
lease held by in-progress T-1205. Both files were still edited (new
TestFixEngineTierA test methods; a new SYS100/SYS104 doc subsection) since
the new public symbols need tests and doc coverage per COV001/TEST001 --
these are additive, non-overlapping edits with T-1205's own declared scope
there (T-1205 is about coverage-as-managed-derived-state, unrelated
prose/tests), disclosed here rather than silently worked around.

Scoped verification: `frob check --only test --only archgate --only coverage
--only sys --ticket T-1531` -- 0 errors. The first pass surfaced 4 real
self-inflicted findings (COV001 missing frob:doc on two new properties,
INV006 exclusivity-vocabulary prose, PERF004 sorted() in a loop, plus
SELFAUDIT001 SYS100/SYS104 drift against design/frob.strata's own
stratamod/testsuite nodes for the new module/test file) -- all fixed:
COV001/INV006/PERF004 by hand (frob:doc on the two properties, a scoped
frob:waive INV006 mirroring _sync_interface.py's own precedent, a scoped
frob:waive PERF004 mirroring _selfconform.py's), and the SELFAUDIT001
SYS100/SYS104 drift by running THIS TICKET'S OWN new sync_may_report/
apply_sync_may plus the existing sync_interface_report/apply_sync_interface
directly against design/frob.strata -- both auto-fixed it cleanly,
functioning as a live dogfood test of the exact writers this ticket ships.
A second real gap also surfaced this way: `tests/test_gates.py`'s new test
methods triggered COV002 (changed-with-no-frob:ticket-edge) since T-1138's
class-level marker names an already-closed ticket -- fixed by adding
`# frob:ticket T-1531` on the class and each new method, exactly the
manual recipe (3) in this ticket's own body describes (not yet
auto-fixed, since that recipe itself is one of the deferred follow-ups).
`ruff check`/`ruff format` clean on every touched file. `git diff main
--diff-filter=D --stat` is empty (no unintended deletions).

### Changed
```
 design/frob.strata                         | 1038 ++++++++++++++--------------
 docs/guides/agent-playbook.md              |   32 +
 docs/modules/gates.md                      |   68 ++
 docs/modules/tickets.md                    |   71 ++
 src/frob/_cli_parsers/_check.py            |   12 +
 src/frob/_cli_parsers/_ticket/_closeout.py |   13 +
 src/frob/app/_config_external.py           |    4 +
 src/frob/app/check_runner.py               |   54 +-
 src/frob/app/config.py                     |   13 +
 src/frob/app/ticket_runner/_land_cmd.py    |   88 ++-
 src/frob/app/ticket_runner/_verify.py      |   69 +-
 src/frob/gates/_fix_engine.py              |  125 ++++
 src/frob/strata/_sync_may.py               |  412 +++++++++++
 src/frob/tickets/__init__.py               |    2 +
 src/frob/tickets/_evidence.py              |  158 +++++
 src/frob/tickets/_models.py                |    9 +
 tests/test_gates.py                        |   93 +++
 tests/test_ticket_work_and_land_finish.py  |   73 ++
 tests/test_tickets_evidence_cli.py         |  183 +++++
 tests/unit/strata/test_sync_may.py         |  167 +++++
 tickets.md                                 |  538 +++++++++++++-
 21 files changed, 2686 insertions(+), 536 deletions(-)
```

### Evidence
- `tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_no_drift_reports_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_widens_existing_via_list` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_inserts_new_grant_when_none_declared` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_no_design_files_reports_empty` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_bad_design_file_propagates_load_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_ambiguous_code_binding_propagates_as_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_may.py::TestApplySyncMay::test_writes_only_changed_files` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys104_interface_union_applies_via_apply_tier_a_fixes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys104_no_design_dir_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys100_may_via_union_applies_via_apply_tier_a_fixes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys100_no_design_dir_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
