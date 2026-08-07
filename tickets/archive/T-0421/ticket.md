---
id: T-0421
title: 'frob check per-language tooling display: show skipped (unchanged) vs hidden
  (language absent), not silently omitted'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0410
tier: ticket
sprint: null
scope:
- src/frob/app/
- src/frob/check/
- frob.toml
- tests/unit/test_app_runners_batch6.py
- pyproject.toml
- .frob-release.json
- uv.lock
- tests/system/test_cli_check.py
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_runners_batch6.py
  reason: new TestSkipUnchangedLanguage coverage for the T-0421 skip-unchanged-vs-hidden-absent
    behavior lives in this existing batch file, alongside the other check_runner runner
    tests
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: these files were touched and committed under sibling ticket T-0420 (release-version
    bookkeeping + gate-family-split test updates) earlier in this same worktree/branch;
    T-0420's own commit subject does not name it explicitly so frob check's SCOPE001
    cross-ticket exemption cannot resolve it for T-0421's diff -- extending scope
    here rather than rewriting already-closed T-0420's commit history
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: these files were touched and committed under sibling ticket T-0420 (release-version
    bookkeeping + gate-family-split test updates) earlier in this same worktree/branch;
    T-0420's own commit subject does not name it explicitly so frob check's SCOPE001
    cross-ticket exemption cannot resolve it for T-0421's diff -- extending scope
    here rather than rewriting already-closed T-0420's commit history
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: these files were touched and committed under sibling ticket T-0420 (release-version
    bookkeeping + gate-family-split test updates) earlier in this same worktree/branch;
    T-0420's own commit subject does not name it explicitly so frob check's SCOPE001
    cross-ticket exemption cannot resolve it for T-0421's diff -- extending scope
    here rather than rewriting already-closed T-0420's commit history
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/system/test_cli_check.py
  reason: these files were touched and committed under sibling ticket T-0420 (release-version
    bookkeeping + gate-family-split test updates) earlier in this same worktree/branch;
    T-0420's own commit subject does not name it explicitly so frob check's SCOPE001
    cross-ticket exemption cannot resolve it for T-0421's diff -- extending scope
    here rather than rewriting already-closed T-0420's commit history
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_check.py
  reason: these files were touched and committed under sibling ticket T-0420 (release-version
    bookkeeping + gate-family-split test updates) earlier in this same worktree/branch;
    T-0420's own commit subject does not name it explicitly so frob check's SCOPE001
    cross-ticket exemption cannot resolve it for T-0421's diff -- extending scope
    here rather than rewriting already-closed T-0420's commit history
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_app_runners_batch6.py::TestSkipUnchangedLanguage::test_unchanged_python_reports_skipped_not_silent
- tests/unit/test_app_runners_batch6.py::TestSkipUnchangedLanguage::test_changed_python_still_runs
- tests/unit/test_app_runners_batch6.py::TestSkipUnchangedLanguage::test_absent_language_never_shown
designated_repro_test: null
threat: null
component: null
---
User UX ask: frob check shows Python tooling (ruff/ruff-format/ty) but NO Rust tooling (cargo/clippy/cargo-fmt) and no clear TypeScript status. Desired: (1) if a language IS present in the project but its package/sources did NOT change since last run, show its tooling line as SKIPPED (with a reason: unchanged), not absent -- so the human knows it was considered and intentionally not re-run (same for Python/TS tooling when nothing changed). (2) If a language is NOT present in the project at all (no .ts/.tsx anywhere), do NOT show that languages tooling line at all. Requires: detect which languages the project actually contains, track per-language change (reuse the parse-cache/content-hash + git diff), and render skipped/absent/ran accordingly. This makes the tooling section honest: ran / skipped-unchanged / not-applicable, never silently missing.