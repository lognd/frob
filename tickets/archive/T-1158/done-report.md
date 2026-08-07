## Done report

Declared a real `owns "tickets.md" "0644";` claim on design/frob.strata's
five tickets_ledger writer nodes (cli/gates/fleet/core/serve), dropping
the five `waive "SYS205:tickets_ledger" ...` clauses T-1061 added. Now
possible because T-1164 filtered `runs_as=None` out of the blast-radius
user set (these nodes declare no `runs_as`), so the new owns= claim no
longer trips a spurious HOST-BLAST scan.

Verified end-to-end via `frob sys audit`: SYS201 (resource contention)
skips all ten pairwise overlaps among the five nodes since they share
tickets_ledger's declared `lock "tickets.lock"` arbiter (T-1149's
arbiter-awareness, wired live via T-1146's module= plumbing); SYS203
(store contention) already skipped via the declared arbiter; SYS205
(mode-conformance) now proves clean with 0 waived instead of the 5
no_declared_path waivers -- confirmed identical 5 pre-existing unrelated
gaps (THREAT003 testsuite, LINT004 serve/testsuite) before and after,
diffed directly against `frob sys audit` run from the primary checkout.

Added a `frob:tests` directive on design/frob.strata's tickets_ledger
resource block pointing at `tests/system/test_frob_self_model.py::
TestFrobSelfModel::test_sys_gate_zero_violations` -- the real
`frob check --only sys`-equivalent system test that runs against this
repo's own live `design/` tree, so evidence binds to the scoped design
file, not just an unrelated CLI-dispatch smoke test.

### Changed
```
 design/frob.strata | 56 +++++++++++++++++++++++++++++++++++++++++++++++++-----
 tickets.md         | 38 +++++++++++++++++++++++++++++++++++-
 2 files changed, 88 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 549 warning(s), 502 waived
- error-findings: none (measured, zero errors)
