## Done report

Documented T-1886's `_WAIVE004_PROPORTIONAL_MIN_LIVE_COUNT = 2` floor in the
T-1620 mass-invalidation addendum of docs/modules/gates.md, mirroring the
`_DEFLATION_MIN_KNOWN_MODULES` precedent. Recorded the T-1579/T-1592
history (a `_rule_has_live_finding` escape hatch that deleted 55 live
waivers during a real land because a partially-degraded run found some
instances of a rule lexically while missing the sites the waivers
covered; reverted, locked by
`tests/test_gates.py::TestWaive004DegradedRunGuard::test_mass_invalidation_with_live_finding_elsewhere_still_refuses`)
so a future reader understands both guards' unconditional-refusal
behavior is the deliberate post-incident state, not an oversight -- and
that the successor design (per-site analysis-coverage proof) is T-1904,
not yet built.

Bound the doc to code via a `frob:describes` anchor on
`src/frob/gates/_fix_engine_sync.py::_WAIVE004_PROPORTIONAL_MIN_LIVE_COUNT`
placed in docs/modules/gates.md itself (no source-file edit needed, kept
the change inside the ticket's declared docs/modules/gates.md scope), then
`frob ack`'d it. Extended scope to include frob.lock since acking writes
it.

### Changed
```
 docs/modules/gates.md    | 41 +++++++++++++++++++++++++++++++++++++++++
 frob.lock                | 14 ++++++++++++++
 tickets/T-1893/ticket.md | 10 +++++++++-
 3 files changed, 64 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 1 error(s), 1051 warning(s), 695 waived
- error-findings: REG002@docs/design/registry/check-coverage.yaml
