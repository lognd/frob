# Gate rule families

<!-- frob:describes src/frob/gates/_models.py::GateConfig doc -->

## What it is and where it lives

`frob check` runs a fixed set of rule *families* -- `_KNOWN_GATE_RULES`
(`src/frob/gates/_waive.py`) spans roughly 50 prefixes today (COV, TEST,
DRIFT, SCOPE, PRE, DOC, PERF, SYS, THREAT, COMPLIANCE, WAIVE, INV, TODO,
DEC, DUP, FUZZ, REL, SEC, VET, LINT, ARCH, AFFECT, CPPTHROW, DEAD, DEBT,
DEPR, DSL, EXCL, EXHAUST, FFI, FMT, HOST, KRB, LANG, LARGE, NATIVE, OPAQUE,
PARSE, PII, PLACE, PROTO, REF, REG, RELWAIVE, RENDER, SELFAUDIT, SYSWAIVE,
TICK, VALGRIND, WALK, and more) -- see the full catalog table in
`docs/modules/gates.md#rule-catalog`. Each family is one gate function
living in `src/frob/gates/` (or, for strata-native families like THREAT,
COMPLIANCE, LINT, CVEFP, in `src/frob/strata/`), returning a
`tuple[Violation, ...]` (or the family's own `*Violation` model). The
per-rule severity default lives in `GateConfig` (`src/frob/gates/_models.py`)
and is overridable per-repo via `[gates.severity]` in `frob.toml`.

## Add-an-entry recipe (new rule id in an existing family)

1. Pick the next free number in the family (e.g. `TEST009` if `TEST008` is
   the current max -- check `docs/modules/gates.md#rule-catalog`, the
   authoritative table).
2. Add the check function (or extend the family's existing collector) in
   the family's module, returning a `Violation`/`*Violation` with
   `rule="TESTnnn"`.
3. Wire it into the family's top-level entrypoint (e.g. `run_gates` in
   `src/frob/gates/__init__.py` for the core families, or the strata
   report builder for THREAT/COMPLIANCE/LINT/CVEFP).
4. Add the row to `docs/modules/gates.md#rule-catalog`.
5. Add a unit test asserting the violation fires (and one asserting it does
   NOT fire on the clean case -- deny-by-default families need both).

## Drift-locks that fire

- **DOC001/DOC002** -- if you reference the new rule id in a doc without a
  resolvable `frob:doc`/`frob:describes` anchor, or add a new `docs/**/*.md`
  file without linking it from a root, the doclink gate fails.
- **COV001** -- a new public check function with no `frob:doc` edge.
- **TEST001** -- a new public check function with no `frob:tests` edge.
- **WAIVE002** -- if you `frob:waive` the new rule id somewhere before it
  can actually fire on that line (typo'd rule id, or waiving a rule that
  structurally cannot match there), the waiver itself is a violation.

## Worked example

Adding `TEST008` (empty coverage-to-path join, "0 classes joined"):
`src/frob/gates/_coverage.py::_parse_classes` returns the raw join score;
the check lives in the coverage family's entrypoint, which raises
`TEST008` when `classes and known_paths` but zero results were joined
(see the `_score_root` / "0/%d class(es) joined" log line in
`_coverage.py`). The row landed in `docs/modules/gates.md#rule-catalog`
in the same change.

## Common mistakes

- Adding a rule id to a doc table without a working check function --
  `docs/modules/gates.md` must describe reality, not aspiration.
- Forgetting the "does NOT fire on the clean case" test: several gates here
  are deny-by-default (THREAT002, COMPLIANCE, LINT), so a check that only
  ever fires is as broken as one that never fires.
- Bumping severity to `error` in `[gates.severity]` for a brand-new rule
  before any real repo has been swept once -- this repo's own gates started
  every new rule at `warn` for one release cycle (see `docs/modules/gates.md`
  "Severity" section) specifically to avoid a false-positive storm on day one.
