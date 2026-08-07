## Done report

## Done report

Changed:
- docs/modules/gates.md (added a note under `GateConfig`'s description, next to its `gates` subset field, stating the drift gate (DRIFT001/DRIFT002) always evaluates regardless of `gates`/`--only` narrowing, T-0265, with the exact rationale from `_build_jobs`'s own comment: cost-free since `st.snapshot`/`st.lock` are already unconditionally loaded before selection is applied)

This is a docs-only ticket with no pytest surface of its own. Per the agent playbook (section 5), evidence is the existing CLI-dispatch integration test:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches

Measured: `uv run pytest tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches -n0 -v -p no:cacheprovider` -- "1 passed".

Gates: `FROB_AGENT=1 FROB_WORKTREE=<worktree> uv run frob check --ticket T-0683 --only <stage>` clean (exit 0) for lint and static. `gates-fast` shows 11 COV002 errors, all on `src/frob/gates/__init__.py` symbols this SAME worktree changed for the two prior tickets in this dispatch (T-0730, T-0783) -- expected, not caused by T-0683: with T-0683 (docs-only, scope `docs/modules/gates.md` only) as the active ticket, those symbols no longer have an active-ticket scope match (they had one when T-0730/T-0783 were themselves active), and since T-0730 and T-0783 BOTH declare `src/frob/gates/**`/`tests/test_gates.py` in scope with equal specificity, `_scope_covers` treats that as an ambiguous multi-ticket match requiring an explicit `frob:ticket` edge per symbol -- exactly the same COV002 shape already fixed for the NEW symbols added in those two tickets' own Done reports. These findings will clear naturally once T-0730/T-0783 land to `main`. The rest of `gates-fast`'s findings (COV007, TICK, WAIVE004, etc.) are pre-existing unrelated repo debt, none touching `docs/modules/gates.md`.

Evidence: tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches, bound with --accepts 0.

Filed: none.

Scope: `git diff main --diff-filter=D --stat` is empty.

### Changed
```
 docs/design/registry/check-coverage.yaml |   6 +-
 docs/modules/gates.md                    |  51 ++++-
 src/frob/gates/__init__.py               | 250 ++++++++++++++++++----
 src/frob/gates/_pii_structural.py        | 201 +++++++++++++++---
 tests/test_gates.py                      | 350 ++++++++++++++++++++++++++++++-
 tickets.md                               | 262 ++++++++++++++++++++++-
 6 files changed, 1031 insertions(+), 89 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
