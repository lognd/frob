## Done report

Fixed PERF005's bare-short-name recursion detector to treat '::' as a
scope operator, excluded from the receiver-aware candidate-callee set the
same way non-self '.'-qualified calls already are. Added must-fire and
must-stay-quiet Rust fixtures. Confirmed via `uv run frob check --only perf`
that gate:PERF is 0 errors/64 warnings/139 waived with no model.rs:257
finding in the output. `uv run frob test` (touched=5) is clean, python
exit=0.

Filed: none (no out-of-scope work found).

### Changed
```
 src/frob/perf/_recursion.py | 25 +++++++++++++++--------
 tests/test_perf.py          | 50 +++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3479/ticket.md    |  3 +++
 3 files changed, 70 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_perf.py::test_perf005_does_not_fire_on_unrelated_scope_qualified_new` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_perf005_still_fires_on_scope_qualified_self_recursion` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 22 error(s), 4081 warning(s), 867 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3479, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/app/ticket_runner/_land_cmd.py, WIRE002@src/frob/gates/_arch.py, WIRE002@src/frob/gates/_coverage_sites.py, WIRE002@src/frob/gates/_render_lint.py, WIRE002@tests/unit/test_new_ticket_scope_overlap_warning.py
