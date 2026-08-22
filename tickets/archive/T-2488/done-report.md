## Done report

Changed:
docs/design/registry/capability-via-ratchet.lock.json (6 entries: 4
bumped, 2 newly added)

Evidence:
cmd:bash /tmp/t2488_verify.sh exit=0 sha256=df7a93730321
(re-runs `frob check --only sys` and asserts zero SYS111 hits)

Filed:
T-2490 (SYS100: T-2411's own new wiring test in
tests/test_lang_conformance_gate.py uses subprocess.run without a
declared testsuite::exec via-site for that file -- found while
measuring this ticket, out of this ticket's own scope, filed rather
than fixed inline)

Gates: `frob check --only sys` shows zero SYS111 hits after this edit
(was 6 before). The 5 SYS100 hits visible in the same run are the
pre-existing T-2411 gap now tracked as T-2490, unrelated to this
ticket's own scope (docs/design/registry/capability-via-ratchet.lock.json
only).

Summary: SELFAUDIT001/SYS111 was firing 6 times because two already-
landed tickets (T-2482, T-2464) each declared new capability grants in
design/frob.strata without bumping the ratchet lock in the same diff --
the same "ratchet fell behind" pattern T-2460 fixed once before.

Attribution method (per the T-2460 discipline): diffed
design/frob.strata's via-list SETS across git history using `git log -S
<filename> -- design/frob.strata` per new filename, not assumed from
ticket titles:

- gates::fs.read 47->48: T-2482 added src/frob/gates/_waive_audit_watermark.py
- testsuite::exec 186->188: T-2482 added tests/unit/gates/test_rel001_deferred_bump.py, tests/unit/test_waive_audit_runner.py
- testsuite::fs.read 132->134: T-2482 added tests/unit/test_waive_audit_runner.py, tests/unit/test_waive_audit_watermark.py
- testsuite::fs.write 348->351: T-2482 added tests/unit/gates/test_rel001_deferred_bump.py, tests/unit/test_waive_audit_runner.py, tests/unit/test_waive_audit_watermark.py
- stratamod::net.connect 0->1 (brand-new capability kind, no prior lock entry): T-2482 added src/frob/strata/_threat_catalog_benign.py
- testsuite::net-mutate 0->1 (brand-new capability kind, no prior lock entry): T-2464 added tests/test_capability_registry.py

Every added filename was confirmed against the actual declaring commit's
diff (`git show <sha> -- design/frob.strata`), not just a `-S` hit --
T-2482's own commit message ("Declare fs.read/fs.write/exec for
T-2467's waive-audit module+tests") and T-2464's own in-file comment
("TestNetMutateVerbSplit's own fire fixtures contain real
requests.post(/httpx.delete( needle literals, proving the new
net-mutate split actually fires") both confirm genuine, reasoned
declarations, not accidental ones. T-2482 alone contributes to 5 of the
6 entries (one ticket, multiple capability grants across the files it
added -- explaining the coordinator's "multiple contributors per entry"
expectation as multiple CAPABILITIES per file within one ticket, not
multiple tickets per entry); T-2464 contributes the sixth
(testsuite::net-mutate) alone.

Both brand-new ceiling=0 entries (stratamod::net.connect,
testsuite::net-mutate) were verified genuine before ratcheting, per the
coordinator's explicit caution: read the declaring code directly in
both cases (not just the via-list literal) and confirmed each is a real
capability use tied to a real fixture/module, not a stray or mistaken
declaration.

Ceilings set to exactly the current measured count in every case (48,
188, 134, 351, 1, 1) -- no padding beyond genuinely-attributed growth.

### Changed
```
 tickets/T-2488/ticket.md | 16 ++++++++++++++--
 1 file changed, 14 insertions(+), 2 deletions(-)
```

### Evidence
- `cmd:bash /tmp/t2488_verify.sh exit=0 sha256=df7a93730321` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t2488-ratchet/src/frob/app/ticket_runner/_waive_audit.py, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
