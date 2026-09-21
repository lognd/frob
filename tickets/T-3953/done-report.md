## Done report

T-3953: RACE001: concurrent read-then-write test obligation
worktree: /home/logan/projects/frob/.claude/worktrees/t-3953
HEAD: 14400b70f

## WHAT changed

- src/frob/gates/_inv.py: added `race001_violations(root, snapshot)` plus
  its private helpers (`_race001_guard_present`, `_race001_subscript_read`,
  `_race001_subscript_write_targets`, `_race001_function_violation`,
  `_race002_binding_tests_are_concurrent`,
  `_race002_test_obligation_violation`) and the `_RACE001_GUARD_RE`/
  `_RACE002_CLAIM_RE`/`_RACE002_CONCURRENT_TEST_RE` regex constants. Every
  new symbol carries `# frob:ticket T-3953` (COV002) and
  `race001_violations` carries a resolving `frob:doc <file>#<slug>`
  anchor (COV001 -- verified the slug against
  `frob.gates._doclink_docanchor._doc_anchor_slugs` before committing,
  having hit the bare-file-path mistake once already on the T-3997 series
  before this one).
- tests/gates_suite/test_invariant.py: added `TestRace001Violations` with
  5 tests, written BEFORE the implementation (confirmed failing on
  `ImportError: cannot import name 'race001_violations'` first, per the
  playbook's failing-test-first instruction), covering fire/silent/
  companion cases for both RACE001 and RACE002.
- docs/modules/gate-race001.md (new): standalone rule doc, since
  docs/modules/gates.md is leased by T-3259/T-draft-a62505d4 for this
  ticket's whole duration (same lease conflict T-3997/TESTMOCK001 hit).
- tickets/T-3953/ticket.md: scope now includes docs/modules/gate-race001.md
  (mirrored via `frob ticket scope T-3953 --add ...`), evidence recorded
  for both acceptance items.

## WHY

F-181 (T-3942 item 7), same rule T-3919 item 3 first asked for and never
built. The delta audits kept re-finding an unlocked read-then-write of
the same key (a `dict.get(key)` read followed by a derived `dict[key] =`
write, with no lock/Lua/INCR/conditional-UPDATE guard) as an un-tracked
shape, plus a related, cheaper-to-check gap: a docstring/spec claiming
cap/quota/single-use/idempotent behavior with no test that actually calls
the function from concurrent callers. `race001_violations` walks every
Python function symbol's AST for both shapes and fires `Severity.WARN`
(never ERROR -- the ticket's own body explicitly warns this heuristic
"will be waived into uselessness fast" if pitched as a hard gate; WARN
plus a generous, false-negative-biased guard check is the mitigation).

## Acceptance criteria proof

1. "given a function with an unlocked read of a value followed by a
   write derived from it and no lock/Lua/INCR/conditional-UPDATE guard,
   when frob check runs, then RACE001 fires" --
   `tests/gates_suite/test_invariant.py::TestRace001Violations::
   test_fires_on_unlocked_read_then_write_same_key`: `STORE.get(key, 0)`
   read into `current`, then `STORE[key] = current + 1` with no guard --
   fires exactly one RACE001. Two companion (non-accepted, false-positive-
   guard) tests prove the rule does not over-fire:
   `test_silent_when_a_lock_guards_the_read_then_write` (identical shape
   wrapped in `with _LOCK:`) and
   `test_silent_when_read_and_write_target_different_keys` (read one key,
   write a different one -- not the same-key race this rule is about).
2. "given a docstring/spec claiming cap, quota, single-use or idempotent
   behavior with no concurrent-callers test, when frob check runs, then a
   test obligation is reported" --
   `tests/gates_suite/test_invariant.py::TestRace001Violations::
   test_test_obligation_fires_with_no_concurrent_binding_test`: a
   docstring claiming "single-use" cap behavior bound to one single-
   caller test fires RACE002. The companion
   `test_test_obligation_satisfied_by_a_concurrent_binding_test` (same
   docstring, bound to a test literally named `test_bump_concurrently`)
   is silent -- proving the obligation is genuinely satisfiable, not a
   rule that always fires regardless of the test.

## Test node ids (evidence, bound with --base-ref dev, AFTER the last commit)

- tests/gates_suite/test_invariant.py::TestRace001Violations::test_fires_on_unlocked_read_then_write_same_key  (accepts 1)
- tests/gates_suite/test_invariant.py::TestRace001Violations::test_test_obligation_fires_with_no_concurrent_binding_test  (accepts 2)

All 5 tests in TestRace001Violations pass:
`PYTHONPATH=$(pwd)/src .venv/bin/python -m pytest
tests/gates_suite/test_invariant.py::TestRace001Violations -p no:cacheprovider -q`
-> `SUITE-RESULT: exitstatus=0 collected=5 failed=0`

## Commit shas

- 35d1ebd48  chore(tickets): scope T-3953  (scope mirror, before the code commit)
- 4d4067901  feat(gates): add RACE001/RACE002 concurrent read-write detector (T-3953)
- e39479869  fix(gates): resolve COV001/COV002 for RACE001/RACE002 symbols
  (T-3953) -- same doc-anchor-slug + frob:ticket fix T-3997's own series
  needed, caught here by re-running the coverage check before READY
  rather than after
- 2ee9da360 / 14400b70f  chore(tickets): record evidence for T-3953
  (both AFTER e39479869, the last code commit -- evidence bound after the
  last commit as the playbook requires)

## Scope refusal / follow-up (out-of-scope work)

Same lease-blocked wiring gap as T-3997/TESTMOCK001: this ticket's scope
is `src/frob/gates/_inv.py` only, and wiring `race001_violations` into
the live `frob check` job list needs `src/frob/gates/__init__.py`. T-4647
already tracks TESTMOCK001's wiring against that same file; I did not
file a second near-duplicate ticket -- `docs/modules/gate-race001.md`
records that RACE001/RACE002's wiring can land in the same follow-up pass
once `src/frob/gates/__init__.py`'s lease clears. I did not append a
fold-in note to T-4605's body (not my ticket, did not want to touch
another agent's ticket body under fleet load) -- the doc file's own text
records the fold-in intent instead.

## Cross-ticket lease note

None found: `grep -l` over `.git/frob-leases/*.json` for
`src/frob/gates/_inv.py` and `tests/gates_suite/test_invariant.py` shows
only T-3953's own lease.

## Pre-READY checks

- `frob check --only sys --files src/frob/gates/_inv.py --files
  tests/gates_suite/test_invariant.py --files docs/modules/gate-race001.md
  --base dev`: `UNRES  gate-summary  7 errors, 557 warnings, 0 unresolved,
  5 waived` -- zero attributable to my files (pre-existing DRIFT001/
  DSL001/DOCARCH001 in unrelated files, same baseline the T-3997 series
  measured minutes earlier on the same box). No SELFAUDIT001 findings.
- `frob check --only arch --files src/frob/gates/_inv.py --files
  tests/gates_suite/test_invariant.py --base dev`: `pass  frob-arch  19
  warnings (36 waived), 546 suggestions`. No ARCH001/LARGE001 gate
  finding. One advisory NOTE worth flagging to the coordinator:
  `_inv.py` crossed the 800-line "large-file" and 8-import "high-
  coupling" pattern-suggestion thresholds (now 1182 lines / 9 local
  imports) -- but the file was ALREADY at 897 lines (over 800) before
  this ticket touched it, so this is a pre-existing condition my ~300
  new lines made numerically worse, not a new crossing; frob-arch's own
  gate status stayed "pass" (these are suggestions, not ARCH001/LARGE001
  violations).
