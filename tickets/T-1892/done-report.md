## Done report

WHY. `run_cmd_evidence` (the `--evidence-cmd` primitive `add_cmd_evidence`
uses for docs-kind tickets, T-0215) recorded a sha256 digest over captured
stdout alone. A silent zero-exit command (`grep -q`, `true`, `: `, `cd .`)
captures empty stdout, so ALL of them collide on `sha256=e3b0c44298fc` --
the SHA-256 of the empty string. The ledger entry looks like a well-formed
evidence record and demonstrates nothing about what was actually checked.
MEASURED closing T-1644 on main: `grep -q '...' design/frob.strata`
recorded exactly this empty digest.

FIX CHOSEN: option 1 (refuse), not option 1+2. `run_cmd_evidence` now
refuses (`Err(EvidenceCmdSilent)`, a new `TicketError` variant) any
command whose captured stdout+stderr are BOTH empty, even when it exits
0 -- before the digest is ever computed. The refusal message names the
concrete fix (prefer `grep -c`/`grep -n` over `grep -q`) so the failure
mode is a nudge toward a real check, not a dead end. Option 2 (folding the
command string into the digest input) was NOT added: it would make two
different silent commands produce two different digests, but each would
still look like independently-verified proof while proving nothing --
distinguishable garbage is still garbage. Refusing at record time is the
only fix that actually restores the channel's integrity, so 1 alone is
sufficient and 2 would only add a second axis of false confidence.

COMPATIBILITY DECISION: prospective-only, deliberately. Existing ledger
entries carrying the empty-string digest (T-1644's included) are NOT
retroactively flagged or invalidated by this change -- `reverify_cmd_
evidence` (the read-path re-check) is untouched, so an already-closed
ticket's stale empty-digest entry still reverifies exactly as it did
before. Rationale: (a) the ticket instructions say explicitly not to
silently invalidate historical evidence, and retroactively flagging past
closes would either force a costly resurrection sweep of every past
docs-kind ticket or fabricate certainty ("this evidence was BAD") that a
static digest match cannot actually establish -- the underlying command
may well have verified something real even though its own OUTPUT was
silent, we just can no longer prove it from the ledger entry alone; (b)
the refusal is cheap and immediate at RECORD time going forward, which is
the actual point of leverage -- every new close is protected starting
now, and a bulk retroactive audit of historical `cmd:` evidence (if
wanted) is a separable, explicitly-scoped follow-up, not something to
fold silently into this bug fix.

FOLLOW-UP FILED: docs/modules/tickets.md needed a matching note in its
cmd: evidence section (the ticket's own docs/modules/tickets.md#public-api
anchor already documents `run_cmd_evidence`), but that file is leased by
T-1883 (in-progress) for the entire duration of this ticket's work
(`ScopeLeaseConflict` on `--add docs/modules/tickets.md`), so it could not
be touched here. Filed T-1899 ("docs: document T-1892's
EvidenceCmdSilent refusal in docs/modules/tickets.md", kind=docs, scope
docs/modules/tickets.md) to land once the T-1883 lease clears.

Changed:
- src/frob/tickets/_evidence.py::run_cmd_evidence
- src/frob/tickets/_models.py::TicketError (new variant EvidenceCmdSilent)
- tests/test_tickets_cmd_evidence.py::TestSilentCmdEvidenceRefused (new)

Evidence:
- tests/test_tickets_cmd_evidence.py::TestSilentCmdEvidenceRefused::test_silent_zero_exit_command_is_refused
- tests/test_tickets_cmd_evidence.py::TestSilentCmdEvidenceRefused::test_grep_q_silent_match_is_refused
- tests/test_tickets_cmd_evidence.py::TestSilentCmdEvidenceRefused::test_chatty_zero_exit_command_is_accepted
- tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_exit_zero
- tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_nonzero_exit

Filed: T-1899 (docs update, blocked on T-1883's docs/modules/tickets.md lease)

Gates: `frob check --ticket T-1892 --only gates` clean (0 errors, 984
warnings/696 waived -- all pre-existing repo-wide, none newly introduced by
this change; gate:PRE cleared after `frob ticket sweep T-1892`).

### Changed
```
 tickets/T-1892/ticket.md           | 31 ++++++++++++++++++++++++++++++-
 tickets/T-1899/ticket.md | 38 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 68 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_cmd_evidence.py::TestSilentCmdEvidenceRefused::test_silent_zero_exit_command_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestSilentCmdEvidenceRefused::test_grep_q_silent_match_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestSilentCmdEvidenceRefused::test_chatty_zero_exit_command_is_accepted` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_exit_zero` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_nonzero_exit` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 3 error(s), 986 warning(s), 696 waived
- error-findings: invalid-argument-type@src/frob/app/ticket_runner/_lifecycle.py, invalid-argument-type@tests/test_tickets_scope_mutation.py, invalid-argument-type@tests/unit/gates/test_sys_interface_canonical_order.py
