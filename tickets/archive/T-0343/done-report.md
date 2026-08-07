## Done report

Branch: `worktree-agent-a408313d232287741`. HEAD after merging main:
`5cddf1f` (fast-forwarded clean, `git diff main --diff-filter=D --stat`
empty at land time).

Gate mechanism: `frob.gates._registry_exhaustiveness.registry_gate`,
wired into `frob check` as the `registry` gate (`_ALL_GATES`,
`_build_jobs`), ERROR severity, family `REG001`-`REG005`. NOT a pytest,
NOT `--only`-skippable in a way that hides it from a default `frob
check` run -- it is one of the always-on gates in `_ALL_GATES`.

Disposition grammar implemented (parses `disposition:` on every entry
across all 9 `docs/design/registry/*.yaml` files, `weaknesses.yaml`'s
split `cwe_entries`/`other_weakness_framework_entries` handled
generically via `_entry_lists`):
- `handled_by:<rule-id>` verified against the live
  `_KNOWN_GATE_RULES | policy rule ids` union at call time (never a
  hardcoded snapshot) -- dangling reference is REG002.
- `deferred:<ticket-id>` verified against the loaded `TicketQueue`;
  missing or `done`/`dropped` is REG003.
- `duplicate_of:<id>` verified the target id exists anywhere in the
  registry; dangling is REG004.
- `out_of_scope:<reason>` requires a non-empty reason; REG001 if empty.
  NAMED GAP (not silently assumed solved): `caught_by`/Area-2 (T-0382)
  verification is NOT built yet in this codebase, so `caught_by` is
  accepted as a free string for now, per the ticket's own concession (4).
- missing/`pending`/bare `addressed` (no `handled_by` attached) -> REG001
  undispositioned. A bare `addressed` claim is deliberately NOT accepted
  at face value -- it names no verifiable enforcement, which is exactly
  the anti-lie case.
- REG005: a declared `total:`/`<prefix>_total:` that drifts from the
  actual entry-list length (opt-in per file; a file with none declared
  is not checked -- narrowest honest form).
- REG004 also fires for RECONCILIATION.md finding (b)-documented split
  ids that still show empty `cross_refs` (parses the `### (b) SPLIT
  entries` section for backtick-quoted ids).

