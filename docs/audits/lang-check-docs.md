# Audit: lang / check / doc-machinery / CLI orchestration

Status: 2026-07-27

North-star tested: "if `frob check` passes, the code is actually good AND the docs actually match."
Verdict up front: **FALSE in several structural ways.** The doc/coverage/drift guarantee is
Python-only, the strongest doc gate (COV001) is a non-blocking WARN, a parse/IO failure erases a
file's obligations silently, and DRIFT is one-directional (code->doc only). Details below.

---

## (A) What is implemented and how

### Parsing (`src/frob/lang/**`)
- `_EXTENSION_TABLE` maps `.py/.ts/.tsx/.rs/.c/.h/.cpp/.hpp/.cc/.hh/.cxx` to tree-sitter grammars;
  `.strata` routes to strata-core (`_walk_strata`). `parse_file` -> `ParsedFile` (symbols, comments,
  content_hash). Escape hatches: `raw_tree`, `symbol_tree`, `extract_imports`, `iter_identifiers`.
- Parse-failure detection (`_parse`, lang/__init__.py:179): `unusable = root_node is None or
  (root_node.has_error and root_node.child_count == 0)`. Everything else is treated as a good tree
  (tree-sitter error-recovery is intentionally tolerated).
- Digests (`graph/digest.py`): three SHA256 digests per **source symbol** -- `sig`, `body`, `doc`
  (over the code symbol's own docstring text). No digest is ever taken over a doc-page's content.

### Per-language runner dispatch (`src/frob/check/**`, `app/check_runner.py`)
- `_detected_types` enumerates ALL present language sentinels (Cargo.toml/CMakeLists.txt/pyproject|setup/
  package.json); `_run_all_detected` runs each and merges results. `check_type` pin runs one and adds
  `SKIPPED:` note lines (exit 0) per excluded language.
- Python pipeline (`run_check`): ruff, ty, cycle, dup, arch, bind, exports, **gates** (this is the only
  pipeline that runs `_run_gates`). C++/Rust/TS pipelines run only their native toolchains
  (cmake/clang, cargo, tsc/eslint/prettier/vitest) -- **no gates stage**.
- Missing-tool doctrine (T-0142): a missing binary returns `tool_unavailable_result` (exit 1, error
  severity) -> loud FAIL, not a silent skip. Verified for tsc/eslint/prettier/vitest (via `_run_npx`
  None->`_missing_tool_result`), cmake/clang-tidy/clang-format/ctest, cargo/cargo-fmt/cargo-test.
- `_report_check_result` exits 1 iff `total_errors > 0`. Warnings/notes never fail the run.

### Doc machinery (gates)
- COV001 (`_cov001`): public symbol with no *resolving* `frob:doc` edge -> **WARN**. Correctly ignores
  broken edges (T-0233 `_resolved_documented_srcs`) and generated/test files.
- DOC001 (`doclink_gate`): orphan doc file (nothing links to it) -> ERROR.
- DOC002 (`docanchor_gate`): `frob:doc <file>#<slug>` whose file/anchor doesn't resolve -> ERROR.
  Resolution = heading-slug or `<a id>` exists; content under the anchor is never inspected.
- DOC003 (`_doc003`): `frob:claims <view>` marker whose strata view isn't PROVED -> ERROR (strata-specific).
- DRIFT001 (`_drift001`+`graph/lock.py`): an acked (ref, facet) whose **source-symbol digest** moved ->
  ERROR "run frob ack". DRIFT002: dangling edge endpoint -> ERROR.
- Malformed-directive surfacing is per-flavor: WAIVE001 (frob:waive missing reason), TEST010 (bad
  frob:tests kind). There is **no** malformed-`frob:doc` gate.

---

## (B) FALSE-NEGATIVE / EVASION findings (priority)

### TOP-5 (ranked)

**1. [HIGH] Doc/coverage/drift gates run ONLY in the Python pipeline; a non-Python repo passes with
zero doc enforcement.**
`run_check_cpp/run_check_rust/run_check_ts` (check/__init__.py:424-550) never call `_run_gates`;
`_run_gates` is appended only in `_python_tasks` (check/__init__.py:260). So for a pure Rust / C++ /
TypeScript repo, `frob check` runs only the native toolchain -- COV001/DOC001/DOC002/DOC003/DRIFT001/
DRIFT002/INV/DEC/TODO001 never execute. The module docstrings and DSL advertise polyglot doc-binding
("bind frob:doc/frob:tests ... like any other grammar's", lang/__init__.py:76-78), and the graph
parses all languages, but the enforcement layer is Python-gated. North-star is simply not delivered
off Python. Repro: a repo with only `package.json`; add a public exported symbol and a lying/broken
`frob:doc` -> `frob check` green. Fix: run the gates stage in every pipeline (build the graph once,
run `run_gates` regardless of detected language), or at minimum emit a loud "gates NOT run for
<lang>" stage line so the gap is visible.

**2. [HIGH] A parse failure / IO failure silently erases a file's entire obligation set.**
`_parse_source_file_fresh` (graph/__init__.py:196-207): on `parse_file` Err (ParseFailed,
UnsupportedLanguage, IoFailed, NativeParserUnavailable) it logs a warning and returns
`True, (), (), ()` -- the file is recorded as successfully processed with zero symbols and zero
edges. Consequence: every public symbol, every `frob:doc`/`frob:invariant`/`frob:describes`/
`frob:tests` edge in that file vanishes from the snapshot, so COV001/exports/DRIFT/INV all pass
vacuously for it. Repro: a `.strata` file in a native-less install (NativeParserUnavailable, debug-
level only -- see memory "worktree natives artifact") drops ALL strata design symbols and their
frob:invariant/frob:doc edges -> gates green while the design graph is invisible. Also triggerable by
any file tree-sitter can't parse at all. Nothing in the check output signals "N files failed to
parse." Fix: surface parse/IO failures as an ERROR-severity gate violation (a PARSE001-style rule)
rather than a swallowed warning, so an unparseable-but-present file fails the run.

**3. [HIGH/MEDIUM] COV001 is only a WARN, so "docs actually match" never blocks on missing docs.**
`_cov001` emits `Severity.WARN` (gates/__init__.py:1053); `_report_check_result` exits 1 only on
`total_errors`. A brand-new public symbol with no `frob:doc` edge at all passes `frob check`. The
north-star claim "docs actually match" is unenforceable for any symbol that simply has no doc edge --
the whole DRIFT machinery only engages once someone voluntarily adds and acks an edge. Repro: add a
new public function, no directive -> COV001 warning, exit 0. Fix direction: this is a deliberate
severity choice, but it means the north-star is opt-in; if the goal is real enforcement, COV001 must
be ERROR (or a `--strict-docs` mode that promotes it), otherwise document that missing docs are a
warning only.

**4. [MEDIUM] DRIFT is one-directional: editing a doc page to LIE never trips anything.**
Digests are computed over the source symbol (`graph/digest.py`); the lock records the source-symbol
digest at ack time (`graph/lock.py:106`). DOC002 only checks that an anchor *exists*, never its
content. So if code is unchanged and someone edits the doc paragraph under the anchor to say something
false, no digest moves, DOC002 still resolves, and `frob check` stays green. The check/__init__.py
module docstring and the north-star imply doc<->code consistency, but only code->doc drift is
detected. Repro: ack a `frob:doc` edge, then rewrite the referenced doc section to contradict the
code -> green. Fix direction: track a digest over the doc *content region* the anchor owns (heading
span) as a fourth facet and fold it into DRIFT001, so doc edits require re-ack too. This is a real
feature, not a one-liner -- flag it explicitly.

**5. [MEDIUM] Malformed `frob:doc` directives are silently downgraded, not surfaced.**
Malformed directives are surfaced only for `frob:waive` (WAIVE001) and `frob:tests` (TEST010) by
substring-matching `md.reason` (gates/__init__.py:496-517, 2438). A malformed/typo'd `frob:doc` line
that `dsl.py` demotes to `MalformedDirective` matches neither filter, so it produces no violation. The
symbol then appears to have no doc edge -> at worst a COV001 WARN (which, per #3, doesn't fail). Net:
a fat-fingered doc directive silently loses its drift tracking with no error. Repro: write `frob:doc
docs/x.md` with a subtle syntax error dsl.py rejects -> no DOC/DRIFT violation, symbol silently
undocumented. Fix: add a generic malformed-directive gate (DSL001) that surfaces EVERY
`MalformedDirective` as an error, and delete the per-flavor WAIVE001/TEST010 special-cases.

### Additional false-negatives / evasions

**6. [MEDIUM] Auto-detect fallback runs the Python pipeline on `unknown` repos.**
`_run_auto_detected_stages` (check_runner.py:401): `detected = _detected_types(root) or
[detect_project_type(root)]`; `_dispatch_check` maps any unrecognized type (incl. `"unknown"`) to
`_dispatch_check_python` (check_runner.py:227). A repo with no sentinel files runs the full Python
gate stack -- ruff/ty over a non-Python tree produce noise, and gates run over whatever the graph
happened to pick up. More importantly a genuinely unsupported project silently gets Python treatment
rather than a clear "unsupported project type" failure. Fix: make `unknown`/unmapped types a loud
config error, not a silent Python fallback.

**7. [MEDIUM] Nested / top-level-less native sources escape detection entirely.**
`detect_project_type` only globs `root.glob("*.cpp"|"*.cc"|"*.c")` at the top level
(check/__init__.py:569) and `_detected_types` requires `CMakeLists.txt`/`Cargo.toml` at root. A C/C++
project whose sources live only in `src/` with no CMakeLists at root returns `unknown` -> Python
pipeline (#6), so clang/cmake never run. Repro: <!-- frob:waive DOC006 reason="illustrative hypothetical repro filename, not a real path in this repo" -->`src/foo.c` only, no CMakeLists -> no native checks.
Fix: detect native sources recursively, or fail loudly on unknown.

**8. [MEDIUM] `_walk_doc_files` only scans `docs/**/*.md`; `frob:describes` anchors elsewhere are invisible.**
graph/__init__.py:129-155 walks only the `docs/` dir. A `frob:describes` anchor placed in `README.md`
or a top-level design note is never parsed, so its DESCRIBES edge (and the facet it selects for
DRIFT001) never exists. DOC001's root set includes README.md, but the describes-anchor discovery does
not. Repro: put a literal frob-describes directive example (naming a placeholder symbol) in README.md -> not tracked. Fix: scan the
same include/exclude glob set doclink uses, not a hardcoded `docs/` dir.

**9. [MEDIUM] Weak parse-failure threshold lets partially-broken files drop symbols silently.**
`_parse` (lang/__init__.py:179) treats a tree as usable whenever the root has >=1 child, even with
`has_error=True`. A file with a broken region parses into a partial tree; symbols inside the error
region silently don't extract, so they get no COV001/exports/drift. For Rust/C++/TS repos (which have
no gates anyway, #1) nothing else in frob catches this; for Python, ruff/ty catch the syntax error, so
impact is language-dependent. Fix: when `root_node.has_error`, emit a warning-or-error gate signal
naming the file so silent symbol loss is visible.

**10. [LOW] `_parse_vitest_report` swallows non-JSON and falls back to exit code alone.**
check/_ts.py:113-128 returns `[]` on JSON decode error; `_run_vitest` then reports
`"tests passed" if not returncode`. A vitest run that crashes-but-somehow-exits-0, or emits a partial
non-JSON report with a 0 code, is reported as passing with no per-test detail. Bounded (vitest
normally exits non-zero on crash) but the fallback is optimistic. Fix: treat non-JSON output with a
zero exit as a warning rather than a clean pass.

**11. [LOW] `detect_project_type` requires BOTH package.json AND tsconfig for `typescript`, but
`_detected_types` requires only package.json -- divergent contracts.**
check/__init__.py:567 vs check_runner.py:115. The auto-detect path (`_detected_types`) will run the TS
pipeline on a package.json-only repo where `detect_project_type` would say `unknown`. Not a security
hole but the two "what is a TS repo" definitions disagree; `_run_all_detected` and any
`detect_project_type` caller can diverge. Fix: single source of truth for language detection.

**12. [LOW] `active_ticket`/gate load-failure swallowing.** `_run_gates` (check/_python.py:535)
docstring says "most load failures (git repo ...) " degrade -- verify that a gates *internal*
exception becomes a FAIL ToolResult, not a dropped stage. `_collect_results` calls `future.result()`
which re-raises, so an uncaught exception in a gate task would propagate and abort the whole run
(loud) rather than silently pass -- acceptable, but confirm every gate wraps its own IO in Result.

---

## (C) FALSE-POSITIVE / soundness
- `_resolved_documented_srcs` correctly prevents a broken `frob:doc` from both erroring (DOC002) and
  masking COV001 -- sound (T-0233).
- `docanchor_gate` uses `st.repo_root` not the scoped path (T-0314) -- avoids spurious DOC002 under
  `frob check <subdir>`. Verified in docstring + `_docanchor_check_edge` path handling.
- `_skip_note_result` uses severity `note` + exit 0, so a `check_type` pin does not inflate error
  counts -- honest, no false positive.
- `run_check_ts` no-test-files case: vitest exits non-zero on "no test files found", surfacing as a
  FAIL even when the repo legitimately has no vitest suite -- a **false positive** for repos that use
  a different test runner. Minor; note it.
- Waiver-aware dup/arch summaries (T-0375): not deeply re-verified here (see Notes).

## (D) Per-component pessimistic verdict
- **lang parsing**: RIGHT-leaning and clean, but the usable-tree threshold + the graph-layer's
  swallow-on-Err (finding #2/#9) make it possible for present-but-unparseable files to vanish.
  Good enough for Python; risky for the polyglot promise. Verdict: adequate, one real hole.
- **per-language check dispatch**: FAST over RIGHT. Missing-tool doctrine is genuinely solid. But the
  Python-only gates coupling (#1) is a design-level north-star failure, not a nit.
- **doc-anchor / doclink**: RIGHT for structure (anchor existence, orphans), but constitutionally
  cannot detect content lies (#4) and DOC001/COV001 severity split means missing docs don't block
  (#3). Good enough as "structural doc linter," not as "docs actually match."
- **check orchestration + summaries**: The T-0122 stdout-handler race mitigation is real and
  defensively correct; `future.result()` re-raise means a stage error aborts loudly (not the old
  swallow). Post-T-0375 summaries look honest. Verdict: good.

## (E) >=10 concrete gaps -- see items 1-12 above (each has severity + repro + file:line).

---

## Notes -- what I checked vs skipped
Checked and believe correct: missing-tool doctrine across all four native pipelines
(`tool_unavailable_result`, exit 1/error); `_resolve_only` loud-config-error on unknown `--only`
stage; `_skip_note_result`/`_warn_if_polyglot` honesty; DOC002 repo-root rebasing (T-0314); COV001
broken-edge masking fix (T-0233); the T-0122 stdout-handler save/restore; `_report_check_result`
exit-on-errors-only logic; digest determinism (NUL-join, three facets).

Deliberately skipped or only skimmed: the strata-specific DOC003 PROVED-view logic and strata-core
kernel (out of the lang/check surface); the full `run_gates` internals for INV/DEC/SYS/PII/secrets
gates (only traced the doc/coverage/drift paths that bear on the north-star); the T-0375 waiver
grouping math for DUP/ARCH counts (assumed correct per its review history, not re-derived); the dup
R4 Zhang-Shasha path via `symbol_tree`; perf/xref/bind runners. I did not execute `uv run frob check`
against a synthetic polyglot fixture to empirically confirm #1/#2 -- the conclusions are from reading
the dispatch wiring, which is unambiguous, but an empirical repro fixture would harden #1, #2, and #9.
</content>
</invoke>
