## Done report

T-0330's SOLID catalog's OCP slice, built on T-0609's normalized-model
groundwork: `type-dispatch smell` and `non-exhaustive enum match`
(ARCH1xx family), both python-only for now via the existing tree-sitter
walks (matching the sibling ARCH1xx tickets' scope).

REUSE (the ticket's explicit mandate): `type-dispatch-smell` does not
re-implement isinstance-chain detection. T-0332's pattern recommender
already walks this exact shape as the `type-switch` hallmark
(`frob.arch._patterns._check_type_switch`); T-0617 factored the shared
walk out into a module-level generator, `iter_type_switch_chains`, and
both `_check_type_switch` (recommendation) and the new
`_check_type_dispatch_smell` (OCP smell, `frob.arch._ocp`) call it --
one detector, two outputs, non-behavior-changing to the existing
pattern-recommendation output (verified: `test_isinstance_chain_
recommends_strategy` and the rest of `TestPatternRecommender` in
test_arch.py stayed green unchanged).

`non-exhaustive-enum-match` is a new detector (no existing signal to
reuse): finds a `match`/`case` over a variable statically tied to a
locally-defined Enum-family class with no wildcard/capture default arm
that omits >=1 member. Fails toward silence per the ticket's precision
mandate: skips whenever the enum class isn't defined in the same file,
any case pattern isn't a bare `EnumClass.MEMBER` value pattern (or a
`|`-union of same) naming that exact class, or the case patterns
disagree on which class they qualify.

Both categories are new `ArchCategory` literals (`type-dispatch-smell`,
`non-exhaustive-enum-match`), advisory (`severity="warning"`) on the
existing unwaivable channel, each with `symref`/`metric` populated so a
future ARCH1xx gate (the `ARCH001` pattern) can bind a `frob:waive`
without re-instrumenting these checks -- no gate itself is wired in this
ticket (matching sibling T-0616's identical scope: `_solid.py`/
`_models.py`/docs/tests only, no `frob.gates` touch).

Coordination: tests live in a new `tests/unit/test_arch_ocp.py` (not
`test_arch.py`, per dispatch instructions for concurrent T-0615/T-0616);
new module `src/frob/arch/_ocp.py`; `_patterns.py` touched only to
extract the shared generator (scope-added with reason, see scope_changes
audit trail) -- `test_arch.py` itself was NOT edited and stays green
unchanged.

REL001: two rounds of version bump were needed -- 0.89.0 -> 0.90.0 for
this ticket's own new public API, then (after merging main, which
carried T-0616's SRP/cohesion ARCH1xx family landing concurrently)
0.90.0 -> 0.91.0 for the combined public-API delta once both were
present. `frob release stamp` + `uv lock` re-run after each bump.

Measured: `uv run pytest tests/unit/test_arch_ocp.py tests/unit/test_arch.py
-p no:cacheprovider -q` -- 117 passed (10 new + 107 existing, unchanged).
`uv run frob check --ticket T-0617` -- exit 0, all gates pass (COV/PRE/
REL/SCOPE/DOC errors seen mid-implementation were all fixed: COV001/
COV002 via frob:doc/frob:ticket directives, SCOPE001 via a scope-add for
src/frob/arch/__init__.py, PRE001 via `frob ticket sweep`, REL001 via
the version bumps above). `git diff main --diff-filter=D --stat` is
empty (deletion-filter land check, run after the T-0616 merge).

### Changed
```
 .frob-release.json          |  22 ++-
 CHANGELOG.md                |   4 +
 docs/modules/arch.md        |  38 ++++++
 pyproject.toml              |   2 +-
 src/frob/arch/__init__.py   |  24 +++-
 src/frob/arch/_models.py    |   8 ++
 src/frob/arch/_ocp.py       | 323 ++++++++++++++++++++++++++++++++++++++++++++
 src/frob/arch/_patterns.py  |  31 ++++-
 tests/unit/test_arch_ocp.py | 239 ++++++++++++++++++++++++++++++++
 uv.lock                     |   2 +-
 10 files changed, 678 insertions(+), 15 deletions(-)
```

### Evidence
(no evidence recorded)
