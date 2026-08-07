---
id: T-1681
title: Backfill ~122 missing rule ids into docs/modules/gates.md's rule catalog table
state: done
kind: docs
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
docs/modules/gates.md's "Rule catalog" table frames itself as the
exhaustive index of gate rule ids, but a mechanical scan of every
`"XXXX###"`-shaped string literal under src/frob/gates/ found 122 real,
already-fired rule ids missing from that table (found during T-1610's
docs completeness sweep, see docs/audits/docs-completeness-2026-08-06.md
item 2 for the method and representative age evidence).

Every one of these 122 IS documented somewhere else in docs/ (a
per-family module doc) -- this is a discoverability/completeness gap in
the one file that claims to be the catalog, not an undocumented-behavior
gap.

Full missing-id list (grep src/frob/gates/**/*.py for the literal, then
write one accurate one-line "Fails when" row per id, matching the
existing table's style -- read the owning gate's implementation for each
row rather than guessing from the id name):

ARCH102 ARCH103 COMPLIANCE001 COMPLIANCE002 COMPLIANCE003 DEC000 DOC011
FUZZ002 FUZZ003 HOST001 HOST002 KRB001 KRB002 KRB003 KRB004 LANG001
LANG002 LANG003 LINT001 LINT002 LINT003 LINT004 LINT005 PERF002 PERF005
PERF006 PERF007 PERF010 PERF013 PERF014 PII001 PII002 PII003 PII004
PROTO004 REG002 REG003 REG004 REG005 REG006 REG007 REG009 REL220 REL221
REL222 REL230 REL231 REL240 REL241 REL250 REL260 REL261 REL270 REL271
REL272 REL280 REL281 REL290 REL291 REL300 REL301 REL310 REL311 REL320
REL321 REL330 REL331 REL340 REL350 REL351 REL360 REL370 REL371 REL372
REL380 REL381 REL382 REL383 REL390 REL391 REL392 REL393 REL394 REL395
REL396 REL397 RELWAIVE002 RENDER001 SEC004 SEC005 SYS103 SYS105 SYS106
SYS107 SYS201 SYS202 SYS203 SYS204 SYSWAIVE003 TEST009 TEST010 TEST013
TEST014 TEST015 THREAT001 THREAT002 THREAT003 THREAT004 THREAT005 TICK003
TIERBDEMO001 TODO003 VET001 VET002 VET003 VET004 VET005 VET006 VET007
VET008 VET009 VET010 VET011 WAIVE006 WAIVE007

A gate that maintains a rule-catalog table like this one is itself a
candidate for a static completeness check (a gate that greps for rule id
literals in gates/ and diffs against the catalog table) -- worth noting
for whoever picks this up, though that mechanism is T-1611's territory,
not this ticket's.