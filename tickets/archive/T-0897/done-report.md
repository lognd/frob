## Done report

Changed:
- `src/frob/gates/_render_lint.py::_parse001_violation` (new, private)
- `src/frob/gates/_render_lint.py::render_lint_gate` (except-skip now
  appends a PARSE001 `Violation` instead of a DEBUG-only log line)
- `src/frob/gates/_pii_structural.py::_parse001_violation` (new, private)
- `src/frob/gates/_pii_structural.py::pii_structural_gate` (same
  except-skip -> PARSE001 change for the Python-`ast.parse` branch;
  consults `frob.excludes.is_excluded`/`load_exclude_globs` so a
  `[graph].exclude`-matched path stays silent, matching the central
  parse-failure mechanism's own posture for those paths)
- `src/frob/gates/_cve_fingerprint_scan.py::_parse001_violation` (new,
  private)
- `src/frob/gates/_cve_fingerprint_scan.py::cve_fingerprint_scan_gate`
  (same except-skip -> PARSE001 change for its plain-text read; same
  `frob.excludes` consult)

Rather than replatforming these three gates onto `frob.lang.parse_file`
(infeasible without rewriting each gate's own AST/text scan logic --
`frob.lang.parse_file` returns a `ParsedFile` of extracted symbols/
comments, not a raw Python `ast` tree these gates' own scan functions
walk), each gate now emits a `PARSE001` `Violation` matching
`frob.gates._parse_failures.parse_failure_gate`'s rule id, severity
(ERROR), and message shape on its own read/parse failure -- "a single
PARSE001-shaped signal" per the ticket's fix direction, achieved via rule
consistency rather than a shared code path (the three private read
mechanisms genuinely differ: AST parse, AST parse, plain-text read).

Discovered mid-fix: making PII010/SEC110 loud on this repo's own
`tests/fixtures/lang/broken.py` (a deliberately syntax-broken fixture,
git-tracked, scanned by `pii_structural_gate`'s raw `git ls-files`
listing) turned a permanently-broken, intentionally-unparseable fixture
into an unwaivable ERROR -- `tests/fixtures/**` is excluded from
`frob.graph`'s own ingestion (`frob.toml`'s `[graph].exclude`), so no
`frob:waive` directive placed anywhere can ever bind to it (waivers only
match through graph-ingested `Edge`s). Fixed by having the two
all-tracked-file gates (`pii_structural_gate`, `cve_fingerprint_scan_gate`)
consult `frob.excludes.is_excluded`/`load_exclude_globs` directly and stay
silent for an excluded, unparseable/unreadable path -- consistent with
`[graph].exclude`'s own documented intent ("kept out of the... obligation
surface COV001/TEST001 run over"), extended here to PARSE001.
`render_lint_gate` needed no such guard: it only scans `src/frob/**`
(`_tracked_python_files`'s own `git ls-files -- src/frob` restriction),
which never overlaps `tests/fixtures/**`.

Evidence (collected via `pytest --collect-only -q -o addopts=""`, all
observed passing):
- `tests/test_gates.py::TestRenderLintGate::test_unparseable_file_fires_parse001`
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_unparseable_python_file_fires_parse001`
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_unparseable_file_under_graph_exclude_is_silent`
- `tests/unit/strata/test_cve_fingerprint_scan.py::TestGate::test_undecodable_file_fires_parse001`
- `tests/unit/strata/test_cve_fingerprint_scan.py::TestGate::test_undecodable_file_under_graph_exclude_is_silent`

`uv run pytest tests/test_gates.py tests/unit/strata/test_cve_fingerprint_scan.py tests/test_pii_structural_gate.py tests/test_lang.py -q`
(FROB_WORKTREE/FROB_AGENT unset, per docs/guides/agent-playbook.md#5b) --
all passed, 0 failures.

Filed: T-0911 (SELFAUDIT001: `src/frob/arch/_logging_checks.py`
capabilities undeclared on `graphlang` node) -- an unrelated, pre-existing
gate failure surfaced by `frob check --only gates-security` against a
file this ticket never touches (landed via a concurrent main merge mid-
ticket), not caused by this fix.

Gates: `frob check --ticket T-0897 --only prework/gates-fast/gates-
security/gates-native/lint/static` all clean (0 errors) after re-sweeping
(`frob ticket sweep T-0897`) post-merge; `gates-security`'s
`gate:SELFAUDIT` 5-error failure is the unrelated T-0911 finding
above, not a violation this ticket's own touched files produce.
