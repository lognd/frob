## Done report

Repro: committed tests/unit/verify/test_quarantine.py alone (7b2289ede),
confirmed it FAILS at that commit via --check-repro (FAILED_AT_PARENT).
Fixed in a separate commit (e32ae9e11).

Root cause: raise_quarantine treated every finding identically. TICK004
(ticket-rot, date.today() minus a ticket's created date) has no commit
that could ever be its cause -- commit=None there is the TRUTH, not a
failed attribution -- yet it was raising quarantine off deferred landing
repo-wide the same as a genuine unattributed code regression.

Fix: a curated, human-decided frozenset (_NATURALLY_UNATTRIBUTABLE_RULES,
currently {TICK004}) is filtered out of findings inside raise_quarantine
itself, before the emptiness check and before persisting -- the single
choke point both real callers (_land_cmd's backpressure-timeout raise and
_rapid_sweep's red-batch raise) already go through, so neither needed its
own copy of this rule. Membership is decided by reading the RULE's own
implementation (does it read git-tracked content at all, or purely
date.today()/queue state), never inferred from an Attribution's runtime
status -- a genuinely unattributed CODE finding (attribution attempted,
walked the reference graph, found zero/more-than-one candidates) is NOT
in this set and still raises, per the T-1686 prior-art incident this
module's own docstring already references (a sweep once dropped
UNATTRIBUTED findings as non-regressions; that was itself a bug).

### Changed
```
 src/frob/verify/_quarantine.py       | 65 ++++++++++++++++++++++++++++++++++--
 tests/unit/verify/test_quarantine.py | 62 ++++++++++++++++++++++++++++++++++
 tickets/T-2132/ticket.md             | 37 ++++++++++++++++++--
 3 files changed, 158 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_a_naturally_unattributable_finding_alone_does_not_raise` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_an_unattributed_code_finding_still_raises` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_a_mixed_batch_raises_with_only_the_attributable_finding_kept` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/verify/_quarantine.py, DUP001@src/frob/verify/_quarantine.py, E501@/home/logan/projects/frob/.claude/worktrees/t2132-t1966/src/frob/verify/_quarantine.py, PRE001@tickets/T-2132, SELFAUDIT001@design, TICK004@tickets.md
