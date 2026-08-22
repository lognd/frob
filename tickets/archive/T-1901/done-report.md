## Done report

Reproduced the SYS004 finding at the parent of e1a603603e101abb08e624517f3ba72d9c14fcda
(commit 67894869e9366977fad805b0f50c2b3af493e0a2): design/frob.strata's
claude_hooks/scripts_ops/testsuite nodes declared

    attr interface=[
        [],
    ];

which parses as a one-element list containing an empty list, i.e. a call
of a symbol named "[]" -- the same corruption class T-1900 already fixed
elsewhere in this file. sys_gate reports that as SYS004 (design file
load/elaborate failure) against design/frob.strata.

The fix was already applied directly to main by the owner in
e1a603603e101abb08e624517f3ba72d9c14fcda ("fix(design): final repair of
strata corruption before T-1900's fix takes effect"), which collapsed all
three malformed `attr interface=[[],];` blocks to the correct
`attr interface=[];`. That commit predates this dispatch and is already
an ancestor of HEAD; it never cited T-1901.

Verified on the current tree: `uv run frob check --only sys` reports 0
errors/0 warnings, and
tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
(the repo-live sys_gate regression guard) passes. `frob ticket evidence
T-1901 --check-repro ... --base-ref e1a603603e101abb08e624517f3ba72d9c14fcda~1`
confirms FAILED_AT_PARENT for that same node id, so this is a real
(already-applied) repro, not confirmatory-only evidence.

No code change was needed in this ticket beyond recording the fix and
closing it out -- the corruption was hand-repaired on main before this
ticket was picked up. Per T-1870/T-1916's standing owner directive, no
automatic mutation of design/frob.strata is reintroduced here; this
report only documents a hand-edit that already happened.

### Changed
```
 tickets/T-1901/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 941 warning(s), 696 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, DOC001@docs/design/cli-hygiene.md, SEC110@src/frob/app/ticket_runner/_new.py
