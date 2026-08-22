## Done report

Three over-attributions in `_BUILTIN_RAISERS`, all fixed by a syntactic
test rather than type inference -- which was the explicit bar set for
this work: a fix that only recognised the env-var idiom the survey
happened to surface would rot the moment someone wrote the same mistake
differently.

WHAT THE SURVEY ACTUALLY SHOWED. All 26 EXHAUST002 findings naming
`TypeError` were reachable to an `int()`/`float()` call -- 26 of 26, no
residue -- but they were NOT one idiom. The argument shapes were
`int(entry.name)` over `/proc`, `int(match.group(1))` after a `\d+`
match, `int(fields[19])` and `int(line.split()[1])` over parsed text,
`float(path.read_text().split()[0])`, and only three instances of the
env-var read. Pattern-matching any of those shapes would have been the
rot the brief warned about. What they share is not a shape, it is an
OWNER: every way `int()` can raise `TypeError` is a static type error.

POSITIVE CONTROL, because "the type checker covers it" is a claim about
another tool and had to be measured rather than assumed. A probe with
three functions -- `int(raw)` with `raw: str | None` None-guarded,
the same unguarded, and `int({"a": 1})` -- run through `ty`:
  - unguarded `int(str | None)`  -> error[invalid-argument-type]
  - `int(dict)`                  -> error[invalid-argument-type]
  - guarded `int(str)`           -> silent, correctly
Dropping the same probe into `src/frob/` and reading `frob check --only
ty --json` confirms both are severity=error, exit=1, inside the gate
run. So `ty` discriminates precisely the case this resolver structurally
cannot (it has no None-narrowing), and the residual risk moves to a
STRICTER gate rather than going unowned. That asymmetry is the whole
argument for the change; without it this would be a soundness loss.

`getattr(o, name, default)` and `next(it, default)` needed no such
argument -- the default argument IS the failure result, so the raise is
impossible by the documented overload. `_DEFAULT_ARG_DISCHARGES` maps
the bare callee name to the positional arity at which the default is
present; `NormalizedCall.args` already carried arity from T-0632, so no
model change was needed. All 4 affected sites in this repo pass a
literal default. The narrow forms still contribute their raise, asserted
in the same test (`test_getattr_with_default_raises_nothing` checks the
2-arg form STILL leaks `AttributeError`) so a future over-broad
narrowing fails loudly instead of silently.

MEASURED, unbudgeted, `FROB_NO_GATE_CACHE=1`, `frob check --only
exhaustive_handling`:
  EXHAUST002  56 -> 47
  EXHAUST003 141 -> 141 (untouched by design)
The count moves by 9 but the corpus changes more than that: every
`TypeError`, `AttributeError` and `StopIteration` mention is gone from
the family, and the 18 findings that survive do so only because they
ALSO name `KeyError` from the subscript rule (T-2543's Class A). What
remains is 40 `KeyError` and 7 `ValueError`.

Tests: 304 collected / 0 failed in tests/unit/test_arch.py. The three
new tests were committed at cfb0ddc03 AHEAD of the fix and observed
failing there (`frozenset({'TypeError','ValueError'}) == frozenset(
{'ValueError'})`, `frozenset({'AttributeError'}) == frozenset()`,
`frozenset({'StopIteration'}) == frozenset()`); designated repro
re-verified FAILED_AT_PARENT against that commit.

CUT DISCLOSED: does not reach zero and does not promote either code.
T-2543 keeps the Class A decision; T-2377 keeps the promotion.

### Changed
```
 docs/modules/arch.md               |  23 ++++++++
 src/frob/arch/_mayraise.py         |  50 ++++++++++++++++-
 tests/unit/test_arch.py            | 111 +++++++++++++++++++++++++++++++++++++
 tickets/T-2543/ticket.md           |  31 ++++++++++-
 tickets/T-2552/ticket.md           | 105 +++++++++++++++++++++++++++++++++++
 tickets/T-draft-7fa19c2a/ticket.md |  78 ++++++++++++++++++++++++++
 6 files changed, 392 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestBuiltinRaiserPrecision::test_int_does_not_contribute_type_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestBuiltinRaiserPrecision::test_getattr_with_default_raises_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestBuiltinRaiserPrecision::test_next_with_default_raises_no_stop_iteration` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2377/src/frob/app/ticket_runner/_verify.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
