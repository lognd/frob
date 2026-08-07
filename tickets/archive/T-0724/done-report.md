## Done report

REVIEW ROUND 2 (reviewer rejection): enabling `check_resource_contention`
in production made `frob sys audit` exit 1 against frob's OWN
`design/frob.strata` -- 4 unwaived SYS203 findings on the `tickets_ledger`
store (written by `cli`, `core`, `fleet`, `gates`). This was real and
correct behavior (the check working as designed), not a bug in the
wiring -- but my original Done report never disclosed it. Fixed properly
instead of hidden:

1. Waived all 4 per-writer findings in `design/frob.strata`, one
   `waive "SYS203:tickets_ledger" reason "all ledger writers serialize
   through .frob/tickets.lock (T-0458/T-0633); mode-blind until T-0700
   arbitrated_by can express this -- re-evaluate at T-0700" ticket
   "T-0700";` clause on each of the `cli`/`core`/`fleet`/`gates` node
   blocks (the T-0699/T-0174 RULE:SUBTARGET waiver channel,
   `contention_port_waived.strata`'s syntax). The disposition is real: the
   ledger genuinely has an arbiter (the `.frob/tickets.lock` flock,
   T-0458 single-writer CLI + T-0633's locked wholesale ops) -- SYS203 is
   mode-blind by the grammar's current ceiling and cannot express an
   arbiter until T-0700's access-modes+`arbitrated_by` construct lands.

2. Adding those waivers surfaced a SECOND, real bug: `_audit.py`'s
   `_gap_rule_in_scope` (the predicate `evaluate_exhaustiveness`'s OWN
   waiver-staleness sweep uses) excluded SYS100-102/HOST001-002 from its
   scope (each owns its own waiver channel) but NOT SYS200-203, so my
   legitimate SYS203 waivers were reported STALE by
   `evaluate_exhaustiveness`'s pass (`SYSWAIVE002` under the "waiver"
   family) even while `check_resource_contention`'s own `apply_waivers`
   call correctly matched and applied the SAME waivers. Fixed with the
   smallest possible `_audit.py` addition: `RESOURCE_CONTENTION_RULES`
   added to `_gap_rule_in_scope`'s exclusion tuple (one import, one line
   in the tuple, expanded docstring/comment). T-0630 is concurrently
   reworking this file for unrelated root= binding wiring -- this touch
   is orthogonal (a different function, a pre-existing predicate) and
   the coordinator authorized exactly this "smallest possible addition"
   for an overlap case.

3. Verified `uv run frob sys audit` (bare, in the worktree) after both
   fixes: all 4 SYS203 findings on `tickets_ledger` print loudly via
   `_log_waived_contention` (`WARNING ... WAIVED family=sys rule=SYS203
   node=<cli|core|fleet|gates> detail=store tickets_ledger is also
   written by ...`), then `sys audit: resource-contention PROVED (4
   waived) -- zero UNWAIVED SYS2xx gaps`.

   HOWEVER: `frob sys audit`'s overall exit code is still nonzero in
   this worktree, for a REASON UNRELATED TO T-0724 -- merging `main`
   (required to pick up the T-0630-overlap check per the coordinator's
   instruction below) brought in `src/frob/arch/_srp.py` (the SRP
   architecture check, landed on main independently of this ticket),
   which introduced 4 new SYS100 self-conformance gaps: `graphlang`
   observes `net`/`exec`/`fetch_url` at `_srp.py:311-313` (+one more
   `fetch_url` site) that `design/frob.strata`'s `graphlang` node does
   not declare. This is NOT a SYS203/contention finding and NOT
   introduced by anything in this ticket's scope -- confirmed by
   checking that `_srp.py` landed in a separate main commit
   (`a45bbace`/ancestors) with no relation to T-0699/T-0724. Filed
   `T-draft-890e0667` ("graphlang missing net/exec/fetch_url capability
   declarations for src/frob/arch/_srp.py (SYS100)") rather than fixing
   silently or leaving undisclosed. `frob check --ticket T-0724` (the
   ticket-scoped gate, which does not evaluate unscoped SYS100 gaps
   against the full `frob sys audit` surface) is clean at 0 errors --
   see the numbers below.

4. Added `design/frob.strata` to scope (`--reason` recorded) for the
   waivers, plus `src/frob/strata/_audit.py`'s minimal fix (already
   covered by the existing `src/frob/strata/**` glob, added explicitly
   for the audit trail anyway), plus `pyproject.toml`/`CHANGELOG.md`
   (REL001 forced a second bump, 0.90.0 -> 0.91.0, after the `_audit.py`
   change; both bumps now have CHANGELOG entries).

T-0630 root= wiring note (separate coordinator ask, addressed here since
it required the same main-merge): T-0630 ("wire real code binding into
production discharge entrypoints so G1 fail-closed actually fires") is
still `state: queued` on `main` as of this merge (`git show
main:tickets.md` confirms) -- its `root=` threading through
`evaluate_exhaustiveness`/`render_audit_matrix`/`plan_obligations` has
NOT landed. Per instruction, skipped adding `root=` at `sys_runner.py`'s
three call sites rather than reimplementing T-0630's entrypoints myself;
this is a disclosed skip, not an oversight -- the coordinator will file
the three-line follow-up once T-0630 actually lands.

Wiring point (unchanged from round 1): `src/frob/app/sys_runner.py::
_run_audit`. SYS203 store-id threading (unchanged from round 1):
`DesignIds.store_ids` populated from parsed `Module.stores` in
`_design_load.py` before elaboration.

Measured (this round): `uv run pytest tests/system/test_cli_sys_plan.py
tests/unit/strata/test_contention.py -p no:cacheprovider -q` -> 18
passed (7 + 11), unchanged from round 1. `uv run frob check --ticket
T-0724` -> 0 errors, 408 warnings, 200 waived (gate-summary pass) after
the design/frob.strata scope amendment, the `_audit.py` scope amendment,
the CHANGELOG.md scope amendment, and a re-run of `frob ticket sweep
T-0724` (PRE001 clean). `uv run frob sys audit` (bare, whole-repo):
resource-contention leg PROVED (4 waived, all printed), overall exit
nonzero solely due to the unrelated, freshly-merged T-0728-class SYS100
gap (`T-draft-890e0667` filed).

Version: 0.89.0 -> 0.90.0 (round 1, this ticket's public API) -> 0.91.0
(round 2, the `_audit.py` fix). `.frob-release.json` re-stamped both
times.

### Changed
```
 .frob-release.json                |  21 ++++++-
 CHANGELOG.md                      |   8 +++
 design/frob.strata                |  22 ++++++++
 pyproject.toml                    |   2 +-
 src/frob/app/sys_runner.py        | 100 ++++++++++++++++++++++++++++++---
 src/frob/strata/_audit.py         |  26 ++++++---
 src/frob/strata/_design_load.py   |  54 ++++++++++++++----
 tests/system/test_cli_sys_plan.py |  42 +++++++++++++-
 tickets.md                        | 115 +++++++++++++++++++++++++++++++++++++-
 uv.lock                           |   2 +-
 10 files changed, 356 insertions(+), 36 deletions(-)
```

### Evidence
- `tests/system/test_cli_sys_plan.py::TestSysAuditContentionCli::test_duplicate_port_fires_sys200_through_cli` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_contention.py::TestDuplicatePort::test_two_nodes_same_port_fires` (pytest node id, verified passing when recorded)
