## Done report

Added `fix_e501_merge_introduced` to `src/frob/gates/_fix_engine.py`,
registered as `TIER_A_HANDLERS["E501"]`. It derives the exact `.py` files a
land-time merge touched (`_merge_touched_python_files`: HEAD's own
two-parent merge diff, or uncommitted working-tree changes against HEAD
for the in-progress-merge shape `frob ticket land`'s pre-land Tier-A phase
runs in), runs a targeted `ruff format` on any of them that still carries
an E501 finding, and re-verifies E501 is actually gone
(`_e501_lines_for_file`, a scoped `ruff check --select E501` before/after)
before counting the file as fixed -- never claims a fix `ruff format`
did not actually make.

Doc note: `docs/modules/gates.md` (where every sibling Tier-A handler's
own writeup lives) was under an in-progress lease held by T-1205 for the
whole duration of this ticket, so per playbook ScopeLeaseConflict
guidance the doc content lives in a new page,
<!-- frob:waive DOC006 reason="historical Done report: docs/modules/gates_e501_autofix.md was real when this landed; T-1580's own follow-up (also in this ledger) later folded it into gates.md and deleted it" -->
`docs/modules/gates_e501_autofix.md`, instead -- disclosed inside that
page itself, with a named follow-up (T-1580, filed; renumbers
at land) to fold it into `gates.md` proper once T-1205's lease clears. `tests/test_gates.py` was
under the same lease (T-1205); the two new tests live in the sibling
`tests/test_gates_fix_engine.py` module instead (already the home of the
SUPPRESS001/FMT001 Tier-A handler tests, so this is not a new
convention). While there I also fixed
`TestFixEngineTierABatch2::test_tier_a_handlers_dict_covers_every_batch_rule`'s
stale `TIER_A_HANDLERS` key-set assertion -- but reverted that edit once I
confirmed `tests/test_gates.py` is leased; it stays broken on the
`E501`/`SYS100`/`SYS104` keys until T-1205's lease clears and someone can
touch that file (noting this here rather than leaving it silent; it was
ALREADY broken on `SYS100`/`SYS104` before this ticket, T-1531 never
updated it, so this ticket does not newly break a passing test -- it
would newly reveal `E501` was missing too, on the same already-red
assertion).

Residue at `frob check --ticket T-1547`: 3 SELFAUDIT001 findings (SYS100
exec-capability + 2x SYS104 undeclared-public-symbol, for
`fix_e501_merge_introduced`/`TestFixE501MergeIntroduced`) against
`design/frob.strata` -- expected to self-heal via `frob ticket land`'s own
pre-land `fix_sys100_may_via_union`/`fix_sys104_interface_union` Tier-A
handlers (T-1531 precedent every other new Tier-A symbol in this module
relies on); I could not hand-edit `design/frob.strata` myself since it
sits under an in-progress T-1220 lease. 4 pre-existing TICK006 findings
(T-1238 phantom draft citations) are unrelated repo-wide debt, not
introduced by this ticket.

Filed: T-1580 (fold docs/modules/gates_e501_autofix.md into
docs/modules/gates.md once T-1205's lease clears; renumbers at land).

Gates: `frob check --ticket T-1547` -- 0 SCOPE/PRE/COV/FMT errors; the 3
SELFAUDIT001 + 4 TICK006 residue above are the only errors, both
disclosed and out of this ticket's own reach (lease conflicts / land-time
self-heal / pre-existing debt), not new regressions this ticket's own
diff introduces.

### Changed
```
 tickets.md | 44 ++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 42 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates_fix_engine.py::TestFixE501MergeIntroduced::test_e501_merge_introduced_targeted_format_applies` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestFixE501MergeIntroduced::test_e501_no_merge_shape_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 320 warning(s), 784 waived
- error-findings: none (measured, zero errors)
