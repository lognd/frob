## Done report

Changed: (ticket-hygiene only, no src/ change)
tickets/T-2384/ticket.md (parent edge: T-1382 -> T-2964, via `frob ticket
  set-parent`)
tickets/T-2964/ticket.md (new top-level epic)
tickets/T-2965/ticket.md (new ticket, unrelated tooling gap filed as a
  by-product of this investigation)

Investigation: T-1382 is the Makefile-decoupling epic (acceptance: every
documented frob workflow works via a frob subcommand with no Makefile
dependency -- all 3 acceptance items measured UNBOUND, i.e. genuinely
unstarted). Its `frob ticket epic T-1382` rollup read "3/3 done (100%)"
because T-2384 (a portability/schema-resolution epic, tier=epic, with
its own children T-2891/T-2892, all done) carried `parent: T-1382` --
confirmed by reading T-2384/T-2891/T-2892's ticket bodies in full: none
of the three mentions the Makefile, cross-platform shell portability,
or any frob-subcommand-replaces-make-target work. They are entirely
about a DIFFERENT kind of portability: frob's own gates/schema
resolvers/skills-sync working correctly when frob is deployed to a
sibling repo that is not frob's own source tree (lograder, feldspar).
Confirmed via `git grep parent: tickets/T-2384/T-2891/T-2892/
ticket.md`: only T-2384 itself carries `parent: T-1382` directly (T-2891/
T-2892 are parented to T-2384, not T-1382 -- the false-complete signal
comes from the epic rollup walking the full descendant tree, not from
three separate mislinks).

No existing epic in the ledger already covered this "cross-repo
portability of frob's own enforcement surface" subject (checked every
`tier: epic` ticket in the active ledger) -- T-2384 IS that epic's real
content, it simply had no correctly-scoped parent. Re-parenting to
`null` was the semantically correct fix, but `frob ticket set-parent`
(T-2770, src/frob/tickets/_setters.py::set_parent) has NO route to
clear a parent to null -- `parent-id` is a required positional and
`_validate_parent_edge` refuses anything that does not resolve to an
existing ticket (confirmed by reading the setter's own docstring: its
motivating case is one-directional, "re-parenting the successor ONTO
the epic," never detaching). Filed T-2965 for that tooling gap rather
than hand-editing frontmatter (forbidden) or leaving T-2384 stuck under
the wrong epic.

Fix applied: filed T-2964 (new top-level epic, "Epic: cross-repo/
multi-project portability of frob's enforcement surface") as T-2384's
correct home, then `frob ticket set-parent T-2384 T-2964 --reason ...`.

Re-verified after the move:
  `frob ticket epic T-1382` -> "0/0 done (0%)" (was "3/3 done (100%)")
  `frob ticket epic T-2964` -> "3/3 done (100%)" (T-2384/T-2891/T-2892,
    correctly grouped under a portability epic that actually describes
    them)
  T-1382's own frontmatter: state=queued, parent=null -- unchanged,
    still honestly reflects that its own acceptance criteria are
    unstarted. NOT closed, NOT decomposed further, no progress invented.

Filed:
T-2964 -- new top-level epic, home for T-2384's real subject
T-2965 -- frob ticket set-parent needs a --clear path to detach a
  mis-parented ticket to root (the tooling gap this investigation
  surfaced; out of T-2959's own scope, real scoped work for its own
  ticket)

Disclosed: this ticket's own re-parenting used a newly-created epic
(T-2964) rather than clearing T-2384's parent to null, because the CLI
tooling to do the latter does not exist (T-2965). This is not a
guess at ambiguous intended parentage -- T-2384's subject matter is
unambiguous (cross-repo portability, not Makefile decoupling) -- it is
a structural workaround for a confirmed, one-directional tooling gap,
disclosed rather than silently forced.

Gates: no src/ change in this ticket; `frob ticket epic T-1382`/
`frob ticket epic T-2964` re-verified live, as shown above.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 28 error(s), 476 warning(s), 854 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2962/ticket.md, DOC008@docs/commands/check.md, LANG004@src/frob/lang/_support.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/serve/_socketd.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
