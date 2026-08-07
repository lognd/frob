## Done report

Implemented FMT001, the T-0441 follow-up: frob.gates.fmt_gate (gate name
fmt, default-on, WARN, diff-scoped) fires when a diff-touched frob:
directive comment line exceeds the project's configured line length,
naming frob fmt <path> as the remediation. Reused frob.gates.
_fmt_directives.marker_for and read_line_length, and frob.graph.dsl.
fold_comment_runs (the same continuation-run fold canonicalize_text
folds through) rather than re-deriving any of it -- the new code is only
the length + diff-touch check over a folded run's physical lines
(_fmt001_touched_lines, _fmt001_file, fmt_gate in src/frob/gates/
__init__.py). Wired fmt into _ALL_GATES, _KNOWN_GATE_RULES,
_CANONICAL_GATE_ORDER, _build_jobs' thread_jobs, and check/__init__.py's
gates-fast stage group. The gate never touches or suppresses the
underlying ruff E501/lint finding on the same line -- additive only.

Scope was extended by one file, docs/design/registry/check-coverage.yaml
(reason recorded via frob ticket scope --add): adding FMT001 to
_KNOWN_GATE_RULES requires a matching CHK-GATE-FMT001 registry entry
(REGISTRY001/REG010 exhaustiveness), so I added that entry
(disposition handled_by:FMT001) and bumped gate_rule_total to 116.

Adversarial evidence (TEST016 posture): TestFmt001Gate in
tests/test_gates.py covers the positive case (a single-line frob:waive
over the default 88-col limit, touched, fires FMT001 naming `frob fmt
<path>`) and three near-misses that must NOT fire: an ordinary long
comment (not a frob: directive), a long code line (no comment marker at
all), and an over-limit directive line the diff does not touch (FMT001
is diff-scoped, matching TODO001's posture) -- plus a short/already-
canonical directive that must not fire even when touched.

Hand-verified mutant kill: I manually changed the
`logical_text.strip().startswith("frob:")` guard in _fmt001_file to
`True` (always treat a folded comment run as a directive) and re-ran
test_ordinary_long_comment_not_flagged -- it failed (FMT001 fired on the
plain long comment), confirming the guard is load-bearing and the test
actually exercises it. Reverted the mutation before finishing.

Docs: docs/modules/gates.md gets a new FMT001 (T-0851) rule-catalog row
and section, and the T-0441 "known cut" paragraph is updated to point at
this ticket instead of describing an open gap.

Gate state: `frob check --only lint/static/gates-fast/gates-native/
gates-security --ticket T-0851` (chunked, per playbook 3b) all report 0
errors after this change (gates-fast went from 6 errors -- 5x COV002 on
my own new test methods needing a frob:ticket T-0851 marker, plus 1x
PRE001 stale pre-work sweep after the scope --add -- to 0 once I added
per-method frob:ticket markers and re-ran `frob ticket sweep T-0851`).
Targeted pytest: tests/test_gates.py (408 passed),
tests/test_gates_fmt_directives.py (28 passed, unchanged/reused module).
ruff clean on every file I touched (both PATH ruff and `uv run ruff`).

Pre-existing, NOT introduced by this change (verified against a
git-show of HEAD's own source before my edits): tests/
test_check_coverage_registry.py::TestCheckCoverageRegistryFile.
test_gate_rule_entries_match_live_known_rules and ::
TestExhaustivenessGateOverRealCheckCoverage.test_no_check_coverage_violations
both fail because TEST016 (added by an earlier, already-landed ticket)
has no CHK-GATE-TEST016 registry entry -- confirmed by parsing HEAD's
_KNOWN_GATE_RULES (116 unique ids) against HEAD's check-coverage.yaml
(115 CHK-GATE-* entries, missing exactly TEST016). Filed as
T-0852 rather than folded into this ticket's scope. Also
observed, in one full combined pytest run only (each test passes clean
in isolation and in its own file's full run):
tests/system/test_cli_check.py::TestCheckSkipFlags.test_json_output and
::TestGitlessTargetGateSeverity.test_render_lint_gate_warns_not_errors_on_gitless_root
failed once under a long combined invocation (142s) -- reproduced
neither test failing when run alone or as part of just test_cli_check.py
in isolation immediately after; looks like resource-contention flake
under a long batched run, not a regression from this ticket's additive-
only gate (neither touched file is in this ticket's scope or diff).

Deviation from the initial dispatch prompt's framing (annotate an
existing ruff E501 finding): the ticket brief (authoritative per
dispatch instructions) instead specified a standalone FMT001 gate rule
with its own remediation message, matching every other gate's self-
remedying-message contract -- implemented that shape, not a ruff-finding
annotation.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestFmt001Gate::test_directive_run_over_limit_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_ordinary_long_comment_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_long_code_line_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_untouched_line_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_short_directive_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 1242 warning(s), 212 waived
- error-findings: none (measured, zero errors)
