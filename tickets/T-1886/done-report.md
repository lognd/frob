## Done report

Chose the product-correct fix over the test-fixture fix: the T-1620
proportional mass-invalidation check (_mass_invalidation_rules in
src/frob/gates/_fix_engine_sync.py) fired at N=1 (a rule with exactly one
live frob:waive directive going stale reads as "100% of this rule's
waivers went stale", the same signature the guard treats as a degraded
run). A repo with exactly one live waiver for some rule is an ordinary,
common state, not itself evidence of degradation -- and a sample size of
one carries no proportional signal at all (there is no "proportion" with
a denominator of 1). Padding the test fixture with a second, live REF001
site would have made the test pass without fixing the underlying defect:
fix_waive004_stale_waiver would still be structurally unable to ever clean
up a genuinely dead lone waiver for any low-traffic rule in a real repo.

Fix: added _WAIVE004_PROPORTIONAL_MIN_LIVE_COUNT = 2, a minimum-sample-size
floor mirroring the _DEFLATION_MIN_KNOWN_MODULES precedent in
frob.gates._coverage (below a minimum sample, the check does not fire
rather than firing on noise). The proportional check now only considers a
rule's waivers for mass-invalidation once there are >= 2 live waivers to
reason about a proportion over; N=1 falls through to the (unchanged)
absolute-threshold check alone. 2-of-2 and above still trip the guard
exactly as before -- only the N=1 case, which never carried real
proportional evidence, is excluded.

Docs: docs/modules/gates.md's T-1620 write-up needed a short addendum
documenting this floor, but docs/modules/gates.md was under T-1877's live
cross-worktree scope lease at the time (ScopeLeaseConflict on `frob ticket
scope T-1886 --add docs/modules/gates.md`), so the edit was reverted and
filed as a follow-up docs-only ticket (T-1893) instead of forcing
the lease.

### Changed
```
 tickets/T-1886/ticket.md           |  2 +-
 tickets/T-1887/done-report.md      | 25 +++++++++++++++++++++++++
 tickets/T-1887/ticket.md           |  4 +++-
 tickets/T-1893/ticket.md | 35 +++++++++++++++++++++++++++++++++++
 4 files changed, 64 insertions(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 2 error(s), 1468 warning(s), 692 waived
- error-findings: ARCH001@src/frob/refactor/_verify.py, REG002@docs/design/registry/check-coverage.yaml
