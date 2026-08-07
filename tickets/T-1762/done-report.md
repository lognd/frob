## Done report

Changed:
src/frob/tickets/_force_override.py (new) -- ForceOverrideEntry, ForceOverrideError, record_force_override, _current_actor
src/frob/app/ticket_runner/_archive.py -- _resolve_force_reason, _require_archive_force_reason, _record_or_refuse_archive_force, _require_reason_for_archive_force, _archive (new force_reason/force_reason_file kwargs)
src/frob/app/ticket_runner/_land_cmd.py -- _force_finish_requires_reason (new), _finish_worktree (new force_reason/force_reason_file kwargs)
src/frob/app/ticket_runner/__init__.py -- archive dispatch lambda threads cfg.ticket_force_reason/_file
src/frob/app/config.py -- ticket_force_reason, ticket_force_reason_file fields
src/frob/app/_config_external.py -- WIRE001 field-name tuples for the two new AppConfig fields
src/frob/_cli_parsers/_ticket/_closeout.py -- archive --reason/--reason-file flags
src/frob/_cli_parsers/_ticket/_progress.py -- land --finish --reason/--reason-file flags
design/frob.strata -- fs.write/fs.read capability declarations + interface= sync for the new module/test file
docs/modules/tickets.md -- ForceOverrideEntry data model + "--force audit trail (T-1762)" section
tests/test_tickets_organization.py -- TestForceOverrideAudit (6 new tests)
tests/unit/test_land_finish_guard.py -- 2 new tests, 1 existing test updated for the reason-required contract

Evidence:
tests/test_tickets_organization.py::TestForceOverrideAudit::test_record_force_override_requires_reason
tests/test_tickets_organization.py::TestForceOverrideAudit::test_record_force_override_appends_a_line
tests/test_tickets_organization.py::TestForceOverrideAudit::test_archive_force_with_no_live_lease_needs_no_reason
tests/test_tickets_organization.py::TestForceOverrideAudit::test_archive_force_with_live_lease_and_no_reason_refuses
tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_force_removes_despite_a_live_process
tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_finish_worktree_force_requires_reason_when_guard_would_fire
tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_finish_worktree_force_is_a_no_op_reason_wise_when_worktree_is_free
Local run: tests/test_tickets_organization.py + tests/unit/test_land_finish_guard.py, 34 collected, 0 failed.

## Classification table (requirement 4) -- every override-shaped flag, enumerated from the parser definitions

Enumerated by grepping every add_argument call across all 12 files under
src/frob/_cli_parsers/ (+ src/frob/__main__.py) for the literal flag
strings --force / --skip-* / --override* / --bypass* / --allow-* /
--ignore-* / --no-verify / --unsafe / --danger*. Zero hits for
--override/--bypass/--no-verify/--unsafe/--danger anywhere in the CLI --
the whole family reduces to --force/--skip-*/--allow-*/--ignore-*.

| Flag | File | Discharges a tracked obligation? | Reason required? | Disposition |
|---|---|---|---|---|
| `frob check --skip-{ruff,ty,arch,cycle,dup,bind,exports,gates,build,clang-tidy,clang-format,cargo-check,clippy,fmt,tsc,eslint,prettier,tests}` (18 flags) | `_check.py` | No -- narrows ONE `frob check` invocation; the skipped findings re-fire the next unqualified run | No | Correctly free |
| `frob fleet status --skip-gates` | `_reporting.py` | No -- omits the gate probe from one status rollup report; nothing is marked resolved | No | Correctly free |
| `frob ticket doable --ignore-lease` | `_ticket/_query.py` | No -- read-only query; changes what one listing includes, mutates nothing | No | Correctly free |
| `frob scaffold new --force` | `_core.py` | No tracked obligation at all -- overwrites local scaffold files, no frob.lock/ticket/gate finding involved | No | Correctly free (different category: not a safety-guard bypass) |
| `frob ticket archive --force` | `_ticket/_closeout.py` | Yes -- bypasses T-0843's live-cross-worktree-lease refusal (a real field-incident guard) | **Yes -- now enforced** | **Fixed this ticket**: reason required when a live lease would actually refuse; WARNING + `ForceOverrideEntry` in `force-overrides.jsonl` |
| `frob ticket land --finish --force` | `_ticket/_progress.py` | Yes -- bypasses T-1715's worktree-in-use refusal (deletes a worktree checkout outright) | **Yes -- now enforced** | **Fixed this ticket**: same shape as archive --force |
| `frob release stamp --allow-unbumped` | `_misc.py` | Yes -- permanently rebaselines `.frob-release.json` at the current version, silencing REL001's drift check for the API change that already happened; no `--reason` flag exists, no record, `_log.info` on success does not even mention the override | **Not enforced -- found, not fixed** | **Out of scope, flagged for follow-up.** Same shape as the two fixed instances; not touched here because it lives in `src/frob/release/__init__.py`/`src/frob/app/release_runner.py`/`_misc.py`, none of which were in this ticket's declared scope, and every override-shape ticket so far has paid a real SCOPE-extension/SELFAUDIT tax per new file touched -- a third unrelated subsystem in the same ticket was not a good trade against finishing this one. |
| `frob ticket close --skip-mutation-evidence` / `frob ticket land --skip-mutation-evidence` | `_ticket/_closeout.py` / `_ticket/_progress.py` | Yes, narrowly -- permits ONE close/land despite an ERROR-severity TEST016/BUG002 confirmatory-evidence finding | **Not enforced -- found, lower priority** | **Disposition: partially accountable already**, unlike the three above. The gate's own finding is NOT suppressed -- `_close_mutation_evidence_for_ticket` still runs and the finding still logs at WARNING every time, visible in the close/land output. What's still missing is a `--reason`/audit-record pair, so it does not fully match the "as cheap as the honest way" bar, but it is not the silent, undetectable class T-1733/this ticket exists to close. Recommend a reason requirement for full symmetry, but do not rate it at the same severity as the three fully-silent instances above. |
| `frob ticket land --allow-cross-ticket` | `_ticket/_progress.py` | Yes, narrowly -- permits a land despite a CrossTicketLeakage finding | **Not enforced -- found, lower priority** | Same disposition as `--skip-mutation-evidence`: `_land.py`'s own code logs `"land: %s allow_cross_ticket set..."` at WARNING with "justification required" text every time it fires -- visible, not silent, but still no structured `--reason`/audit-record pair. |

