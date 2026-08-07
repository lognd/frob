## Done report

Main's ledger is migrated to v2: 1748 tickets moved from the
tickets.md/tickets-archive.md monofiles into per-ticket
tickets/T-####/ directories.

T-1669 names the v1 monofile as the root cause of nearly every
ticket-handling failure in this drive, and the day's incident list bears
that out. One file holding every record, copied into every worktree,
merged line-wise by git, produced: T-1721 (the land splice silently
dropping a sibling ticket's edit -- three lost attempts before it was
caught), T-1740 (a refused land leaving merged files staged in root's
index, where a bare commit published 1416 lines of another agent's work),
T-1755 (the detached sweep leaving ledger writes uncommitted and blocking
every land repo-wide, four manual clears), and an archive pass that gave
an in-flight worktree duplicate ticket ids across active and archive.
Every one of those is a consequence of shared-file, line-wise merging of
structured records.

VERIFICATION, count AND content, not exit status:
- active 158 -> 158, archive 1590 -> 1590, union 1748 -> 1748
- zero missing, zero extra
- `frob ticket list` reads the v2 store back correctly
- gates clean afterwards

Run by the coordinator by hand rather than dispatched, because the change
rewrites the ticketing system while agents are using the ticketing
system. Three live agents were quiesced first and their work committed to
their branches; ten stale worktrees were removed after checking each for
uncommitted work and unlanded commits.

TWO PRE-EXISTING DEFECTS SURFACED, both of which a count-only check would
have missed:

T-0450 was already lost. Its YAML block sat inside T-0449's section with
no ticket marker, so `_parse_ledger` had been silently skipping it --
1590 ids present in the file, 1589 parsed. The migration did not drop it;
it had been invisible to frob for some time. The marker was restored and
the migration re-run so it carried across. This is the strongest argument
for the count-and-content bar: the first migration run reported
1747 -> 1747 and looked perfectly clean.

T-1433's attachments had never been committed. The record referenced
three files that existed only as untracked working-tree state in agent
worktrees; `attachments/` had zero tracked files. Recovered and verified
against the ticket's own recorded sha256 digests.

ROLLBACK remains available and was deliberately preserved: the migrator
never deletes the monofiles, so removing the tickets/T-*/ and
tickets/archive/ trees restores the previous state exactly. Retiring the
monofiles is deliberately NOT part of this ticket -- they stay until the
v2 store has been exercised through real land/archive cycles.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 661 warning(s), 724 waived
- error-findings: none (measured, zero errors)
