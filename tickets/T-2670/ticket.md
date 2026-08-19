---
id: T-2670
title: 'docs/modules/gates.md: 80 gate rule ids in the DOCENUM001 member list have
  zero documentation'
state: done
kind: docs
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/gates.md
evidence_scope:
- tests/test_docenum_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_claimed_member_with_no_doc_row_fires_warn
- tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_claimed_member_with_doc_row_does_not_fire
- tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_documented_via_heading_section_does_not_fire
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 9d89369d14716fb953cb3a17d1a23a05614e0bde
---
T-2664 extended DOCENUM001 (src/frob/gates/_docenum.py) to also check,
per claimed member id in the frob:enumerates members="..." list at the
top of docs/modules/gates.md, whether that id resolves to a
documentation row/section anywhere in the same file -- a leading table
cell (| RULEID | ... |, combined cells like DUP001/DUP002 included) or a
#/##/### heading naming the id (combined headings like
"## AFFECT001 AFFECT002 (T-0628)" included).

Measured at introduction: of the 336 members in the current list, 80
have neither shape anywhere in the file:

ARCH101 BUDGET001 BUG003 CAP001 CHECK001 CLAUDE001 COMPLIANCE004
COMPLIANCE006 COMPLIANCE007 CVEFP001 DEAD001 DEBT001 DEBT002 DEBT003
DEC003 DEPLOY001 DEPLOY002 DEPLOY003 DEPR001 DEPR002 DEPR003 DEPR004
DEPR005 DOC003 DOC007 DSL001 E501 EXHAUST003 EXHAUST004 FUZZ001
HOST-BLAST LANG004 LEDGERV1001 PERF001 PERF003 PERF004 PERF008 PERF009
PERF011 PERF012 PORT001-IDENT PORT001-PATH REG001 REG008 REG010 REG011
REG012 REL200 REL201 REL210 REL211 SEC-CVE-FINGERPRINT-001 SYS101 SYS102
SYS108 SYS110 SYS111 SYS112 SYS200 SYS205 SYSWAIVE002 TEST008 TEST012
TEST016 THREAT006 TICK001 TICK002 TICK004 TICK005 VET-JS VET-JS003
VET-JS004 VET-PY001 VET-PY002 VET-PY003 VET-RS001 VET-RS002
VET-SOURCE-UNAVAILABLE VET-TIMEOUT WAIVE008

The new check reports these at WARN severity specifically so this
existing backlog does not redden main (see docs/modules/gates.md's
DOCENUM001 section, T-2664 addendum). This ticket tracks writing a real
table row or prose section for each -- not a bare id restating the name,
a genuine "fails when" description like the rest of the catalog -- so
the WARN count can eventually go to zero and this note itself is
resolved. Some ids above may turn out to already be covered by a
combined table row this batch's grep-based detector could not resolve
(e.g. prose sentences that mention an id inline without a leading table
cell or heading) -- verify per id, do not assume every listed id needs a
brand new row.

Filed per T-2664's own instruction to file the backlog separately rather
than force it through as a blocking gate.