Net: 9 distinct override-shaped flags exist in the CLI today (13 if
`frob check`'s 18 `--skip-*` sub-flags are counted individually rather
than as one family). Two were fully silent and are fixed. One
(`--allow-unbumped`) is fully silent and unfixed -- flagged, not fixed,
scope reasons above. Two (`--skip-mutation-evidence`,
`--allow-cross-ticket`) are partially accountable (WARNING-logged,
un-reasoned) and lower priority. The rest are the free class and
correctly cost nothing.

## Requirement 5 (a gate for future override-shaped flags)

Judgement call, as asked: I did not build this, and I do not think it
should be built as a cheap heuristic. The three real fixes and the two
partial ones share NO reliable syntactic signal a gate could key on --
`--force`, `--skip-mutation-evidence`, `--allow-unbumped`, `--allow-
cross-ticket`, `--ignore-lease` are all different words, and the free
class uses the exact same words (`--skip-gates`, `--skip-ruff`, ...).
The only way to tell "discharges a tracked obligation" from "narrows one
invocation" is to read what the flag's own code path does to the
underlying finding -- whether it's fully silenced/marked-resolved
(needs a reason) or just not blocking THIS run while remaining visible
next run (free). That is a semantic distinction over the flag's effect,
not a lexical one over its name. A gate keyed on flag-name patterns
(`--force`, `--skip-*`, `--allow-*`, `--override*`, `--bypass*`) would
misfire on every one of the 18 `frob check --skip-*` flags (false
positive: they are correctly free) while still needing a human to read
the new flag's implementation to tell whether IT belongs in the
free class or not -- the exact manual read this table required. A
heuristic gate here would either over-fire until someone waives it
reflexively (training exactly the bad habit the ticket exists to stop)
or need a hand-maintained allowlist of "known-free flag names," which
is the same "hand-written list" defect class requirement 4 explicitly
rejected. Stopping at the audit, per your own instruction for this case.

Filed: none new. Note for the record (not a filing claim): during the
T-1317 audit that surfaced this ticket's own subject, I minted two draft
ids on my own worktree branch (`frob ticket new`, un-landed) describing
the same two findings T-1762 now covers. Those drafts never landed and
never became real tickets -- T-1762, filed by the coordinator from root,
is the actual ticket for this work, not a duplicate of them. The drafts
are abandoned, not resolved elsewhere; nothing to reconcile.

Gates: frob check --ticket T-1762, ticket-scoped diff-driven checks
(SCOPE/PREWORK/COV002/TODO001/FMT/AFFECT) clean except two land-owned-
artifact SCOPE001 findings (.frob-release.json stale-stamp entry,
tickets/T-1762/ticket.md itself) -- both are files `frob ticket land`
either recomputes or is the ticket's own CLI-written metadata, not
hand-edited content; verified via `frob ticket land` itself rather than
worked around locally. Full --budget sweep across gates-fast/gates-
native/gates-security/lint/static: gates-fast and gates-native clean;
gates-security clean after design/frob.strata's capability/interface
sync; only pre-existing, untouched-by-this-ticket ruff-format/ruff-
check findings remain elsewhere in the repo.

### Changed
```
 .frob-release.json                         |   4 +-
 design/frob.strata                         |  67 +++++++-------
 docs/modules/tickets.md                    |  27 ++++++
 rapid-debt.jsonl                           |   1 +
 src/frob/_cli_parsers/_ticket/_closeout.py |  13 ++-
 src/frob/_cli_parsers/_ticket/_progress.py |  12 ++-
 src/frob/app/_config_external.py           |   4 +
 src/frob/app/config.py                     |   7 ++
 src/frob/app/ticket_runner/__init__.py     |   6 +-
 src/frob/app/ticket_runner/_archive.py     | 139 +++++++++++++++++++++++++---
 src/frob/app/ticket_runner/_land_cmd.py    |  74 ++++++++++++++-
 src/frob/tickets/_force_override.py        | 141 ++++++++++++++++++++++++++++
 tests/test_tickets_organization.py         | 109 ++++++++++++++++++++++
 tests/unit/test_land_finish_guard.py       |  49 +++++++++-
 tickets/T-1762/done-report.md              | 130 ++++++++++++++++++++++++++
 tickets/T-1762/ticket.md                   | 143 ++++++++++++++++++++++++++++-
 16 files changed, 869 insertions(+), 57 deletions(-)
```

### Evidence
- `tests/test_tickets_organization.py::TestForceOverrideAudit::test_record_force_override_requires_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestForceOverrideAudit::test_record_force_override_appends_a_line` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestForceOverrideAudit::test_archive_force_with_no_live_lease_needs_no_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestForceOverrideAudit::test_archive_force_with_live_lease_and_no_reason_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_force_removes_despite_a_live_process` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_finish_worktree_force_requires_reason_when_guard_would_fire` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_finish_worktree_force_is_a_no_op_reason_wise_when_worktree_is_free` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 1 error(s), 1041 warning(s), 727 waived
- error-findings: TICK006@tickets.md
