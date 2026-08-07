## Done report

Measured live via chunked `frob check --only gates-native --json` (2026-07-27,
natives rebuilt via `make core`). Baseline at pickup: ARCH101 2 live/0 waived,
ARCH102 23 live/0 waived, ARCH103 24 live/0 waived.

**ARCH101 (low-cohesion-class) -- 0 live, PROMOTED to error.** Both live
findings (`_Mutator`, `_PointCollector` in `src/frob/mutate/__init__.py`) were
false positives from a real bug in `frob.arch._python`'s field-access
extractor -- every `attribute` tree-sitter node was recorded as a
`self.<field>` read/write regardless of whether the object half was actually
`self` or whether the attribute was a method call's own callee
(`self._hit(...)` counted as a field access on a phantom field `_hit`).
Fixed via a new `_py_is_self_attribute` guard. Both findings drop to zero
without touching `mutate/__init__.py`. `[gates.severity] ARCH101 = "error"`
now set in `frob.toml`. Verified: `frob check --only gates-native` shows
`pass gate:ARCH 0 errors` post-flip.

Also found and fixed a second, independent bug while investigating:
ARCH101/ARCH103's `symref` was a bare qualname (e.g. `"BigService"`), but
`frob.gates._match_waiver`'s symbol-exact path requires the `path::qualname`
shape `frob.graph.dsl._enclosing_src` produces -- so no `frob:waive
ARCH101/ARCH103` could ever have matched anything before this fix. Fixed by
qualifying both with `f"{module.path}::{name}"` in `frob.arch._srp`.
Verified working: the 22 ARCH103 waivers added this ticket all register
(confirmed via `frob check --only gates-native --json` diff before/after).

**ARCH102 (god-module) -- 23 -> 11 live, heuristic fixed, STAYS ADVISORY.**
Audited the clustering heuristic for finding 4's named blind spot. Found it:
a module whose exports are predominantly zero-method data classes (pydantic
`BaseModel`/`dataclass`/`StrEnum`/`ErrorSet`) has no possible usage edge and a
naming signal that is just its own unique name, so a conventional
`_models.py` catalogue of N unrelated DTOs inevitably clustered into N
singleton groups pre-fix, regardless of real cohesion. Confirmed against
`cve/_models.py` (15 classes/0 methods), `dup/_models.py` (11/0),
`gates/_models.py` (14/0), `strata/_ast.py` (39 classes/1 method) -- all real
false positives. Fixed: `frob.arch._srp._is_data_only_class` excludes
zero-method classes from the export/cluster count entirely. Live findings
dropped 23 -> 11 (measured). New tests
`test_data_only_classes_are_excluded_from_god_module` /
`test_method_bearing_classes_still_count_toward_god_module` pin the fix.
Decision: ARCH102 STAYS ADVISORY (not promoted) -- the heuristic's most
severe unsoundness is fixed, but 11 real findings remain, each needing an
actual module split (or an honest per-file waiver); promoting now would red
`main`. Follow-up filed (draft id `T-0980`, renumbered at land).

**ARCH103 (mixed-concern-function) -- 24 -> 2 live, promotion BLOCKED on 2
sites.** Burned down 22 of 24 via a reasoned `frob:waive ARCH103` at each
site (`frob.app.*_runner.py` CLI entrypoints, `check/_ts.py`,
`fuzz/_signatures.py`, `gates/__init__.py`, `testing/_collect.py`,
`testing/_runners.py`, `tickets/_store.py`, `vet/_nvd.py`, `vet/_registry.py`
-- each carries its own real structural argument, not a blanket waiver). The
last 2 (`gates/_fmt_directives.py::format_paths`,
`natives/_build.py::build_natives`) are BOTH in `T-0976`'s concurrent
ARCH001 finding list for the same files/functions -- left untouched per this
ticket's coordination instruction (do not refactor, or by extension
permanently waive, functions a sibling ticket is actively deciding on for a
different rule). Decision: ARCH103 stays `"warning"` (2 live findings would
red `main`); follow-up filed (draft id `T-0979`, `blocked_by`
T-0976, renumbered at land).

Docs updated: `docs/audits/gates-quality.md` gained a full T-0977 section
(root-cause bugs, per-category decisions, evidence, filed children);
`docs/modules/arch.md`'s SRP/cohesion section updated per-category;
`docs/modules/app.md` notes `App.__call__`'s ARCH103 waiver (AFFECT001).

Test evidence: `pytest tests/unit/test_arch.py tests/unit/test_arch_srp.py
tests/test_gates.py tests/test_mutate.py` -> **766 passed** (measured, this
session). `frob check --only lint/static/gates-fast/gates-native/
gates-security --ticket T-0977` (chunked per docs/guides/agent-
playbook.md#3b) all pass 0 errors -- the two lint warnings that remain
(`_lock_ordering.py`, `test_arch.py` needing reformatting) are pre-existing
debt outside this ticket's diff (`git diff main -- <file>` confirms 0
changes to either file).

Deletion-filter check (`git diff main --diff-filter=D --stat`): empty, no
unintended deletions.

Filed: `T-0980` (ARCH102 burn-down + promotion, 11 findings),
`T-0979` (ARCH103 last 2 sites + promotion, `blocked_by` T-0976).
Both renumbered to real `T-####` ids at land time per this repo's normal
convention.

Gates: `frob check --only lint/static/gates-fast/gates-native/gates-security
--ticket T-0977` clean (0 errors each stage, chunked per playbook 3b) --
no waivers needed beyond the 22 `frob:waive ARCH103` sites (each carrying
its own `reason=`) documented above.