- `frob check --only coverage --files src/frob/gates/_inv.py --files
  tests/gates_suite/test_invariant.py --files docs/modules/gate-race001.md
  --base dev`: FIRST run (against commit 4d4067901, bare `frob:doc
  docs/modules/gate-race001.md` with no `#anchor`, no `frob:ticket`
  markers -- same mistake T-3997's own series made): `FAIL gate:COV 19
  errors` with 10 of them naming RACE001/RACE002 symbols (COV001 on
  `race001_violations`, COV002 on the other 9 new symbols). Fixed
  (commit e39479869) and RE-RUN: `FAIL gate:COV 9 errors`, zero naming
  `race001`/`RACE001`/`RACE002`/`_race00*` -- all 9 pre-existing
  (`_DOC_INVARIANT_MARKER_RE`, `_DOC_WAIVE_MARKER_RE`, etc., all already
  `[waived: ...]` in the run's own output).
- `ruff check src/frob/gates/_inv.py tests/gates_suite/test_invariant.py`:
  "All checks passed!" (one `ruff format` pass needed first).
- `ty check src/frob/gates/_inv.py`: "All checks passed!" (one fixup:
  `_race001_subscript_write_targets`'s parameter widened from `ast.stmt`
  to `ast.AST` -- it is called from an `ast.walk` loop that yields the
  wider type).

### Changed
```
 docs/modules/gate-race001.md        |   87 ++
 src/frob/gates/_inv.py              |  296 +++++
 tests/gates_suite/test_invariant.py |  132 ++
 tickets/T-3953/done-report.md       | 2320 +++++++++++++++++++++++++++++++++++
 tickets/T-3953/ticket.md            |   22 +-
 5 files changed, 2845 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/gates_suite/test_invariant.py::TestRace001Violations::test_fires_on_unlocked_read_then_write_same_key` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_invariant.py::TestRace001Violations::test_test_obligation_fires_with_no_concurrent_binding_test` (pytest node id, verified passing when recorded)
