## Done report

Reproduced: yes, before the fix. `frob sys audit` over the T-0115 vuln-
litmus model (`may "sql"` capability, `subject:child` collection flow into
a Pii store, no discharge claims) printed the identical CWE-639 WARNING
block once per `DEFAULT_QUALITY_VIEWS` view (3x, same family/rule/detail)
and the identical COPPA WARNING block once per `DEFAULT_COMPLIANCE_VIEWS`
view (4x) -- 9 raw gaps rendered as 9 near-duplicate blocks even though
only 4 are genuinely distinct (security, quality, compliance, lint).

Fix location: `src/frob/strata/_audit.py` (report-generation module) --
NOT `src/frob/app/sys_runner.py`'s output logic, per dispatch. Added
`GroupedGap` (BaseModel) and `group_gaps_by_view(gaps) -> tuple[GroupedGap,
...]`, which collapses `FamilyGap`s that are verbatim-identical on
`(family, rule, detail, target, sub_target)` -- differing only in `view`
-- into one group carrying every view it fired under, order-preserving on
first occurrence. `AuditReport.gaps`/`waived` are left completely
untouched (the verdict/`proved` property and waiver matching still
evaluate the full, ungrouped set) -- this is a presentation-layer
transform only, applied at print time.

`src/frob/app/sys_runner.py` changes are mechanical wiring only: `_log_
gaps` and `_log_waived_gaps` now iterate `group_gaps_by_view(report.gaps)`
/ `group_gaps_by_view(report.waived)` instead of the raw tuples, and print
`views=<comma-joined>` instead of a single `view=`. No new logic lives in
sys_runner.py; the dedup decision is entirely in `_audit.py`.

Verified manually against a real repro repo (sql-capability model, same
shape as `test_undischarged_capability_exits_nonzero_with_named_gap`):
before the fix, `frob sys audit` printed the CWE-639 block 3 times
identically; after the fix it prints once as `GAP family=quality
views=web-performance-baseline,reliability-baseline,web-quality-security-
baseline rule=THREAT003 detail=...`, while the single-view CWE-89 security
gap and the LINT001 gap remain their own distinct blocks. `audit: evaluated
views=12 -> 5 gap(s)` (the verdict-affecting count) was unchanged before
and after.

Litmus test added: `tests/unit/strata/test_audit.py::
TestGroupGaps::test_group_gaps_by_view` -- runs
`evaluate_exhaustiveness` over the existing `_vulnerable_model()` fixture,
asserts `len(report.gaps) == 9` (verdict-affecting count unchanged),
asserts no two `group_gaps_by_view` blocks render an identical `(family,
rule, detail)` tuple, asserts the CWE-639 quality gap collapses into one
group naming all 3 `DEFAULT_QUALITY_VIEWS`, asserts the COPPA compliance
gap collapses into one group naming all 4 `DEFAULT_COMPLIANCE_VIEWS`,
asserts the CWE-89 security gap stays single-view (`("owasp-top-10",)`,
not merged with anything), and asserts the 9 raw gaps collapse to exactly
4 printed groups (security, quality, compliance, lint) -- proving distinct
gaps are preserved while verbatim repeats collapse.

Evidence:
- `tests/unit/strata/test_audit.py::TestGroupGaps::
  test_group_gaps_by_view` -- PASS (`uv run pytest tests/unit/
  strata/test_audit.py -q`: 11 passed)
- `uv run pytest tests/unit/strata/ tests/system/test_cli_sys_audit.py -q`
  -- 578 passed
- `uv run pytest tests/unit/strata/test_selfconform.py -q -k
  TestRealGateGreen` -- 1 passed
- `uv run ruff check` + `uv run ruff format --check` on all touched files
  -- clean
- `make typecheck` (`uv run ty check src/`) -- "All checks passed!"
- `make coverage` (foreground, full suite) -- all tests green,
  `stamp_coverage: stamped 397 file(s)`
- `uv run frob check` (foreground, full repo) -- `8 errors, 8 warnings,
  202 waived`. All 8 remaining errors are PRE-EXISTING and outside this
  ticket's scope: 2x COV003 on `tickets/T-0214` (an unrelated ticket's
  stale evidence id), 5x TEST001 on `src/frob/app/_style.py` (T-0179's
  `style_ok`/`style_fail`/`style_warn`/`style_header`/`style_rule`
  helpers, untouched by this ticket), and 1x REL001 (`pyproject.toml`
  major-version gate, unrelated to this change and outside scope). The
  ONE error this ticket introduced (TEST001 on `group_gaps_by_view`) was
  fixed by adding a `frob:tests` directive binding it to the new litmus
  test; confirmed by re-running `frob check` before/after (9 errors ->
  8 errors, with `group_gaps_by_view` no longer listed).

Filed: none -- no out-of-scope discoveries. The self-conformance report
(`SelfConformReport`, `_log_selfconform_violations`) has no per-view
dimension (single pass, no view loop), so it was not touched and does not
need this treatment.

Gates: `frob check` run to completion in-worktree (see Evidence above);
8 pre-existing errors remain, none introduced by or attributable to this
ticket's scope. Deletion-filter clean: `git diff main --diff-filter=D
--stat` empty.

Worktree: `.claude/worktrees/agent-a41fd191d37eb038b`, branch tip after
this work is a commit on top of `66fe627` (main's tip at worktree
warm-up; `git merge main` reported already up to date).
