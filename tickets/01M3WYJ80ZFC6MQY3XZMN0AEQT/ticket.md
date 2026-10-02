+++
id = "01M3WYJ80ZFC6MQY3XZMN0AEQT"
title = "Wire frob-lease, frob-evidence, frob-tests and frob-ack verbs into the frob binary"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0031"]
labels = ["milestone:2.0.0", "component:frob-bin"]
scope = ["crates/frob/**", "docs/reference/**", "docs/schemas/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ80KZFWBMZRGS901RTA2"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80MB15DKQ823WGQY08T"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80NQWKC2VVY6AFX52KA"

[[acceptance]]
text = "Given the frob binary, when frob --schema work, frob --schema test, frob --schema ack and frob ticket evidence --schema run, then each prints a schema and exits 0"
bound = false

[[acceptance]]
text = "Given a code-type ticket without measured evidence, when ticket close runs, then exit is 3 with the frob test remedy"
bound = false
+++

T-0019, T-0020 and T-0021 each expose a register(cli) function and guard implementations instead of editing crates/frob. This ticket adds the dependencies to crates/frob, calls each register, installs the evidence CloseGuard and the lease LeaseCheck into the ledger verbs, regenerates docs/reference via cargo dev gen, and adds assert_cmd tests that frob work, frob test, frob ack, frob graph and ticket evidence are reachable with --schema.
