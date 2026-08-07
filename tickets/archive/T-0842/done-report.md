## Done report

## Done report

Changed:
  src/frob/gates/__init__.py::_tick008_unknown_ledger_fields (new;
    reworked after review rejection -- see Severity decision below)
  src/frob/gates/__init__.py::tickets_gate (updated to include TICK008)
  src/frob/gates/__init__.py::_KNOWN_GATE_RULES (registered TICK008)
  tests/test_gates.py::TestTick008UnknownLedgerFields (new test class,
    5 tests; severity assertion updated ERROR -> WARN after review)
  docs/modules/gates.md (TICK008 table row + "### TICK008 (T-0842)"
    detail section, following the TICK007 precedent; severity and
    reasoning updated after review)

Evidence (all 5 recorded via `frob ticket evidence`, unchanged node ids
-- only assertions inside the bodies changed, not the test names):
  tests/test_gates.py::TestTick008UnknownLedgerFields::test_fires_on_unknown_field
  tests/test_gates.py::TestTick008UnknownLedgerFields::test_fuzzy_hint_on_near_miss_typo
  tests/test_gates.py::TestTick008UnknownLedgerFields::test_silent_on_clean_ledger
  tests/test_gates.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean
  tests/test_gates.py::TestTick008UnknownLedgerFields::test_waivable
  All 5 pass individually (`pytest -k TestTick008` -> 5 passed), and the
  FULL `tests/test_gates.py` suite passes end to end (`pytest
  tests/test_gates.py -p no:cacheprovider -q` -> all green, no failures)
  after the rework, proving the severity change did not regress any
  sibling gate test.

Filed: none -- no out-of-scope work discovered.

Severity decision -- REWORKED after adversarial-review rejection:

  Original submission used Severity.ERROR. Rejected finding (verbatim
  trace, confirmed correct): `frob ticket land`'s claim re-verification
  (`_reverify_done_report_claims_post_merge`) spawns `frob check
  --ticket <id>` via `sys.executable` from the ROOT checkout's venv --
  the root binary's OLD `src` tree (playbook section 2's stale-binary
  hazard, one level up from the usual "you ran a stale global frob"
  case: here it's `frob ticket land`'s OWN subprocess that is stale
  relative to the very ticket it is landing). While a schema-extending
  ticket is ITSELF being landed, root's stale `Ticket` model does not
  yet know the new field that ticket just added -- a populated new
  field on that ticket's own ledger block gets captured as
  `__pydantic_extra__` by the stale root model. `tickets_gate` scans
  the WHOLE merged queue (correctly -- it must, since stale drift
  anywhere is real), so an ERROR TICK008 fires over the full merged
  ledger at exactly the land moment, `real_errors` diverges from the
  worktree-captured claim, and land refuses via `ClaimDivergence`. A
  `frob:waive TICK008` cannot route around this: the same stale root
  binary evaluating the gate evaluates the waiver, so the schema gap
  causing the false ERROR equally prevents the waiver being recognized
  as covering it. My original docstring's claim -- "no case where this
  rule stays red once the schema catches up" -- is false during exactly
  that land window: "the schema catching up" IS the land event being
  refused.

  Fix applied: downgraded TICK008 to Severity.WARN (matching the
  TICK004/TICK006/TICK007 precedent this ticket's own Description
  invoked but I had not actually applied). `frob check`'s pass/fail
  gating and land's real-errors/claim-divergence comparison both key
  off ERROR-severity counts, not WARN, so a WARN cannot cause the same
  ClaimDivergence refusal during a schema-extending ticket's own land.
  WARN still satisfies the actual T-0838 review demand -- a live,
  mechanical `frob check` finding instead of a WARNING log line no gate
  reads -- since the drive treats warnings as work-to-zero, not as
  invisible.

  Both `_tick008_unknown_ledger_fields`'s docstring and
  docs/modules/gates.md's "### TICK008 (T-0842)" section now state this
  land-window hazard explicitly (citing T-0838 and this review) as the
  reason for WARN, so a future attempt to "promote to ERROR" re-derives
  the same constraint instead of re-discovering it.

_models.py: no change (unchanged from original submission --
`Ticket.__pydantic_extra__` was already a clean accessor).

check-coverage.yaml: still explicitly OUT of scope -- CHK-GATE-TICK008
left for the coordinator to add at land time (T-0788/COMPLIANCE005
precedent).

Waivability: TICK008 still NOT added to `_UNWAIVABLE_RULES`. Covered by
`test_waivable`. (Waivability was never in question -- only severity.)

Gates (re-run after the WARN rework): `frob check --ticket T-0842`
chunked (`--only lint`, `--only static`, `--only gates-fast`, `--only
gates-native`, `--only gates-security`) all report 0 errors, after
re-running `frob ticket sweep T-0842`.

`ruff check` / `ruff format --check` clean on every file touched.

Unscoped real-ledger proof (the critical requirement): `frob check
--only tickets` against this repo's own live ledger reports `gate:TICK
0 errors, 1 warning` where the 1 warning is TICK003 (pre-existing,
unrelated) -- explicitly grepped for "TICK008" in the full `--only
tickets` output and got 0 matches. Zero TICK008 findings on the real
ledger, confirmed after the WARN rework.

Deletion filter: `git diff main --diff-filter=D --stat` is empty (no
unintended deletions relative to main).

Commits this round: `0e11da24` (fix: downgrade TICK008 to WARN, fix
land-refusal hazard), on top of the prior round's `94500041` (feat:
add gate), `116f2b63` (merge main), `a63ae92d` (chore: evidence/Done
report).

Deviations from a clean single pass: same two as the prior round
(docs/modules/gates.md scope-add, and the mid-ticket main-merge for
T-0836's worktree-sweep landing), plus this round's own rework in
response to adversarial review, plus a SECOND mid-ticket main-merge
(main advanced again during the rework, landing T-0834 among others --
`git diff main --diff-filter=D --stat` caught it again per playbook
section 9, resolved the same way: commit WIP, `git merge main`, ledger
merge-driver spliced automatically, `make core`, re-verify). All
disclosed above rather than silently absorbed.

Non-attributable gate state: after this second merge, `frob check
--only tickets` reports `gate:TICK 1 error` -- TICK003 (61 closed
tickets un-archived, threshold 60), NOT TICK008. This is pre-existing
ledger-hygiene drift from the ambient lands that happened during this
session (nothing in `src/frob/gates/__init__.py`, `tests/test_gates.py`,
or `docs/modules/gates.md` -- this ticket's own scope -- causes or
fixes TICK003), and `frob check --only tickets` still shows ZERO
TICK008 findings (grepped explicitly: `grep -c TICK008` on the full
`--only tickets` output -> 0). Not fixed here -- out of this ticket's
scope; `frob ticket archive` is the documented remedy and belongs to
whoever next runs a quiet-window archive pass, not this ticket.

### Changed
```
 docs/modules/gates.md      |  62 +++++++++++++++++++
 src/frob/gates/__init__.py | 105 ++++++++++++++++++++++++++++++--
 tests/test_gates.py        |  97 +++++++++++++++++++++++++++++
 tickets.md                 | 148 ++++++++++++++++++++++++++++++++++++++++++++-
 4 files changed, 406 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTick008UnknownLedgerFields::test_fires_on_unknown_field` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick008UnknownLedgerFields::test_fuzzy_hint_on_near_miss_typo` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick008UnknownLedgerFields::test_silent_on_clean_ledger` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick008UnknownLedgerFields::test_waivable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 1206 warning(s), 210 waived
