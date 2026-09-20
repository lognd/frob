## Done report

Updated the Deferred post-land sweep section of docs/modules/tickets-verify-sweep.md to describe T-4335's measure/persist split -- what run_deferred_post_land_sweep now persists to the rolling baseline on each branch (first-run establish, filed regression, no-new-findings tolerated debt, stale-queue refusal excluded), and the inherited-vs-introduced debt distinction that motivates the split. No code changes; docs-only, scoped to this one file per the ticket.

### Changed
```
 docs/modules/tickets-verify-sweep.md | 45 +++++++++++++++++++++++++++++-------
 tickets/T-4344/ticket.md             |  2 ++
 2 files changed, 39 insertions(+), 8 deletions(-)
```

### Evidence
- `cmd:uv run frob check --ticket T-4344 exit=0 sha256=b69f65e5a1b2` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 4799 warning(s), 957 waived
- error-findings: none (measured, zero errors)
