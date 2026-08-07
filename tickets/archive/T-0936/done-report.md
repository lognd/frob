## Done report

Migrated all OPEN (queued) EPIC-titled tickets to tier=epic via the CLI
verb landed by T-1069 (frob ticket tier <id> <tier>), never a hand-edit.

Enumeration: grepped every occurrence of "epic" (case-insensitive) in
tickets.md, then applied the ticket's own stated convention -- a
CASE-INSENSITIVE PREFIX match on the title (titles starting "EPIC:" or
"EPIC ") -- to the candidate list, keeping only queued/open tickets
(done/archived tickets excluded per instructions).

Matched and migrated (3):
- T-0329  'EPIC arch multi-language: ...'
- T-0341  'EPIC: strata conformance totality ...'
- T-0969  'Epic: burn WARN-tier quality gates to zero, then promote to ERROR'

Excluded as non-matches (title contains "epic" but not as a prefix, so
the ticket's own convention does not cover them):
- T-0254  'frob deploy epic: ...'          (epic mid-title, not a prefix)
- T-0321  'frob daemon epic: ...'          (epic mid-title, not a prefix)
- T-0397  'AUDIT REMEDIATION EPIC: ...'    (EPIC mid-title, not a prefix)

Verified via `frob ticket show` that all three matched tickets were
state=queued (open) before mutation, and via `grep -n tier: tickets.md`
that exactly three `tier: epic` lines now exist (192, 226, 684 -- one per
migrated ticket) and no other ticket's tier line changed.

Did not touch tickets-archive.md's own EPIC-titled entries (all
done/archived) per the ticket's explicit "done/archived tickets stay
untouched" instruction.

The story-tier-for-children question the ticket raises as open ("also
worth deciding here... whether direct children of an epic-titled ticket
should default to tier: story") was NOT decided or acted on here -- it
is explicitly framed in the ticket body as a separate judgment call, not
part of this migration's acceptance criteria, and doing so would touch
tickets outside the EPIC-title match set this ticket scopes. Left as-is;
noted here rather than silently skipped.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 585 warning(s), 419 waived
- error-findings: ARCH102@src/frob/gates/_waive.py, COV003@tickets/T-0666
