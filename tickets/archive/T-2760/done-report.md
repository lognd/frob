## Done report

Changed:
- src/frob/tickets/_models.py::Ticket.findings (new field)
- src/frob/tickets/_models.py::TicketSpec.findings (new field, _normalize_findings validator)
- src/frob/tickets/_models.py::TicketError.DuplicateFinding (new error)
- src/frob/tickets/_new_renumber.py::_normalize_finding_file
- src/frob/tickets/_new_renumber.py::_find_finding_duplicate
- src/frob/tickets/_new_renumber.py::_refuse_finding_duplicate
- src/frob/tickets/_new_renumber.py::_validate_new_ticket_spec (wired the new check in)
- src/frob/tickets/_new_renumber.py::_ticket_from_spec (carries spec.findings onto Ticket)
- src/frob/tickets/_evidence.py::_warn_if_finding_duplicate_at_start
- src/frob/tickets/_evidence.py::_transition_guard (calls the warn at IN_PROGRESS)
- src/frob/_cli_parsers/_ticket/_new.py::_add_ticket_new_parser (new --finding RULE:FILE flag)
- src/frob/app/config.py::AppConfig.ticket_findings (new field)
- src/frob/app/_config_external.py (_LIST_FIELDS registration)
- src/frob/app/ticket_runner/_new.py::_resolve_new_findings (new)
- src/frob/app/ticket_runner/_new.py::_ticket_spec_from_cfg (wires findings through)
- src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket (populates
  findings=tuple(unfiled_pairs) on the auto-filed TicketSpec -- covers the sweep's
  own auto-filing path, the one T-2760's incident showed diverges most from a
  hand-written title)
- docs/modules/tickets-data-storage.md (Ticket.findings / TicketSpec.findings
  documented in the Data models section)

Approach: added a structured `findings: tuple[tuple[str, str], ...]` field to
both `Ticket` and `TicketSpec`, separate from `scope` (a file write-lease claim)
and never parsed from title/body prose (per the ticket's own explicit "do not
title-after-the-fact" direction). `frob ticket new --finding RULE:FILE`
(repeatable) sets it by hand; the rapid sweep's auto-filing path
(`_file_regression_ticket`) sets it directly from its own already-structured
`unfiled_pairs`, so the auto-filing path that diverges most from hand-written
titles is covered by construction. `_refuse_finding_duplicate` (filing time)
refuses `Err(TicketError.DuplicateFinding)` when any open (non-DONE,
non-DROPPED) ticket already declares an overlapping (rule, file) pair, naming
the other ticket -- overlap on ANY shared pair, not exact-set equality, so a
ticket owning several distinct findings is unaffected. `_warn_if_finding_
duplicate_at_start` (start time) WARNS loudly (does not refuse -- see its own
docstring for why: a ticket may already carry real scope/evidence filed before
the overlap existed, and refusing would strand legitimate work), naming the
other ticket. Both sides normalize the file component to repo-relative POSIX
form (`_normalize_finding_file`, mirroring T-2036's `_normalize_identity_file`
precedent) so an absolute-path finding and a repo-relative finding for the same
file are never treated as different identities.

Positive controls verified (both in pytest and by hand via a scratch repo):
- same (rule, file): second ticket refused, naming the first (test_same_finding_
  is_refused; manual repro: T-0001 filed with --finding RULEX:some/file.py,
  T-0002 with the same pair refused with "T-0001 already declares finding(s)
  [('RULEX', 'some/file.py')]")
- different findings, same file: BOTH allowed (test_different_findings_in_the_
  same_file_are_both_allowed; manual repro: RULEY:some/file.py succeeded
  alongside the existing RULEX:some/file.py ticket)
- existing title-based duplicate check (T-1744) unchanged
  (test_title_duplicate_check_still_works_unchanged)
- DONE ticket's finding does not block refiling a regression
  (test_done_finding_does_not_block_refiling)
- no findings declared -> never checked (test_no_findings_declared_is_never_
  checked)
- start-time warning names the other ticket
  (test_start_warns_and_names_the_other_ticket)

Evidence: tests/test_tickets.py::TestNewTicketFindingDuplicateRefusal::test_same_finding_is_refused
tests/test_tickets.py::TestNewTicketFindingDuplicateRefusal::test_different_findings_in_the_same_file_are_both_allowed
tests/test_tickets.py::TestNewTicketFindingDuplicateRefusal::test_no_findings_declared_is_never_checked
tests/test_tickets.py::TestNewTicketFindingDuplicateRefusal::test_done_finding_does_not_block_refiling
tests/test_tickets.py::TestNewTicketFindingDuplicateRefusal::test_title_duplicate_check_still_works_unchanged
tests/test_tickets.py::TestTicketStartWarnsOnFindingDuplicate::test_start_warns_and_names_the_other_ticket

Also re-ran the full tests/test_tickets.py (192 passed) and tests/unit/test_rapid_sweep.py
(156 passed) and tests/unit/test_app_config_flag_coverage.py (7 passed) to confirm no
regressions.

Filed: none (no out-of-scope work discovered).

Gates: frob check --ticket T-2760 --only gates-fast clean for every gate this
scope covers (gate:AFFECT, gate:SCOPE both 0 errors). Remaining gate-summary
failures (gate:COV/DRIFT/TEST/TICK) are repo-wide, pre-existing, and touch
files this ticket's diff never modified (verified via `git diff --stat` against
each finding's file) -- per the tool's own gate:scope-note, those families are
not filtered to this ticket's scope.

### Changed
```
 tickets/T-2760/ticket.md | 99 +++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 98 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets.py::TestNewTicketFindingDuplicateRefusal::test_same_finding_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestNewTicketFindingDuplicateRefusal::test_different_findings_in_the_same_file_are_both_allowed` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestNewTicketFindingDuplicateRefusal::test_no_findings_declared_is_never_checked` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestNewTicketFindingDuplicateRefusal::test_done_finding_does_not_block_refiling` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestNewTicketFindingDuplicateRefusal::test_title_duplicate_check_still_works_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestTicketStartWarnsOnFindingDuplicate::test_start_warns_and_names_the_other_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 17 error(s), 1413 warning(s), 710 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DUP001@src/frob/tickets/_new_renumber.py, E501@/home/logan/projects/frob/.claude/worktrees/t2760-t2762/src/frob/tickets/_new_renumber.py, PERF004@src/frob/tickets/_evidence.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
