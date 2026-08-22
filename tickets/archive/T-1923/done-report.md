## Done report

frob:no-behavior-change reason="F401 is an unused-import deletion (no production behavior). The 5 archived tickets' evidence rebinds are ledger-only edits pointing stale evidence at a real, resolving successor test -- no production code for those tickets changed. Nothing here alters any runtime behavior; the designated repro test already passes at both parent and fix."

Reproduced the full error floor myself before touching anything (the
ticket body understated it -- 6 identities recorded by the rolling
sweep baseline vs 19 actually measured; see "Sweep undercount" below).

## Root cause

T-1916 (5e17bb70a6a4) retired `fix_sys_interface_canonical_order`
(SYS-IFACE-ORDER) as a deletion: the Tier-A handler, its
`TIER_A_HANDLERS` registration, the false `CHK-GATE-SYS-IFACE-ORDER`
registry row, and the entire test file
`tests/unit/gates/test_sys_interface_canonical_order.py` all went in
one commit. That test file was the ONLY evidence for 5 already-closed
tickets (T-1872, T-1895, T-1896, T-1900, T-1906), so every one of their
evidence node ids stopped resolving (COV003), and one leftover
`TYPE_CHECKING`-only import in `_fix_engine_sync.py`
(`frob.strata._code_binding.CodeBinding`, only ever used by the deleted
handler's type hints) became unused (F401).

## Investigation: does the tested behavior survive on main under another path?

Read the deleted test file at its parent commit
(`git show 5e17bb70a6a4^:tests/unit/gates/test_sys_interface_canonical_order.py`).
All 5 tests exercised exactly one function,
`fix_sys_interface_canonical_order`, asserting the order-only
canonical-reorder invariant for `interface=` declarations. That
function's module (`src/frob/gates/_fix_engine_sync.py`) now carries a
module-docstring paragraph (T-1916) explaining the retirement in full:
the handler was the ONE Tier-A id in `TIER_A_HANDLERS` never backed by
a real gate/policy detector (REG002 caught the registry's false "live,
enforced gate rule" claim about it) -- every other Tier-A id has a real
detector behind it. The retirement was deliberate and is now
mechanically locked in: `tests/test_registry_exhaustiveness.py::
TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails`
(added by T-1916 itself) asserts `"SYS-IFACE-ORDER" not in
known_gate_rule_ids()` and fails loudly if the id ever reappears there
without a real detector.

VERDICT per ticket: all 5 are the same case -- CASE 1, not case 2.
`grep -rn "SYS-IFACE-ORDER\|fix_sys_interface_canonical_order" --include='*.py'`
across the whole repo shows zero surviving call sites outside comments/
docs that narrate the retirement's own history (`_fix_engine.py`'s
`TIER_A_HANDLERS` comment block, `docs/strata/surface.md`,
`_land_cmd.py`'s T-1900-incident writeup, `CHANGELOG.md`). The
canonical-interface-ordering behavior these 5 tickets' evidence proved
does NOT survive on main under any other code path -- it was fully,
intentionally removed, and a regression test now guards against it
silently reappearing. This is NOT a coverage regression: T-1916 did not
quietly drop protection for live behavior, it deleted dead-detector
code and its own tests together, correctly, in the same commit.

- T-1872 (built the handler): evidence retired alongside the code it
  proved.
- T-1895 (extracted a scanner SHARED between SYS-IFACE-ORDER and
  `_sync_may.py`): the 3 `test_sync_may.py::TestNodeBodySpan` evidence
  ids still resolve fine (untouched, the shared scanner survives in
  `_sync_may.py`/SYS100, which is very much alive) -- only the 4 ids
  pointing at the deleted SYS-IFACE-ORDER-side test file were stale.
- T-1896 (ty invalid-argument-type fix on 2 of the deleted tests):
  evidence retired alongside the code.
- T-1900 (3-part hardening of the same handler, 5 evidence ids): all 5
  targeted the deleted file; evidence retired alongside the code.
- T-1906 (further hardening, 5 evidence ids, all overlapping T-1900's
  set): same, evidence retired alongside the code.

## Fix

- `src/frob/gates/_fix_engine_sync.py`: deleted the now-unused
  `TYPE_CHECKING`-only import of `frob.strata._code_binding.CodeBinding`
  (F401). No other reference to it remains in the file.
- For each of the 5 archived tickets' 18 dangling evidence ids: `frob
  ticket evidence <id> --replace <old> <new> --reason-file <...>
  --archived`, rebinding to
  `tests/test_registry_exhaustiveness.py::TestDisposition::
  test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails`
  -- the real, resolving successor test that proves each ticket's
  subject (SYS-IFACE-ORDER) stays correctly retired. The `--reason`
  text on every rebind states explicitly that this is a "removed
  behavior, evidence retired alongside the code" case, not a renamed/
  relocated test masquerading as continuity. No evidence id was deleted
  outright -- every rebind is a `--replace`, auditable in each ticket's
  `evidence_changes` trail.

## Sweep undercount (flagging per coordinator's ask)

The ticket body said "6 new errors" (COV003, F401) based on the rolling
sweep baseline's own recorded identities. A full unscoped measurement
found 19: 18 COV003 (T-1872 x2, T-1895 x4, T-1896 x2, T-1900 x5, T-1906
x5) + 1 F401. The rolling baseline evidently only recorded whichever
COV003 identities it happened to observe first, undercounting the true
new-error set by roughly 3x. Worth a separate ticket on the rolling-
baseline sweep's own counting logic -- filed as residue below, not
fixed here (out of T-1923's own scope, which is the 5 tickets plus
`_fix_engine_sync.py`).

## Before/after (measured)

`timeout 530 uv run frob check --only coverage --only ruff`, same
worktree, before vs after:

Before:
  FAIL  ruff-check   1 errors, 12 warnings   (F401 at _fix_engine_sync.py:67:43)
  FAIL  gate:COV     18 errors, 22 warnings, 182 waived

After:
  pass  ruff-check   0 errors, 12 warnings   (unrelated pre-existing I001 warnings only)
  pass  gate:COV     0 errors, 23 warnings, 182 waived

## Other dangling residue check (per coordinator's ask)

Searched for any OTHER dangling reference to the retired handler the
sweep did not flag: `git grep -n "SYS-IFACE-ORDER\|fix_sys_interface_canonical_order"`.
Every hit outside the 5 tickets' own evidence is either (a) the
module-docstring/comment prose in `_fix_engine_sync.py`/`_fix_engine.py`
narrating the retirement itself (correct, load-bearing history, not
residue), (b) `docs/strata/surface.md`'s own retirement writeup
(likewise historical record), (c) `_land_cmd.py`'s T-1900-incident
writeup (an unrelated past incident that happened to involve this
handler, not a live reference to it), or (d)
`test_registry_exhaustiveness.py`'s own regression guard (the successor
test used above). Nothing half-retired found; no residue ticket needed
for that specific concern.

## Pre-existing, unrelated failure noticed in passing (NOT fixed, out of
## scope)

`tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::
test_no_reg008_findings_for_check_coverage_yaml` fails on this worktree
both before and after this ticket's change -- it asserts REG008 is
empty for `docs/design/registry/check-coverage.yaml`, and this repo's
own T-1872 Done report already flagged "REG002/REG008/REG011 dangling
CHK-GATE-SYS104 registry rows -- leftover from T-1870's SYS104
deletion, tracked there" as a known, separately-tracked, pre-existing
condition. Confirmed unrelated: T-1923's own diff touches
`_fix_engine_sync.py` (one import) and 5 archived tickets' evidence
lists only, neither of which is `check-coverage.yaml` or gate-registry
code. Not filed as new residue since T-1872's Done report already
tracks it elsewhere; flagging here only so it is not mistaken for
something T-1923 introduced.

Filed: T-1935 (renumbers at land) -- rolling post-land sweep
baseline undercounts new-error identities by roughly 3x (T-1923 claimed
6, measured 19).

Gates: `uv run frob check --only coverage --only ruff` clean (0 errors
each). `uv run frob check --ticket T-1923 --only scope --only prework`
clean after a re-sweep.

### Changed
```
 tickets/T-1923/ticket.md           |   4 +-
 tickets/T-1935/ticket.md |  55 ++++++++
 tickets/archive/T-1872/ticket.md   | 136 +++++++++++++++++-
 tickets/archive/T-1895/ticket.md   | 206 ++++++++++++++++++++++++++-
 tickets/archive/T-1896/ticket.md   |  90 +++++++++++-
 tickets/archive/T-1900/ticket.md   | 279 ++++++++++++++++++++++++++++++++++++-
 tickets/archive/T-1906/ticket.md   | 212 +++++++++++++++++++++++++++-
 7 files changed, 959 insertions(+), 23 deletions(-)
```

### Evidence
- `tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 819 warning(s), 696 waived
- error-findings: none (measured, zero errors)
