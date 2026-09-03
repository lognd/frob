## Done report

Wrote docs/design/ledger-mirror-batching.md: a pending-mirror-queue + per-event-flush design for mirror_ledger_change_to_primary (land-completion / sweep-completion / bounded-timer flush triggers), crash-safety for enqueue and flush, T-3297 merge-driver reuse for the flush commit path, which verbs stay per-commit (block/unblock edges, land's own commit) versus batch (scope/body/evidence/done-report/mirror), and an explicit file-reader-vs-git-history-reader classification (doable/show read files and are safe to lag; land's own ancestry check, TDD001, and CrossTicketLeakage/scope-closure are git-history readers, the last of which needs an owner call this doc could not resolve on its own). Re-measured the 41 file commits in 300 T-3544 assumed were sweep-filed: actual measurement against main HEAD 42ab32443 found 12 sweep-filed and 41 ordinary frob-ticket-new filings, neither a batching target (sweeps already file at most one per run per T-3544's own Failure log; the 41 are distinct human/agent filing decisions, not mechanical repetition). Filed the implementation ticket T-3559, blocked by T-3550 pending the owner sign-off the design doc names. Did not implement batching in this ticket per its own body. Filed: T-3559.

### Changed
```
 tickets/T-3550/ticket.md | 15 +++++++++++++--
 tickets/T-3559/ticket.md | 34 ++++++++++++++++++++++++++++++++++
 2 files changed, 47 insertions(+), 2 deletions(-)
```

### Evidence
- `cmd:bash -c "grep -n \"Re-measurement\\|Hazard needing an owner call\\|Deliverable status\" docs/design/ledger-mirror-batching.md" exit=0 sha256=c83bc0e4e94f` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
