## Done report

Changed: tickets/archive/T-2796/done-report.md

Measurement: re-ran `frob check --only doclink --only docanchor --only
tickets --json` on current main (post-rebase). DOC001 and DOC011 do not
reproduce at all repo-wide (0 hits for both rules) -- confirmed already
fixed by T-2879 ("Red-tail sweep: COV001/DRIFT002/DOCENUM001/PERF004/
DOC011/DOC006", commit a40cf2f3a), which directly edited
docs/investigations/T-2796-backlog-reproduction.md for exactly this
reason. Those two of the three identities filed here are stale-baseline
false positives, already resolved before this ticket was even filed.

The third identity, TICK006@tickets.md, DID still reproduce: T-2796's own
archived Done report claimed "Filed: T-draft-b1ac02d7 ..." but that draft
never survived land and never resolved to any real ticket id (verified:
`git log --all` shows only the original filing commit 94763205f, never
renumbered/promoted; no ticket anywhere covers its stated scope). This is
the T-0577 draft-loss class documented in docs/modules/gates.md's TICK006
section. Per-instance `frob:waive TICK006` is not viable (the Violation
is file-scoped only, so a waiver there would blanket-suppress every
current and future TICK006 finding in the ledger -- documented precedent:
tickets/archive/T-0741/ticket.md, tickets/archive/T-2722/done-report.md).
Fixed per the sanctioned option (b) from that same precedent: rewrote the
affirmative "Filed:" claim into a NOTE-style disclosure (negated/
descriptive, not an affirmative filing claim), so TICK006's grammar no
longer matches it. Re-measured after the edit: TICK006 no longer fires
for tickets.md.

Evidence: docs/ledger-only fix, no pytest surface. Per playbook section
5, recording the existing CLI-dispatch integration test as evidence:
tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches

Filed: none -- the underlying gap the phantom draft named (documenting
drop --absorbed-by vs fail in agent-playbook.md) is out of this ticket's
scope (docs/investigations/ and tickets.md only) and is left unfiled per
the NOTE; a future agent or coordinator can re-file it if still wanted.

Gates: `frob check --only doclink --only docanchor --only tickets --json`
run before and after the fix, scoped re-measurement matching this
ticket's declared scope; zero DOC001/DOC011/TICK006 findings for the two
files in scope after the fix.

### Changed
```
 tickets/T-2804/done-report.md | 56 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2804/ticket.md      |  6 ++++-
 2 files changed, 61 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 17 error(s), 434 warning(s), 845 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@tickets/T-2880/ticket.md, DOC006@tickets/T-2884/ticket.md, DOC006@tickets/T-2886/ticket.md, TICK004@tickets.md