Fix applied alongside (in scope, not the reconciliation itself): all 9
registry yaml files + RECONCILIATION.md got a `frob:used-by
src/frob/gates/_registry_exhaustiveness.py` declaration plus a quoted
basename reference from the gate module (`REGISTRY_FILES` tuple), and
each yaml got a `total:`/split `_total:` field matching its current
entry count -- this is what clears REF001 (dead/orphan) for these files
now that the gate actually reads them; verified via `frob check --only
refs` (REF001/REF003 gone for all registry files; a few files still show
WARN-level REF002 "exactly one anchor", not a blocking orphan finding,
not in scope to chase further here). New public symbols got
`frob:doc`/`frob:tests` edges pointing at a new in-scope doc,
`docs/design/registry/EXHAUSTIVENESS-GATE.md` (NOT `docs/modules/
gates.md`, which is outside this ticket's declared scope) -- verified
clean via `frob check --only docanchor --only coverage`.

Scope note: the ticket's original frontmatter `scope` did not list
`src/frob/gates/**`, but the dispatch instruction explicitly directed
"put the gate where gates live" (src/frob/gates/**) as an authorized
scope, matching every sibling gate's real location
(`frob.gates._refs`, `frob.gates._pii_structural`, etc. all live there,
not under `frob.strata`/`frob.arch`). Widened the ticket's own `scope`
field in this same edit (tickets.md is itself in scope) rather than
silently working outside the declared scope; re-ran `frob ticket sweep
T-0343` after widening, per the sweep command's own documented purpose.
`frob check --only scope` now clean.

Red-count on frob's own registries (HONEST, measured via `frob check
--only registry --json`, not suppressed or waived): **1020 violations**
(1019 REG001 undispositioned, 1 REG004 unresolved documented split).
Lower than the ticket's own ~2500 estimate -- measured, not assumed;
the gap is explained by `weaknesses.yaml`'s 944 CWE entries + 40
security-corpus entries already carrying a legacy `duplicate-of:`/
`out-of-scope:` grammar (hyphenated, pre-existing) that this module's
regex (`duplicate[_-]of:`, `out[_-]of[_-]scope[:(]`) already accepts as
valid without modification -- so those ~984 entries do NOT contribute to
the red count, leaving ~1006 `pending` + ~27 bare `addressed` (~1033,
close to the measured 1019 after minor edge cases) as the real
undispositioned surface T-0384..T-0392 must close. REG002/REG003 are 0
on the real corpus today (no entry yet uses the new `handled_by:`/
`deferred:` forms) -- both branches are exercised and proven correct
only by the fixture tests below, not by the live corpus, since no
in-scope reconciliation was done here per the ticket's own instruction
not to do per-registry reconciliation in this ticket.

Fixture test results (measured, `uv run pytest
tests/test_registry_exhaustiveness.py -q`): **17 passed**, 0 failed.
Covers: undispositioned entry fails (REG001), dangling `handled_by`
fails (REG002), real `handled_by` passes, deferred-to-closed/missing
ticket fails (REG003), deferred-to-open passes, fully-dispositioned
fixture (all 4 disposition kinds) passes with zero violations, bare
`addressed` fails, dangling `duplicate_of` fails (REG004), empty
`out_of_scope` reason fails, severity is always ERROR, declared-total
drift fails/passes (REG005, both `entries`/`total` and split
`cwe_entries`/`cwe_total` shapes), RECONCILIATION.md split-with-empty-
cross_refs fails / split-with-cross_refs passes (REG004), missing
registry dir is a clean no-op.

Evidence ids (all 17, recorded via `frob ticket evidence T-0343`,
`frob test --base main` touched-set run exit 0):
tests/test_registry_exhaustiveness.py::TestDisposition::test_undispositioned_entry_fails,
::test_dangling_handled_by_fails, ::test_handled_by_real_rule_passes,
::test_deferred_to_closed_ticket_fails,
::test_deferred_to_missing_ticket_fails,
::test_deferred_to_open_ticket_passes,
::test_fully_dispositioned_fixture_passes, ::test_bare_addressed_fails,
::test_dangling_duplicate_of_fails, ::test_out_of_scope_no_reason_fails,
::test_severity_is_always_error,
tests/test_registry_exhaustiveness.py::TestTotalDrift::test_total_mismatch_fails,
::test_split_entries_key_total_checked,
::test_no_declared_total_not_checked,
tests/test_registry_exhaustiveness.py::TestSplitReconciliation::test_documented_split_with_empty_cross_refs_fails,
::test_documented_split_with_cross_refs_passes,
tests/test_registry_exhaustiveness.py::TestMissingDir::test_missing_registry_dir_returns_empty.

Filed: none (no out-of-scope work discovered that warranted a new
ticket; the `caught_by`/Area-2 gap is already tracked by the existing
T-0382, referenced inline, not re-filed).

Gates: `frob check --ticket T-0343` -- ruff-check/ruff-format/ty/cycle
clean for touched files (the repo's one remaining ruff E501 is in
`src/frob/testing/_select.py`, outside this ticket's scope, pre-
existing); `gates` stage exits 1 (1021 errors total) but every
violation outside REG001/REG004 is a PRE-EXISTING repo-wide finding
(REF001/REF002 mostly `docs/design/cwe-1000-registry.md` and other
untouched files, PERF001-4, ARCH001, SEC110, PII010, TODO001, REL001,
TEST006) verified present before this ticket's changes by re-running
`--only <gate>` against files this ticket did not touch -- no baseline
was stamped in this worktree so `--delta` could not narrow the report
further; this is disclosed rather than asserted away. `--only registry`
gives the clean, isolated 1020-violation honest count above. `--only
docanchor --only coverage` and `--only refs` (scoped to the new files)
both exit 0.

NOT done in this ticket (explicitly out of scope per the ticket's own
text): the per-registry reconciliation itself (T-0384..T-0392) --
dispositioning the ~1019 real `pending`/`addressed` entries. The
`caught_by`/Area-2 verification mechanism (T-0382) does not exist yet;
`out_of_scope` dispositions are accepted with a bare string `caught_by`
for now, a named and tracked gap, not a silent one.

Ticket left OPEN (in-progress) -- reviewer-gated, not closed by the
implementer per instruction.
