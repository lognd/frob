## Done report

Verified before touching anything (per playbook caution on sweep-filed
tickets): re-derived the E501 finding at the sweep's own commit
(918ec0c7d0675c95e5afa3a468fe3738c13dbc56) and confirmed it was real --
three lines over 88 chars in src/frob/app/ticket_runner/_waive_audit.py,
including line 453:
`f"verdict={payload['verdict']} watermark={watermark.commit_sha} audited={watermark.waivers_audited}"`.

That commit was superseded by two later lands touching the same file
(1b1cac1c0 T-2485, f2fea5ae0 T-2493) before this sweep ticket was ever
worked. `git show HEAD:src/frob/app/ticket_runner/_waive_audit.py | grep`
for the offending line's text finds nothing -- it no longer exists on
main. Confirmed with `frob check --only lint` (unscoped, full ruff-check
pass): zero E501 findings anywhere in this file at current HEAD, only
one unrelated pre-existing I001 (import order) finding.

No code change needed -- the identity was real at the sweep's commit but
is not present on main today, fixed as an incidental side effect of
unrelated work on the same file. Closing as pre-existing/superseded per
the ticket's own stated escape hatch ("if they are pre-existing residue
... close this ticket with that finding stated explicitly").

### Changed
```
 tickets/T-2489/ticket.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md


frob:no-behavior-change reason="verified the sweep's E501 identity no longer exists on main -- superseded by later lands (T-2485/T-2493) touching the same file; no code change needed"
