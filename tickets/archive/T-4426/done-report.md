## Done report

Changed:
- tickets/T-4041/done-report.md (Filed: line)

Investigation: git-logged T-4383 (cfc17a573, filing commit's own
title names the intended real id as T-0843). Confirmed T-0843 was never
created (no tickets/T-0843/ in the active ledger or archive), and the draft
file itself (tickets/T-4383/) no longer exists in the tree, last
touched at ba8b976cb/c2669e42e with no subsequent promotion/rename commit.
T-4394's own post-land-sweep investigation independently reached the same
conclusion (pre-existing, disclosed draft-loss residue). There is no live
id to repoint the citation to.

Fix: corrected T-4041's Done report to disclose the draft loss explicitly
(T-0707/T-0615 incident class) instead of citing a dead id as if it
resolves, and flagged that the archive-lease regression the draft was
meant to capture is unfiled if it is still a live concern. Used
`frob ticket done-report T-4041 --why-file ...` (a ticket verb, not a
hand-edit of tickets.md).

Filed: none (this ticket already covers the fix; no further follow-up
identified).

Gates: `frob ticket evidence --check-repro` N/A (docs kind, no test
evidence path) -- 2 --evidence-cmd checks recorded instead: absence of the
raw dead citation is implied by the corrected text (grep confirms the new
disclosure sentence is present in T-4041's done-report.md).

### Changed
```
 tickets/T-4041/done-report.md | 16 +++++++++++++++-
 1 file changed, 15 insertions(+), 1 deletion(-)
```

### Evidence
- `cmd:grep -c T-4383 tickets/T-4041/done-report.md exit=0 sha256=4355a46b19d3` (cmd evidence, exit=0)
- `cmd:grep -c 'was LOST before promotion' tickets/T-4041/done-report.md exit=0 sha256=4355a46b19d3` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 8 error(s), 4800 warning(s), 959 waived
- error-findings: DOC011@docs/modules/tickets-lifecycle.md, LARGE001@src/frob/app/verify_runner.py, LARGE001@src/frob/testing/_collect.py, MILE001@tickets.md, MILE002@tickets.md, PRE001@tickets/T-4426, TICK004@tickets.md, TICK006@tickets.md
