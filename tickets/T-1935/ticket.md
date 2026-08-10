---
id: T-1935
title: Rapid post-land sweep undercounts new-error identities (T-1923 said 6, measured
  19)
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
- tickets/T-1952/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_rapid_sweep*
  reason: narrowing to the actual rapid-sweep source module; docs/modules/tickets.md
    collides with T-1720's live lease
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/tickets/_rapid_sweep*
  reason: wrong path guessed; no such module under src/frob/tickets
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: docs/modules/tickets.md
  reason: collides with T-1720's live lease
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: the actual rapid post-land sweep counting logic this ticket investigates
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: the new _true_finding_count_for_identities tests live here
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-1952/ticket.md
  reason: the follow-up residue ticket T-1935 itself filed for the T-1720-blocked
    doc re-ack
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_rapid_sweep.py::TestTrueFindingCount::test_counts_every_diagnostic_matching_an_identity
- tests/unit/test_rapid_sweep.py::TestTrueFindingCount::test_unparsable_json_is_none_not_zero
- tests/unit/test_rapid_sweep.py::TestTrueFindingCount::test_spawn_refused_is_none_not_zero
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Found while working T-1923 (post-land sweep regression from T-1916).
T-1923's own ticket body, filed by the deferred rapid-profile post-land
sweep, reported "6 new error(s) (COV003, F401)". A full unscoped
measurement of the same two gate families
(`uv run frob check --only coverage --only ruff`) on the exact same
commit found 19: 18 COV003 (5 archived tickets' evidence ids, all
pointing at a test file T-1916 deleted) + 1 F401, not 6.

The rolling baseline the sweep persists (`rapid-debt.jsonl` /
`.frob/rapid-sweep` mechanics, T-1684) evidently records only whichever
new-error IDENTITIES it happens to observe first per (rule, file) pair
rather than every distinct finding -- in this case it looks like it
recorded one COV003 per distinct FILE (5 archived ticket files) plus
something that summed to 6, undercounting the true per-finding count
(18 distinct evidence ids across those 5 files) by roughly 3x. This
matters because a ticket filed off the sweep's own undercount can look
"smaller" than the real fix, and an agent trusting the ticket body's
count without re-measuring (exactly the failure mode section 6c of the
agent playbook warns about, generalized to sweep-authored tickets, not
just human-filed ones) would under-scope its own verification.

Investigate whether the rolling-baseline sweep is meant to count
per-(rule, file) IDENTITIES (in which case 6 for T-1923's shape -- 5
files x COV003 plus 1 F401 file -- might be intentional and the ticket
body's parenthetical "N new error(s)" phrasing is simply misleading
about what N counts) or per-finding (in which case it under-recorded
and should read 19). Either fix the counting logic or fix the ticket
body's phrasing so "N new error(s)" means what a reader would assume it
means. Not fixed as part of T-1923 itself -- that ticket's scope was
the 5 archived tickets plus `_fix_engine_sync.py`, not the sweep
counting mechanism.

## Done report

Investigated and fixed the T-1923 undercount.

Root cause: the deferred rapid-profile sweep's whole comparison pipeline
(`_land_cmd._unscoped_error_findings` -> `_verify._parse_error_findings_from_json`)
identifies findings by `(rule_id, file)` only, deliberately dropping
line/message -- confirmed at `_verify.py`'s own docstring ("captures the
file and rule-id code, deliberately not the message"). This is correct
for the attribution/quarantine machinery (`_rapid_sweep.py`'s own
docstring: they reason about "which files went red", not individual
diagnostics), but `_file_regression_ticket` reported `len(pairs)` as
"N new error(s)" -- which is only ever a count of distinct (rule, file)
IDENTITIES, never a raw finding count. T-1923's case: 5 files each
carrying multiple COV003 findings (18 total) plus 1 F401 collapsed to
6 identities, exactly matching the observed "6" vs the true 19.

Both files identified as needing the actual identity-widening fix
(`src/frob/app/ticket_runner/_land_cmd.py` and `_verify.py`) were under
LIVE leases at the time of this fix (T-1720 and T-1929 respectively) --
confirmed by direct `frob ticket scope --add` refusals
(`ScopeLeaseConflict`). Rather than force a lease collision or leave the
undercount unaddressed, the fix stays entirely inside
`src/frob/app/ticket_runner/_rapid_sweep.py` (mine to touch):

1. `_file_regression_ticket`'s title/body no longer call the identity
   count "error(s)" -- they call it "(rule, file) identit(ies)" and
   explicitly flag that findings sharing an identity are collapsed.
2. New `_true_finding_count_for_identities` (+ its `_spawn_true_count_check`
   ARCH001 split) independently re-measures the TRUE per-finding count
   for the new identities via a SECOND, independent `frob check --json`
   spawn -- paid only on the rare red-batch path (a clean sweep never
   reaches it), so T-1684's "one check per land" cost goal for the common
   case is unaffected. `_file_regression_ticket`'s title/body now report
   BOTH numbers when the re-measure succeeds (e.g. "6 new (rule, file)
   identit(ies), 19 finding(s)"), and degrade gracefully (identity count
   alone, with a caveat) when the re-measure is itself unmeasurable
   (spawn refused/timeout/unparsable) -- never a wrong number.
3. Module docstring documents the counting semantics and why the true
   identity-widening fix is deferred (both candidate files leased).

Filed T-1952 (real id assigned at land) to re-ack
docs/modules/tickets.md's two affected sections once T-1720's lease
frees -- AFFECT001/DRIFT001 both waived with that ticket cited, since
docs/modules/tickets.md itself could not be touched here.

Real fail-then-pass proof: `TestTrueFindingCount.test_counts_every_
diagnostic_matching_an_identity` reproduces T-1923's exact shape (5
files x multiple COV003 + 1 F401, 6 identities) via a mocked `frob check
--json` payload and asserts `_true_finding_count_for_identities` returns
19, not 6 -- this test/function did not exist before this ticket, so it
fails to even collect at the parent commit (FAILED_AT_PARENT via
ImportError), confirming a genuine fail-then-pass.

Gate verification: `frob check --ticket T-1935` across gates-fast,
gates-native, gates-security all report 0 errors after the fix except
the pre-existing, already-filed T-1941 (COV003 on T-0185's stale
evidence, confirmed unrelated to this ticket's scope both before and
after this change).

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py | 171 +++++++++++++++++++++++++++--
 tests/unit/test_rapid_sweep.py             | 107 ++++++++++++++++++
 tickets/T-1935/ticket.md                   |  43 +++++++-
 tickets/T-1952/ticket.md         |  24 ++++
 4 files changed, 334 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestTrueFindingCount::test_counts_every_diagnostic_matching_an_identity` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestTrueFindingCount::test_unparsable_json_is_none_not_zero` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestTrueFindingCount::test_spawn_refused_is_none_not_zero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 1032 warning(s), 701 waived
- error-findings: COV003@tickets/T-0185
