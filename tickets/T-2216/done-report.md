## Done report

frob ticket block <id> --by <other> appended --by to the existing ticket's
blocked_by unconditionally (ticket.blocked_by + (cfg.ticket_by,)). Two
successive block calls with the SAME --by (the real incident: a
coordinator "restoring" an edge that was never actually lost) wrote a
duplicate entry -- blocked_by=[T-2211, T-2211] -- that survives the first
blocker being cleared, since any single-occurrence removal only clears one
copy.

Fix: _block now checks `cfg.ticket_by in ticket.blocked_by` before
appending -- a structured tuple-membership check against the already-
parsed blocked_by tuple (never a lexical/string comparison against the
rendered YAML, per the standing token/grammar directive) -- and refuses
(exit 1, naming the existing edge) rather than silently no-opping.

Chose refusal over silent idempotence deliberately: a silent skip would
have let the real incident's mistaken "restore" through unnoticed a
second time with no signal that nothing actually changed. A refusal
naming the existing edge tells the caller immediately "this is already
true, you did not just fix anything" -- the more useful answer to "did my
restore work", and it is exactly the information the coordinator was
missing when they wrote the duplicate. `TestBlockCliValidatesBy::
test_blocking_by_the_same_id_twice_does_not_duplicate_the_edge` pins this.

MUST-STILL-PASS control: test_blocking_by_a_different_second_id_still_
appends verifies a genuinely different second --by still appends normally
(blocked_by = [A, B]) -- the fix does not dedupe broadly or refuse every
second block call, only an exact repeat of an already-present blocker.

Checked whether `frob ticket new --blocked-by` shares this path: it does
NOT. TicketSpec.blocked_by is set ONCE at construction time
(_new_renumber.py:279, `blocked_by=spec.blocked_by`) -- there is no
append here, so there is no analogous duplicate-append hazard for that
path. `_block` (this ticket's own subject, _lifecycle.py:1128) is the
ONLY post-creation append site, per its own pre-existing T-1132 comment.

### Changed
```
 src/frob/app/ticket_runner/_lifecycle.py | 29 ++++++++++++++++
 tests/test_tickets.py                    | 59 ++++++++++++++++++++++++++++++++
 tickets/T-2216/ticket.md                 | 12 +++++--
 3 files changed, 98 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestBlockCliValidatesBy::test_blocking_by_a_different_second_id_still_appends` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestBlockCliValidatesBy::test_cli_refuses_empty_string_by` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestBlockCliValidatesBy::test_cli_refuses_malformed_by` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestBlockCliValidatesBy::test_cli_accepts_valid_by` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestBlockCliValidatesBy::test_blocking_by_the_same_id_twice_does_not_duplicate_the_edge` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2216/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2216/tests/test_ticket_work_and_land_finish.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2216, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
