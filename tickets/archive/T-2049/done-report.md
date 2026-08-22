## Done report

Fixed both halves of T-2049's proposed fix, per the standing "surface
automatically where people already look, don't add a command" rule:

1. scripts/fleet_status.py: new `quarantine_state()` reads
   `.frob/quarantine.json` directly (raw JSON, matching this script's
   existing import-light/no-frob-package-dependency style, same
   pattern `leases()` already uses) and returns `("raised"|"clear"|
   "unknown", undisposed_count)`. `main()` now prints a QUARANTINE line
   unconditionally, before the LEASES/WORKTREES sections -- RAISED
   names the undisposed count and the deferred-landing consequence,
   UNKNOWN is reported as unsafe (never silently read as clear, per
   the "cannot verify is never verified" rule this repo already
   applies to quarantine everywhere else), clear is stated plainly.
2. src/frob/app/ticket_runner/_land_cmd.py:
   `_quarantine_override_ceilings`'s own ERROR line (still logged
   BEFORE `block_until_watermark_advances`'s verification work, as it
   already was) now names the undisposed finding count and the exact
   remedy (`frob verify dispose`) via a new `_quarantine_undisposed_
   summary` helper, instead of naming only the ticket id -- the
   previous message was accurate but actionless and was read past
   across four separate land attempts in the real incident this
   ticket describes.

Did NOT: add a new command (explicitly ruled out by the ticket), touch
the "skip synchronous verification" behavior (explicitly ruled out),
or auto-clear/auto-dispose anything (explicitly ruled out).

Acceptance criterion 4 (measure whether other land-cost state belongs
in fleet_status.py by the same argument): measured `frob.verify.
_watermark.queue_status(root)` against this repo's own root -- 17
queued verify entries right now, a non-trivial, currently-nonzero
number with the identical "silently changes land cost, surfaced
nowhere already-looked-at" shape. No incident in this session ties it
to real lost throughput the way quarantine's two dead imports did, so
I did not add it speculatively (that would repeat exactly the mistake
T-2049's own "Do NOT fix it this way" section warns against for the
quarantine case itself). Filed as a follow-up instead: T-2126.

Also promoted T-1860's own follow-up (drafted-then-lost per your
instruction) in the sibling t1860-series worktree -- now T-2112 there
(uncommitted in that worktree as of this report; its promotion
collided with main's OWN concurrently-filed T-2109, a different
ticket, renumbered to T-2112 to clear it). T-2049's own new draft then
independently promoted to that SAME T-2112 id inside THIS worktree
(each worktree's local ledger cannot see the other's uncommitted
renumber), caught before commit and renumbered again to T-2126 by
checking both `main:tickets/` and the sibling worktree's local ledger
before finalizing -- per T-2105/T-2111's own "a ticket's declared state
can disagree with the live/authoritative copy across worktrees"
lesson, applied here to id allocation rather than scope.

## Done report

Changed:
scripts/fleet_status.py::QUARANTINE
scripts/fleet_status.py::quarantine_state
scripts/fleet_status.py::main
src/frob/app/ticket_runner/_land_cmd.py::_quarantine_override_ceilings
src/frob/app/ticket_runner/_land_cmd.py::_quarantine_undisposed_summary

Evidence:
tests/unit/test_coordinator_scripts.py::TestQuarantineState.test_reports_raised_with_undisposed_count
tests/unit/test_coordinator_scripts.py::TestQuarantineState.test_reports_clear_when_store_says_cleared
tests/unit/test_coordinator_scripts.py::TestQuarantineState.test_reports_clear_when_no_file
tests/unit/test_coordinator_scripts.py::TestQuarantineState.test_unreadable_store_is_unknown_never_clear
tests/unit/test_coordinator_scripts.py::TestQuarantineState.test_non_dict_record_is_unknown
tests/unit/test_coordinator_scripts.py::TestFleetStatusMainQuarantine.test_prints_raised_with_undisposed_count_and_consequence
tests/unit/test_coordinator_scripts.py::TestFleetStatusMainQuarantine.test_prints_clear
tests/unit/test_coordinator_scripts.py::TestFleetStatusMainQuarantine.test_prints_unknown_as_unsafe
tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings.test_notice_names_undisposed_count_and_dispose_command
(41/41 collected/0 failed across both files; both repro tests confirmed
FAILED_AT_PARENT against their own pre-fix commits via --check-repro:
64da63433 for the fleet_status.py repro, 5bebcfcb1 for the land_cmd.py
repro -- playbook 7b technique, since --check-repro against main itself
hits the T-2025 post-land-squash limitation for any newly-added test)

Filed: T-2126 (verify queue depth/age symmetry, deferred per acceptance
criterion 4's own "measure, do not add speculatively" instruction) --
filed and committed inside THIS worktree/branch, ships with T-2049.
T-2112 (T-1860's own promoted-and-renumbered follow-up) was ALSO filed
this session but lives in the sibling t1860-series worktree, not this
one -- named here for the coordinator's own record, not claimed as
part of T-2049's own filing trail.

Gates: frob check --ticket T-2049 --only scope --only prework clean (0
errors) after a fresh `frob test --collect` (9859 node ids) and `frob
ticket sweep T-2049`; `uv run ruff check scripts/fleet_status.py
src/frob/app/ticket_runner/_land_cmd.py` clean of anything I introduced
(1 pre-existing I001 import-sort finding at an unrelated, untouched
import line, not from this change -- confirmed via `git show HEAD --
src/frob/app/ticket_runner/_land_cmd.py`); deletion-filter (`git diff
main --diff-filter=D --stat`) not yet re-checked against current main
tip -- will re-verify immediately before landing

### Changed
```
 scripts/fleet_status.py                 |  92 +++++++++++++++++++++++-
 src/frob/app/ticket_runner/_land_cmd.py |  37 +++++++++-
 tests/unit/test_coordinator_scripts.py  | 115 ++++++++++++++++++++++++++++++
 tests/unit/test_land_cmd_quarantine.py  |  27 +++++++
 tickets/T-2049/done-report.md           | 120 ++++++++++++++++++++++++++++++++
 tickets/T-2049/ticket.md                |  74 +++++++++++++++++++-
 tickets/T-2126/ticket.md                |  49 +++++++++++++
 7 files changed, 509 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestQuarantineState::test_reports_raised_with_undisposed_count` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestQuarantineState::test_reports_clear_when_store_says_cleared` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestQuarantineState::test_reports_clear_when_no_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestQuarantineState::test_unreadable_store_is_unknown_never_clear` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestQuarantineState::test_non_dict_record_is_unknown` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestFleetStatusMainQuarantine::test_prints_raised_with_undisposed_count_and_consequence` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestFleetStatusMainQuarantine::test_prints_clear` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestFleetStatusMainQuarantine::test_prints_unknown_as_unsafe` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings::test_notice_names_undisposed_count_and_dispose_command` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_quarantine.py::TestQuarantineUndisposedSummary::test_no_quarantine_ever_raised_is_unknown_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_quarantine.py::TestQuarantineUndisposedSummary::test_corrupt_store_is_unknown` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_quarantine.py::TestQuarantineUndisposedSummary::test_raised_record_counts_undisposed_findings` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: COV001@src/frob/__main__.py, COV001@src/frob/tickets/_land_git_ops.py, E501@/home/logan/projects/frob/.claude/worktrees/t2049-series/src/frob/tickets/_land.py, TEST001@src/frob/__main__.py, TICK004@tickets.md, TICK006@tickets.md
