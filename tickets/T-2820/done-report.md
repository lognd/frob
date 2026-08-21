## Done report

Changed:
src/frob/gates/_refs.py::_load_allowlist
src/frob/gates/_refs.py::_is_glob_entrypoint
src/frob/gates/_refs.py::_allowlist_covers
src/frob/gates/_refs.py::_ref_gate_file_violations
src/frob/gates/_refs.py::_ref001_or_002
src/frob/gates/_refs.py::ref_gate
frob.toml ([[refs.entrypoint]] table: 4 new entries)
docs/modules/gates.md (REF001/REF002 severity + glob-entrypoint doc)
docs/modules/tickets-data-storage.md (real second reference for
  _attach_backfill.py)
docs/index.md (real references for docs/commands/format.md and two
  previously-unlinked investigation docs)
docs/design/test005-ratchet-schedule.md, docs/investigations/
  T-2782-land-serialization.md, docs/investigations/
  T-2790-check-stage-profile.md, docs/investigations/
  T-2796-backlog-reproduction.md (inline `frob:waive REF002 reason=...`,
  singly-anchored-by-design precedent)

Re-measured before starting (parent T-2369's own body cited 37 across
REF001/REF002/REG008 from 2026-08-18; that number had moved): a full,
non-budget-truncated `uv run frob check --json --budget 900` (budget 500
silently truncates and SKIPS the gates-fast/native/security/lint groups
that run these three rules -- confirmed via the JSON `budget.
skipped_groups` field, not assumed) found REF001=275, REF002=6,
REG008=18 -- REF001 in particular had grown 257 -> 275 since the parent's
disclosure.

Read a sample of the 275 REF001 findings before grinding, per the
brief's instruction to check for a single systematic cause: 261 of 275
(95%) were `changelog.d/T-XXXX.md` -- one per landed ticket, forever,
write-once fragments the land pipeline assembles into CHANGELOG.md and
never references again by name. This is ONE homogeneous class, not 257
independent findings. A second pass after the first fix found a matching
second class: ticket `attachments/`/`evidence/` artifacts (12 more),
same write-once-per-ticket-forever shape.

Fix: `[[refs.entrypoint]]`'s `path` field now also accepts an
fnmatch-style glob (`_allowlist_covers`/`_is_glob_entrypoint`) alongside
its existing literal-path matching, so one frob.toml entry
(`changelog.d/*.md`, `tickets/*/attachments/*`, `tickets/*/evidence/*`)
covers a whole structurally-permanent class instead of needing a new
literal entry every single future land. This collapsed REF001 275 -> 2
and REF002 6 -> 5 in one shot (verified via a second full, non-truncated
check run).

The remaining 7 (2 REF001 + 5 REF002) were genuinely heterogeneous
one-offs, small enough to fix directly rather than deferring to another
batch:
- `docs/commands/format.md` was missing from docs/index.md's own command
  table (a real doc-coverage gap, not an exemption) -- added.
- Two investigation docs (T-2790, T-2796) were unlinked from docs/index.md
  entirely -- added to the Investigations section, matching the existing
  T-2782/T-2202 entries' format.
- `src/frob/app/ticket_runner/_attach_backfill.py` had only its own
  package `__init__.py` as a consumer -- gave it a real second reference
  by documenting `--backfill-drafts` in docs/modules/tickets-data-
  storage.md (a genuine doc-coverage gap, not busywork).
- The four remaining still-singly-anchored docs (test005-ratchet-
  schedule.md, T-2782/T-2790/T-2796) match this repo's own established
  precedent (docs/audits/tickets-testing-round2.md, docs/design/tickets-
  package-scope-precedent.md, et al.) for a deliberately-singly-anchored
  design/investigation doc -- waived inline with the same reasoning
  shape, not fixed with an artificial second link.
- `tickets/T-2504/census-2026-08-18-raw.json` (a one-off raw-data
  attachment directly under its ticket dir, not under attachments/ or
  evidence/) got its own literal `[[refs.entrypoint]]` entry, with a note
  that a recurrence of this exact shape should generalize to a glob
  instead of adding more literals.

Final re-measurement (full, non-truncated `--budget 900`, `complete:
true`): REF001 = 0, REF002 = 0. Both promoted `Severity.WARN ->
Severity.ERROR` in `_ref001_or_002` (`src/frob/gates/_refs.py`) --
verified zero remaining BEFORE writing the promotion, per policy. REF003
(dangling `frob:used-by`) is untouched and stays WARN.

REG008 (18 findings, `frob.gates._registry_exhaustiveness` -- a
different gate module from REF001/002/003's `frob.gates._refs`) is
UNTOUCHED and stays on parent T-2369 for a separate batch; T-2369 stays
open, not closed by this child's land.

Evidence:
tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_exempts_matching_files
tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_does_not_exempt_non_matching_files
tests/test_refs_gate.py::TestSeverityAndDegrade::test_all_violations_are_warn_severity (name
  kept despite now asserting ERROR severity -- T-0396/T-0831/T-1653/
  T-1665 all cite this exact node id as their own evidence; renaming it
  would have silently orphaned four other tickets' evidence)

Also ran the full REF-family test surface after the change:
tests/test_refs_gate.py, tests/unit/gates/test_refs.py,
tests/unit/test_check_gates_summary.py, tests/unit/graph/
test_dsl_markdown_waive.py, tests/unit/gates/test_lexical_selfcheck.py,
tests/test_gates.py -k "REF or ref or Ref" -- 76+63 collected, 0 failed
across both runs. Found and fixed three literal `Severity.WARN`
assertions in tests/unit/gates/test_refs.py the first full run caught
that a search alone would have missed.

Filed: none new (all discovered gaps -- format.md's missing index entry,
the two unlinked investigation docs, _attach_backfill.py's thin doc
coverage -- were fixed directly in this batch rather than deferred,
since each was a small, real, in-scope fix, not a widening of scope).

Gates: `frob check --ticket T-2820` re-measured with COV002
(new/changed test classes needed `frob:ticket` directives -- added),
COV003 (a citing ticket's evidence node-id would have broken from the
test rename -- avoided by keeping the old name), PRE001/SCOPE001 (scope
narrowed to the touched files) all clean; remaining errors in that run
are pre-existing repo-wide findings unrelated to this diff (CYCLE001,
COV001, DOC006/011, DRIFT001/002, PERF004, REG002, SEC110, SELFAUDIT001,
SYS003, TEST001, TICK003/004/006, claude-config-drift). No waivers
needed beyond the four inline REF002 waivers documented above (an
explicitly-supported, pre-existing mechanism, not a new one).

### Changed
```
 tickets/T-2369/ticket.md           | 93 +++++++++++++++++++++++++++++++++++++-
 tickets/T-2820/ticket.md | 52 +++++++++++++++++++++
 2 files changed, 143 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_exempts_matching_files` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_does_not_exempt_non_matching_files` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestSeverityAndDegrade::test_all_violations_are_warn_severity` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 19 error(s), 977 warning(s), 714 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
