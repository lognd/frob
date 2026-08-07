## Done report

Changed:
- src/frob/vet/_capability.py -- `_is_self_path` renamed to public `is_self_pattern_path`
  (same three-path exclusion set: this module, `_capability_registry.py`, `_cve_fingerprint.py`),
  added to `__all__`. `_is_self_path` kept as a thin private alias so this module's own two
  pre-existing call sites needed no rename.
- src/frob/strata/_effects.py -- `_line_effects` now calls `is_self_pattern_path` and returns
  `[]` for excluded files, before either `extract_effects` or `check_capability_conformance`
  (via `_file_capability_violations`) ever see a line from them. Fixes the stratamod 'fs' x2
  violations (`_cve_fingerprint.py:120/:190` needle literals).
- src/frob/strata/_selfconform.py -- `_observed_extended_kinds_by_node` and
  `_observed_all_kinds_by_node` both now skip `is_self_pattern_path` files before calling
  `scan_file_capabilities`. Fixes the stratamod 'deserialize'+'sql' and vet 'html_render'
  violations (extended-kind catalog needle self-match).
- design/frob.strata -- `node vet`'s `may` list: removed `deserialize`/`eval`/`exec`/`sql`.
  With the shared exclusion applied consistently, a clean scan shows these four are NEVER
  genuinely observed under `src/frob/vet/**` outside the three now-excluded catalog files
  (`_ecosystem.py::_pickle_violation` only detects shipped `.pkl` files by extension, never
  calls `pickle.load`; `_cache.py`/`_nvd.py`/`_registry.py`'s `conn.execute(...)` calls are
  parameterized, not the `execute(f"...")` shape the 'sql' needle patterns for; no bare
  `eval`/`exec` call exists anywhere in real vet code). This is the T-0169-round-2 finding
  made real: these `may` declarations existed only to cover self-match noise. `may "fetch_url"`
  kept (real: `_nvd.py`/`_registry.py` urlopen-shaped fetches). `may "net"` LINT004 comment
  narrowed since it's now the sole risky-capability-with-no-kill-switch case on this node.
- tests/golden/frob_export_seccomp.json -- regenerated: `export_seccomp` derives the vet
  node's seccomp allowlist from its `may` set, so removing `exec` drops
  clone/execve/execveat/fork/vfork from that node's syscall list. `frob_export_iam.json` and
  `frob_export_k8s.yaml` are unaffected (verified via git diff --stat, zero changes).
- tests/test_vet.py -- new `TestFingerprintScan::test_self_pattern_exclusion_covers_every_
  needle_table_module` drift-lock test (registry-of-pattern-files): greps every `.py` file
  under `src/frob/` for a `needles=(...)` or `needles: tuple[...]` literal-table marker and
  asserts every match is covered by `is_self_pattern_path`, plus a sanity check that the
  exclusion set is exactly the three known catalog modules (not vacuously empty).

Root cause confirmed: `_effects.py::_line_effects` and `_selfconform.py`'s two extended/
all-kind observation helpers each independently scanned every `code=`-bound file with no
self-match exclusion at all -- `_capability.py::_is_self_path` (now public
`is_self_pattern_path`) existed and was already used by `frob.vet`'s own directory
aggregation, but neither `_selfconform.py` nor `_effects.py` called it. This is the T-0169
round-2 prototype (reverted at the time) done for real this time: applying the exclusion
surfaced 4 SYS101 stale-design violations (deserialize/eval/exec/sql on `vet`), confirmed by
grep that none of those four capabilities are genuinely exercised anywhere under
`src/frob/vet/**` outside the excluded catalog files, so the corresponding `may` declarations
in design/frob.strata were removed as dishonest (never real).

Evidence (measured, this session):
- `uv run pytest -q tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant`
  -- 1 passed (was FAILED with 5 violations before this ticket's fix; an intermediate run
  after applying the shared exclusion but before recalibrating design/frob.strata showed
  exactly the predicted 4 SYS101 violations, confirming the T-0169 round-2 finding).
- `uv run pytest -q tests/` (full suite) -- exit 0, all passed (2 skipped, xdist-parallel).
- `uv run pytest -q tests/unit/strata/ tests/test_vet.py tests/test_capability_registry.py tests/test_vet_containment.py tests/unit/cve/test_vet_match.py`
  -- exit 0, all passed (regenerated seccomp golden verified here too).
- `uv run frob check` -- 2 unwaived violations remain: COV003 on T-0168's evidence id and
  TEST006 (no coverage stamp). Both confirmed PRE-EXISTING via `git stash` + `frob check` on
  the unmodified tree (identical 2 violations before this ticket's changes) -- not introduced
  by this ticket, out of scope, TEST006 is the campaign-wide stamp warning the playbook says
  to ignore.
- `uv run ruff format --check .` -- clean (1 file, tests/test_vet.py, reformatted before
  this report).
- `uv run frob test --base main` -- exit 0, `[PASS] python exit=0 2.95s` over the
  touched-set selection (tests/test_vet.py, TestFrobSelfModel, test_cli_vet.py hook-mode,
  test_pii.py PII posture).
- `git diff main --diff-filter=D --stat` -- empty (deletion-filter land rule, clean).

Filed: none -- no out-of-scope discoveries; the design/frob.strata recalibration was
explicitly disclosed as in-scope by the dispatch prompt, not filed separately.

Gates: `frob check` clean of anything ticket-introduced (2 remaining violations are
pre-existing, verified above via stash comparison); `frob test --base main` clean.

Two merge rounds against a moving main mid-session (main advanced twice: T-0169's
`_capability_binding` multi-language superset landed on `_selfconform.py`, then a further
close/land cycle added `tests/unit/strata/litmus/managed_*.strata`/`test_managed.py`).
Resolved the T-0169 conflict by keeping BOTH sides in `_selfconform.py`'s two observation
helpers -- T-0169's superset binding stays the iteration source, T-0201's
`is_self_pattern_path` skip still applies within it -- then re-ran `make core`, the full
`pytest -q tests/` suite (exit 0), `uv run frob check` (same 2 pre-existing violations,
ruff-format clean after re-formatting the merge-resolved file), `uv run frob test --base
main` (exit 0), and `git diff main --diff-filter=D --stat` (empty) against the final merged
tip (`47ce4e3` plus the second main pull) before writing this report.

Not closing per dispatch instructions -- review-gated flow, leaving T-0201 in-progress for
the reviewer.
