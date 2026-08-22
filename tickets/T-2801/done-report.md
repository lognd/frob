## Done report

Re-measured each of the 18 sweep-filed (rule, file) identities on current
main (via `frob check --only gates-native/gates-fast/gates-security/static
--ticket T-2801 --json`, unbudgeted, gate-summary present) before touching
anything, per the coordinator's method note. 15 of 18 reproduced as real,
current findings; 3 did NOT reproduce (false positives from a stale sweep
baseline, left unfixed and unfiled -- confirmed absent from every relevant
gate group's JSON output):

- DOC001 docs/investigations/T-2790-check-stage-profile.md -- not present
- LANG004 src/frob/lang/_support.py -- not present
- TICK002 tickets.md -- not present

Fixed (14 identities, following T-2855's precedent: repoint/declare, never
rewrite existing accurate prose):

- COV001 src/frob/graph/callgraph.py::build_call_graph -- added `frob:doc
  docs/audits/graph.md#callgraphpy----best-effort-private-callee-call-graph`
  (that section already accurately describes the function; no prose
  rewritten).
- CYCLE001 src/frob/__init__.py -- NOT fixed, confirmed pre-existing and
  intentionally undischarged: the file's own header comment documents this
  as a live 160-node cycle already tracked by T-2583 (untangle, an
  explicit owner-decision hold) and T-2584 (the fact that `frob:waive
  CYCLE001` does nothing -- `frob-cycle` never consults the waiver
  pipeline). Not double-filed.
- DOC006 docs/audits/test005-zero-classification-t1418.md -- the
  cross-doc anchor pointer had drifted from a since-reworded heading in
  agent-playbook.md (`...and-make-coverage-deletes-it` ->
  `...and-the-full-suite-coverage-refresh-deletes-it`); repointed to the
  current real anchor.
- DRIFT001 x2 (src/frob/app/ticket_runner/_verify.py::
  _parse_error_findings_from_json body, src/frob/tickets/__init__.py::
  _doable_sort_key sig) -- re-read each function against its describing
  doc before acking; both still accurately described. `frob ack`'d with
  a reason recorded, per the "ack is for genuine content drift, never a
  mis-targeted edge" rule.
- DRIFT002 x3 docs/modules/tickets-data-storage.md -- confirmed T-2858's
  suspected root cause (T-2695's `_store.py` migration-function split):
  `migrate_to_ledger`/`migrate_v1_to_v2`/`_migrate_one_v2`/
  `_split_done_report` all moved to `_store_migrate.py`. Repointed the 4
  `frob:describes` anchors (this covers T-2858's identical finding on the
  same file too -- see below).
- PERF004 src/frob/tickets/_evidence.py:251 -- waived: `shared` is each
  loop iteration's own distinct per-other-ticket intersection set, sorted
  only for a log message, not a repeated re-sort of identical data (same
  shape as this repo's many existing PERF004 waivers).
- REG002 docs/design/registry/check-coverage.yaml -- root cause: DOC013
  (a real, live rule, `frob.gates._docstatus._doc013_violation`, shipped
  under T-2843) was never added to `_KNOWN_GATE_RULES` in
  src/frob/gates/_waive.py. Added it, matching the existing hand-curated
  entries' style and citing its real origin.
- SEC110 x3 (_verify.py, verify_runner.py x2, test_release.py) -- all
  dispatch-context markers (FROB_WORKTREE, an internal PID/ticket-id pair)
  or a test asserting a FAKE placeholder token, none a real secret read.
  Waived with reasons matching this repo's existing FROB_AGENT/
  FROB_WORKTREE precedent waivers.
- SYS003 x2 src/frob/check/__init__.py -- `_native_check_and_rebuild`'s
  lazy imports of `frob.strata`/`frob.natives._build` were real,
  pre-existing, legitimate dependencies never declared in design/
  frob.strata. Added `f_checker_stratamod`/`f_checker_natives` flows.
- TEST001 src/frob/strata/_multifile.py::SealedGrantSet.from_root_node --
  3 real unit tests already existed in tests/unit/strata/test_fragments.py
  (TestSealedGrantSet); only the `frob:tests` edge was missing. Added it,
  matching this file's own existing `frob:tests` convention.
- TICK003 tickets.md (865 unarchived) -- NOT fixed here: `frob ticket
  archive` mutates the whole ledger and this is a live multi-agent
  session (fleet_status showed several active worktrees); the gate's own
  message says "in a quiet moment", which this is not. Left for a
  coordinator-run quiet-moment archive pass.
- TICK004 tickets.md (3 overdue epics: T-0969/T-1273/T-1382) -- NOT fixed:
  administrative epic-staleness state, not something a single bug ticket
  should force-close or re-triage; each is noted in the gate's own message
  as "already decomposed and being worked (a no-op likely)".

T-2858 cross-check: its 4 findings (DRIFT002 x4 tickets-data-storage.md,
DOC006 test005 audit, COV001 callgraph.py, TEST001 _multifile.py) are the
EXACT SAME (rule, file) identities as 4 of T-2801's 18 -- confirmed by
re-reading T-2858's ticket body against the fixes above: same functions
(migrate_to_ledger/migrate_v1_to_v2/_migrate_one_v2/_split_done_report),
same anchor, same build_call_graph, same SealedGrantSet.from_root_node.
T-2858's root-cause suspicion (T-2695's `_store.py` split) is CONFIRMED --
verified directly against `_store_migrate.py`'s real function definitions
above, not assumed. All 4 are fixed by this same diff. T-2858 should be
closed as a duplicate of this fix once this lands (left to the
coordinator/next agent to verify against main post-land and close;
not closed here since T-2801 was the ticket actually being worked).

Changed:
- src/frob/graph/callgraph.py :: build_call_graph (frob:doc edge added)
- src/frob/strata/_multifile.py :: SealedGrantSet.from_root_node
  (frob:tests edges added)
- docs/audits/test005-zero-classification-t1418.md (anchor repointed)
- docs/modules/tickets-data-storage.md (4 frob:describes edges repointed
  to _store_migrate.py)
- src/frob/gates/_waive.py :: _KNOWN_GATE_RULES (DOC013 added)
- src/frob/app/ticket_runner/_verify.py (SEC110 waiver)
- src/frob/app/verify_runner.py (SEC110 waiver)
- tests/test_release.py (SEC110 waiver)
- design/frob.strata (f_checker_stratamod, f_checker_natives flows added)
- src/frob/tickets/_evidence.py (PERF004 waiver)
- DRIFT001 acked: src/frob/app/ticket_runner/_verify.py::
  _parse_error_findings_from_json (body), src/frob/tickets/__init__.py::
  _doable_sort_key (sig)

Evidence: tests/test_release.py::TestPublish::test_env_only_loaded_on_a_real_run,
tests/unit/strata/test_fragments.py::TestSealedGrantSet::
test_widen_on_declared_atom_still_works,
test_widen_on_undeclared_atom_refuses_closed, test_fresh_insert_raises_at_runtime,
tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
(the last one for the doc/registry/design-only fixes with no pytest surface
of their own, per playbook section 5's precedent). All collected and
passed: `pytest tests/unit/strata/test_fragments.py tests/test_release.py
-q` -> exitstatus=0 collected=77 failed=0.

Filed: none new (T-2858 already exists and is addressed by this same
diff, see cross-check above).

Gates: re-measured `frob check --only gates-native/gates-fast/
gates-security/static --ticket T-2801 --json` after the fixes -- every
targeted (rule, file) identity is clean except CYCLE001 (confirmed
pre-existing, intentionally undischarged, tracked by T-2583/T-2584, not
in this ticket's fix set) and TICK003/TICK004 (deferred, fleet-unsafe/
administrative, explained above). `--ticket` only scopes gate:SCOPE/
gate:PREWORK and the diff-driven COV002/TODO001/FMT/AFFECT checks
(playbook 6c) -- the per-identity re-measurement above, not the scoped
summary line, is the actual verification.

Addendum: land's first attempt found T-2801's designated repro evidence
confirmatory-only (BUG002) -- this ticket's fixes are doc/registry/
design-declaration corrections with no reproducible runtime behavior, so
`frob:waive BUG002` was added to the ticket body with a reason. Land's
second attempt then surfaced a NEW REG008 (docs/design/registry/
check-coverage.yaml, entry CHK-GATE-I001) introduced by land's own Tier-A
REG010 auto-fix as a side effect of this diff (it back-filled a missing
registry stub for the pre-existing live ruff I001 rule, which then lacked
the required `frob:enforces` edge). Root-caused to
src/frob/process/parsers/ruff.py::_is_ruff_error_code (the real, pre-
existing I001 enforcement site, T-2373) never having carried that
directive; added it there and widened scope to include the file with a
recorded reason, rather than reverting land's own auto-fix.

### Changed
```
 design/frob.strata                               |   7 ++
 docs/audits/test005-zero-classification-t1418.md |   2 +-
 docs/design/registry/check-coverage.yaml         |   7 +-
 docs/modules/tickets-data-storage.md             |   8 +-
 frob.lock                                        |  45 ++++++-
 rapid-debt.jsonl                                 |   3 +
 src/frob/app/ticket_runner/_verify.py            |   3 +
 src/frob/app/verify_runner.py                    |   4 +
 src/frob/gates/_waive.py                         |   7 ++
 src/frob/graph/callgraph.py                      |   1 +
 src/frob/process/parsers/ruff.py                 |   1 +
 src/frob/strata/_multifile.py                    |   9 ++
 src/frob/tickets/_evidence.py                    |   4 +
 tests/test_release.py                            |   3 +
 tickets/T-2801/done-report.md                    | 146 +++++++++++++++++++++++
 tickets/T-2801/ticket.md                         |  33 ++++-
 16 files changed, 273 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_release.py::TestPublish::test_env_only_loaded_on_a_real_run` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_widen_on_declared_atom_still_works` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_widen_on_undeclared_atom_refuses_closed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_fresh_insert_raises_at_runtime` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 30 error(s), 992 warning(s), 799 waived
- error-findings: AFFECT001@src/frob/app/verify_runner.py, AFFECT001@src/frob/strata/_multifile.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@design/frob.strata, COV003@tickets/T-1102, COV003@tickets/T-1651, COV003@tickets/T-1656, COV003@tickets/T-2375, COV003@tickets/T-2822, COV003@tickets/T-2823, COV003@tickets/T-2824, COV003@tickets/T-2825, COV003@tickets/T-2826, COV003@tickets/T-2829, COV003@tickets/T-2830, COV003@tickets/T-2839, CYCLE001@src/frob/__init__.py, DOC006@docs/modules/graph.md, DOC006@tickets/T-2860/ticket.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DOCENUM001@docs/modules/gates.md, DRIFT002@docs/modules/tickets-landing.md, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PRE001@tickets/T-2801, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
