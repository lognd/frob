## Done report

Rule id + home: **DOC003** (not DOC002 -- DOC002 was already taken by the
doc-anchor-resolution gate, T-0127, by the time this landed; charter
drift documented in docs/strata/threat.md's "the exhaustiveness proof is
computed" section). DOC003 lives inside `frob.gates.sys_gate`
(`src/frob/gates/__init__.py::_doc003`/`_doc003_one_marker`/
`_doc003_violation`/`_claims_markers`), opt-in on `design/` existing,
same posture as SYS001-004 -- not a standalone `docanchor`-family gate,
since it needs the loaded design model, not just doc-to-doc anchor
resolution. Registered in `_KNOWN_GATE_RULES` for WAIVE002.

Matrix format: `frob sys doc [path] [--view VIEW]` (default view
`owasp-top-10`) prints deterministic markdown: one `##` section per
`WeaknessEntry.family`, each a 6-column table (CWE, title, precondition,
mitigation, status, citation), plus an `## out-of-scope` section and a
`## catalog gaps (THREAT001)` section when non-empty. Status is one of
`PROVED (<rung>)`, `FAILING: <detail>`, `not applicable`, or `not
evaluated (no precondition detector yet, phase A)` for the `capability_
kind=None` catalog entries. Rendering (`render_audit_matrix`) and the
claims audit (`audit_claim`, returning `ClaimAuditResult`) both live in
the new `src/frob/strata/_sysdoc.py`, importing only `frob.strata.
_threat`'s public surface (`evaluate_threats`/`check_catalog_
completeness`/`check_discharge_completeness`/`CWE_CATALOG`/`VIEWS`/the
catalog pydantic models) -- no `_threat.py` catalog-internal function is
imported or touched, per the T-0116-concurrency scope note. `_may_kind`
is imported from `._effects` the same way `_threat.py` itself already
does (pre-existing precedent, not a new cross-module reach). `merge_
models` is public in `_sysdoc.py` (not the private, unrelated `_merge_
models` `frob.app.sys_runner` already has for `frob sys plan`) because
`frob.gates` cannot import `frob.app` (wrong direction) and needs the
same merge for DOC003.

`frob:claims <view>` is the new doc marker (`<!-- frob:claims <view>
-->`, HTML-comment style like `frob:describes`) -- no new `EdgeKind`/DSL
verb was added (`src/frob/graph/dsl.py` untouched): the gate scans the
same doclink `include`/`exclude`/`roots` doc set directly with its own
regex, matching `doclink_gate`/`docanchor_gate`'s existing local-regex
convention rather than routing through the general directive-DSL graph
edges. `docs/commands/sys.md` itself now carries a live `frob:claims
owasp-top-10` marker over `design/frob.strata` (T-0081 self-hosting) --
DOC003 verifies that exact claim on every `frob check` run.

Files changed: `src/frob/strata/_sysdoc.py` (new), `src/frob/strata/
__init__.py` (exports), `src/frob/gates/__init__.py` (`_CLAIMS_RE`,
`_claims_markers`, `_doc003_violation`, `_doc003_one_marker`, `_doc003`,
wired into `sys_gate`, `DOC003` added to `_KNOWN_GATE_RULES`),
`src/frob/app/sys_runner.py` (`_run_doc`, `run` dispatch), `src/frob/
__main__.py` (`frob sys doc` parser + `--view`), `src/frob/app/config.py`
(`sys_view` field), `docs/commands/sys.md` (usage + the claims-audit
section + the live claim marker), `docs/strata/threat.md` (charter-drift
note, three DOC002->DOC003 corrections, phase-F SHIPPED note),
`tests/unit/strata/test_sysdoc.py` (new, 12 cases), `tests/system/
test_cli_sys_doc.py` (new, 3 CLI cases), `tests/test_gates.py`
(`TestSysGate`, 4 new DOC003 cases), `tickets.md` (this ticket's scope
widened to match the actual dispatch prompt -- the stored `scope` field
predated `src/frob/app/**`/`src/frob/gates/**`/`__main__.py`/`docs/**`
being named; `frob ticket sweep T-0085` re-run after widening).

Exact numbers: 19 new test cases total (12 unit in `test_sysdoc.py`, 3
system/CLI in `test_cli_sys_doc.py`, 4 gate cases in `TestSysGate`), all
19 bound as ticket evidence (`frob ticket evidence T-0085 ...`, all
resolvable). Full suite: `uv run pytest -q` -> all green (same pre-
existing 2 `PytestCollectionWarning`s, unrelated). `uv run frob check
--ticket T-0085` -> `0 errors` (`WARN`, 277 pre-existing warnings,
matching the whole-repo `frob check .` baseline). Matrix golden/
determinism: `TestRenderAuditMatrix.test_deterministic_rendering` proves
two renders of the same model produce byte-identical output.

Filed: **T-0137** -- out-of-scope discovery, `src/frob/testing/_select.py`
territory: `frob test --base main`'s pytest invocation mixes touched
non-test symbol node ids (e.g. `src/frob/strata/_sysdoc.py::merge_
models`) into the same `pytest` argv as real test files; under
pytest-xdist this collects 0 items and exits 5 for the WHOLE run, even
though the real tests pass cleanly in isolation. Reproduced independent
of this ticket's code (any touched public symbol triggers it), so not
fixed here -- `frob test --base main` currently reports a false `[FAIL]`
for this reason; `uv run pytest -q <real test files>` and `frob check
--ticket T-0085` are the two verifications actually run and both are
clean, per the numbers above.

Gates: `frob check --ticket T-0085` clean (0 errors). No waivers added
by this ticket.

## Round 2 (reviewer REJECT: CRITICAL, fence/inline-code-unaware extraction)

Reviewer reproduced: `_claims_markers`/`_CLAIMS_RE` matched a `frob:claims`
marker written to DOCUMENT the directive inside a ```-fenced example (the
natural way to show the directive in prose), registering it as a live
claim -- undermining the claims-honesty contract DOC003 exists to
enforce.

Fixed in `src/frob/gates/__init__.py::_claims_markers`: a simple
line-by-line fence-state toggle (`_FENCE_RE`, matches a line starting
with three-or-more `` ` `` or `~`, ignoring leading whitespace) skips
every line while inside a fenced block, opening OR closing on either
fence character; inline single-backtick code spans on a still-scanned
line are blanked out first (`_strip_inline_code_spans` /
`_INLINE_CODE_SPAN_RE`, paired `` `...` ``, column-preserving) before the
`_CLAIMS_RE` search, so a marker quoted in prose backticks is also never
extracted. Both rules and the CommonMark rationale (inline spans never
cross a line boundary, so an unpaired backtick cannot corrupt fence
state) are documented directly in `_claims_markers`'s docstring.

Regression tests added to `tests/test_gates.py::TestSysGate` (calling
`gates_mod._claims_markers` directly, same private-helper-import
convention `test_default_design_dir_mirror_stays_in_sync` already uses):
`test_doc003_marker_in_fenced_block_ignored` (a marker inside a fenced
block extracts nothing), `test_doc003_marker_in_inline_code_ignored` (a
marker inside inline backticks extracts nothing),
`test_doc003_real_marker_with_fenced_example_extracts_once` (a page with
BOTH a real top-level marker AND a fenced example of the same marker
extracts exactly the real one, at its correct line). All three added to
this ticket's evidence (22 ids total now, all resolvable via `frob
ticket evidence T-0085`).

Re-verified: the 3 new tests + the 4 original DOC003 tests + the full
`tests/unit/strata/test_sysdoc.py`/`tests/system/test_cli_sys_doc.py`
suites all green; `uv run pytest -q` full suite green (same 2
pre-existing `PytestCollectionWarning`s, unrelated); `ruff check` /
`ruff format --check` / `ty check` clean on every touched file; `frob
sys doc . --view owasp-top-10` run twice produces byte-identical output
(determinism intact -- unaffected by this change, since fence/inline
handling only narrows extraction, never touches rendering); `uv run frob
check --ticket T-0085` -> `0 errors` after `frob ticket sweep T-0085`
(re-run since the round-2 edits post-dated the round-1 sweep).
