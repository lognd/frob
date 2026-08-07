## Done report

Fixed the T-0380 incident class: closed the write-time gap (an empty-
string or malformed blocked_by/parent entry could silently enter the
ledger) at every write path found, and added a doctor scan for any
already-malformed entry.

Write-time refusal, two distinct sites (both matter -- pydantic's
model_copy does not re-run field validators, so one alone is not enough):
- `TicketSpec.blocked_by`/`parent` field validators (frob.tickets._models)
  reject an empty-string or non-T-####/T-draft-<hex> entry at `frob
  ticket new` construction time. `Ticket` (the ledger LOAD model) does
  NOT carry the same validator -- deliberately: `Ticket.model_validate`
  is also the strict ledger-load path (frob.tickets._store._parse_ledger),
  and a hard validator there would fail the ENTIRE shared (1000+-ticket)
  ledger's load the moment a single historical malformed entry exists
  anywhere in it -- a much worse failure mode than the T-0380 incident
  itself. Documented this design choice directly in Ticket's docstring so
  a future reader does not "fix" it back onto Ticket.
- `frob ticket block <id> --by <other>` (frob.app.ticket_runner._lifecycle
  ._block) is the one CLI verb that appends to an EXISTING ticket's
  blocked_by post-creation, via model_copy -- which bypasses TicketSpec/
  Ticket validators entirely regardless, per pydantic's own documented
  model_copy semantics. Added an explicit is_valid_ticket_ref(cfg.
  ticket_by) check before the write, refusing with a clear error.

New public helper: is_valid_ticket_ref (frob.tickets._models, re-exported
from frob.tickets) -- the shared shape check both the field validators
and the manual _block guard use.

Read side: frob.doctor.scan_malformed_ticket_edges scans tickets.md AND
tickets-archive.md for an existing malformed blocked_by/parent entry,
wired into DoctorReport.malformed_ticket_edges / run_diagnosis's healthy
verdict and remediation text (same class as the existing stale-mutate-
journal check -- a finding DOES make healthy False). Deliberately reads
RAW frontmatter dicts (new frob.tickets._store.iter_raw_ledger_frontmatter,
tolerant of one malformed YAML block rather than failing the whole scan),
never the strict Ticket loader, for the same reason Ticket itself does
not validate on load: doctor's job is to find a bad edge WITHOUT risking
every other frob command (built on load_all) hard-failing the instant one
exists.

Updated docs/modules/tickets.md (public-api entry for is_valid_ticket_ref,
storage-internals entry for iter_raw_ledger_frontmatter, a blocked_by
field note) and docs/guides/install.md (new "Malformed ticket edge scan
(T-1132)" section, matching the existing mutate-journal/scaffold section
style) in the same change.

Verified the CURRENT tickets.md/tickets-archive.md (1133 tickets,
active+archive) carries zero existing malformed edges -- scan_malformed_
ticket_edges reports an empty list against the real ledger.

Out of scope, not touched: the same pre-existing SCOPE002 scope-closure
debt across src/frob/tickets/** noted in T-1125's Done report (already
tracked as T-1145); the pre-existing TICK006 phantom (T-1114's Done
report citing a dead draft id) and INV006 finding (src/frob/app/
ticket_runner/_mutate.py) surfaced by `frob check --ticket T-1132` are
unrelated to this diff, confirmed by symbol/file (neither touches
anything this ticket's scope covers).

### Changed
```
 docs/guides/install.md                   |  39 +++++++
 docs/modules/tickets.md                  |  32 ++++++
 src/frob/app/ticket_runner/_lifecycle.py |  20 +++-
 src/frob/doctor.py                       | 120 ++++++++++++++++++++-
 src/frob/tickets/__init__.py             |   2 +
 src/frob/tickets/_models.py              |  95 ++++++++++++++++
 src/frob/tickets/_store.py               |  51 +++++++++
 tests/system/test_cli_doctor.py          | 101 +++++++++++++++++
 tests/test_tickets.py                    | 180 +++++++++++++++++++++++++++++++
 tickets.md                               |  48 ++++++++-
 10 files changed, 681 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestBlockCliValidatesBy::test_cli_refuses_empty_string_by` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestBlockCliValidatesBy::test_cli_refuses_malformed_by` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestBlockCliValidatesBy::test_cli_accepts_valid_by` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestTicketSpecValidatesBlockedByAndParent::test_new_ticket_refuses_empty_string_blocked_by` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestTicketSpecValidatesBlockedByAndParent::test_new_ticket_refuses_malformed_parent` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestTicketSpecValidatesBlockedByAndParent::test_new_ticket_accepts_well_formed_blocked_by_and_parent` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestIsValidTicketRef::test_accepts_final_id` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestIsValidTicketRef::test_accepts_draft_id` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestIsValidTicketRef::test_rejects_empty_string` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestIsValidTicketRef::test_rejects_malformed_id` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestIterRawLedgerFrontmatter::test_returns_raw_dict_per_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestIterRawLedgerFrontmatter::test_skips_malformed_yaml_block_without_raising` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_run_diagnosis_healthy_with_no_malformed_edges` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_scan_flags_empty_string_blocked_by` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_scan_flags_malformed_parent` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_scan_ignores_well_formed_edges` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 16 passed (from 16 evidence id(s))
- gates: 17 error(s), 978 warning(s), 427 waived
- error-findings: COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:295, INV006@src/frob/app/ticket_runner/_mutate.py, PII012@tests/system/test_cli_doctor.py, SELFAUDIT001@design, TICK006@tickets.md
