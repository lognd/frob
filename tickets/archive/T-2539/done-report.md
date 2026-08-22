## Done report

Two independent false-positive classes in the may-raise resolver's input
model, both found while triaging T-2377's EXHAUST002 corpus site by site.
Both pushed toward the exact change this repo's doctrine forbids: the
cheapest way to silence either is a blanket `except Exception:`.

1. Multi-type except clause. `_py_except_exception_type`'s own docstring
   admitted it: `except (A, B):` resolved to the tuple's FIRST member.
   `NormalizedCatch` holds one `exception_type`, so every consumer asking
   "does this function catch T?" answered NO for every member after the
   first. `except (OSError, ValueError):` read as catching `OSError`
   alone, leaking `ValueError` and (via `_EXCEPTION_PARENT`)
   `JSONDecodeError`. Fixed by adding `NormalizedCatch.exception_types`
   (the full member tuple; `exception_type` stays the representative
   first member so the rust/typescript/kotlin adapters, single-type by
   grammar, need no change) plus `caught_type_names` as the single
   accessor both consumers -- `_mayraise.compute_may_raise`'s catch
   subtraction and `_exhaustive_handling._has_catch_all` -- now read it
   through.

2. Slice subscript. Every `subscript` node was recorded as a
   `NormalizedSubscript` and each one contributed the curated dict-index
   `KeyError` default. A slice (`lines[start + 1 :]`) clamps
   out-of-range bounds on every builtin sequence; it cannot raise
   `KeyError` or `IndexError` at all. Fixed by
   `NormalizedSubscript.is_slice` (set when every `subscript`-field child
   is a `slice` node -- a mixed `a[1:2, 3]` stays conservative) and by
   `_resolve_call_contributions` contributing `KeyError` only when the
   function has at least one non-slice subscript.

MEASURED, unbudgeted, `FROB_NO_GATE_CACHE=1`, `frob check --only
exhaustive_handling --json` on this repo's own source:

  EXHAUST002  74 -> 69 (fix 1) -> 56 (fix 2)
  EXHAUST003 141 -> 141 -> 141  (unchanged, as expected: EXHAUST003 is
             the unresolved-callee `Unknown` signal, which neither fix
             touches)

18 of 74 EXHAUST002 findings, 24 pct of the corpus, were the gate being
wrong about the site rather than the site being wrong.

Tests: 301 collected / 0 failed in tests/unit/test_arch.py; 7 collected /
0 failed for `pytest tests/test_gates.py -k "exhaust or mayraise"`.
Designated repro verified FAILED_AT_PARENT against 783e09cc3 (the
test-only commit deliberately committed ahead of the fix so a genuine
test-without-fix ref exists).

CUT DISCLOSED: this ticket fixes the resolver, it does NOT burn the
family to zero and does NOT promote either code to ERROR -- that stays
T-2377's own two-part closure, with 197 findings still standing.

### Changed
```
 docs/modules/arch.md                   |  24 ++++-
 src/frob/arch/_mayraise.py             |  17 +++-
 src/frob/arch/_normalized.py           |  46 +++++++++-
 src/frob/arch/_python.py               |  48 +++++++---
 src/frob/gates/_exhaustive_handling.py |  11 ++-
 tests/unit/test_arch.py                | 160 +++++++++++++++++++++++++++++++--
 tickets/T-2377/ticket.md               |  43 +++++++--
 tickets/T-2539/ticket.md               | 115 ++++++++++++++++++++++++
 8 files changed, 433 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestCaughtTypeNames::test_tuple_clause_reports_every_member` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestCaughtTypeNames::test_python_adapter_records_every_tuple_member` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestCaughtTypeNames::test_tuple_except_discharges_every_member` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSliceSubscriptRaisesNothing::test_python_adapter_marks_slice_subscripts` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSliceSubscriptRaisesNothing::test_slice_only_function_leaks_no_key_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2377/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2377/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2377/src/frob/graph/summary.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2377/src/frob/testing/_collect_kotlin.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2377/tests/unit/test_ticket_runner_repro_merge_base.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2539, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
