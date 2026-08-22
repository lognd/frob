## Done report

Added a repo-wide `.gitattributes` default (`* text=auto eol=lf`) so
`core.autocrlf=true` (a Windows-checkout setting, present on this
Linux/WSL clone) can no longer write CRLF into any tracked text file's
working-tree copy -- the T-2586 pins for rapid-debt.jsonl/
force-overrides.jsonl and the T-1433/T-2239 `-text` attachment pins stay
as explicit, self-documenting lines below the new default and continue
to win for their own paths (git's "last matching pattern wins" rule).

Verified the decisive control this ticket names: BEFORE the fix,
`awk 'length($0)>88'` reported 6 apparent E501 violations on
src/frob/app/ticket_runner/_ledger_mirror.py while
`ruff check --select E501` reported it clean (368 CR bytes present).
AFTER the fix + a forced re-checkout of every tracked file in this
worktree (`git ls-files -z | xargs -0 rm -f && git checkout -- .`,
needed because git only rewrites a file's working-tree bytes on checkout
when it decides a write is warranted -- an in-place attribute change
alone does not trigger it for content that already round-trips through
autocrlf's own checkin conversion), 0 of 6457 tracked files in this
worktree contain a CR byte, and awk/ruff now agree on every sampled
file.

Also confirmed by direct measurement (not just by construction):
- `git status` is clean immediately after the renormalization.
- `git check-attr eol -- rapid-debt.jsonl force-overrides.jsonl` still
  reports `lf` (T-2586's pins hold).
- `git check-attr text -- tickets/*/attachments/**` still reports
  `unset` (T-1433/T-2239's binary pin holds); `gate:COV`'s COV004 shows
  the same 2 pre-existing (unrelated, predate this ticket) sha-mismatch
  findings before and after this change -- no new COV004 findings.

Evidence: added tests/unit/test_gitattributes_crlf_normalization.py,
asserting `git check-attr eol` resolves `lf` for a representative
tracked-source sample plus both T-2586/T-1433 pins, at the ATTRIBUTE
level (what a fresh checkout actually consults) rather than asserting on
this worktree's own already-renormalized bytes. Verified genuine
FAILED_AT_PARENT via the T-2021 technique (commit the test alone against
the still-unfixed .gitattributes, confirm failure, then commit the fix):
`frob ticket evidence T-2611 --check-repro ...test_sampled_source_files_are_pinned_to_lf
--base-ref 72fef98277ad48ad416046b8c20234a49b6a24d0` -> FAILED_AT_PARENT.
Designated as this ticket's repro evidence; two supporting assertions
(attachment pin, rapid-debt pin) bound as flat evidence alongside it.

## NOT LANDED -- awaiting a coordinator-scheduled quiet window

Per this ticket's own explicit sequencing requirement and the dispatch
brief: this change is fully implemented, tested, and evidence-bound in
this worktree, but deliberately NOT landed. Renormalizing a tree this
size touches (or is capable of touching, once other worktrees next
re-checkout) essentially every tracked file's working-tree bytes, and the
hazard is other agents' currently-open worktrees, not "lands in flight"
at any single instant -- `frob check`/`fleet_status.py` cannot measure
that hazard, so a momentary LANDS IN FLIGHT: 0 reading is not
authorization to land this one. Reporting ready; the coordinator will
schedule the window.

Filed: none new for this ticket.

### Changed
```
 .gitattributes                                     | 23 +++++++
 .../unit/test_gitattributes_crlf_normalization.py  | 78 ++++++++++++++++++++++
 tickets/T-2611/ticket.md                           | 16 ++++-
 3 files changed, 115 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_gitattributes_crlf_normalization.py::TestGitattributesEolNormalization::test_sampled_source_files_are_pinned_to_lf` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitattributes_crlf_normalization.py::TestGitattributesEolNormalization::test_attachment_binary_pin_still_holds` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitattributes_crlf_normalization.py::TestGitattributesEolNormalization::test_rapid_debt_lease_pin_still_holds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2611, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
