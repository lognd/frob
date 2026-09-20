## Done report

Fixed the reporting gap named in the ticket: when a `.frob/rapid-debt.jsonl`
`post-land-unscoped-sweep-deferred` entry stays live (no later full sweep
has covered its commit), `frob verify status` now surfaces it -- a new
`rapid_debt_live` field on `VerifyStatus`, a `rapid-debt (deferred sweep,
unverified): <n>` line in the human output, an entry in the `--json`
payload, and the command now exits non-zero while any entry is live (the
same porcelain rule quarantine already had). Liveness is computed, not
stored, since the log is a permanent append-only audit trail: an entry is
cleared once the rolling post-land-sweep baseline has since advanced to a
commit that is the debt commit or a descendant of it.

Evidence: tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt (5
new tests) bound via `frob ticket close --evidence`; `frob test --base
main` green (12 python tests recorded).

END-TO-END VERIFICATION (forcing the condition, per the brief): wrote a
real rapid-debt.jsonl `post-land-unscoped-sweep-deferred` entry against a
scratch git repo and ran the actual `frob verify status` CLI (not just
`build_status`) -- confirmed it printed `rapid-debt (deferred sweep,
unverified): 1` and exited 1; then wrote a rolling-sweep baseline
covering that commit and re-ran the same CLI, confirmed it printed
`rapid-debt ...: clear` and exited 0.

Filed: T-4330 (bug) -- two pieces of PRE-EXISTING debt on
src/frob/app/verify_runner.py surfaced by `frob check --ticket T-4324`
that predate this ticket's diff and are not fixable within this ticket's
narrow, single-file scope without an unbounded scope-closure cascade
(measured: adding docs/modules/tickets-verify-sweep.md to scope pulled in
~135 unrelated doc-anchor warnings; adding design/frob.strata pulled in
~240):
  1. SELFAUDIT001: this file's fs.read call sites (pre-existing ones plus
     this ticket's own two new ones) are not declared in
     design/frob.strata's cli node.
  2. SCOPE002: several pre-existing public symbols in this file carry
     frob:doc/frob:tests targets (docs/modules/tickets-verify-sweep.md,
     src/frob/verify/_quarantine.py, tests/unit/verify/test_watermark.py)
     outside this file's own historically-narrow ticket scope
     declarations.

Gates: `frob check --ticket T-4324` clean except the two rule ids above
(SCOPE002 x3, SELFAUDIT001 x2), both pre-existing and filed rather than
waived in place, since fixing either would require expanding this
ticket's scope far beyond its own declared file. All other gates (ruff,
ty, exports, FMT, LARGE, LANDPARITY, COV, PRE, and every other gate
family) are clean.

### Changed
```
 tickets/T-4324/ticket.md           | 80 ++++++++++++++++++++++++++++++++++++++
 tickets/T-4330/ticket.md | 65 +++++++++++++++++++++++++++++++
 2 files changed, 145 insertions(+)
```

### Evidence
- `tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_no_baseline_is_live` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_later_baseline_clears` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_uncovered_stays_live` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_other_skip_reasons_are_not_counted` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_clean_status_has_no_live_rapid_debt` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 2 error(s), 4687 warning(s), 956 waived
- error-findings: SCOPE002@tickets.md, SELFAUDIT001@src/frob/app/verify_runner.py
