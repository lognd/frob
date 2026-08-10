## Done report

Changed:
- src/frob/gates/_fix_engine_sync.py::_IFACE_EMPTY_LINE_RE (new)
- src/frob/gates/_fix_engine_sync.py::_iface_find_spans
- src/frob/gates/_fix_engine_sync.py::_IFACE_LEGACY_LINE_RE
- src/frob/gates/_fix_engine_sync.py::_reorder_node_interface_block
- src/frob/gates/_fix_engine_sync.py::_iface_rewrite_parses (new)
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder.test_empty_interface_one_line_form_is_not_read_as_a_name (new)
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder.test_round_trip_every_node_shape_reparses (new)
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder.test_rewrite_that_would_not_parse_is_refused (new)

All four required parts of the diagnosis addressed:

1. _iface_find_spans now recognizes the one-line empty form
   'attr interface=[];' via a dedicated _IFACE_EMPTY_LINE_RE, matched
   BEFORE the legacy per-name regex, yielding a span with ZERO declared
   names instead of a name literally called '[]'. _IFACE_LEGACY_LINE_RE
   also hardened with a negative lookahead against the literal '[]'
   token as defense in depth, independent of match order.

2. Round-trip tests added over every node shape (compact multi-name,
   legacy one-name-per-line, empty) -- rewritten design/frob.strata
   text is re-parsed via strata_core's parse_module and must succeed.
   The empty case is asserted byte-identical (single_clean stays True,
   confirmed both by a dedicated test and by direct measurement against
   the real design/frob.strata below).

3. _reorder_node_interface_block's guard strengthened from
   "multiset preserved" to "multiset preserved AND result parses":
   after the existing Counter check, a new _iface_rewrite_parses()
   helper re-parses the full rewritten file text via
   frob.strata._parse.parse_module and the rewrite is refused (lines
   returned unchanged) if that fails -- not just if the name multiset
   changed. Covered by test_rewrite_that_would_not_parse_is_refused
   (monkeypatches the new guard to force a parse failure and asserts
   the file stays untouched).

4. Investigated per the ticket's own instruction: confirmed by reading
   src/frob/app/ticket_runner/_land_cmd.py that
   _assert_design_loads_pre_land runs BEFORE _tier_a_pre_land_step
   inside _absorb_pre_land_fixes -- the synchronous parse guard checks
   design/frob.strata's state BEFORE the Tier-A rewrite that can
   corrupt it, so it structurally cannot catch corruption the rewrite
   itself introduces. This requires touching _land_cmd.py (land-flow
   ordering), a different file outside T-1900's declared scope
   (src/frob/gates/_fix_engine_sync.py + its test file) -- reported to
   the coordinator, who filed it separately as T-1903 (CRITICAL) with
   this exact measurement. Not touched here per the coordinator's
   explicit instruction to leave it to T-1903.

Verification against the REAL design/frob.strata (current main tip
after this worktree's merge, i.e. after the coordinator's three hand
repairs and every ticket landed since):
- Direct Python invocation of fix_sys_interface_canonical_order(root,
  None) against the worktree's design/frob.strata: pass 1 applies 0
  fixes (the file was already canonical, including its 3 empty-
  interface nodes) and the result still parses via parse_module
  (.is_ok == True). Pass 2 (re-running the same call) also applies 0
  fixes and produces output byte-identical to pass 1's -- confirms the
  double-application idempotence the ticket asked for.
- All 5 tests in tests/unit/gates/test_sys_interface_canonical_order.py
  pass (2 pre-existing + 3 new).

Evidence: the 5 pytest node ids above, bound via `frob ticket evidence`.

Filed: T-1903 (filed by the coordinator from this ticket's part-4
finding, not by me) -- "Pre-land strata parse guard runs BEFORE the
Tier-A rewrite, so it cannot catch corruption the rewrite itself
introduces". No other new tickets filed from this work.

Gates: `frob check --ticket T-1900` -- gate:SCOPE, gate:PRE, gate:FMT
all clean (0 errors) after registering scope and re-sweeping (T-1579's
then T-1896's live leases on the two touched files cleared mid-ticket,
reported to the coordinator each time before proceeding). Remaining
FAILs in that run (ruff-check/ruff-format/ty repo-wide counts,
gate:REG's CHK-GATE-SYS-IFACE-ORDER dangling-rule-reference) are
pre-existing and out of this ticket's scope -- confirmed the REG
finding predates this ticket (introduced by T-1870, `git show
main:docs/design/registry/check-coverage.yaml` before this branch's
commits), and confirmed the only per-file ty/ruff hits inside my two
touched files are the already-ticketed T-1896 invalid-argument-type
finding (pre-existing on the 2 old tests, same signature used
identically by my 3 new tests -- not a new occurrence, not fixed here
since T-1896 already owns it).

`frob test --base main` was not used as gating evidence: after merging
current main into this worktree the diff base swept in every other
ticket landed on main since this branch point (T-1901..T-1904 etc.),
producing dozens of unrelated failures across ticket-lease/export/
strata-golden/tmlanguage-grammar tests with no connection to
_fix_engine_sync.py. Targeted pytest node-id runs (see Evidence) plus
the scoped `frob check --ticket T-1900` are the correct verification
per the playbook's "do not run the full suite" guidance.

### Changed
```
 src/frob/gates/_fix_engine_sync.py                 |  78 +++++++++++++--
 .../gates/test_sys_interface_canonical_order.py    | 107 ++++++++++++++++++++-
 tickets/T-1900/ticket.md                           |  23 ++++-
 3 files changed, 199 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_empty_interface_one_line_form_is_not_read_as_a_name` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_round_trip_every_node_shape_reparses` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_rewrite_that_would_not_parse_is_refused` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_groups_by_kind_then_alpha` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_order_only_multiset_preserved_and_idempotent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 4 error(s), 820 warning(s), 694 waived
- error-findings: REG002@docs/design/registry/check-coverage.yaml, invalid-argument-type@src/frob/app/ticket_runner/_lifecycle.py, invalid-argument-type@tests/test_tickets_scope_mutation.py, invalid-argument-type@tests/unit/gates/test_sys_interface_canonical_order.py
