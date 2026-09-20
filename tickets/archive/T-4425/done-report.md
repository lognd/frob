## Done report

CI self-gate DOC011 failed on all three legs: docs/modules/tickets-lifecycle.md cited T-4313, a ghost id printed by frob ticket new on 2026-09-09 that was never written anywhere. Replaced the citation with T-4342, the real ticket that added orphaned-lock detection for exactly this shape. Verified with uv run frob check --only docstatus (0 DOC011 hits, 0 errors).

### Changed
```
 docs/modules/tickets-lifecycle.md |  3 ++-
 tickets/T-4425/ticket.md          | 12 +++++++++++-
 2 files changed, 13 insertions(+), 2 deletions(-)
```

### Evidence
- `cmd:uv run frob check --only docstatus exit=0 sha256=47c178cc1d65` (cmd evidence, exit=0)
